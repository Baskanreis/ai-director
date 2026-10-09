# v2.11 Advanced NLE Core

This release adds UI-independent foundations for four major professional workflows:

- **Compound / nested clips:** group timeline material into reusable sequences without flattening the edit.
- **Adjustment layers:** timeline ranges that carry effects independently from source clips.
- **Proxy media:** media-to-proxy mapping with safe original-media fallback.
- **Multicam:** camera angles plus time-based editorial camera switches.

The state is JSON-safe and is intended to live under `project.editor_data["advanced_nle"]`, allowing the existing project format to remain backward compatible.
