# AI Director v2.5 — Beat Sync & Edit Motion

Adds a deterministic, non-destructive edit synchronization layer:
- BPM-based beat grid
- nearest-beat alignment for cut points
- transition cues for the existing FFmpeg xfade renderer
- hook/pattern-break/B-roll motion cues
- machine-readable edit sync plans

The planner does not claim to infer musical beats from arbitrary audio yet; it uses
asset BPM metadata. A future audio-analysis pass can replace the BPM source without
changing the plan API.
