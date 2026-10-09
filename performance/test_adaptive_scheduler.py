from app.performance.adaptive_scheduler import AdaptiveRenderScheduler, AdaptivePolicy
from app.performance.render_scheduler import ResourceSnapshot, SchedulerPolicy
class J:
    def __init__(self,kind): self.kind=kind
def test_priority_prefers_preview_over_long():
    s=AdaptiveRenderScheduler(AdaptivePolicy(base=SchedulerPolicy(max_parallel=1)),lambda:ResourceSnapshot(10,10)); assert s.priority(J('preview'))>s.priority(J('long'))
def test_score_has_headroom_component():
    s=AdaptiveRenderScheduler(AdaptivePolicy(base=SchedulerPolicy(max_parallel=1)),lambda:ResourceSnapshot(20,30)); assert s.score(J('short'))>s.priority(J('short'))
def test_acquire_for_preserves_resource_gate():
    s=AdaptiveRenderScheduler(AdaptivePolicy(base=SchedulerPolicy(max_parallel=1)),lambda:ResourceSnapshot(95,10)); assert not s.acquire_for(J('long'),timeout=.01)


def test_vram_limit_blocks_render():
    s=AdaptiveRenderScheduler(AdaptivePolicy(base=SchedulerPolicy(max_parallel=1,max_vram_percent=80)),lambda:ResourceSnapshot(10,10,85))
    assert not s.acquire_for(J("short"),timeout=.01)
