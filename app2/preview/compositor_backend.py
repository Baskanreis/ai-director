"""Low-level preview compositor backend selection.

The actual Qt video surface remains responsible for presenting frames. This
layer prevents accidental CPU mapping: GPU-backed frames are passed through as
TextureFrame handles, while effects that require CPU pixels explicitly request
a software fallback.
"""
from __future__ import annotations

from dataclasses import dataclass
from .gpu_backend import GPUBackend, TextureFrame, can_zero_copy, select_backend


@dataclass(frozen=True)
class CompositeStats:
    frames: int = 0
    gpu_frames: int = 0
    cpu_frames: int = 0
    zero_copy_frames: int = 0


class PreviewCompositorBackend:
    def __init__(self, preferred: str = "auto", env: dict[str, str] | None = None) -> None:
        self.backend: GPUBackend = select_backend(preferred, env=env)
        self.stats = CompositeStats()

    @property
    def zero_copy_enabled(self) -> bool:
        return self.backend.zero_copy and self.backend.available

    def accept_frame(self, frame: TextureFrame | object, pixel_format: str = "NV12") -> TextureFrame | object:
        gpu = isinstance(frame, TextureFrame) and can_zero_copy(self.backend, pixel_format)
        self.stats = CompositeStats(
            frames=self.stats.frames + 1,
            gpu_frames=self.stats.gpu_frames + int(gpu),
            cpu_frames=self.stats.cpu_frames + int(not gpu),
            zero_copy_frames=self.stats.zero_copy_frames + int(gpu and frame.zero_copy),
        )
        return frame

    def accept_qvideo_frame(self, info: object) -> TextureFrame | object:
        """Accept a frame produced by the real Qt QVideoSink bridge.

        The bridge deliberately supplies a TextureFrame only for RHI-backed
        QVideoFrames. No QVideoFrame.map() is called here.
        """
        texture = getattr(info, "texture", None)
        pixel_format = getattr(info, "pixel_format", "UNKNOWN")
        frame = getattr(info, "frame", info)
        return self.accept_frame(texture if texture is not None else frame, pixel_format)

    def requires_cpu_mapping(self, effect_requires_pixels: bool = False) -> bool:
        return effect_requires_pixels or not self.zero_copy_enabled

    def reset_stats(self) -> None:
        self.stats = CompositeStats()


__all__ = ["PreviewCompositorBackend", "CompositeStats"]
