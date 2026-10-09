# v2.54 — Retention Predictor

Adds a CPU-light, explainable retention-risk layer to Autonomous Revision.

- No additional model is loaded.
- Without owned Analytics it reports a structural heuristic with low confidence.
- With owned YouTube Analytics it calibrates against channel-level baselines, but does not claim causal edit effects.
- Produces evidence, warnings and actionable hotspots.
- Autonomous Revision uses the score as a small tie-break/quality signal; hard QC remains authoritative.
