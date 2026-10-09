# v2.53 — Autonomous Revision Engine

AI Director can now evaluate an initial edit and perform up to three targeted revisions.
The controller is deliberately model-free: it consumes the existing preview renderer,
visual/audio QC and Channel Brain score. A provider-backed Final Director remains the
only optional heavy model call.

## Loop

1. Evaluate v1 using the real preview/QC callback.
2. Diagnose actionable issues.
3. Apply the smallest safe repair.
4. Evaluate v2/v3.
5. Accept only a meaningful improvement; never regress.
6. Stop when QC is clean, no safe repair exists, or the round limit is reached.

Repairs include audio peak protection, duplicate cue removal, light visual sharpening,
optional-heavy-layer disabling and duration guards. Speech/caption content is preserved
by default.

## CPU policy

No new model process is started. FFmpeg/rendering remains under the existing preview
pipeline's resource policy. The revision controller itself is deterministic and cheap.
