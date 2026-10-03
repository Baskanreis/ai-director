"""Auto Director engine — v1.5.

Bu modül, düşük seviyeli AI önerilerini tek bir edit kararına dönüştürür.
İlk sürüm deterministiktir: LLM zorunlu değildir ve kararların tamamı
gerekçesi/confidence alanlarıyla dışarı aktarılabilir.

Hedef: ileride kanal analizi, referans video analizi ve model tabanlı karar
verme eklendiğinde değişmeyecek bir "Director Contract" oluşturmak.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Iterable

from .models import AnalysisReport, CUT_KINDS, Suggestion, SuggestionKind
from app.subtitle.models import Transcript

class EditProfile(str, Enum):
    YOUTUBE_LONGFORM = "youtube_longform"
    SHORTS = "shorts"
    TIKTOK = "tiktok"
    INSTAGRAM_REEL = "instagram_reel"
    HIGH_RETENTION = "high_retention"

@dataclass(frozen=True)
class DirectorPolicy:
    """Bir kanal/format için kurgu davranış sözleşmesi."""

    profile: EditProfile
    max_pause: float
    aggressive_pause: float
    filler_confidence: float
    repetition_confidence: float
    silence_confidence: float
    preserve_min_gap: float
    max_cut_ratio: float
    highlight_words: int
    description: str

POLICIES = {
    EditProfile.YOUTUBE_LONGFORM: DirectorPolicy(
        EditProfile.YOUTUBE_LONGFORM, 1.6, 2.8, .90, .86, .78, .18, .18, 12,
        "Uzun videoda doğal konuşmayı koruyan, gereksiz boşlukları temizleyen kurgu."
    ),
    EditProfile.SHORTS: DirectorPolicy(
        EditProfile.SHORTS, .65, 1.25, .95, .92, .88, .10, .28, 8,
        "Kısa formda yüksek tempo; fakat anlam taşıyan duraklamaları korur."
    ),
    EditProfile.TIKTOK: DirectorPolicy(
        EditProfile.TIKTOK, .55, 1.10, .95, .94, .90, .08, .30, 8,
        "TikTok için sıkı pacing, hızlı giriş ve gereksiz tekrar temizliği."
    ),
    EditProfile.INSTAGRAM_REEL: DirectorPolicy(
        EditProfile.INSTAGRAM_REEL, .65, 1.25, .94, .92, .88, .10, .28, 8,
        "Reels için hızlı fakat konuşmanın doğal ritmini koruyan kurgu."
    ),
    EditProfile.HIGH_RETENTION: DirectorPolicy(
        EditProfile.HIGH_RETENTION, .50, 1.00, .96, .95, .91, .08, .32, 10,
        "Yüksek retention hedefli agresif kurgu; güvenlik sınırları korunur."
    ),
}

@dataclass
class DirectorDecision:
    kind: str
    start: float
    end: float
    confidence: float
    accepted: bool
    reason: str
    risk: str = "low"

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

class EditEventKind(str, Enum):
    HOOK = "hook"
    BEAT = "beat"
    PATTERN_BREAK = "pattern_break"
    BROLL_CUE = "broll_cue"
    EMPHASIZE = "emphasize"


@dataclass
class DirectorEvent:
    kind: str
    start: float
    end: float
    score: float
    reason: str
    payload: dict = field(default_factory=dict)


@dataclass
class DirectorPlan:
    profile: str
    source_duration: float
    estimated_final_duration: float
    cut_seconds: float
    cut_ratio: float
    pacing_score: float
    decisions: list[DirectorDecision] = field(default_factory=list)
    events: list[DirectorEvent] = field(default_factory=list)
    highlight_words: list[str] = field(default_factory=list)
    chapters: list[dict] = field(default_factory=list)
    hook_score: float = 0.0
    narrative_score: float = 0.0
    metadata: dict = field(default_factory=dict)

    def accepted_decisions(self) -> list[DirectorDecision]:
        return [d for d in self.decisions if d.accepted]

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

def _duration(transcript: Transcript | None, report: AnalysisReport) -> float:
    if transcript and transcript.segments:
        return max((s.end for s in transcript.segments), default=0.0)
    return max((s.end for s in report.suggestions), default=0.0)

def _overlap(a: tuple[float,float], b: tuple[float,float]) -> bool:
    return a[0] < b[1] and b[0] < a[1]

def _merge_ranges(items: Iterable[tuple[float,float]]) -> list[tuple[float,float]]:
    out=[]
    for s,e in sorted(items):
        if e <= s: continue
        if out and s <= out[-1][1] + .02:
            out[-1]=(out[-1][0], max(out[-1][1],e))
        else: out.append((s,e))
    return out

def _pacing_score(duration: float, cuts: float, profile: DirectorPolicy) -> float:
    if duration <= 0: return 0.0
    ratio=cuts/duration
    # Sağlıklı aralıkta 100'e yaklaşır; aşırı kesim cezalandırılır.
    target = profile.max_cut_ratio * .55
    if ratio > profile.max_cut_ratio:
        return max(0.0, 100.0 - (ratio-profile.max_cut_ratio)*300.0)
    distance=abs(ratio-target)
    return max(0.0, 100.0 - distance*180.0)

_HOOK_TERMS = {"nasıl", "neden", "sonunda", "ama", "fakat", "inanılmaz", "imkansız", "ilk", "son", "gizli", "gerçekten", "asla", "şok", "şaşırtıcı", "denedik", "başardık", "kaybettik", "kazandık"}
_TRANSITION_TERMS = {"şimdi", "sonra", "ardından", "fakat", "ama", "çünkü", "bu yüzden", "sonunda", "önce", "gelelim", "asıl", "burada", "peki"}
_BROLL_TERMS = {"ürün", "telefon", "araba", "ev", "para", "harita", "ekran", "grafik", "istatistik", "fotoğraf", "kamera", "oyun", "site", "uygulama", "şehir", "ülke"}

def _tokens(text: str) -> list[str]:
    return re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+", text.lower())

def _narrative_events(transcript: Transcript | None, profile: EditProfile) -> tuple[list[DirectorEvent], float, float]:
    if not transcript or not transcript.segments:
        return [], 0.0, 0.0
    events: list[DirectorEvent] = []
    early = [seg for seg in transcript.segments if seg.start < 30.0]
    hook_candidates = []
    for seg in early:
        toks = _tokens(seg.text or "")
        hits = [x for x in _HOOK_TERMS if x in toks]
        numbers = sum(any(c.isdigit() for c in x) for x in toks)
        questions = sum("?" in (seg.text or "") for _ in [0])
        score = min(100.0, 36.0 + len(hits) * 9 + numbers * 8 + questions * 12)
        if score >= 45:
            hook_candidates.append((score, seg, hits))
    hook_candidates.sort(key=lambda x: (-x[0], x[1].start))
    if hook_candidates:
        score, seg, hits = hook_candidates[0]
        events.append(DirectorEvent(EditEventKind.HOOK.value, seg.start, seg.end, score, "İlk 30 saniyede güçlü merak/vaat sinyali.", {"signals": hits}))
    hook_score = max((x[0] for x in hook_candidates), default=0.0)
    durations = sorted(max(seg.duration, .01) for seg in transcript.segments)
    median = durations[len(durations)//2] if durations else 1.0
    for seg in transcript.segments:
        text = (seg.text or "").strip()
        toks = _tokens(text)
        transitions = [x for x in _TRANSITION_TERMS if x in toks]
        if transitions:
            events.append(DirectorEvent(EditEventKind.BEAT.value, seg.start, seg.end, min(100.0, 50 + len(transitions)*12), "Anlatı geçişi/konu ilerlemesi tespit edildi.", {"signals": transitions[:4]}))
        if seg.duration > max(3.0, median * 2.2):
            events.append(DirectorEvent(EditEventKind.PATTERN_BREAK.value, seg.start, seg.end, 72.0, "Uzun konuşma bloğu; pattern-break veya B-roll için uygun.", {"suggestion": "broll_or_cutaway"}))
        broll = [x for x in _BROLL_TERMS if x in toks]
        if broll:
            events.append(DirectorEvent(EditEventKind.BROLL_CUE.value, seg.start, seg.end, min(95.0, 55 + len(broll)*10), "Somut görsel öğe geçtiği için B-roll adayı.", {"subjects": broll[:5]}))
    beats = sum(e.kind == EditEventKind.BEAT.value for e in events)
    breaks = sum(e.kind == EditEventKind.PATTERN_BREAK.value for e in events)
    narrative = min(100.0, 35.0 + min(40.0, beats*4.0) + min(25.0, breaks*5.0))
    if profile in (EditProfile.SHORTS, EditProfile.TIKTOK, EditProfile.INSTAGRAM_REEL, EditProfile.HIGH_RETENTION):
        narrative = min(100.0, narrative + 5.0)
    return events, round(hook_score, 2), round(narrative, 2)

def _select_cut_budget(decisions: list[DirectorDecision], duration: float, policy: DirectorPolicy) -> list[DirectorDecision]:
    if duration <= 0:
        return decisions
    budget = duration * policy.max_cut_ratio
    used = 0.0
    for d in sorted(decisions, key=lambda x: (-x.confidence, x.start)):
        if d.accepted and used + d.duration > budget:
            d.accepted = False
            d.risk = "medium"
            d.reason += " Otomatik kesim bütçesi dolduğu için sonraki inceleme turuna bırakıldı."
        elif d.accepted:
            used += d.duration
    return decisions


def build_director_plan(
    report: AnalysisReport,
    transcript: Transcript | None = None,
    profile: EditProfile = EditProfile.YOUTUBE_LONGFORM,
    bpm: float | None = None,
    beat_times: list[float] | None = None,
) -> DirectorPlan:
    """Analiz raporundan güvenlik sınırları olan otomatik kurgu planı üretir."""
    policy=POLICIES[profile]
    duration=_duration(transcript, report)
    raw=[]
    for s in report.suggestions:
        if s.kind not in CUT_KINDS or s.end <= s.start:
            continue
        if s.kind == SuggestionKind.LONG_PAUSE:
            conf = .97 if s.duration >= policy.aggressive_pause else (
                .90 if s.duration >= policy.max_pause else .35
            )
            reason=f"{s.duration:.1f}s duraklama; profil eşiği {policy.max_pause:.1f}s"
        elif s.kind == SuggestionKind.FILLER_WORD:
            conf=policy.filler_confidence
            reason="Dolgu kelime; konuşmanın anlamını değiştirmeden çıkarılabilir."
        elif s.kind == SuggestionKind.REPETITION:
            conf=policy.repetition_confidence
            reason="Yakın tekrar/kekeleme tespit edildi; ilk söyleyiş korunur."
        else:
            conf=policy.silence_confidence
            reason="Ses seviyesi düşük; otomatik kesim adayı."
        # Çok kısa/çok uzun kesimleri korumacı ele al.
        risk="low"
        accepted=conf >= .75
        if s.duration > 5.0:
            accepted=False; conf=min(conf,.55); risk="high"
            reason += " Uzun aralık olduğu için otomatik kesim kilitlendi."
        raw.append(DirectorDecision(s.kind.value,s.start,s.end,conf,accepted,reason,risk))

    # Çakışan kararları tek bir kesime indir; toplam süreyi abartma.
    accepted_ranges=[]
    decisions=[]
    for d in sorted(raw,key=lambda x:(x.start,x.end)):
        if not d.accepted: decisions.append(d); continue
        if any(_overlap((d.start,d.end), r) for r in accepted_ranges):
            d.accepted=False
            d.reason += " Başka bir kesimle çakıştığı için birleştirilmiş kesime bırakıldı."
            decisions.append(d)
        else:
            accepted_ranges.append((d.start,d.end)); decisions.append(d)

    decisions = _select_cut_budget(decisions, duration, policy)
    accepted_ranges = [(d.start,d.end) for d in decisions if d.accepted]
    merged=_merge_ranges(accepted_ranges)
    cut=sum(e-s for s,e in merged)
    ratio=cut/duration if duration else 0.0

    highlights=[]
    if transcript:
        # Analyzer'ın önerdiği kelimeler varsa onları kullan; yoksa basit içerik kelime frekansı.
        highlights=[s.word for s in report.suggestions
                    if s.kind==SuggestionKind.HIGHLIGHT_WORD and s.word][:policy.highlight_words]
        if not highlights:
            stop={"ve","bir","bu","şu","o","da","de","ile","için","gibi","ama","çok","daha","olan"}
            words=[]
            for w in transcript.all_words():
                x=re.sub(r"[^\wçğıöşüÇĞİÖŞÜ]","",w.text.lower())
                if len(x)>=5 and x not in stop: words.append(x)
            highlights=[w for w,_ in Counter(words).most_common(policy.highlight_words)]

    chapters=[]
    if transcript:
        for i,seg in enumerate(transcript.segments):
            txt=(seg.text or "").strip()
            if txt and (i==0 or len(txt)>=45):
                chapters.append({"time":round(seg.start,2),"title":txt[:70]})
    chapters=chapters[:30]

    events, hook_score, narrative_score = _narrative_events(transcript, profile)

    meta={
        "director_version":"1.6",
        "decision_passes":["cut_safety", "narrative_structure", "hook_detection", "broll_cues"],
        "profile_description":policy.description,
        "automation":"deterministic",
        "safety_note":"Confidence < 0.75 or risk=high is not auto-applied.",
    }
    # v2.6: Sync is attached to the plan as metadata, keeping the DirectorPlan
    # contract backwards compatible while making beat/motion decisions available
    # to the existing exporter/apply layer.
    try:
        from .beat_sync import build_edit_sync_plan
        sync = build_edit_sync_plan(
            [d.start for d in decisions if d.accepted],
            duration,
            bpm=bpm,
            events=[asdict(e) for e in events],
            profile=profile.value,
            beat_times=beat_times,
        )
        meta["edit_sync"] = sync
    except Exception as exc:  # sync must never break core Director planning
        meta["edit_sync_error"] = str(exc)
    return DirectorPlan(
        profile=profile.value,
        source_duration=round(duration,3),
        estimated_final_duration=round(max(0,duration-cut),3),
        cut_seconds=round(cut,3),
        cut_ratio=round(ratio,4),
        pacing_score=round(_pacing_score(duration,cut,policy),2),
        decisions=decisions,
        events=events,
        highlight_words=highlights,
        chapters=chapters,
        hook_score=hook_score,
        narrative_score=narrative_score,
        metadata=meta,
    )

def adapt_plan_to_channel(plan: DirectorPlan, channel_profile) -> DirectorPlan:
    """Kanal DNA'sını mevcut planın event kararlarına düşük riskli şekilde uygular.

    Bu fonksiyon timeline'ı doğrudan değiştirmez; yalnızca DirectorPlan metadata'sını
    ve öncelik skorlarını zenginleştirir. Böylece kullanıcı önce farkı görebilir,
    sonra apply katmanında güvenli bir ikinci pass çalıştırabilir.
    """
    from dataclasses import replace
    recommendations = []
    if plan.cut_ratio < channel_profile.avg_cut_ratio - 0.03:
        recommendations.append("increase_cut_density")
    elif plan.cut_ratio > channel_profile.avg_cut_ratio + 0.03:
        recommendations.append("reduce_cut_density")
    if plan.hook_score < channel_profile.avg_hook_score - 8:
        recommendations.append("strengthen_hook")
    if plan.narrative_score < channel_profile.avg_narrative_score - 8:
        recommendations.append("increase_narrative_beats")
    target_broll = channel_profile.avg_broll_cues_per_minute
    current_broll = (sum(e.kind == EditEventKind.BROLL_CUE.value for e in plan.events) /
                     (plan.source_duration / 60.0)) if plan.source_duration > 0 else 0.0
    if current_broll < target_broll - 0.8:
        recommendations.append("add_broll_cues")
    metadata = dict(plan.metadata)
    metadata["channel_intelligence"] = {
        "channel": channel_profile.name,
        "confidence": channel_profile.confidence,
        "recommendations": recommendations,
    }
    return replace(plan, metadata=metadata)

def apply_director_plan(report: AnalysisReport, plan: DirectorPlan) -> int:
    """Planı report üzerine geri yazar; mevcut apply katmanı tek kaynak olarak kalır."""
    accepted={(round(d.start,4),round(d.end,4),d.kind) for d in plan.accepted_decisions()}
    changed=0
    for s in report.suggestions:
        key=(round(s.start,4),round(s.end,4),s.kind.value)
        if s.kind in CUT_KINDS:
            new=s.accepted and key in accepted
            if s.accepted != new:
                s.accepted=new; changed+=1
    return changed

__all__=["EditProfile","DirectorPolicy","DirectorDecision","DirectorEvent","EditEventKind", "DirectorPlan","POLICIES", "build_director_plan","adapt_plan_to_channel","apply_director_plan"]
