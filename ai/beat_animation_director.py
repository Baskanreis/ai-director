"""Beat-Synced Animation Director — v2.71.

Turns beat cues into sparse asset-stack animation keyframes.  Manual keyframes
are protected by default and generated motion respects an intensity ceiling,
cooldown and minimum beat distance.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Iterable

from app.ai.beat_sync import BeatCue
from app.effects.asset_animation import add_asset_keyframe

@dataclass(frozen=True)
class BeatAnimationPolicy:
    intensity_ceiling: float = 1.0
    cooldown: float = 0.28
    minimum_beat_distance: float = 0.16
    attack: float = 0.10
    release: float = 0.12
    protect_manual_keyframes: bool = True
    min_strength: float = 0.25

@dataclass(frozen=True)
class BeatAnimationCue:
    time: float
    strength: float
    peak: float
    reason: str = "beat_asset_animation"


def _existing_times(item: dict[str, Any], prop: str) -> list[float]:
    return [float(k.get("time", 0.0) if isinstance(k, dict) else k.time)
            for k in item.get("keyframes", {}).get(prop, [])]


def plan_asset_animation(beats: Iterable[BeatCue], *, base: float = 1.0,
                         policy: BeatAnimationPolicy | None = None) -> list[BeatAnimationCue]:
    policy = policy or BeatAnimationPolicy()
    out: list[BeatAnimationCue] = []
    last = -1e9
    for beat in beats:
        if beat.strength < policy.min_strength:
            continue
        if beat.time - last < max(policy.minimum_beat_distance, policy.cooldown):
            continue
        peak = min(policy.intensity_ceiling, max(base, base + 0.35 * beat.strength))
        out.append(BeatAnimationCue(round(beat.time, 6), round(beat.strength, 4), round(peak, 4)))
        last = beat.time
    return out


def apply_asset_animation(clip: Any, asset_id: str, beats: Iterable[BeatCue], *,
                          policy: BeatAnimationPolicy | None = None, index: int = 0,
                          property_name: str = "intensity") -> list[BeatAnimationCue]:
    policy = policy or BeatAnimationPolicy()
    cues = plan_asset_animation(beats, base=1.0, policy=policy)
    stack = list(clip.creative_metadata.get("asset_stack", []))
    matches = [(i, x) for i, x in enumerate(stack) if x.get("asset_id") == asset_id]
    if not matches:
        return []
    item_index, found = matches[min(max(0, index), len(matches) - 1)]
    existing = _existing_times(found, property_name) if policy.protect_manual_keyframes else []
    applied: list[BeatAnimationCue] = []
    for cue in cues:
        release_time = cue.time + policy.release
        if policy.protect_manual_keyframes and any(abs(t - cue.time) <= 1e-3 or abs(t - release_time) <= 1e-3 for t in existing):
            continue
        add_asset_keyframe(clip, asset_id, property_name, cue.time, cue.peak,
                           easing="ease_out", index=item_index)
        # Return-to-base is deliberately scheduled as a separate keyframe so the
        # beat accent does not permanently raise the recipe intensity.
        add_asset_keyframe(clip, asset_id, property_name, release_time,
                           1.0, easing="ease_in", index=item_index)
        applied.append(cue)
    return applied

__all__ = ["BeatAnimationPolicy", "BeatAnimationCue", "plan_asset_animation", "apply_asset_animation"]
