# AI Director v2.26

## Render Bridge
- Smart Reframe plans are now materialized as real non-destructive crop keyframes.
- The existing FFmpeg command builder can consume those keyframes with `eval=frame`.
- Dynamic caption timing/motion decisions are retained as timeline metadata.
- Added a Director decision bridge that safely ignores unknown decisions.
- Added focused render-bridge tests.


## v2.26 Unified FFmpeg Render Bridge
- Caption events are now first-class serialized clip metadata and automatically collected into timeline-relative ASS subtitles.
- Animated ASS captions are burned after video transition composition in the final FFmpeg filtergraph.
- Timed SFX inputs are trimmed, gain-adjusted, delayed, faded and mixed into the final audio graph.
- Unified export accepts `RenderOptions`; existing voice-driven music sidechain ducking remains in the same render.
- Added focused render-pipeline regression tests and usage documentation.

## v2.26.1 — Unified Professional Render

- Added word-level karaoke adapter and ASS generation from `words[]` caption metadata.
- Added `RenderController`, `RenderJob`, `RenderQueue`, and render preflight validation.
- Added low-quality preview jobs that reuse the production filtergraph.
- Connected controller-generated karaoke ASS to the single-pass FFmpeg export path.
- Fixed timed SFX fade offsets after `adelay`.
- Added regression coverage for karaoke metadata and controller integration.

## v2.26.1 — Professional Render Upgrade
- Added adaptive CPU/NVIDIA/VideoToolbox render profile selection with conservative auto detection.
- Added persistent render queue metadata and reset/cancel lifecycle support.
- Added configurable music ducking controls and optional final loudness normalization.
- Kept word-level karaoke, Smart Reframe, transitions, SFX and music ducking in one FFmpeg render graph.
- Added targeted regression coverage and end-to-end FFmpeg smoke validation.

## v2.26.2 — Performance & Batch Editing
- Added content-addressed FFmpeg proxy cache planning for deterministic low-resolution previews.
- Added declarative transition presets with clean/cinematic/beat-punch/flash-beat/dramatic profiles.
- Added batch render orchestration on top of the existing unified RenderController.
- Reused existing beat detector/sync planner as the timing source; no duplicate audio analysis path was introduced.

## v2.26.3 — Smooth Editing / Performance Stability

- Waveform extraction moved out of `paintEvent()` into the shared background pool.
- Timeline clip dragging no longer calls `updateGeometry()` on every mouse move.
- Waveforms are visually downsampled to the available pixel width.
- Preview proxy manager added with content-addressed FFmpeg proxy cache.
- Preview proxies are generated only while playback is paused, preventing proxy transcoding from competing with real-time playback.
- Preview automatically switches to a valid proxy for the current source when available.
- Added preview performance regression coverage.

Performance rule: the Qt UI thread must never execute FFmpeg, media probing, waveform extraction, or proxy generation.

## v2.26.7 — GPU Preview / Zero-Copy Path
- Backend-neutral hardware decode selection with software fallback.
- FFmpeg hwaccel discovery for VAAPI/Vulkan and platform-aware D3D11VA/VideoToolbox/CUDA paths.
- GPU texture-handle path avoids Python-side pixel copies until an effect explicitly requires CPU pixels.
- Preview compositor tracks GPU/CPU/zero-copy usage.
