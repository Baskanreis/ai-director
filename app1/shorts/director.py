"""Professional AI Shorts Director — candidate extraction and editorial planning.

No claim of guaranteed virality is made. The score optimizes observable editorial
signals associated with short-form watchability: early promise, narrative payoff,
context completeness, emotional change, pacing and rewatch cues.
"""
from __future__ import annotations
import re
from dataclasses import replace
from typing import Iterable, Sequence
from app.subtitle.models import Transcript, Segment
from app.shorts.models import ShortsCandidate, ShortsPlan, CaptionCue, BrollCue, ReframeCue

_HOOK = {"nasıl","neden","ama","fakat","sonunda","gizli","gerçekten","asla","ilk","son","inanılmaz","imkansız","şok","şaşırtıcı","denedik","başardık","kaybettik","kazandık","meğer","aslında","bakın"}
_PAYOFF = {"sonuç","sonunda","işte","oldu","başardık","kazandık","kaybettik","çıktı","anladım","öğrendim","meğer","asıl","cevap","gerçek"}
_EMOTION = {"korku","şaşır","şaşırtıcı","inanılmaz","mutlu","üzgün","sinir","komik","gül","ağla","şok","heyecan","başar","kaybet","kazand","sevindim"}
_BROLL = {"telefon","araba","ev","para","harita","ekran","grafik","istatistik","fotoğraf","kamera","oyun","site","uygulama","şehir","ülke","ürün","masa","yemek"}
_STOP = {"ve","bir","bu","şu","o","da","de","ile","için","gibi","ama","çok","daha","olan","olanı","ben","sen","biz","siz"}

def _tokens(text: str) -> list[str]:
    return re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+", (text or "").lower())

def _signal(text: str, terms: set[str]) -> int:
    toks = set(_tokens(text)); return sum(1 for t in terms if t in toks)

def _text_between(segments: Sequence[Segment], start: float, end: float) -> str:
    return " ".join(s.text.strip() for s in segments if s.end > start and s.start < end and s.text.strip()).strip()

def _window_segments(segments: Sequence[Segment], start_idx: int, max_duration: float) -> tuple[int,int]:
    start = segments[start_idx].start; end_i = start_idx
    while end_i + 1 < len(segments) and segments[end_i + 1].end - start <= max_duration:
        end_i += 1
    return start_idx, end_i

def extract_candidates(transcript: Transcript, min_duration: float = 12.0, max_duration: float = 58.0, limit: int = 12) -> list[ShortsCandidate]:
    """Create ranked, context-safe candidate windows from a transcript."""
    segs = sorted([s for s in transcript.segments if s.end > s.start], key=lambda s:s.start)
    if not segs: return []
    candidates: list[ShortsCandidate] = []
    for i, seg in enumerate(segs):
        a,b = _window_segments(segs, i, max_duration)
        if b <= i: continue
        start,end = segs[a].start,segs[b].end
        if end-start < min_duration: continue
        # Prefer a strong early sentence, then a later payoff within the same window.
        hook_seg = max(segs[i:b+1], key=lambda s: (0.55*_signal(s.text,_HOOK)+0.25*min(2, sum(c.isdigit() for c in s.text))*8+0.20*(12 if '?' in s.text else 0)))
        payoff_seg = max(segs[i:b+1], key=lambda s: (0.65*_signal(s.text,_PAYOFF)+0.35*_signal(s.text,_EMOTION)))
        full = _text_between(segs,start,end)
        hook = min(100.0, 38 + _signal(hook_seg.text,_HOOK)*10 + (12 if '?' in hook_seg.text else 0) + (8 if any(c.isdigit() for c in hook_seg.text) else 0))
        payoff = min(100.0, 35 + _signal(payoff_seg.text,_PAYOFF)*12 + _signal(payoff_seg.text,_EMOTION)*6)
        context = min(100.0, 58 + (18 if i == 0 or segs[i].start <= start + 1 else 0) + min(24, len(_tokens(full)) / 7))
        emotion = min(100.0, 30 + _signal(full,_EMOTION)*7 + min(25, abs(_signal(hook_seg.text,_EMOTION)-_signal(payoff_seg.text,_EMOTION))*8))
        wpm = len(_tokens(full)) / max((end-start)/60, 0.1)
        pacing = 100 - min(55, abs(wpm-150)*0.42) - (15 if end-start > 55 else 0)
        rewatch = min(100.0, 45 + (15 if '?' in hook_seg.text else 0) + (15 if hook_seg.text.strip().lower()[:12] in full.lower() else 0) + min(25, _signal(full,_HOOK)*5))
        tags=[]
        if hook >= 70: tags.append("strong_hook")
        if payoff >= 65: tags.append("clear_payoff")
        if _signal(full,_BROLL): tags.append("broll_ready")
        if '?' in hook_seg.text: tags.append("curiosity")
        candidates.append(ShortsCandidate(
            id=f"short-{len(candidates)+1:03d}", source_start=round(start,3), source_end=round(end,3),
            hook_start=round(hook_seg.start,3), hook_end=round(hook_seg.end,3),
            payoff_start=round(payoff_seg.start,3), payoff_end=round(payoff_seg.end,3),
            hook_score=round(hook,2), payoff_score=round(payoff,2), context_score=round(context,2),
            emotion_score=round(emotion,2), pacing_score=round(max(0,pacing),2), rewatch_score=round(rewatch,2),
            text=full[:600], reason="Hook→build-up→payoff yapısı, bağlam bütünlüğü ve pacing sinyalleri birlikte değerlendirildi.", tags=tuple(tags)))
    # Diversity-aware ranking: near-duplicates are suppressed.
    candidates.sort(key=lambda c:(-c.score, c.source_start))
    chosen=[]
    for c in candidates:
        if any(abs(c.source_start-x.source_start)<7 or abs(c.payoff_start-x.payoff_start)<5 for x in chosen): continue
        chosen.append(c)
        if len(chosen)>=limit: break
    return chosen

def build_plan(candidate: ShortsCandidate, transcript: Transcript | None = None, target: str = "youtube_shorts", face_track: Sequence[tuple[float,float,float]] | None = None, beat_times: Sequence[float] | None = None) -> ShortsPlan:
    segs = transcript.segments if transcript else []
    captions=[]; broll=[]
    if transcript:
        for s in segs:
            if s.end <= candidate.source_start or s.start >= candidate.source_end: continue
            a=max(candidate.source_start,s.start); b=min(candidate.source_end,s.end)
            words=_tokens(s.text); emphasis=tuple(dict.fromkeys(w for w in words if len(w)>=5 and w not in _STOP))[:3]
            captions.append(CaptionCue(round(a,3),round(b,3),s.text.strip(),emphasis,"dynamic_bold","lower_safe"))
            hits=[x for x in _BROLL if x in set(words)]
            if hits: broll.append(BrollCue(round(a,3),round(b,3),hits[0],min(100,55+len(hits)*10),"Konuşulan somut nesne/konu için cutaway adayı."))
    reframes=[]
    track = list(face_track or [])
    if track:
        for t,x,y in track:
            if candidate.source_start <= t <= candidate.source_end:
                reframes.append(ReframeCue(round(t,3),max(0,min(1,x)),max(0,min(1,y)),1.0,"tracked_subject","speaker/face tracking"))
    else:
        # Center-safe 9:16 crop: editorial fallback, not fake computer vision.
        reframes=[ReframeCue(round(candidate.source_start,3),0.5,0.5,1.08,"main_subject","9:16 safe-center fallback")]
    punch=[]
    for t in (candidate.hook_start,candidate.payoff_start):
        if candidate.source_start <= t <= candidate.source_end:
            punch.append(ReframeCue(round(t,3),0.5,0.5,1.055,"main_subject","narrative emphasis punch-in"))
    silence=[]
    if transcript:
        words=sorted(transcript.all_words(),key=lambda w:w.start)
        prev=None
        for w in words:
            if w.end <= candidate.source_start or w.start >= candidate.source_end: continue
            if prev and w.start-prev.end >= .42:
                silence.append((round(max(candidate.source_start,prev.end),3),round(min(candidate.source_end,w.start),3)))
            prev=w
    beats=tuple(round(float(t),3) for t in (beat_times or []) if candidate.source_start<t<candidate.source_end)
    return ShortsPlan("",target,round(candidate.duration,3),candidate.id,candidate.score,candidate.source_start,candidate.source_end,tuple(reframes),tuple(captions),tuple(broll),tuple(punch),tuple(silence),beats,("Virallik garanti edilmez; plan retention/watchability sinyallerini optimize eder.","Aşırı zoom/cut yoğunluğu bilinçli olarak sınırlandırıldı."))
