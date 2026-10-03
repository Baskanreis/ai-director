from app.preview.gpu_backend import TextureFrame, can_zero_copy, ffmpeg_hwaccel_args, select_backend
from app.preview.compositor_backend import PreviewCompositorBackend


def test_software_backend_is_always_available():
    b = select_backend("software", env={})
    assert b.name == "software"
    assert ffmpeg_hwaccel_args(b) == []
    assert not can_zero_copy(b)


def test_forced_windows_backend_and_zero_copy():
    b = select_backend("d3d11va", env={"AI_DIRECTOR_FORCE_D3D11VA": "1"})
    assert b.name == "d3d11va"
    assert b.zero_copy
    assert ffmpeg_hwaccel_args(b) == ["-hwaccel", "d3d11va"]
    assert can_zero_copy(b, "NV12")


def test_compositor_keeps_texture_handle_without_mapping():
    c = PreviewCompositorBackend("d3d11va", env={"AI_DIRECTOR_FORCE_D3D11VA": "1"})
    frame = TextureFrame("d3d11va", "texture:42", 1920, 1080)
    out = c.accept_frame(frame)
    assert out is frame
    assert c.stats.zero_copy_frames == 1
    assert not c.requires_cpu_mapping(False)
    assert c.requires_cpu_mapping(True)
