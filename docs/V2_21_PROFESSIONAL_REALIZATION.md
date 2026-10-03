# v2.21 — Professional Layer Realization

This release moves beyond planning: after safe cuts are materialized, Director motion cues and supplied/local starter audio assets are attached to the real timeline.

## Applied layers
- motion keyframes (punch/push/micro-push)
- local starter SFX on an SFX track
- loopable local music on a duck-enabled music track
- caption and B-roll decisions preserved as renderer-ready metadata
- transition policy preserved without inventing overlap semantics

## Safety
Only assets actually present in the project are materialized. B-roll is not fabricated: missing external footage remains a cue for a later asset-matching stage.
