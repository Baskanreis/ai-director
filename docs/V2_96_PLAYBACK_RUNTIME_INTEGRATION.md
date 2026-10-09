# v2.96 — Playback Runtime Integration

v2.96 connects the playback performance governor to the real preview runtime without making the Qt layer responsible for policy decisions.

## Runtime bridge

`app/performance/playback_runtime.py` converts preview timer cadence into `PlaybackMetrics` and applies `GovernorDecision` through optional hooks:

- background pause/resume
- proxy priority boost
- decision telemetry sink

The bridge is Qt-independent and therefore testable on build machines without PySide6.

## Preview integration

`PreviewPlayer` now owns a `PlaybackRuntimeBridge` while preserving its existing timeline/source-switching behavior. Each playback tick feeds measured cadence into the governor and emits `performance_changed` for the host UI/control center.

## Proxy worker integration

`ProxyGenerationService` exposes governor hooks:

- `set_background_paused()` prevents new background proxy jobs from starting while playback is under pressure.
- `boost_queued_priorities()` raises queued proxy priority without interrupting a running encode.

No timeline media paths are rewritten by this integration.
