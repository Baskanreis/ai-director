"""Non-UI beat visualization model: markers, strength and nearest beat lookup."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class BeatMarker:
    time: float
    strength: float=1.0
    index: int=0

def markers(beats:list[float], strengths:list[float]|None=None)->list[BeatMarker]:
    strengths=strengths or [1.0]*len(beats)
    return [BeatMarker(float(t),float(strengths[i]) if i<len(strengths) else 1.0,i) for i,t in enumerate(beats)]
def nearest_beat(time:float, beats:list[float])->float|None:
    return min(beats,key=lambda x:abs(x-time),default=None)
