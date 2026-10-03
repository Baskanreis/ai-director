"""Content understanding layer for the AI Director.

The module converts transcript/analysis metadata into bounded editorial signals.
It is intentionally model-agnostic: a future vision/audio/LLM model can populate
these same fields without changing downstream editing code.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
import re
from typing import Any

from app.ai.models import AnalysisReport
from app.subtitle.models import Transcript

@dataclass(frozen=True)
class SegmentSignal:
    start: float
    end: float
    text: str
    importance: float = 0.0
    emotion: str = "neutral"
    energy: float = 0.0
    hook: float = 0.0
    payoff: float = 0.0
    information: float = 0.0
    suspense: float = 0.0
    comedy: float = 0.0
    action: float = 0.0
    broll_need: float = 0.0
    silence_sensitive: float = 0.0

    def to_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass
class ContentUnderstanding:
    topic: str = "unknown"
    narrative_arc: str = "adaptive"
    emotional_arc: str = "stable"
    energy: float = 0.5
    information_density: float = 0.5
    suspense: float = 0.0
    comedy: float = 0.0
    action: float = 0.0
    hook_strength: float = 0.0
    payoff_strength: float = 0.0
    broll_need: float = 0.0
    segments: list[SegmentSignal] = field(default_factory=list)
    signals: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]: return asdict(self)

_HOOK = {"neden","nasıl","sonunda","ama","fakat","inanılmaz","imkansız","ilk","gizli","gerçekten","asla","şok","şaşırtıcı","denedik","başardık","kaybettik","kazandık"}
_INFO = {"çünkü","neden","nasıl","örneğin","şu","özellik","adım","sonuç","istatistik","tarih","bilgi","önemli","dikkat"}
_SUSPENSE = {"gece","karanlık","bekle","sonra","henüz","görmedik","duydum","ses","kapı","gölge","lanet","hayalet","korkunç","gerilim"}
_COMEDY = {"şaka","komik","haha","güldük","espri","şaka yaptım","inanılmaz"}
_ACTION = {"gol","vurdu","kaçtı","koştu","kazandık","kaybettik","boss","kill","ateş","drift","patladı","başladı"}
_BROLL = {"ürün","telefon","araba","ev","para","harita","ekran","grafik","istatistik","fotoğraf","kamera","oyun","site","uygulama","şehir","ülke","örnek"}

def _words(text: str) -> list[str]: return re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+", text.lower())

def _score(words: list[str], terms: set[str]) -> float:
    hits = sum(1 for w in words if w in terms)
    return min(1.0, hits / max(5.0, len(words) * .35))

def understand_content(transcript: Transcript | None, report: AnalysisReport | None = None, topic: str | None = None) -> ContentUnderstanding:
    segments: list[SegmentSignal] = []
    if transcript:
        for seg in transcript.segments:
            text = (seg.text or "").strip()
            if not text or seg.end <= seg.start: continue
            words = _words(text)
            hook = min(1.0, .18 + .16 * sum(w in _HOOK for w in words) + (.16 if "?" in text else 0))
            info = _score(words, _INFO)
            suspense = _score(words, _SUSPENSE)
            comedy = _score(words, _COMEDY)
            action = _score(words, _ACTION)
            broll = _score(words, _BROLL)
            energy = min(1.0, .18 + .10 * len(words) + .25 * max(comedy, action))
            importance = min(1.0, .25 + .42 * info + .30 * hook + .22 * max(comedy, action, suspense))
            payoff = min(1.0, .15 + .35 * action + .30 * comedy + .20 * (1.0 if any(x in text.lower() for x in ("sonuç", "sonunda", "işte", "başardık", "gerçek şu")) else 0))
            emotion = "suspense" if suspense >= max(comedy, action, .35) else "comedy" if comedy >= max(action, .35) else "action" if action >= .35 else "informative" if info >= .35 else "neutral"
            segments.append(SegmentSignal(seg.start, seg.end, text, importance, emotion, energy, hook, payoff, info, suspense, comedy, action, broll, suspense))
    avg = lambda attr: sum(getattr(x, attr) for x in segments) / len(segments) if segments else 0.0
    narrative = "hook_build_payoff" if len(segments) >= 3 and max((s.hook for s in segments), default=0) > .5 and max((s.payoff for s in segments), default=0) > .4 else "information_flow" if avg("information") > .35 else "adaptive"
    emotional = "tension_release" if avg("suspense") > .25 else "high_energy" if max(avg("action"), avg("comedy")) > .3 else "calm"
    return ContentUnderstanding(
        topic=topic or "unknown", narrative_arc=narrative, emotional_arc=emotional,
        energy=round(avg("energy"), 3), information_density=round(avg("information"), 3),
        suspense=round(avg("suspense"), 3), comedy=round(avg("comedy"), 3), action=round(avg("action"), 3),
        hook_strength=round(max((s.hook for s in segments), default=0), 3),
        payoff_strength=round(max((s.payoff for s in segments), default=0), 3),
        broll_need=round(avg("broll_need"), 3), segments=segments,
        signals={"segment_count": float(len(segments)), "avg_energy": round(avg("energy"),3)},
        metadata={"version":"2.28", "model_agnostic":True, "source":"transcript_and_analysis"},
    )

__all__ = ["SegmentSignal", "ContentUnderstanding", "understand_content"]
