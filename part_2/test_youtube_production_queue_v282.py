import tempfile
from pathlib import Path
from app.youtube.production_queue import ProductionQueue, ProductionJob, ProductionState

def test_long_video_done():
    with tempfile.TemporaryDirectory() as td:
        out=Path(td)/'video.mp4'; q=ProductionQueue(); j=q.add(ProductionJob('video','Main',str(out)))
        def render(job, progress): out.write_bytes(b'ok'); progress(1); return {'rendered':True}
        def qc(job): return {'ok':True,'score':96}
        def upload(job, progress): progress(1); return {'video_id':'abc'}
        q.run_one(j,renderer=render,qc=qc,uploader=upload)
        assert j.state==ProductionState.DONE and j.result['video_id']=='abc'

def test_qc_failure_does_not_upload():
    with tempfile.TemporaryDirectory() as td:
        out=Path(td)/'short.mp4'; q=ProductionQueue(); j=q.add(ProductionJob('short','Short',str(out))); calls=[]
        def render(job, progress): out.write_bytes(b'ok'); return {}
        def qc(job): return {'ok':False,'score':42}
        def upload(job, progress): calls.append(1); return {}
        q.run_one(j,renderer=render,qc=qc,uploader=upload)
        assert j.state==ProductionState.FAILED and calls==[]

def test_serialization_and_cancel():
    q=ProductionQueue(); j=q.add(ProductionJob('thumbnail','Thumb','x.jpg')); data=q.to_dict(); q2=ProductionQueue.from_dict(data); assert q2.jobs[0].id==j.id; assert q.cancel(j.id) is True; assert j.state==ProductionState.CANCELLED
