from threading import Event
from app.performance.render_scheduler import RenderAdmission, ResourceSnapshot, SchedulerPolicy

def test_parallel_limit():
    s=RenderAdmission(SchedulerPolicy(max_parallel=1), lambda: ResourceSnapshot(10,10))
    assert s.acquire(timeout=.01); assert s.active==1
    assert not s.acquire(timeout=.01); s.release(); assert s.active==0

def test_high_load_blocks():
    s=RenderAdmission(SchedulerPolicy(max_parallel=2,max_cpu_percent=80), lambda: ResourceSnapshot(95,10))
    assert not s.acquire(timeout=.01)

def test_unknown_gpu_is_allowed():
    s=RenderAdmission(SchedulerPolicy(max_parallel=1), lambda: ResourceSnapshot(20,None))
    assert s.acquire(timeout=.01); s.release()

def test_cancel_while_waiting():
    e=Event(); s=RenderAdmission(SchedulerPolicy(max_parallel=1), lambda: ResourceSnapshot(95,95))
    e.set(); assert not s.acquire(e, timeout=.05)
