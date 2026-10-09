from app.proxy import SmartProxyProfileSelector, FFmpegProxyWorker, ProxyJob, ProxyProfile


def test_4k_under_pressure_selects_540p():
    c = SmartProxyProfileSelector().choose({"width":3840,"height":2160,"cpu_pressure":.9,"storage_pressure":.2})
    assert c.height == 540


def test_4k_normal_load_selects_720p():
    c = SmartProxyProfileSelector().choose({"width":3840,"height":2160,"fps":60,"cpu_pressure":.2,"gpu_pressure":.2})
    assert c.height == 720


def test_light_source_does_not_get_oversized_proxy():
    c = SmartProxyProfileSelector().choose({"width":1280,"height":720})
    assert c.height <= 720


def test_worker_uses_job_metadata_profile():
    w = FFmpegProxyWorker(ffmpeg="ffmpeg")
    j = ProxyJob("m", "in.mov", "out.mp4", metadata={"width":3840,"height":2160,"cpu_pressure":.95})
    cmd = w.command(j)
    assert "scale=-2:540:flags=bicubic" in cmd


def test_explicit_profile_overrides_selector():
    w = FFmpegProxyWorker(ffmpeg="ffmpeg", profile=ProxyProfile(height=1080, crf=20, preset="veryfast"))
    j = ProxyJob("m", "in.mov", "out.mp4", metadata={"width":3840,"height":2160,"cpu_pressure":.99})
    cmd = w.command(j)
    assert "scale=-2:1080:flags=bicubic" in cmd
