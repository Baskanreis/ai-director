from pathlib import Path
from app.youtube.health import check_youtube_health
from app.youtube.production_manager import YouTubeProductionManager
from app.youtube.production_queue import ProductionJob

def test_youtube_health_shape():
    h=check_youtube_health()
    assert hasattr(h,'oauth_token_present')
    assert isinstance(h.messages, tuple)

def test_existing_upload_requires_real_output(tmp_path):
    m=YouTubeProductionManager()
    job=m.add_job('long','Existing',str(tmp_path/'missing.mp4'))
    f=m.submit_existing_upload(job, lambda j,p: {})
    out=f.result(timeout=3)
    assert out.state.value == 'failed'
    assert 'missing.mp4' in out.error
    m.queue.shutdown()
