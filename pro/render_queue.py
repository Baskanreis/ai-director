"""Persistent-friendly render queue model.

The queue stores serializable jobs and can be consumed by a UI worker. It does
not start FFmpeg itself, so cancelling a render never corrupts the project.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
from enum import Enum

class RenderState(str,Enum):
    QUEUED="queued"; RUNNING="running"; DONE="done"; FAILED="failed"; CANCELLED="cancelled"

@dataclass
class RenderJob:
    output_path: str
    settings: dict = field(default_factory=dict)
    name: str = "Render"
    id: str = field(default_factory=lambda: uuid4().hex)
    state: RenderState = RenderState.QUEUED
    progress: float = 0.0
    error: str = ""
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self):
        return {"id":self.id,"name":self.name,"output_path":self.output_path,"settings":self.settings,"state":self.state.value,"progress":self.progress,"error":self.error,"created":self.created}
    @classmethod
    def from_dict(cls,d):
        j=cls(str(d["output_path"]),dict(d.get("settings") or {}),str(d.get("name","Render")),str(d.get("id") or uuid4().hex))
        j.state=RenderState(d.get("state",RenderState.QUEUED.value)); j.progress=float(d.get("progress",0)); j.error=str(d.get("error","")); j.created=str(d.get("created",j.created)); return j

class RenderQueue:
    def __init__(self): self.jobs=[]
    def add(self,job): self.jobs.append(job); return job
    def remove(self,job_id):
        n=len(self.jobs); self.jobs=[j for j in self.jobs if j.id!=job_id]; return len(self.jobs)!=n
    def next(self):
        return next((j for j in self.jobs if j.state==RenderState.QUEUED),None)
    def to_dict(self): return [j.to_dict() for j in self.jobs]
    @classmethod
    def from_dict(cls,d):
        q=cls(); q.jobs=[RenderJob.from_dict(x) for x in (d or [])]; return q
