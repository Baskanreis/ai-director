from pathlib import Path
from threading import Event
from tempfile import TemporaryDirectory
from app.performance.render_scheduler import RenderAdmission, ResourceSnapshot, SchedulerPolicy
from app.youtube.production_queue import ProductionQueue, ProductionJob, ProductionState

def test_scheduler_integrates_with_production_queue():
    with TemporaryDirectory() as d:
        out=Path(d)/"out.mp4"; scheduler=RenderAdmission(SchedulerPolicy(max_parallel=1), lambda: ResourceSnapshot(10,10))
        q=ProductionQueue(max_workers=1, scheduler=scheduler); job=ProductionJob("long","x",str(out))
        q.add(job)
        def renderer(j, progress): progress(.5); out.write_bytes(b"ok"); progress(1); return {}
        r=q.run_one(job, renderer=renderer, qc=lambda j:{"ok":True})
        assert r.state==ProductionState.DONE and scheduler.active==0
        q.shutdown()
