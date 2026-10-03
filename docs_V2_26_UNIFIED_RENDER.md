# v2.26 — Unified FFmpeg Render Pipeline

`export_timeline(..., render_options=RenderOptions(...))` now accepts optional
caption and timed SFX events. The command builder keeps them in the existing
single `-filter_complex` render:

- Smart Reframe remains represented by `crop_*` keyframes and is applied while
  each clip is built.
- Video transitions are composed into `[vout]`; ASS captions are burned after
  that composition so caption placement is stable across cuts/reframes.
- Clip `caption_events` are serialized in timeline JSON. When no explicit
  render options are supplied, `export_timeline` collects them automatically.
- SFX events are separate audio inputs, trimmed, gain-adjusted, delayed to
  timeline time, faded, then mixed into `[aout]`.
- Music ducking remains a true FFmpeg `sidechaincompress` stage driven by
  non-muted tracks whose role is `voice`, targeting tracks whose role is
  `music` and `duck=True`.

Example:

```python
from app.render.unified_pipeline import RenderOptions, SFXEvent
from app.export.ffmpeg_export import export_timeline, ExportSettings

options = RenderOptions(
    captions=[
        {"start": 0.4, "end": 1.2, "text": "Merhaba dünya",
         "animation": "pop", "emphasis": ["dünya"], "position": "lower_safe"}
    ],
    sfx=[SFXEvent("assets/audio/sfx_whoosh.wav", 1.0, 1.7, -10.0)],
)
export_timeline(timeline, media_paths, ExportSettings("output.mp4", 1080, 1920),
                render_options=options)
```

ASS files are generated automatically when `captions` are supplied without an
`ass_path`. Caption times passed directly in `RenderOptions` are timeline-relative;
`clip.caption_events` are clip-local and are shifted automatically during collection.

## v2.26.1 — Karaoke + Professional Render Controller

### Word-level karaoke

`app/render/karaoke.py` adapts caption metadata containing `words[]` into the existing
`app/subtitle.ass_format` ASS engine. The renderer therefore gets real word timestamps,
per-word highlight/pop animation and optional pinned emphasis without baking intermediate
video files.

### Professional render controller

`app/render/controller.py` adds:

- preflight validation of timeline/media/output settings,
- one canonical render path for preview and final output,
- low-quality preview jobs using the same filtergraph,
- deterministic FIFO render queue,
- render options preparation in a dedicated work directory.

The controller calls the existing single-pass FFmpeg exporter; Smart Reframe, transitions,
ASS captions, voice/music sidechain ducking and timed SFX remain in one `-filter_complex` graph.

### Audio correction

Timed SFX fade-in/out now uses the SFX-local timeline after `adelay`, preventing the fade
from being shifted twice by the global cue timestamp.
