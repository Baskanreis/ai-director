# AI Director v2.33 — Variant Intelligence + Resource Runtime

The director can produce several non-destructive professional edit plans from one multimodal analysis. Variant profiles are ranked from content type and signals such as motion, suspense, speech density and emotion.

The resource manager keeps model batching and concurrency inside a configured GPU memory budget and gracefully degrades `final -> balanced -> fast` when memory is constrained.

`ModelRegistry` discovers local ONNX models without forcing downloads. A host application can supply its own authenticated downloader and register the resulting model path.
