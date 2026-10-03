"""Persistent render queue model with resumable state and cancellation metadata."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
import json
from uuid import uuid4

class RenderState(str, Enum):
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
    started: str = ""
    finished: str = ""
    eta_seconds: float | None = None
    speed: float | None = None

    def to_dict(self):
        return {"id":self.id,"name":self.name,"output_path":self.output_path,"settings":self.settings,
                "state":self.state.value,"progress":self.progress,"error":self.error,"created":self.created,
                "started":self.started,"finished":self.finished,"eta_seconds":self.eta_seconds,"speed":self.speed}

    @classmethod
    def from_dict(cls,d):
        j=cls(str(d["output_path"]),dict(d.get("settings") or {}),str(d.get("name","Render")),str(d.get("id") or uuid4().hex))
        j.state=RenderState(d.get("state",RenderState.QUEUED.value)); j.progress=float(d.get("progress",0)); j.error=str(d.get("error",""))
        j.created=str(d.get("created",j.created)); j.started=str(d.get("started","")); j.finished=str(d.get("finished",""))
        j.eta_seconds=d.get("eta_seconds"); j.speed=d.get("speed"); return j

class RenderQueue:
    def __init__(self): self.jobs=[]
    def add(self,job): self.jobs.append(job); return job
    def remove(self,job_id):
        n=len(self.jobs); self.jobs=[j for j in self.jobs if j.id!=job_id]; return len(self.jobs)!=n
    def next(self): return next((j for j in self.jobs if j.state==RenderState.QUEUED),None)
    def cancel(self,job_id):
        job=next((j for j in self.jobs if j.id==job_id),None)
        if not job or job.state not in (RenderState.QUEUED, RenderState.RUNNING): return False
        job.state=RenderState.CANCELLED; job.finished=datetime.now(timezone.utc).isoformat(); return True
    def reset_failed(self):
        for job in self.jobs:
            if job.state in (RenderState.FAILED, RenderState.CANCELLED):
                job.state=RenderState.QUEUED; job.progress=0.0; job.error=""; job.finished=""
    def to_dict(self): return [j.to_dict() for j in self.jobs]
    def save(self,path):
        p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(self.to_dict(),ensure_ascii=False,indent=2),encoding="utf-8")
        return p
    @classmethod
    def load(cls,path):
        p=Path(path); q=cls()
        if not p.is_file(): return q
        try: return cls.from_dict(json.loads(p.read_text(encoding="utf-8")))
        except (OSError,ValueError,TypeError,KeyError): return q
    @classmethod
    def from_dict(cls,d):
        q=cls(); q.jobs=[RenderJob.from_dict(x) for x in (d or [])]; return q
