"""v2.26 render-ready Director pipeline.

Turns Smart Reframe plans and caption/motion decisions into non-destructive
Timeline keyframes. This is the bridge between AI decisions and the existing
single-pass FFmpeg renderer.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

from app.ai.smart_reframe import ReframePlan
from app.timeline.model import Clip, Keyframe, Timeline

@dataclass(frozen=True)
class AppliedDecision:
    clip_id: str
    kind: str
    details: str


def apply_reframe_plan(clip: Clip, plan: ReframePlan) -> AppliedDecision:
    """Apply a 9:16 reframe plan as crop keyframes on a clip.

    The source remains untouched. Keyframe times are relative to the clip.
    """
    if not plan.keyframes:
        return AppliedDecision(clip.id, "reframe", "No keyframes; no change")
    crop_x: list[Keyframe] = []
    crop_y: list[Keyframe] = []
    crop_w: list[Keyframe] = []
    crop_h: list[Keyframe] = []
    base = clip.start
    for k in plan.keyframes:
        t = max(0.0, min(clip.duration, k.time - base))
        x = max(0.0, min(1.0 - k.crop_w, k.center_x - k.crop_w / 2))
        y = max(0.0, min(1.0 - k.crop_h, k.center_y - k.crop_h / 2))
        crop_x.append(Keyframe(t, x, "ease_in_out"))
        crop_y.append(Keyframe(t, y, "ease_in_out"))
        crop_w.append(Keyframe(t, k.crop_w, "hold"))
        crop_h.append(Keyframe(t, k.crop_h, "hold"))
    clip.keyframes["crop_x"] = crop_x
    clip.keyframes["crop_y"] = crop_y
    clip.keyframes["crop_w"] = crop_w
    clip.keyframes["crop_h"] = crop_h
    return AppliedDecision(clip.id, "reframe", f"Applied {len(plan.keyframes)} keyframes")


def apply_caption_motion_metadata(clip: Clip, words: Iterable[dict]) -> AppliedDecision:
    """Store caption timing decisions on the clip without baking text into media.

    The UI/export layer can consume ``clip.caption_events`` when available;
    using a dynamic attribute keeps compatibility with older serialized Clips.
    """
    events = []
    for w in words:
        try:
            start = float(w["start"]); end = float(w["end"])
            text = str(w.get("text", "")).strip()
        except (KeyError, TypeError, ValueError):
            continue
        if end > start and text:
            events.append({"start": start, "end": end, "text": text,
                           "animation": str(w.get("animation", "pop"))})
    clip.caption_events = events
    return AppliedDecision(clip.id, "captions", f"Stored {len(events)} caption events")


def apply_director_decisions(timeline: Timeline, decisions: Iterable[dict]) -> list[AppliedDecision]:
    """Apply render-ready decisions to matching clips.

    Supported decisions: ``reframe`` with a ReframePlan and ``captions`` with
    word dictionaries. Unknown decisions are ignored rather than mutating the
    timeline unexpectedly.
    """
    by_id = {c.id: c for tr in timeline.tracks for c in tr.clips}
    applied: list[AppliedDecision] = []
    for d in decisions:
        clip = by_id.get(str(d.get("clip_id", "")))
        if not clip:
            continue
        kind = d.get("kind")
        if kind == "reframe" and isinstance(d.get("plan"), ReframePlan):
            applied.append(apply_reframe_plan(clip, d["plan"]))
        elif kind == "captions":
            applied.append(apply_caption_motion_metadata(clip, d.get("words", [])))
    return applied


def collect_timeline_captions(timeline: Timeline) -> list[dict]:
    """Collect clip caption events and convert clip-local times to timeline time."""
    events = []
    for track in timeline.tracks:
        if track.kind != "video":
            continue
        for clip in track.clips:
            for event in getattr(clip, "caption_events", []):
                item = dict(event)
                item["start"] = clip.start + float(item.get("start", 0.0))
                item["end"] = clip.start + float(item.get("end", 0.0))
                events.append(item)
    return sorted(events, key=lambda e: (e["start"], e["end"]))
