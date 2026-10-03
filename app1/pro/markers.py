"""Timeline markers, ranges and editorial notes."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from uuid import uuid4

@dataclass
class Marker:
    time: float
    name: str = ""
    color: str = ""
    duration: float = 0.0
    note: str = ""
    id: str = ""
    def __post_init__(self):
        if not self.id: self.id=uuid4().hex
    @property
    def end(self): return self.time+max(0.0,self.duration)
    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls,d): return cls(float(d.get("time",0)),str(d.get("name","")),str(d.get("color","")),float(d.get("duration",0)),str(d.get("note","")),str(d.get("id","")))

class MarkerStore:
    def __init__(self, markers=None): self.markers=list(markers or [])
    def add(self,time,name="",color="",duration=0.0,note=""):
        m=Marker(max(0.0,time),name,color,duration,note); self.markers.append(m); self.markers.sort(key=lambda x:x.time); return m
    def remove(self,marker_id):
        before=len(self.markers); self.markers=[m for m in self.markers if m.id!=marker_id]; return len(self.markers)!=before
    def move(self,marker_id,time):
        for m in self.markers:
            if m.id==marker_id: m.time=max(0.0,time); self.markers.sort(key=lambda x:x.time); return True
        return False
    def at(self,time,tolerance=0.08): return [m for m in self.markers if abs(m.time-time)<=tolerance]
    def to_dict(self): return [m.to_dict() for m in self.markers]
    @classmethod
    def from_dict(cls,d): return cls(Marker.from_dict(x) for x in (d or []))
