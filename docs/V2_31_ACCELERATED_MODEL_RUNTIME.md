# AI Director v2.31 — Accelerated Model Runtime

The editorial engine now has an optional production inference layer.

## Provider priority

TensorRT → CUDA → DirectML → CoreML → OpenVINO → CPU.

Only providers actually installed on the machine are selected. The editor does
not fail when ML packages are absent; it falls back to the existing multimodal
baseline and JSON/model adapters.

## Batching

`BatchedInference` groups frame/segment requests so vision models can process
multiple samples per invocation. The batch size is configurable and defaults to
8.

## Architecture

Video → sampled frames → model runtime → ModelObservation → multimodal fusion →
editorial decision graph → quality gate → GPU compositor.

The runtime deliberately does not prescribe a specific neural-network output
format. `OnnxModelAdapter` accepts model-specific preprocessing/postprocessing,
allowing object detection, scene classification, embeddings and other models
to share the same execution infrastructure.
