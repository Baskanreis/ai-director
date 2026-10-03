# AI Director v2.26.1 — Professional Render Upgrade

## Included

### Karaoke
- Whisper-style word timing metadata is converted to ASS dialogue events.
- Active-word highlight, scale/pop animation, pinned emphasis and normal captions share one ASS pipeline.
- Karaoke captions are burned after the final video compositor, so Smart Reframe and transitions affect the underlying picture without losing caption timing.

### Render profiles
- `hardware_accel=auto` is conservative: CPU is the default unless a usable NVIDIA runtime or VideoToolbox path is actually detected.
- `cpu`, `nvidia`, and `videotoolbox` can be explicitly selected.
- Encoder fallback remains available for unsupported hardware.
- Preview renders reuse the same filtergraph and only change output quality/size.

### Audio
- Music ducking remains backward compatible with the previous threshold/ratio/attack/release defaults.
- Render options expose duck threshold, ratio, attack and release.
- Optional final `loudnorm` pass can be enabled from `RenderOptions.normalize_final_audio`.
- Timed SFX remain part of the same FFmpeg filtergraph.

### Queue
- Render queue jobs can be serialized to JSON.
- Queue state includes progress, ETA, speed, start/finish timestamps and error state.
- Queued/failed/cancelled jobs can be reset and resumed by the host UI.

## Validation

Targeted regression suite: **23 passed**.

End-to-end FFmpeg smoke render: **passed**.

The smoke output was a 2-second H.264/AAC MP4 with two word-level karaoke events burned into the final video stream.

## Recommended next phase

1. GPU-aware proxy cache keyed by media hash + resolution + frame rate.
2. Waveform/beat-aware audio preview with ducking visualization.
3. Scene-level transition presets with duration safety validation.
4. Batch delivery profiles and optional render-farm workers.
5. Timeline UI integration for queue priority, cancel, retry and render diagnostics.
