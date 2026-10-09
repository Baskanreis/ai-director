"""Background-friendly proxy generation queue model."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

class ProxyJobState(str, Enum):
    QUEUED="queued"; RUNNING="running"; PAUSED="paused"; DONE="done"; FAILED="failed"; CANCELLED="cancelled"

@dataclass
class ProxyJob:
    media_id: str
    source: str
    output: str
    priority: int = 0
    id: str = field(default_factory=lambda: uuid4().hex)
    state: ProxyJobState = ProxyJobState.QUEUED
    progress: float = 0.0
    error: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return {"id": self.id, "media_id": self.media_id, "source": self.source, "output": self.output,
                "priority": self.priority, "state": self.state.value, "progress": self.progress, "error": self.error, "metadata": dict(self.metadata)}

    @classmethod
    def from_dict(cls, d):
        j = cls(str(d["media_id"]), str(d["source"]), str(d["output"]), int(d.get("priority", 0)), str(d.get("id") or uuid4().hex))
        j.state = ProxyJobState(d.get("state", "queued")); j.progress = max(0.0, min(100.0, float(d.get("progress", 0)))); j.error = str(d.get("error", "")); j.metadata = dict(d.get("metadata", {}) or {}); return j

class ProxyQueue:
    def __init__(self): self.jobs: list[ProxyJob] = []
    def add(self, job: ProxyJob): self.jobs.append(job); self.jobs.sort(key=lambda x: (-x.priority, x.id)); return job
    def next(self): return next((j for j in self.jobs if j.state == ProxyJobState.QUEUED), None)
    def has_media(self, media_id: str, *, active_only: bool = True) -> bool:
        states = {ProxyJobState.QUEUED, ProxyJobState.RUNNING, ProxyJobState.PAUSED} if active_only else set(ProxyJobState)
        return any(j.media_id == media_id and j.state in states for j in self.jobs)
    def add_if_missing(self, job: ProxyJob) -> ProxyJob:
        if self.has_media(job.media_id):
            return next(j for j in self.jobs if j.media_id == job.media_id and j.state in {ProxyJobState.QUEUED, ProxyJobState.RUNNING, ProxyJobState.PAUSED})
        return self.add(job)
    def cancel(self, job_id: str) -> bool:
        for j in self.jobs:
            if j.id == job_id and j.state in {ProxyJobState.QUEUED, ProxyJobState.PAUSED}:
                j.state = ProxyJobState.CANCELLED; return True
        return False
    def to_dict(self): return [j.to_dict() for j in self.jobs]
    @classmethod
    def from_dict(cls, data):
        q = cls(); q.jobs = [ProxyJob.from_dict(x) for x in (data or [])]; q.jobs.sort(key=lambda x: (-x.priority, x.id)); return q
