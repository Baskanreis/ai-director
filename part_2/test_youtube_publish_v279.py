from pathlib import Path
from datetime import datetime, timezone, timedelta
from app.youtube.publish import PublishPlan, validate_publish_plan, YouTubePublishClient

def test_publish_plan_qc(tmp_path):
    video=tmp_path/'video.mp4'; video.write_bytes(b'video')
    plan=PublishPlan(str(video),'Test Video',description='desc',tags=('one','two'),privacy_status='private')
    qc=validate_publish_plan(plan)
    assert qc.ok and qc.warnings

def test_scheduled_publish_requires_private_and_future(tmp_path):
    video=tmp_path/'video.mp4'; video.write_bytes(b'video')
    future=(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat()
    bad=PublishPlan(str(video),'Test',privacy_status='public',publish_at=future)
    assert not validate_publish_plan(bad).ok
    good=PublishPlan(str(video),'Test',privacy_status='private',publish_at=future)
    assert validate_publish_plan(good).ok

def test_injected_uploader(tmp_path):
    video=tmp_path/'video.mp4'; video.write_bytes(b'video')
    seen=[]
    client=YouTubePublishClient('',uploader=lambda plan, progress: seen.append(plan.title) or {'video_id':'abc'})
    out=client.upload(PublishPlan(str(video),'Hello',description='x',tags=('a','b','c','d','e')))
    assert out['video_id']=='abc' and seen==['Hello']
