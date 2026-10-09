# v2.97 — Hardware Acceleration Detection & Renderer Selection

Adds best-effort GPU/FFmpeg capability discovery and a safe renderer policy.

- Detects NVIDIA/AMD/Intel/Apple/Qualcomm where the host OS exposes a GPU name.
- Probes FFmpeg's available hardware encoders when FFmpeg is installed.
- Keeps Qt Multimedia as the preview backend on systems with a detected GPU.
- Selects FFmpeg hardware rendering only when a hardware encoder is actually advertised.
- Falls back to CPU without blocking startup when detection/probing fails.
- `PreviewPlayer.hardware_capabilities()` and `.renderer_selection()` expose the decision for UI/control-center telemetry.
