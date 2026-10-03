import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication, QSize
from PySide6.QtMultimedia import QVideoFrame, QVideoFrameFormat, QVideoSink
from app.preview.qt_video_bridge import QVideoFrameBridge


def test_bridge_receives_cpu_frame_without_mapping():
    app = QCoreApplication.instance() or QCoreApplication([])
    sink = QVideoSink()
    seen = []
    bridge = QVideoFrameBridge(sink, "software", seen.append)
    frame = QVideoFrame(QVideoFrameFormat(QSize(16, 16), QVideoFrameFormat.PixelFormat.Format_RGBA8888))
    sink.setVideoFrame(frame)
    app.processEvents()
    assert seen
    assert seen[-1].gpu_backed is False
    assert bridge.cpu_frames == 1
    bridge.close()
