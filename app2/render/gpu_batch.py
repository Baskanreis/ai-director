"""GPU-aware isolated batch rendering with per-device concurrency limits."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from threading import Semaphore
from .controller import RenderController, RenderJob
@dataclass(frozen=True)
class GPUWorker:
    device:str='cpu'; slots:int=1
class ParallelGPUBatch:
    def __init__(self,controller:RenderController|None=None,workers:list[GPUWorker]|None=None):
        self.controller=controller or RenderController(); self.workers=workers or [GPUWorker()]
        self._sems={w.device:Semaphore(max(1,w.slots)) for w in self.workers}
    def render(self,items:list[tuple[str,RenderJob]],on_done=None)->list[Path]:
        if not items:return []
        results=[None]*len(items)
        def run(i,name,job,worker):
            with self._sems[worker.device]:
                out=self.controller.render(job)
                return i,out
        futures=[]
        with ThreadPoolExecutor(max_workers=sum(max(1,w.slots) for w in self.workers)) as ex:
            for i,(name,job) in enumerate(items): futures.append(ex.submit(run,i,name,job,self.workers[i%len(self.workers)]))
            for f in as_completed(futures):
                i,out=f.result(); results[i]=out
                if on_done:on_done(i+1,len(items),out)
        return [x for x in results if x is not None]
