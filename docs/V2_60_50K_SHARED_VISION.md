# AI Director v2.60 — 50K Creative Studio + Shared Vision

- Creative catalog is exactly **50,000** original procedural recipes.
- Existing NLE-friendly categories remain compatible: effects, transitions, motion, text, overlays, stickers, SFX, audio FX, filters, templates and music.
- Each recipe carries semantic tags, intent, mood, target format, style family and safe-to-auto-apply metadata.
- A new optional shared Vision pass extracts representative frames once, sends them in one multimodal batch to the configured vision provider, and enriches the shared SceneContext with objects, people/faces, screens/UI, product, environment, shot type, OCR, visual cues and confidence.
- Specialists and Final Director reuse the same enriched context. No model is loaded per scene.
- Without a vision provider, deterministic SceneContext remains the fallback.
- The catalog contains original recipes/metadata, not proprietary CapCut assets.
