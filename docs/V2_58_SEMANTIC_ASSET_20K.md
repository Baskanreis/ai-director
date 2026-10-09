# AI Director v2.58 — Semantic Asset Matching + 20K Creative Library

## What changed
- Creative metadata catalog expanded from 10,000 to exactly 20,000 original procedural recipes.
- Regional Revision now builds a CPU-light semantic context from transcript, objects, emotion, scene, intent, faces and energy.
- Semantic matching ranks assets before the 20K combination search.
- Turkish object terms are normalized into English semantic tags (for example `telefon` -> `phone/product/tech`).
- Regional candidates retain semantic-match evidence so Final Director/QC can explain why an asset was selected.

## CPU design
1. Extract or receive lightweight signals.
2. Metadata/index search over 20K items.
3. Keep a small semantic candidate set.
4. Run the deterministic combination engine.
5. Only the best few stacks reach real preview/QC.

No additional AI model is required for this layer.
