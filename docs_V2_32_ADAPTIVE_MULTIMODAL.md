# AI Director v2.32 — Adaptive Multimodal Intelligence

## Pipeline

Video/audio analysis produces event candidates. The adaptive sampler allocates extra model inference around high-value events (scene changes, motion peaks, beats) while retaining a low-rate periodic baseline.

`media -> baseline sampling -> event sampling -> model runtime -> observations -> confidence fusion -> editorial intelligence -> quality gate -> GPU compositor`

## Model registry

`ModelRegistry` keeps model selection separate from rendering. Models declare task, backend, quality, speed and memory. Selection can be biased toward quality or speed and filtered by installed backend/memory budget.

## Confidence policy

Multimodal evidence is advisory. Agreement increases confidence; disagreement reduces it. Protected speech, continuity and critical-action rules remain higher priority than model confidence.

## Production guidance

- Use fast models during interactive preview.
- Switch to accurate models during final analysis/export.
- Use adaptive sampling for expensive VLM inference.
- Cache results using media/model/config fingerprints.
- Keep CPU/OpenCV fallback enabled when optional runtimes are unavailable.
