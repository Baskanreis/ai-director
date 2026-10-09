"""AI Shorts Director veri modelleri (v2.13)."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field

@dataclass(frozen=True)
class ShortsCandidate:
    id: str
    source_start: float
    source_end: float
    hook_start: float
    hook_end: float
    payoff_start: float
    payoff_end: float
    hook_score: float
    payoff_score: float
    context_score: float
    emotion_score: float
    pacing_score: float
    rewatch_score: float
    visual_score: float = 60.0
    text: str = ""
    reason: str = ""
    tags: tuple[str, ...] = ()

    @property
    def duration(self) -> float:
        return max(0.0, self.source_end - self.source_start)

    @property
    def score(self) -> float:
        weights = (0.25, 0.22, 0.15, 0.13, 0.10, 0.10, 0.05)
        vals = (self.hook_score, self.payoff_score, self.context_score,
                self.emotion_score, self.pacing_score, self.rewatch_score, self.visual_score)
        return round(sum(a*b for a,b in zip(vals, weights)), 2)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tags"] = list(self.tags)
        d["duration"] = round(self.duration, 3)
        d["score"] = self.score
        return d

@dataclass(frozen=True)
class ReframeCue:
    time: float
    x: float
    y: float
    zoom: float = 1.0
    subject: str = "main_subject"
    reason: str = "safe_center"

@dataclass(frozen=True)
class CaptionCue:
    start: float
    end: float
    text: str
    emphasis_words: tuple[str, ...] = ()
    style: str = "dynamic_bold"
    position: str = "lower_safe"

@dataclass(frozen=True)
class BrollCue:
    start: float
    end: float
    subject: str
    priority: float
    reason: str

@dataclass(frozen=True)
class ShortsPlan:
    source: str
    target: str
    duration: float
    candidate_id: str
    candidate_score: float
    source_start: float
    source_end: float
    reframes: tuple[ReframeCue, ...] = ()
    captions: tuple[CaptionCue, ...] = ()
    broll: tuple[BrollCue, ...] = ()
    punch_ins: tuple[ReframeCue, ...] = ()
    silence_cuts: tuple[tuple[float, float], ...] = ()
    beat_cuts: tuple[float, ...] = ()
    notes: tuple[str, ...] = ()
    version: str = "2.13"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["reframes"] = [asdict(x) for x in self.reframes]
        d["captions"] = [asdict(x) for x in self.captions]
        d["broll"] = [asdict(x) for x in self.broll]
        d["punch_ins"] = [asdict(x) for x in self.punch_ins]
        d["silence_cuts"] = [list(x) for x in self.silence_cuts]
        return d
