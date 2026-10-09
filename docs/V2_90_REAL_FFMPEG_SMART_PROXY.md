# v2.90 — Real FFmpeg Smart Proxy Worker

The Smart Proxy Intelligence layer now has a real background FFmpeg execution path.

## Pipeline

1. Smart Proxy Intelligence scores the media.
2. Only selected clips enter `ProxyQueue`.
3. `ProxyGenerationService` submits bounded background jobs.
4. `FFmpegProxyWorker` encodes a temporary proxy file.
5. Progress is parsed from FFmpeg's machine-readable progress stream.
6. On success the temporary file is atomically renamed into the requested proxy path.
7. On failure/cancellation the temporary file is removed.

## Resource safety

A render scheduler can be injected into the worker. Proxy generation must obtain admission before consuming a render slot, so proxy work cannot silently bypass CPU/GPU/VRAM limits.

## Distribution

No user-side Python or FFmpeg installation is assumed by the source architecture. The Windows release continues to target the existing single `AI_Director_Setup.exe` packaging contract; the installer/runtime bundling layer remains responsible for shipping the required FFmpeg runtime.
