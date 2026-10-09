# v2.89 — Smart Proxy Intelligence

Smart Proxy Intelligence decides which clips are worth proxy generation based on resolution, duration, bitrate, FPS, codec, effect intensity and timeline reuse.

It is advisory: actual proxy workers must still obey CPU/GPU/VRAM admission limits. Lightweight clips are not forced through proxy generation, while heavy 4K/HEVC/high-FPS clips are prioritized.

The proxy queue is serializable and supports queued/paused/cancelled states so it can share the application's background worker infrastructure.
