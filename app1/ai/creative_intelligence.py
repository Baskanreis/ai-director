"""Creative editing intelligence — v2.27.

Content-aware editing policy. It classifies the editorial intent of a source and
turns it into a deterministic, inspectable style contract. The contract is not
an ML claim: it is a safe policy layer that can later be calibrated by user
feedback/reference videos.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import re
from typing import Iterable

from app.subtitle.models import Transcript
from .models import AnalysisReport


class CreativeGenre(str, Enum):
    EDUCATIONAL = "educational"
    ENTERTAINMENT = "entertainment"
    HORROR = "horror"
    DOCUMENTARY = "documentary"
    COMMENTARY = "commentary"
    GAMING = "gaming"
    VLOG = "vlog"
    PODCAST = "podcast"
    TUTORIAL = "tutorial"
    REVIEW = "review"
    TECH = "tech"
    SPORTS = "sports"
    TRAVEL = "travel"
    COMEDY = "comedy"
    CINEMATIC = "cinematic"
    NEWS = "news"
    STORYTELLING = "storytelling"
    MUSIC = "music"
    INTERVIEW = "interview"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CreativeStyle:
    genre: CreativeGenre
    pacing: str
    cut_aggression: float
    transition_density: float
    motion_density: float
    caption_style: str
    color_mood: str
    sound_design: str
    broll_density: float
    silence_policy: str
    hook_style: str
    camera_language: str
    effect_budget: float
    avoid: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class CreativeDecision:
    kind: str
    preset: str
    start: float
    end: float
    intensity: float
    reason: str
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CreativeDirection:
    primary: CreativeStyle
    alternatives: list[CreativeStyle] = field(default_factory=list)
    decisions: list[CreativeDecision] = field(default_factory=list)
    signals: dict[str, float] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "primary": self.primary.to_dict(),
            "alternatives": [x.to_dict() for x in self.alternatives],
            "decisions": [x.to_dict() for x in self.decisions],
            "signals": self.signals,
            "metadata": self.metadata,
        }


# Compact, editable editorial knowledge base. Values are deliberately bounded so
# genre detection changes style, not safety/quality gates.
_STYLE = {
    CreativeGenre.EDUCATIONAL: CreativeStyle(CreativeGenre.EDUCATIONAL,"clear",.32,.22,.28,"clean_emphasis","neutral_warm","subtle",.35,"preserve_meaningful","question_then_answer","stable",.35,("overediting","constant_zoom","loud_sfx")),
    CreativeGenre.TUTORIAL: CreativeStyle(CreativeGenre.TUTORIAL,"structured",.38,.25,.35,"step_by_step","neutral","ui_clicks",.55,"trim_dead_air","problem_solution","screen_focus",.42,("flashy_transitions",)),
    CreativeGenre.ENTERTAINMENT: CreativeStyle(CreativeGenre.ENTERTAINMENT,"fast",.72,.68,.72,"dynamic_pop","vibrant","punchy",.65,"tight_but_contextual","cold_open","active",.75,("long_static_gaps",)),
    CreativeGenre.COMEDY: CreativeStyle(CreativeGenre.COMEDY,"fast_comedic",.78,.72,.78,"meme_dynamic","vibrant","comic_hits",.70,"preserve_timing","setup_punchline","reactive",.82,("cutting_the_punchline",)),
    CreativeGenre.HORROR: CreativeStyle(CreativeGenre.HORROR,"controlled",.42,.30,.52,"minimal","dark_cinematic","tension_risers",.42,"protect_silence","slow_reveal","restrained",.68,("random_whooshes","overbright_color","constant_music")),
    CreativeGenre.DOCUMENTARY: CreativeStyle(CreativeGenre.DOCUMENTARY,"measured",.30,.25,.35,"editorial","cinematic_neutral","atmospheric",.72,"protect_narration","context_first","observational",.48,("trend_effects",)),
    CreativeGenre.COMMENTARY: CreativeStyle(CreativeGenre.COMMENTARY,"medium_fast",.55,.48,.50,"speaker_dynamic","balanced","light_punch",.45,"remove_dead_air","strong_claim","speaker_first",.58,("overlong_broll",)),
    CreativeGenre.GAMING: CreativeStyle(CreativeGenre.GAMING,"fast_reactive",.78,.70,.76,"gaming_hud","vibrant","arcade_reactive",.75,"tight_reactions","best_moment","screen_plus_face",.82,("blocking_gameplay",)),
    CreativeGenre.VLOG: CreativeStyle(CreativeGenre.VLOG,"natural",.42,.34,.42,"casual","natural","ambient_plus_music",.65,"keep_personality","day_in_life","observational",.50,("overpolish",)),
    CreativeGenre.PODCAST: CreativeStyle(CreativeGenre.PODCAST,"conversation",.28,.20,.25,"speaker_clean","natural","very_subtle",.30,"protect_conversation","strong_quote","speaker_focus",.28,("constant_cuts",)),
    CreativeGenre.REVIEW: CreativeStyle(CreativeGenre.REVIEW,"medium",.50,.40,.48,"product_callout","accurate","interface_sfx",.68,"trim_repetition","verdict_tease","product_focus",.55,("misleading_visuals",)),
    CreativeGenre.TECH: CreativeStyle(CreativeGenre.TECH,"precise",.44,.36,.42,"technical_callout","cool_clean","digital_subtle",.72,"preserve_numbers","problem_first","screen_product",.52,("visual_noise",)),
    CreativeGenre.SPORTS: CreativeStyle(CreativeGenre.SPORTS,"reactive",.82,.74,.82,"scoreboard","high_contrast","impact_sync",.82,"cut_on_action","moment_first","action_tracking",.86,("missing_context",)),
    CreativeGenre.TRAVEL: CreativeStyle(CreativeGenre.TRAVEL,"flowing",.46,.38,.55,"location_clean","cinematic_warm","ambient_cinematic",.88,"preserve_atmosphere","destination_tease","establishing",.62,("too_many_sfx",)),
    CreativeGenre.CINEMATIC: CreativeStyle(CreativeGenre.CINEMATIC,"deliberate",.24,.18,.34,"minimal","cinematic","cinematic_atmos",.60,"protect_pauses","visual_tease","cinematic",.72,("template_feel",)),
    CreativeGenre.NEWS: CreativeStyle(CreativeGenre.NEWS,"tight_clear",.58,.44,.46,"lower_third","neutral","restrained",.45,"remove_dead_air","fact_first","stable",.38,("sensational_effects",)),
    CreativeGenre.STORYTELLING: CreativeStyle(CreativeGenre.STORYTELLING,"arc_driven",.40,.30,.48,"narrative_emphasis","story_cinematic","emotional",.58,"protect_beats","curiosity_gap","motivated",.60,("random_cuts",)),
    CreativeGenre.MUSIC: CreativeStyle(CreativeGenre.MUSIC,"beat_locked",.75,.70,.78,"lyric_sync","artist_driven","beat_synced",.55,"follow_music","musical_hook","rhythmic",.82,("offbeat_transitions",)),
    CreativeGenre.INTERVIEW: CreativeStyle(CreativeGenre.INTERVIEW,"natural",.34,.24,.30,"speaker_clean","natural","subtle",.45,"protect_answers","quote_hook","speaker_first",.32,("cutting_breaths_too_aggressively",)),
}

_KEYWORDS = {
    CreativeGenre.EDUCATIONAL: {"öğren","eğitim","ders","bilgi","anlatacağım","neden","nasıl çalışır","tarih","bilim"},
    CreativeGenre.TUTORIAL: {"nasıl yapılır","adım","adım adım","kurulum","ayar","rehber","tutorial","yapmak","şuraya tıkla"},
    CreativeGenre.ENTERTAINMENT: {"eğlence","challenge","meydan okuma","denedik","şaka","inanılmaz","reaksiyon","yarış"},
    CreativeGenre.HORROR: {"korku","korkunç","cin","hayalet","gece","karanlık","lanet","tekinsiz","dehşet","gerilim"},
    CreativeGenre.DOCUMENTARY: {"belgesel","araştırma","arşiv","tarihçe","inceleme","kaynaklara göre"},
    CreativeGenre.COMMENTARY: {"yorum","bence","düşünüyorum","eleştiri","gündem","yorumlayalım"},
    CreativeGenre.GAMING: {"oyun","gameplay","minecraft","valorant","fortnite","boss","level","maç"},
    CreativeGenre.VLOG: {"bugün","günüm","vlog","benimle","geziyoruz","gittik"},
    CreativeGenre.PODCAST: {"podcast","sohbet","konuğumuz","mikrofon","bölüm"},
    CreativeGenre.REVIEW: {"inceleme","review","artıları","eksileri","puan","fiyat","deneyim"},
    CreativeGenre.TECH: {"teknoloji","işlemci","ekran kartı","telefon","laptop","yazılım","uygulama","kod"},
    CreativeGenre.SPORTS: {"futbol","basketbol","gol","maç","skor","takım","oyuncu","şampiyona"},
    CreativeGenre.TRAVEL: {"seyahat","tatil","otel","şehir","ülke","gezi","uçak","restoran"},
    CreativeGenre.COMEDY: {"komedi","espri","mizah","komik","şaka","parodi"},
    CreativeGenre.CINEMATIC: {"sinema","sinematik","film","sahne","hikaye görüntüleri"},
    CreativeGenre.NEWS: {"haber","son dakika","gündem","açıklama","bakanlık","resmi"},
    CreativeGenre.STORYTELLING: {"hikaye","başından geçen","bir zamanlar","sonra ne oldu","hikayem"},
    CreativeGenre.MUSIC: {"şarkı","müzik","nakarat","beat","klip","sözler"},
    CreativeGenre.INTERVIEW: {"röportaj","mülakat","konuğumuz","söyleşi","soruyorum"},
}


def _text(transcript: Transcript | None) -> str:
    return " ".join((s.text or "") for s in (transcript.segments if transcript else [])).lower()


def classify_creative_genre(transcript: Transcript | None, report: AnalysisReport | None = None, hint: str | None = None) -> tuple[CreativeGenre, dict[str,float]]:
    if hint:
        h = hint.lower().replace(" ", "_")
        for g in CreativeGenre:
            if h == g.value or h == g.name.lower():
                return g, {g.value: 1.0}
    text = _text(transcript)
    scores: dict[CreativeGenre,float] = {g: 0.0 for g in _STYLE}
    for genre, terms in _KEYWORDS.items():
        for term in terms:
            if term in text:
                scores[genre] += 1.0 if " " not in term else 1.5
    if report:
        n = len(report.suggestions)
        if n > 8:
            scores[CreativeGenre.ENTERTAINMENT] += .5
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0].value))
    if not ranked or ranked[0][1] <= 0:
        return CreativeGenre.UNKNOWN, {"unknown": 1.0}
    top = ranked[0][1]
    confidence = min(1.0, .45 + top * .08)
    return ranked[0][0], {k.value: round(v / max(top, 1.0), 3) for k,v in ranked[:6]} | {"confidence": round(confidence,3)}


def build_creative_direction(transcript: Transcript | None, report: AnalysisReport | None = None, hint: str | None = None) -> CreativeDirection:
    genre, signals = classify_creative_genre(transcript, report, hint)
    primary = _STYLE.get(genre, CreativeStyle(CreativeGenre.UNKNOWN,"adaptive",.40,.30,.35,"clean","neutral","subtle",.40,"preserve_meaningful","context_first","stable",.40))
    alternatives = [s for g,s in _STYLE.items() if g != genre][:4]
    decisions: list[CreativeDecision] = []
    if transcript:
        for seg in transcript.segments:
            if seg.end <= seg.start:
                continue
            duration = seg.end - seg.start
            if genre == CreativeGenre.HORROR and duration >= 3.5:
                decisions.append(CreativeDecision("motion","slow_push",seg.start,min(seg.end,seg.start+1.2),.35,"Gerilimde kontrollü mikro hareket.",.82))
            elif genre in {CreativeGenre.ENTERTAINMENT,CreativeGenre.COMEDY,CreativeGenre.GAMING,CreativeGenre.SPORTS} and duration >= 2.0:
                decisions.append(CreativeDecision("motion","micro_push",seg.start,min(seg.end,seg.start+.6),.28,"Yüksek enerjili içerikte ritmik kadraj hareketi.",.78))
            elif genre in {CreativeGenre.EDUCATIONAL,CreativeGenre.TUTORIAL,CreativeGenre.TECH} and duration >= 2.5:
                decisions.append(CreativeDecision("overlay","key_point",seg.start,min(seg.end,seg.start+1.4),.45,"Bilginin ekranda netleştirilmesi.",.76))
    return CreativeDirection(primary, alternatives, decisions, signals, {
        "engine_version":"2.27",
        "mode":"content_aware_editing",
        "human_review":"recommended_for_ambiguous_genres",
        "learning":"feedback_and_reference_profiles_can_calibrate_style_weights",
    })


__all__ = ["CreativeGenre","CreativeStyle","CreativeDecision","CreativeDirection","classify_creative_genre","build_creative_direction"]
