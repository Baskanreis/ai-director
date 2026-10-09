# v2.52 — Reference Edit DNA

Reference videos can now be analyzed locally and merged into Channel Brain.

## Modes
- Fast (default): ffprobe-only media facts; no model and no full decode.
- Deep (opt-in): one-thread FFmpeg scene-change and silence detection.

## Evidence policy
Reference media is treated as direct style evidence. Public YouTube metadata remains a soft prior, while first-party Analytics remains performance evidence. The system never claims that a visual pattern caused retention without owned performance evidence.

## Context API
```python
{
  "reference_video_paths": ["/path/a.mp4", "/path/b.mp4"],
  "reference_edit_deep": False,
  "reference_edit_max_videos": 20,
}
```

The orchestrator automatically creates `reference_edit_analysis` and feeds it to Channel Brain.
