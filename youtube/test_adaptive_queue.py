from app.youtube.production_queue import ProductionQueue,ProductionJob
from app.performance.adaptive_scheduler import AdaptiveRenderScheduler,AdaptivePolicy
from app.performance.render_scheduler import ResourceSnapshot,SchedulerPolicy
def test_queue_uses_adaptive_priority():
    s=AdaptiveRenderScheduler(AdaptivePolicy(base=SchedulerPolicy(max_parallel=1)),lambda:ResourceSnapshot(10,10)); q=ProductionQueue(max_workers=1,scheduler=s)
    q.add(ProductionJob('long','Long','long.mp4')); b=q.add(ProductionJob('preview','Preview','preview.mp4')); assert q.next() is b; q.shutdown()
