"""Apply an AI Creative Pass to the timeline without rendering yet.

The pass is deliberately non-destructive at source level: it only adds timeline
keyframes/transitions. Export then turns those properties into FFmpeg filters.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.ai.effects_director import CreativePassPlan, CreativeDecision
from app.effects.effect_library import ALL_EFFECTS
from app.effects.pro_asset_library import catalog
from app.timeline.model import Keyframe, Timeline, Transition, Clip


@dataclass
class ApplyReport:
    applied: int = 0
    effects: int = 0
    motions: int = 0
    transitions: int = 0
    text_cues: int = 0
    skipped: int = 0


def _asset_params(asset_id: str) -> dict[str, Any]:
    for a in catalog():
        if a.id == asset_id:
            return dict(a.params)
    return {}


def _clip_at(timeline: Timeline, t: float) -> Clip | None:
    track = timeline.first_track("video")
    if not track:
        return None
    for clip in track.sorted_clips():
        if clip.start - 1e-3 <= t < clip.end + 1e-3:
            return clip
    return None


def _add_kf(clip: Clip, prop: str, time: float, value: float, easing: str = "ease_out") -> None:
    arr = clip.keyframes.setdefault(prop, [])
    arr.append(Keyframe(max(0.0, min(clip.duration, time)), value, easing=easing))
    arr.sort(key=lambda k: k.time)
    # Same timestamp: keep the last value.
    dedup: list[Keyframe] = []
    for k in arr:
        if dedup and abs(dedup[-1].time - k.time) < 1e-4:
            dedup[-1] = k
        else:
            dedup.append(k)
    clip.keyframes[prop] = dedup


def _apply_effect(clip: Clip, decision: CreativeDecision) -> bool:
    params = _asset_params(decision.asset_id)
    preset = params.get("preset")
    values = ALL_EFFECTS.get(preset or "")
    if not values:
        return False
    local_start = max(0.0, decision.start - clip.start)
    local_end = max(local_start, min(clip.duration, decision.end - clip.start))
    # Blend into the look instead of making a hard cut whenever possible.
    for name in ("brightness", "contrast", "saturation", "gamma"):
        if name not in values:
            continue
        base = {"brightness": 0.0, "contrast": 1.0, "saturation": 1.0, "gamma": 1.0}[name]
        target = base + (float(values[name]) - base) * max(0.0, min(1.0, decision.intensity))
        _add_kf(clip, f"effect:{name}", local_start, target, "ease_in")
        _add_kf(clip, f"effect:{name}", local_end, base, "ease_out")
    return True


def _apply_motion(clip: Clip, decision: CreativeDecision) -> bool:
    params = _asset_params(decision.asset_id)
    anim = str(params.get("animation", ""))
    local_start = max(0.0, decision.start - clip.start)
    local_end = max(local_start, min(clip.duration, decision.end - clip.start))
    if "punch" in anim or "punch" in decision.asset_id:
        amount = float(params.get("scale_to", 1.055))
        amount = 1.0 + (amount - 1.0) * max(0.1, min(1.0, decision.intensity))
        _add_kf(clip, "scale", local_start, float(params.get("scale_from", 1.0)), "ease_out")
        _add_kf(clip, "scale", local_end, amount, "ease_out")
        return True
    if "shake" in anim or "shake" in decision.asset_id:
        amp = float(params.get("amplitude", 2.0)) * max(0.1, decision.intensity)
        _add_kf(clip, "pos_x", local_start, -amp, "ease_in")
        _add_kf(clip, "pos_x", (local_start + local_end) / 2, amp, "linear")
        _add_kf(clip, "pos_x", local_end, 0.0, "ease_out")
        return True
    return False


def apply_creative_pass(timeline: Timeline, plan: CreativePassPlan) -> ApplyReport:
    report = ApplyReport()
    for decision in sorted(plan.decisions, key=lambda d: (d.start, d.kind)):
        clip = _clip_at(timeline, decision.start)
        if clip is None:
            report.skipped += 1
            continue
        if decision.kind == "effect":
            ok = _apply_effect(clip, decision)
            report.effects += int(ok)
        elif decision.kind == "motion":
            ok = _apply_motion(clip, decision)
            report.motions += int(ok)
        elif decision.kind == "transition":
            duration = max(0.05, min(0.5, decision.end - decision.start))
            params = _asset_params(decision.asset_id)
            clip.transition_in = Transition(kind=str(params.get("kind", "crossfade")), duration=duration)
            report.transitions += 1
            ok = True
        elif decision.kind == "text":
            # Text rendering is owned by the subtitle engine. Keep the cue in a
            # non-destructive clip metadata bucket for the subtitle renderer/UI.
            clip.creative_text_cues.append({"asset_id": decision.asset_id, "start": decision.start, "end": decision.end, "params": decision.parameters})
            report.text_cues += 1
            ok = True
        else:
            report.skipped += 1
            ok = False
        if ok:
            report.applied += 1
    return report


def apply_creative_stack(timeline: Timeline, items: list[dict[str, Any]]) -> ApplyReport:
    """Apply several Creative Library items to one or more clips in one pass."""
    decisions = []
    for item in items:
        aid = str(item.get("asset_id", "")); clip_id = item.get("clip_id")
        found = timeline.find(clip_id) if clip_id else None
        if found is None:
            continue
        _track, clip = found
        start = float(item.get("start", clip.start)); duration = float(item.get("duration", .8))
        asset = next((a for a in catalog() if a.id == aid), None)
        if asset is None:
            continue
        decisions.append(CreativeDecision(asset.kind, aid, start, min(clip.end, start + duration),
                                          float(item.get("intensity", 1.0)),
                                          "Creative Library stack", float(item.get("intensity", 1.0)), dict(asset.params)))
    return apply_creative_pass(timeline, type("Plan", (), {"decisions": decisions})())
