from app.performance.hardware_acceleration import (
    GPUVendor, HardwareCapabilities, RendererBackend, select_renderer,
)


def test_nvidia_selects_qt_preview_and_hardware_render():
    caps = HardwareCapabilities("Windows", GPUVendor.NVIDIA, "GeForce", True, True, True, ("h264_nvenc",))
    selection = select_renderer(caps)
    assert selection.preview_backend is RendererBackend.QT_MULTIMEDIA
    assert selection.render_backend is RendererBackend.FFMPEG_HARDWARE


def test_cpu_fallback_is_safe():
    caps = HardwareCapabilities("Linux", GPUVendor.UNKNOWN, None, False, False, False)
    selection = select_renderer(caps)
    assert selection.preview_backend is RendererBackend.CPU_FALLBACK
    assert selection.render_backend is RendererBackend.CPU_FALLBACK


def test_qt_preview_can_work_without_ffmpeg_encoder():
    caps = HardwareCapabilities("Windows", GPUVendor.INTEL, "UHD", True, False, True, ())
    selection = select_renderer(caps)
    assert selection.preview_backend is RendererBackend.QT_MULTIMEDIA
    assert selection.render_backend is RendererBackend.CPU_FALLBACK
