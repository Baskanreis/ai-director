"""Qt Multimedia -> backend-neutral GPU frame bridge.

The bridge observes the real QVideoSink used by the preview widget. It never
maps QVideoFrame to CPU memory on the normal path. Qt 6 exposes GPU-backed
frames as QVideoFrame.RhiTextureHandle; the native texture itself remains
owned by Qt/RHI and is only referenced for the lifetime of the frame.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

try:
    from PySide6.QtMultimedia import QVideoFrame, QVideoSink
except Exception:  # Allows the backend module/tests to import without Qt.
    QVideoFrame = object  # type: ignore[misc,assignment]
    QVideoSink = object  # type: ignore[misc,assignment]

from .gpu_backend import TextureFrame


@dataclass(frozen=True)
class VideoFrameInfo:
    frame: object
    texture: TextureFrame | None
    gpu_backed: bool
    pixel_format: str
    width: int
    height: int
    start_time_us: int = -1
    end_time_us: int = -1


def _enum_name(value: object) -> str:
    return str(value).split(".")[-1].lower()


def _pixel_format_name(frame: object) -> str:
    try:
        value = frame.surfaceFormat().pixelFormat()
        return _enum_name(value).replace("format_", "").upper()
    except Exception:
        return "UNKNOWN"


def _handle_token(frame: object) -> object:
    """Keep the QVideoFrame itself as the opaque RHI resource owner.

    PySide6 does not expose the native QVideoFrame handle() accessor. Keeping
    the shallow QVideoFrame reference preserves the resource lifetime and avoids
    inventing a fake texture ID. A native C++ adapter can unwrap it later.
    """
    return frame


class QVideoFrameBridge:
    """Connect a real QVideoSink to PreviewCompositorBackend.

    `on_frame` receives VideoFrameInfo for every decoded frame. GPU-backed
    frames are represented by a TextureFrame handle token and are never mapped.
    CPU fallback is deliberately not performed here.
    """

    def __init__(self, sink: QVideoSink, backend_name: str, on_frame: Callable[[VideoFrameInfo], None] | None = None) -> None:
        self.sink = sink
        self.backend_name = backend_name
        self.on_frame = on_frame
        self.last: VideoFrameInfo | None = None
        self.frames = 0
        self.gpu_frames = 0
        self.cpu_frames = 0
        sink.videoFrameChanged.connect(self._on_video_frame)

    def _is_rhi_texture(self, frame: object) -> bool:
        try:
            return frame.handleType() == QVideoFrame.HandleType.RhiTextureHandle
        except Exception:
            return False

    def _on_video_frame(self, frame: object) -> None:
        self.frames += 1
        gpu = self._is_rhi_texture(frame)
        fmt = _pixel_format_name(frame)
        texture = None
        try:
            size = frame.size()
            if gpu:
                texture = TextureFrame(
                    backend=self.backend_name,
                    handle=_handle_token(frame),
                    width=int(size.width()),
                    height=int(size.height()),
                    format=fmt,
                    zero_copy=True,
                )
        except Exception:
            size = None
        if gpu:
            self.gpu_frames += 1
        else:
            self.cpu_frames += 1
        info = VideoFrameInfo(
            frame=frame,
            texture=texture,
            gpu_backed=gpu,
            pixel_format=fmt,
            width=int(size.width()) if size is not None else int(frame.width()),
            height=int(size.height()) if size is not None else int(frame.height()),
            start_time_us=int(getattr(frame, "startTime", lambda: -1)()),
            end_time_us=int(getattr(frame, "endTime", lambda: -1)()),
        )
        self.last = info
        if self.on_frame:
            self.on_frame(info)

    def close(self) -> None:
        try:
            self.sink.videoFrameChanged.disconnect(self._on_video_frame)
        except (RuntimeError, TypeError):
            pass


__all__ = ["VideoFrameInfo", "QVideoFrameBridge"]
