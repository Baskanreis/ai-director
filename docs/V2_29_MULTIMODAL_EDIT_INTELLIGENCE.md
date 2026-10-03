# v2.29 — Multimodal Edit Intelligence

The AI Director now fuses transcript semantics with visual rhythm and audio timing before building the edit decision graph.

## Pipeline

`Media -> visual/audio analysis -> transcript understanding -> multimodal fusion -> editorial style -> decision graph -> safety optimizer -> quality gate -> timeline/GPU render`

## Baseline signals

- visual brightness/contrast
- frame motion
- scene-change strength
- visual density
- face count when OpenCV Haar data is available
- beat/BPM timing from FFmpeg + NumPy
- model-adapter slots for object detection, scene classification, emotion, speech prosody and VLMs

## Safety behavior

- protected information remains protected
- visual action peaks cannot freely override critical-information ranges
- effect/action spam is reduced automatically before render
- all decisions remain non-destructive and explainable

## Extending to learned models

`VisionAdapter` can be replaced with a GPU model adapter without changing downstream editorial code. The same contract can host object/shot/emotion/VLM inference and feed normalized 0..1 signals into the decision graph.
