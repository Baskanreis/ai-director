from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .production_queue import ProductionQueue, ProductionJob, ProductionState

@dataclass(frozen=True)
class QueueSummary:
    total: int; queued: int; active: int; paused: int; done: int; failed: int; cancelled: int

class YouTubeProductionManager:
    def __init__(self, queue: ProductionQueue | None = None, max_workers:int=2):
        self.queue = queue or ProductionQueue(max_workers=max_workers); self.listeners:list[Any]=[]
    def add_job(self, kind:str,name:str,output_path:str,publish_plan:dict[str,Any]|None=None,max_retries:int=2)->ProductionJob:
        return self.queue.add(ProductionJob(kind=kind,name=name,output_path=output_path,publish_plan=publish_plan or {},max_retries=max_retries))
    def summary(self)->QueueSummary:
        states=[j.state for j in self.queue.jobs]
        return QueueSummary(len(states),states.count(ProductionState.QUEUED),sum(s in {ProductionState.RENDERING,ProductionState.QC,ProductionState.UPLOADING} for s in states),states.count(ProductionState.PAUSED),states.count(ProductionState.DONE),states.count(ProductionState.FAILED),states.count(ProductionState.CANCELLED))
    def _action(self,fn,job_id):
        changed=fn(job_id)
        if changed:self.notify()
        return changed
    def cancel(self,job_id): return self._action(self.queue.cancel,job_id)
    def pause(self,job_id): return self._action(self.queue.pause,job_id)
    def resume(self,job_id): return self._action(self.queue.resume,job_id)
    def retry(self,job_id): return self._action(self.queue.retry,job_id)
    def submit(self,job,**kwargs):
        f=self.queue.submit(job,**kwargs); self.notify(); return f
    def submit_existing_upload(self, job, uploader):
        """Upload an already-rendered output without pretending the queue can render by itself."""
        def renderer(j, progress):
            if not Path(j.output_path).exists():
                raise FileNotFoundError(j.output_path)
            progress(1.0)
            return {"output_path": j.output_path}
        from pathlib import Path
        return self.submit(job, renderer=renderer, qc=lambda j: {"ok": True}, uploader=uploader)
    def notify(self):
        s=self.summary()
        for cb in tuple(self.listeners): cb(s)
    def to_dict(self): return self.queue.to_dict()
    @classmethod
    def from_dict(cls,data): return cls(ProductionQueue.from_dict(data))
