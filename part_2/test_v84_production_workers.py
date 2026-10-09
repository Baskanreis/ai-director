import time
from pathlib import Path
from app.youtube.production_queue import ProductionQueue, ProductionJob, ProductionState

def test_parallel_workers_and_progress(tmp_path):
    q=ProductionQueue(max_workers=2); outs=[]
    def renderer(j, progress):
        outs.append(j.id)
        for i in range(5): progress((i+1)/5); time.sleep(.01)
        Path(j.output_path).write_text('ok'); return {'rendered':True}
    def qc(j): return {'ok':True,'score':1}
    jobs=[q.add(ProductionJob('short',str(i),str(tmp_path/f'{i}.mp4'))) for i in range(2)]
    fs=[q.submit(j,renderer=renderer,qc=qc) for j in jobs]
    [f.result(timeout=3) for f in fs]
    assert all(j.state==ProductionState.DONE for j in jobs)
    assert all(j.progress==1 for j in jobs); q.shutdown()

def test_cancel_and_retry(tmp_path):
    q=ProductionQueue()
    j=q.add(ProductionJob('video','x',str(tmp_path/'x.mp4'),max_retries=2))
    q.cancel(j.id); assert j.state==ProductionState.CANCELLED
    j.state=ProductionState.FAILED; assert q.retry(j.id); assert j.state==ProductionState.QUEUED
    q.shutdown()


def test_pause_resume_blocks_progress(tmp_path):
    q=ProductionQueue(); j=q.add(ProductionJob('video','pause',str(tmp_path/'p.mp4')))
    gate=[]
    def renderer(job, progress):
        progress(.2); assert q.pause(job.id); gate.append(job.state); time.sleep(.03); q.resume(job.id); progress(.8); Path(job.output_path).write_text('ok')
    f=q.submit(j,renderer=renderer,qc=lambda _: {'ok':True})
    f.result(timeout=3); assert gate==[ProductionState.PAUSED]; assert j.state==ProductionState.DONE; q.shutdown()
