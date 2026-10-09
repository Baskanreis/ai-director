# v2.55 — Retention Hotspots

- Timeline now accepts normalized retention hotspots without changing edit data.
- Risk regions are painted directly over the timeline.
- Right-clicking a hotspot can move the playhead or request a targeted AI revision.
- `Retention Predictor` remains CPU-light and does not load an LLM.
- The targeted request is non-destructive and scoped to `[start, end]`.
- The Studio "Retention Tara" action builds a lightweight structural scan from the current timeline.
- Without owned Analytics, the result is explicitly heuristic; it is not presented as viewer behavior.
