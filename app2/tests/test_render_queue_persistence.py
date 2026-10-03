from app.pro.render_queue import RenderJob, RenderQueue, RenderState

def test_queue_roundtrip_and_cancel(tmp_path):
    q=RenderQueue(); job=q.add(RenderJob(str(tmp_path/'out.mp4'), {'hardware_accel':'auto'}, 'Short'))
    path=q.save(tmp_path/'queue.json')
    loaded=RenderQueue.load(path)
    assert loaded.jobs[0].name=='Short'
    assert loaded.jobs[0].settings['hardware_accel']=='auto'
    assert loaded.cancel(job.id)
    assert loaded.jobs[0].state is RenderState.CANCELLED
