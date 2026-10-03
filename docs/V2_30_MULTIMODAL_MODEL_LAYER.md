# v2.30 Multimodal Model Layer

The AI Director now has an optional model-backed intelligence layer. It is deliberately adapter based: the editor does not depend on a particular VLM, object detector, scene classifier, or emotion model.

## Flow

`video/audio -> deterministic baseline -> optional model adapter -> cache -> multimodal timeline -> editorial decision graph -> quality gate -> GPU renderer`

Supported observation concepts:

- objects
- scene labels
- emotions
- shot type
- action label
- natural-language VLM description
- confidence

`AnalysisCache` keys results by media path, size, mtime, model id and configuration. Re-running analysis therefore avoids repeating expensive inference when the source and model configuration are unchanged.

## Adapter contract

Implement `MultimodalModelAdapter.analyze(media_path, sample_times)` and return `ModelObservation` values. A local JSON adapter is included for deterministic/offline integration tests.

Heavy models remain optional. This keeps startup and installation lightweight while making the pipeline ready for Transformers, ONNX Runtime, TensorRT, CoreML, DirectML or a custom C++/CUDA service.

## Editorial behavior

Model observations can produce semantic B-roll matching, close-up preservation, emotion/reaction holds, and presentation-mode effect suppression. These actions remain explainable and pass through the existing protected-range/quality-gate policy.
