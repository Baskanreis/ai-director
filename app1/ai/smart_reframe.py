"""AI Director v2.25 smart reframe planning.

Geometry-only, deterministic planning layer. It consumes optional face/speaker
bounding boxes (normalized 0..1) and produces safe 9:16 crop windows without
modifying source media. A renderer can later turn these plans into keyframes.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class SubjectBox:
    start: float
    end: float
    x: float
    y: float
    w: float
    h: float
    score: float = 1.0
    subject_id: str = "subject"

@dataclass(frozen=True)
class ReframeKeyframe:
    time: float
    center_x: float
    center_y: float
    crop_w: float
    crop_h: float

@dataclass(frozen=True)
class ReframePlan:
    aspect_ratio: str
    keyframes: tuple[ReframeKeyframe, ...]
    mode: str
    warnings: tuple[str, ...] = ()


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def plan_smart_reframe(subjects: Sequence[SubjectBox], start: float, end: float,
                       source_aspect: float = 16/9, target_aspect: float = 9/16,
                       mode: str = "speaker_priority") -> ReframePlan:
    if end <= start:
        return ReframePlan("9:16", (), mode, ("Invalid time range.",))
    # Width fraction needed to produce target aspect from the source frame.
    crop_w = _clamp(target_aspect / source_aspect)
    crop_h = 1.0
    relevant = [s for s in subjects if s.end > start and s.start < end and s.w > 0 and s.h > 0]
    relevant.sort(key=lambda s: (-s.score, s.start))
    if not relevant:
        return ReframePlan("9:16", (ReframeKeyframe(start, .5, .5, crop_w, crop_h),
                                     ReframeKeyframe(end, .5, .5, crop_w, crop_h)), mode,
                           ("No subject boxes supplied; centered fallback used.",))
    # Sample boundaries and subject changes; keep plans compact for real-time use.
    times = sorted({start, end, *[max(start, min(end, s.start)) for s in relevant],
                    *[max(start, min(end, s.end)) for s in relevant]})
    keys=[]
    for t in times:
        active=[s for s in relevant if s.start <= t <= s.end]
        if not active: active=[min(relevant, key=lambda s: abs((s.start+s.end)/2-t))]
        best=max(active, key=lambda s:s.score)
        cx=_clamp(best.x+best.w/2)
        cy=_clamp(best.y+best.h/2)
        half=crop_w/2
        cx=_clamp(cx, half, 1-half)
        keys.append(ReframeKeyframe(round(t,3), round(cx,4), round(cy,4), round(crop_w,4), 1.0))
    return ReframePlan("9:16", tuple(keys), mode)

__all__=["SubjectBox","ReframeKeyframe","ReframePlan","plan_smart_reframe"]
