from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path
from typing import Any, Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Event, RLock
from time import monotonic
try:
    from app.performance.render_scheduler import RenderAdmission
except Exception:
    RenderAdmission = None

class ProductionState(str, Enum):
    QUEUED='queued'; RENDERING='rendering'; QC='qc'; UPLOADING='uploading'; DONE='done'; FAILED='failed'; CANCELLED='cancelled'; PAUSED='paused'

@dataclass
class ProductionJob:
    kind: str
    name: str
    output_path: str
    publish_plan: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid4().hex)
    state: ProductionState = ProductionState.QUEUED
    progress: float = 0.0
    error: str = ''
    qc: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    attempts: int = 0
    max_retries: int = 2
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self):
        d=asdict(self); d['state']=self.state.value; return d
    @classmethod
    def from_dict(cls,d):
        x=cls(kind=str(d['kind']),name=str(d['name']),output_path=str(d['output_path']),publish_plan=dict(d.get('publish_plan') or {}),id=str(d.get('id') or uuid4().hex))
        x.state=ProductionState(d.get('state',ProductionState.QUEUED.value)); x.progress=float(d.get('progress',0)); x.error=str(d.get('error','')); x.qc=dict(d.get('qc') or {}); x.result=dict(d.get('result') or {}); x.created=str(d.get('created',x.created)); x.attempts=int(d.get('attempts',0)); x.max_retries=int(d.get('max_retries',2)); return x

class ProductionQueue:
    """Threaded orchestration model. Transports are injected; workers are bounded and cancellable."""
    def __init__(self, max_workers:int=2, scheduler=None):
        if max_workers < 1: raise ValueError('max_workers must be >= 1')
        self.jobs:list[ProductionJob]=[]; self.max_workers=max_workers; self.scheduler=scheduler
        self._executor=ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='aidir-production')
        self._lock=RLock(); self._pause:dict[str,Event]={}; self._cancel:dict[str,Event]={}; self._futures={}
    def add(self,job:ProductionJob):
        with self._lock:
            self.jobs.append(job); self._pause[job.id]=Event(); self._cancel[job.id]=Event(); return job
    def _job(self,job_id): return next((j for j in self.jobs if j.id==job_id),None)
    def cancel(self,job_id:str):
        with self._lock:
            j=self._job(job_id)
            if not j or j.state in {ProductionState.DONE,ProductionState.FAILED,ProductionState.CANCELLED}: return False
            self._cancel[job_id].set(); self._pause[job_id].set();
            if j.state==ProductionState.QUEUED: j.state=ProductionState.CANCELLED
            return True
    def pause(self,job_id:str):
        with self._lock:
            j=self._job(job_id)
            if not j or j.state not in {ProductionState.RENDERING,ProductionState.UPLOADING}: return False
            self._pause[job_id].clear(); j.state=ProductionState.PAUSED; return True
    def resume(self,job_id:str):
        with self._lock:
            j=self._job(job_id)
            if not j or j.state!=ProductionState.PAUSED: return False
            self._pause[job_id].set(); j.state=ProductionState.RENDERING; return True
    def retry(self,job_id:str):
        with self._lock:
            j=self._job(job_id)
            if not j or j.state!=ProductionState.FAILED or j.attempts>=j.max_retries: return False
            j.state=ProductionState.QUEUED; j.error=''; j.progress=0; return True
    def next(self):
        queued=[j for j in self.jobs if j.state==ProductionState.QUEUED]
        if not queued: return None
        if self.scheduler is not None and hasattr(self.scheduler, "priority"):
            return max(queued, key=lambda j: self.scheduler.priority(j))
        return queued[0]
    def to_dict(self): return [j.to_dict() for j in self.jobs]
    @classmethod
    def from_dict(cls,d):
        q=cls(); q.jobs=[ProductionJob.from_dict(x) for x in (d or [])]
        for j in q.jobs: q._pause[j.id]=Event(); q._cancel[j.id]=Event()
        return q
    def _wait_gate(self,job):
        gate=self._pause[job.id]
        while not gate.wait(0.05):
            if self._cancel[job.id].is_set(): return False
        return not self._cancel[job.id].is_set()
    def _progress(self,job,p):
        if not self._wait_gate(job): raise RuntimeError('Job cancelled')
        job.progress=max(0,min(1,float(p)))
    def run_one(self, job:ProductionJob, *, renderer:Callable[[ProductionJob,Callable[[float],None]],dict[str,Any]], qc:Callable[[ProductionJob],dict[str,Any]], uploader:Callable[[ProductionJob,Callable[[float],None]],dict[str,Any]]|None=None):
        with self._lock:
            if job.state!=ProductionState.QUEUED: return job
            job.attempts+=1; job.state=ProductionState.RENDERING; self._pause[job.id].set()
        started=monotonic()
        try:
            if self.scheduler is not None and not (self.scheduler.acquire_for(job, self._cancel[job.id]) if hasattr(self.scheduler, "acquire_for") else self.scheduler.acquire(self._cancel[job.id])):
                job.state=ProductionState.CANCELLED if self._cancel[job.id].is_set() else ProductionState.FAILED
                job.error="Render admission denied"
                return job
            try:
                job.result=renderer(job, lambda p:self._progress(job,p)) or {}
            finally:
                if self.scheduler is not None:
                    intelligence=getattr(self.scheduler, "intelligence", None)
                    if intelligence is not None:
                        try:
                            snap=self.scheduler.snapshot()
                            features = getattr(job, "render_features", None)
                            if hasattr(features, "__dataclass_fields__"):
                                features = {k:getattr(features,k) for k in features.__dataclass_fields__}
                            intelligence.record(job.kind, monotonic()-started, cpu=snap.cpu, gpu=snap.gpu, vram=snap.vram, success=job.state != ProductionState.CANCELLED, features=features)
                        except Exception:
                            pass
                    self.scheduler.release()
            if self._cancel[job.id].is_set(): job.state=ProductionState.CANCELLED; return job
            if not Path(job.output_path).exists(): raise RuntimeError('Render output not found')
            job.state=ProductionState.QC; job.qc=qc(job) or {}
            if not job.qc.get('ok',False): raise RuntimeError('Production QC failed')
            if uploader:
                job.state=ProductionState.UPLOADING
                job.result.update(uploader(job, lambda p:self._progress(job,p)) or {})
            job.state=ProductionState.DONE; job.progress=1.0
        except Exception as exc:
            if self._cancel[job.id].is_set(): job.state=ProductionState.CANCELLED
            else: job.state=ProductionState.FAILED; job.error=str(exc)
        return job
    def submit(self,job:ProductionJob,**kwargs):
        f=self._executor.submit(self.run_one,job,**kwargs); self._futures[job.id]=f; return f
    def shutdown(self,wait=True): self._executor.shutdown(wait=wait, cancel_futures=True)
