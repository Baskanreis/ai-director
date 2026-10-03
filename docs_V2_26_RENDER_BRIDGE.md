# v2.26 — Render Bridge

This release closes an important gap between AI planning and actual rendering.
Smart Reframe decisions are converted into `Clip.keyframes[crop_*]`, which the
existing FFmpeg filter builder already renders as frame-evaluated crop filters.
No source media is modified.

Caption timing is kept as structured metadata so the UI/render layer can later
choose a caption renderer without baking text into the source clips.
