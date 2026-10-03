# AI Director v2.30 — Multimodal Model Intelligence

## Added
- Optional `MultimodalModelAdapter` contract for VLM/object/scene/emotion/shot/action models.
- `ModelObservation` timeline records for semantic visual understanding.
- Deterministic `AnalysisCache` keyed by media fingerprint, model id and configuration.
- Offline `JsonModelAdapter` for reproducible integration and model-runner handoff.
- Model observations fused into `VisualSignal` without breaking the baseline OpenCV path.
- Editorial decisions for semantic visual matching, close-up preservation, emotion/reaction holds and presentation-mode effect suppression.
- New multimodal intelligence tests.

## Performance
- Heavy ML remains optional; no mandatory transformer/runtime dependency was introduced.
- Cached inference avoids repeating expensive model analysis for unchanged media/configuration.
- Existing GPU/QVideo zero-copy path remains the rendering path.

## Quality policy
Model suggestions remain advisory. Protected information, speech, faces and continuity constraints continue to take precedence over visual effects.
