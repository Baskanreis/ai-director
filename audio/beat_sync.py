"""Beat-aware editing helpers for the Creative Director.

Provides deterministic, non-destructive timing helpers: beat grid, nearest-beat
quantisation, bar/downbeat detection and cue generation for cuts, zooms and SFX.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable, Sequence

@dataclass(frozen=True)
class BeatGrid:
    bpm: float
    offset: float = 0.0
    beats_per_bar: int = 4

    @property
    def interval(self) -> float:
        return 60.0 / max(self.bpm, 1e-6)

    def beats(self, duration: float) -> list[float]:
        if duration <= 0 or self.bpm <= 0:
            return []
        out=[]; t=float(self.offset)
        while t < duration:
            if t >= 0: out.append(round(t, 4))
            t += self.interval
        return out

    def downbeats(self, duration: float) -> list[float]:
        return [t for i,t in enumerate(self.beats(duration)) if i % max(self.beats_per_bar,1)==0]


def quantize_time(t: float, bpm: float, offset: float = 0.0, mode: str = "nearest") -> float:
    if bpm <= 0: return float(t)
    step = 60.0 / bpm
    n = (float(t)-offset)/step
    if mode == "floor": k=int(n//1)
    elif mode == "ceil": k=int(-(-n//1))
    else: k=int(round(n))
    return round(offset + k*step, 4)


def quantize_times(times: Iterable[float], bpm: float, offset: float = 0.0, mode: str = "nearest") -> list[float]:
    return [quantize_time(t,bpm,offset,mode) for t in times]


def snap_cuts(cuts: Sequence[float], bpm: float, tolerance: float = 0.12, offset: float = 0.0) -> list[float]:
    out=[]
    for t in cuts:
        q=quantize_time(t,bpm,offset)
        out.append(q if abs(q-t)<=tolerance else round(float(t),4))
    return out


def build_beat_cues(duration: float, bpm: float, offset: float = 0.0, every_n: int = 1) -> list[dict]:
    grid=BeatGrid(bpm,offset)
    beats=grid.beats(duration)
    n=max(1,int(every_n))
    cues=[]
    for i,t in enumerate(beats):
        if i % n: continue
        cues.append({"time":t,"strength":"downbeat" if i%4==0 else "beat","index":i})
    return cues


def make_rhythm_plan(duration: float, bpm: float, offset: float = 0.0) -> dict:
    grid=BeatGrid(bpm,offset)
    beats=grid.beats(duration)
    return {
        "bpm": float(bpm), "offset": float(offset), "beats_per_bar": grid.beats_per_bar,
        "beats": beats, "downbeats": grid.downbeats(duration),
        "engine_version": "2.28",
    }

__all__=["BeatGrid","quantize_time","quantize_times","snap_cuts","build_beat_cues","make_rhythm_plan"]
