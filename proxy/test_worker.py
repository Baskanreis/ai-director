from pathlib import Path
from threading import Event
from app.proxy import FFmpegProxyWorker, ProxyJob, ProxyJobState, ProxyProfile


def test_command_uses_temp_output_and_scale():
    w = FFmpegProxyWorker(ffmpeg="ffmpeg", profile=ProxyProfile(height=540))
    cmd = w.command(ProxyJob("m", "input.mov", "output.mp4"))
    assert "-vf" in cmd and "scale=-2:540:flags=bicubic" in cmd
    assert "-nostdin" in cmd and "-progress" in cmd
    assert cmd[-1] == "output.mp4"


def test_cancel_before_start_does_not_spawn_ffmpeg(tmp_path):
    w = FFmpegProxyWorker(ffmpeg=str(tmp_path / "missing-ffmpeg"))
    job = ProxyJob("m", "input.mov", str(tmp_path / "out.mp4"))
    cancel = Event(); cancel.set()
    result = w.run(job, cancel=cancel)
    assert result.state == ProxyJobState.CANCELLED
    assert not Path(result.output).exists()


def test_progress_parser():
    assert FFmpegProxyWorker._progress_seconds("out_time_ms=2500000") == 2.5
    assert FFmpegProxyWorker._progress_seconds("frame=10") is None


def test_service_cancel_queued_job(tmp_path):
    from app.proxy import ProxyGenerationService
    service = ProxyGenerationService(worker=FFmpegProxyWorker(ffmpeg=str(tmp_path / "missing")))
    try:
        job = service.add(ProxyJob("m", "in.mov", str(tmp_path / "out.mp4"), priority=10))
        assert service.cancel(job.id)
        assert job.state == ProxyJobState.CANCELLED
    finally:
        service.shutdown()


def test_service_background_pause_blocks_submit_next(tmp_path):
    from app.proxy.queue import ProxyJob
    from app.proxy.service import ProxyGenerationService
    service = ProxyGenerationService(max_workers=1)
    try:
        service.add(ProxyJob("m", str(tmp_path / "missing.mp4"), str(tmp_path / "out.mp4"), priority=10))
        service.set_background_paused(True)
        assert service.submit_next() is None
        assert service.background_paused is True
    finally:
        service.shutdown()


def test_service_boost_queued_priorities_only(tmp_path):
    from app.proxy.queue import ProxyJob, ProxyJobState
    from app.proxy.service import ProxyGenerationService
    service = ProxyGenerationService(max_workers=1)
    try:
        queued = ProxyJob("q", str(tmp_path / "q.mp4"), str(tmp_path / "q_out.mp4"), priority=2)
        running = ProxyJob("r", str(tmp_path / "r.mp4"), str(tmp_path / "r_out.mp4"), priority=5)
        running.state = ProxyJobState.RUNNING
        service.add(queued); service.add(running)
        service.boost_queued_priorities(100)
        assert queued.priority == 102
        assert running.priority == 5
    finally:
        service.shutdown()
