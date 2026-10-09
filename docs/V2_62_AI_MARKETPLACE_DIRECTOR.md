# V2.62 — AI Marketplace Pack Director

The creative decision chain is now pack-first: scene/context signals select a coherent built-in Marketplace pack before individual assets are ranked.

## Decision chain

1. Shared scene/clip context is converted into semantic tags.
2. Marketplace packs are scored for style, energy, scene type, speech, faces, platform and explicit tags.
3. The best pack becomes the primary creative source; a close runner-up may be retained as a secondary style mix.
4. Individual effects, transitions, motion, text, SFX and other recipes are ranked inside the selected pack.
5. Scene Creative Director emits the pack decision as metadata so preview/revision can inspect the reason without destructive timeline mutation.

This remains metadata-first and uses only assets already shipped with AI Director. No external plugin or separate installer is required.
