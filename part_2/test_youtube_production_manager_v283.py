from pathlib import Path
from app.youtube.production_manager import YouTubeProductionManager
from app.youtube.production_queue import ProductionState

def test_manager_summary_and_cancel(tmp_path):
    m=YouTubeProductionManager(); a=m.add_job('long','Long',str(tmp_path/'a.mp4')); b=m.add_job('short','Short',str(tmp_path/'b.mp4'))
    s=m.summary(); assert (s.total,s.queued,s.active)==(2,2,0)
    assert m.cancel(a.id); assert a.state==ProductionState.CANCELLED
    assert m.summary().cancelled==1

def test_manager_roundtrip(tmp_path):
    m=YouTubeProductionManager(); m.add_job('thumbnail','Thumb',str(tmp_path/'t.jpg'),{'privacy_status':'private'})
    restored=YouTubeProductionManager.from_dict(m.to_dict())
    assert len(restored.queue.jobs)==1
    assert restored.queue.jobs[0].publish_plan['privacy_status']=='private'
