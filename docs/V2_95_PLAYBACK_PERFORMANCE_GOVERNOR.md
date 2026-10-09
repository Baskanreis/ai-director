# v2.95 — Playback Performance Governor

Adds a lightweight hysteresis-based governor for interactive playback. The governor consumes measured playback FPS, CPU/GPU/VRAM pressure and dropped-frame counts and returns a deterministic decision for preview scaling, background-work pausing and proxy priority.

The governor is deliberately UI- and backend-agnostic: it does not mutate timeline/media state or spawn processes. The editor/runtime can apply its decision to the preview renderer, proxy queue and background workers.

Actions: `normal`, `reduce_preview`, `pause_background`, `force_proxy`, and `recover`.
