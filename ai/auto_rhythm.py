"""Unified AI Auto-Rhythm Editing — v2.72.

One deterministic rhythm map coordinates cuts, transitions, camera motion,
creative asset animation, subtitle emphasis and SFX.  Decisions are sparse,
ranked and non-destructive; callers may apply only approved decisions.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Iterable

from app.ai.beat_sync import BeatCue, plan_transitions, plan_motion

CHANNELS = ("cut", "transition", "zoom_pan", "asset_animation", "subtitle_emphasis", "sfx")

@dataclass(frozen=True)
class RhythmDecision:
    channel: str
    time: float
    score: float
    strength: float
    reason: str
    beat_index: int = -1

@dataclass(frozen=True)
class RhythmPolicy:
    min_cut_distance: float = 0.65
    motion_budget: float = 0.55
    asset_budget: float = 0.45
    subtitle_budget: float = 0.60
    sfx_budget: float = 0.50
    minimum_decision_score: float = 0.45

@dataclass(frozen=True)
class UnifiedRhythmMap:
    duration: float
    bpm: float | None
    decisions: tuple[RhythmDecision, ...]
    engine_version: str = "2.72"

    def by_channel(self, channel: str) -> list[RhythmDecision]:
        return [d for d in self.decisions if d.channel == channel]

    def to_dict(self) -> dict[str, Any]:
        return {
            "duration": self.duration,
            "bpm": self.bpm,
            "engine_version": self.engine_version,
            "decisions": [asdict(d) for d in self.decisions],
        }


def _scene_importance(events: Iterable[dict], t: float) -> float:
    best = 0.35
    for e in events:
        start, end = float(e.get("start", 0)), float(e.get("end", 0))
        if start <= t <= end:
            kind = e.get("kind", "")
            best = max(best, {"hook": 1.0, "pattern_break": .85, "broll_cue": .72,
                              "speech": .65, "beat": .55}.get(kind, .45))
    return best


def _sparse_cut_times(beats: list[BeatCue], duration: float, events: list[dict], policy: RhythmPolicy) -> list[RhythmDecision]:
    out=[]; last=-1e9
    for b in beats:
        importance = _scene_importance(events, b.time)
        score = b.strength * importance
        if score < policy.minimum_decision_score or b.time-last < policy.min_cut_distance:
            continue
        out.append(RhythmDecision("cut", b.time, round(score,4), b.strength,
                                  "beat_strength_x_scene_importance", b.beat_index))
        last=b.time
    return out


def build_unified_rhythm_map(*, duration: float, beats: Iterable[BeatCue] = (), bpm: float | None = None,
                             events: Iterable[dict] = (), policy: RhythmPolicy | None = None) -> UnifiedRhythmMap:
    policy = policy or RhythmPolicy()
    beat_list = sorted(list(beats), key=lambda x: x.time)
    event_list = list(events)
    decisions = _sparse_cut_times(beat_list, duration, event_list, policy)

    for b in beat_list:
        importance = _scene_importance(event_list, b.time)
        base = b.strength * importance
        if base >= policy.minimum_decision_score:
            if base <= policy.motion_budget:
                decisions.append(RhythmDecision("zoom_pan", b.time, round(base,4), b.strength,
                                                "rhythm_motion_budget", b.beat_index))
            if base <= policy.asset_budget:
                decisions.append(RhythmDecision("asset_animation", b.time, round(base,4), b.strength,
                                                "rhythm_asset_budget", b.beat_index))
            if base <= policy.subtitle_budget:
                decisions.append(RhythmDecision("subtitle_emphasis", b.time, round(base,4), b.strength,
                                                "rhythm_subtitle_emphasis", b.beat_index))
            if base <= policy.sfx_budget:
                decisions.append(RhythmDecision("sfx", b.time, round(base,4), b.strength,
                                                "rhythm_sfx_budget", b.beat_index))

    transitions = plan_transitions([d.time for d in decisions if d.channel == "cut"], bpm, duration)
    for cue in transitions:
        decisions.append(RhythmDecision("transition", cue.at, cue.confidence, cue.confidence,
                                        cue.reason))
    decisions.sort(key=lambda d: (d.time, d.channel))
    return UnifiedRhythmMap(float(duration), bpm, tuple(decisions))


def compile_auto_rhythm(*, duration: float, beats: Iterable[BeatCue], events: Iterable[dict],
                        profile: str = "youtube_longform", bpm: float | None = None,
                        policy: RhythmPolicy | None = None) -> dict[str, Any]:
    rhythm = build_unified_rhythm_map(duration=duration, beats=beats, bpm=bpm, events=events, policy=policy)
    return {
        "engine_version": "2.72",
        "profile": profile,
        "rhythm_map": rhythm.to_dict(),
        "channels": {c: [asdict(x) for x in rhythm.by_channel(c)] for c in CHANNELS},
        "quality_budget": {
            "min_cut_distance": (policy or RhythmPolicy()).min_cut_distance,
            "motion_budget": (policy or RhythmPolicy()).motion_budget,
        },
    }

__all__ = ["CHANNELS", "RhythmDecision", "RhythmPolicy", "UnifiedRhythmMap", "build_unified_rhythm_map", "compile_auto_rhythm"]
