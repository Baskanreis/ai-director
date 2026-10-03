# Qt QVideoFrame -> GPU -> Compositor -> QVideoSink

## Implemented in v2.26.7

- `PreviewPlayer` now observes the real `QVideoWidget.videoSink()`.
- `QVideoFrameBridge` consumes `videoFrameChanged()` and detects
  `QVideoFrame.HandleType.RhiTextureHandle`.
- RHI-backed frames remain opaque and are passed to the backend-neutral
  compositor as `TextureFrame`; the frame is never mapped to CPU memory on the
  normal path.
- `PreviewCompositorBackend.accept_qvideo_frame()` is the integration seam for
  effects/compositor code.
- CPU frames are counted and remain available as a fallback; no automatic
  `map()` call is performed.
- `preview_gpu_stats()` exposes GPU/CPU/zero-copy counters for telemetry.

## Important Qt limitation

PySide6 exposes `RhiTextureHandle` and `QVideoSink.rhi()`, but the native
texture handle accessor is not exposed as a stable Python API. Therefore this
patch deliberately does not fabricate a numeric texture ID. The `QVideoFrame`
object is retained as the opaque owner of the RHI resource. A future native
C++/Shiboken adapter can unwrap the backend-specific resource for custom QRhi
render passes without changing the Python pipeline contract.

## Recommended next rendering stage

For actual GPU effects (color, LUT, transforms, blur, masks, transitions), use
a QRhi/Qt Quick render surface as the compositor target. Keep the `QVideoSink`
as the decode/frame source and submit the RHI-backed frame into the compositor
render pass. Avoid `QVideoFrame.map()` except for explicitly CPU-only effects.
