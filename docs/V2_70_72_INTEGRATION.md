# v2.70–v2.72 Integration

## v2.70 — Keyframe Asset Animation
Creative asset recipes can now contain per-property keyframes for `intensity`, `speed`, `blend`, `position`, and `duration`. Keyframes remain metadata-only and are evaluated with the same deterministic interpolation engine used by the clip keyframe system.

## v2.71 — Beat-Synced Animation Director
Beat cues can generate sparse asset animation accents. The director enforces an intensity ceiling, cooldown, minimum beat distance, and optional protection of existing/manual keyframes.

## v2.72 — Unified AI Auto-Rhythm
`UnifiedRhythmMap` coordinates six channels:
- cut
- transition
- zoom/pan
- asset animation
- subtitle emphasis
- SFX

The planner combines beat strength, scene importance and per-channel quality budgets while enforcing minimum cut distance. The result is non-destructive and serializable.
