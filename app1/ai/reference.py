"""Reference Video Analyzer — v1.8.

Ham video + transcript + DirectorPlan sinyallerini tek bir referans raporunda
birleştirir. Amaç: tek tek videolardan ölçülebilir edit özellikleri çıkarmak ve
Channel Intelligence'a güvenilir veri sağlamak.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import median
from typing import Sequence

from app.ai.director import DirectorPlan
from app.subtitle.models import Transcript

@dataclass(frozen=True)
class ReferenceVideoReport:
    source: str = ""
    duration: float = 0.0
    shot_count: int = 0
    avg_shot_duration: float = 0.0
    cut_density_per_minute: float = 0.0
    hook_score: float = 0.0
    narrative_score: float = 0.0
    pattern_breaks_per_minute: float = 0.0
    broll_cues_per_minute: float = 0.0
    beats_per_minute: float = 0.0
    highlight_density_per_minute: float = 0.0
    transcript_word_count: int = 0
    words_per_minute: float = 0.0
    chapters: int = 0
    profile: str = ""
    signals: tuple[str, ...] = ()
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _rate(n: int, duration: float) -> float:
    return n / (duration / 60.0) if duration > 0 else 0.0


def analyze_reference(
    plan: DirectorPlan,
    transcript: Transcript | None = None,
    source: str | Path = "",
    scene_times: Sequence[float] | None = None,
) -> ReferenceVideoReport:
    """Director plan + transcript + opsiyonel gerçek sahne zamanları ile referans raporu üret."""
    duration = max(float(plan.source_duration), 0.0)
    scenes = sorted(float(x) for x in (scene_times or []) if 0 < float(x) < duration)
    shot_count = len(scenes) + 1 if duration > 0 else 0
    avg_shot = duration / shot_count if shot_count else 0.0
    words = list(transcript.all_words()) if transcript else []
    signals: list[str] = []
    cut_density = _rate(shot_count - 1, duration)
    if cut_density >= 12: signals.append("high_shot_density")
    elif cut_density <= 3: signals.append("low_shot_density")
    if plan.hook_score >= 75: signals.append("strong_hook")
    if plan.narrative_score >= 75: signals.append("narrative_driven")
    if _rate(sum(e.kind == "broll_cue" for e in plan.events), duration) >= 2: signals.append("broll_heavy")
    if _rate(sum(e.kind == "pattern_break" for e in plan.events), duration) >= 2.5: signals.append("frequent_pattern_breaks")
    if transcript and len(words) >= 1:
        wpm = _rate(len(words), duration)
    else:
        wpm = 0.0
    return ReferenceVideoReport(
        source=str(source), duration=round(duration,3), shot_count=shot_count,
        avg_shot_duration=round(avg_shot,3), cut_density_per_minute=round(cut_density,3),
        hook_score=round(plan.hook_score,2), narrative_score=round(plan.narrative_score,2),
        pattern_breaks_per_minute=round(_rate(sum(e.kind == "pattern_break" for e in plan.events), duration),3),
        broll_cues_per_minute=round(_rate(sum(e.kind == "broll_cue" for e in plan.events), duration),3),
        beats_per_minute=round(_rate(sum(e.kind == "beat" for e in plan.events), duration),3),
        highlight_density_per_minute=round(_rate(len(plan.highlight_words), duration),3),
        transcript_word_count=len(words), words_per_minute=round(wpm,2),
        chapters=len(plan.chapters), profile=plan.profile, signals=tuple(signals),
        metadata={"engine_version":"1.8", "scene_times_provided": bool(scene_times)},
    )


def compare_reference_style(reference: ReferenceVideoReport, profile) -> dict:
    """Reference raporunu ChannelStyleProfile ile karşılaştırır."""
    keys = {
        "cut_density_per_minute": getattr(profile, "metadata", {}).get("avg_cut_density_per_minute", 0.0),
        "avg_shot_duration": getattr(profile, "metadata", {}).get("avg_shot_duration", 0.0),
        "hook_score": getattr(profile, "avg_hook_score", 0.0),
        "narrative_score": getattr(profile, "avg_narrative_score", 0.0),
    }
    actual = {"cut_density_per_minute": reference.cut_density_per_minute, "avg_shot_duration": reference.avg_shot_duration,
              "hook_score": reference.hook_score, "narrative_score": reference.narrative_score}
    diffs = {k: round(actual[k] - keys[k], 3) for k in actual if keys[k] != 0}
    return {"reference": actual, "channel": keys, "differences": diffs}

__all__=["ReferenceVideoReport","analyze_reference","compare_reference_style"]
