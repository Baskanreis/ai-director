# v2.87 Render Intelligence

Historical render telemetry is now advisory: successful render durations and resource snapshots are stored per job kind. The model estimates ETA and recommends conservative parallelism. Unknown/insufficient history always falls back to serial scheduling. It never overrides the hard GPU/VRAM/CPU admission gates.
