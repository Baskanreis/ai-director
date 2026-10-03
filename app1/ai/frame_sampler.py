"""Adaptive frame sampling for multimodal inference."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class SamplePoint:
    time: float
    reason: str
    priority: float

def adaptive_sample_times(duration: float, base_hz: float=2.0, *, beats=(), scene_changes=(), motion_peaks=(), max_samples: int=1200) -> list[SamplePoint]:
    if duration <= 0: return []
    base=[]; step=1.0/max(.1,base_hz); t=0.0
    while t < duration and len(base) < max_samples:
        base.append(SamplePoint(round(t,4),"periodic",.35)); t += step
    points=base[:]
    for values,reason,priority in ((beats,"beat",.65),(scene_changes,"scene_change",.9),(motion_peaks,"motion_peak",.85)):
        for x in values:
            x=float(x)
            if 0 <= x <= duration: points.append(SamplePoint(round(x,4),reason,priority))
    merged={}
    for p in points:
        key=round(p.time,2)
        old=merged.get(key)
        if old is None or p.priority>old.priority: merged[key]=p
    return sorted(merged.values(),key=lambda p:p.time)[:max_samples]

__all__=["SamplePoint","adaptive_sample_times"]
