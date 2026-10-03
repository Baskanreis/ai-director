"""Non-destructive application of Director motion cues to timeline clips."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.ai.beat_sync import MotionCue
from app.motion.engine import add_or_update_keyframe
from app.timeline.model import Clip


@dataclass(frozen=True)
class AppliedMotion:
    clip_id: str
    cue: MotionCue
    properties: tuple[str, ...]


def _local_window(clip: Clip, cue: MotionCue) -> tuple[float, float] | None:
    start = max(clip.start, cue.start)
    end = min(clip.end, cue.end)
    if end <= start:
        return None
    return start - clip.start, end - clip.start


def _keyframe(clip: Clip, prop: str, t: float, value: float, easing: str = "ease_out"):
    clip.keyframes[prop] = add_or_update_keyframe(
        clip.keyframes.get(prop, []), t, value, easing=easing
    )


def apply_motion_cue(clip: Clip, cue: MotionCue) -> AppliedMotion | None:
    """Apply one bounded motion cue to one overlapping clip.

    Existing keyframes are preserved except at the exact generated timestamps.
    The operation is therefore suitable for an undo/versioning layer.
    """
    window = _local_window(clip, cue)
    if not window:
        return None
    a, b = window
    mid = a + (b - a) * 0.5
    intensity = max(0.0, min(1.0, cue.intensity))
    changed: list[str] = []

    if cue.preset in ("punch", "micro_push"):
        base_scale = clip.scale
        peak = base_scale * (1.0 + 0.10 * intensity)
        _keyframe(clip, "scale", a, base_scale, "linear")
        _keyframe(clip, "scale", mid, peak, "ease_out")
        _keyframe(clip, "scale", b, base_scale, "ease_in")
        changed.append("scale")
        # A tiny positional accent makes a punch feel alive without becoming shake.
        offset = 8.0 * intensity
        _keyframe(clip, "pos_x", a, clip.pos_x, "linear")
        _keyframe(clip, "pos_x", mid, clip.pos_x + offset, "ease_out")
        _keyframe(clip, "pos_x", b, clip.pos_x, "ease_in")
        changed.append("pos_x")
    elif cue.preset == "push_in":
        base_scale = clip.scale
        peak = base_scale * (1.0 + 0.14 * intensity)
        _keyframe(clip, "scale", a, base_scale, "linear")
        _keyframe(clip, "scale", b, peak, "ease_in_out")
        changed.append("scale")
    elif cue.preset == "pull_out":
        base_scale = clip.scale * (1.0 + 0.10 * intensity)
        _keyframe(clip, "scale", a, base_scale, "linear")
        _keyframe(clip, "scale", b, clip.scale, "ease_out")
        changed.append("scale")
    return AppliedMotion(clip.id, cue, tuple(dict.fromkeys(changed)))


def apply_motion_plan(
    clips: Iterable[Clip],
    cues: Iterable[MotionCue],
    *,
    max_cues_per_clip: int = 8,
) -> list[AppliedMotion]:
    """Apply a plan while preventing an effect flood on any single clip."""
    clips = list(clips)
    applied: list[AppliedMotion] = []
    counts: dict[str, int] = {}
    for cue in sorted(cues, key=lambda c: (c.start, c.end)):
        for clip in clips:
            if counts.get(clip.id, 0) >= max_cues_per_clip:
                continue
            result = apply_motion_cue(clip, cue)
            if result:
                applied.append(result)
                counts[clip.id] = counts.get(clip.id, 0) + 1
    return applied


__all__ = ["AppliedMotion", "apply_motion_cue", "apply_motion_plan"]
