# v2.64 — Autonomous Edit Pass

## Pipeline

`Scene Context → Pack Director → Creative Stack → Preview/QC → Safe Revision → Apply/Render`

The controller does not start another AI model. It reuses the existing semantic library, Marketplace Pack Director, preview/render callbacks and Autonomous Revision engine.

## Safety

- Existing accepted candidate is retained when a revision does not improve the score.
- Speech/caption layers are preserved by default.
- New heavy effects are not introduced during autonomous repair.
- Secondary Marketplace mixing is capped by the existing Pack Director policy.
- Planning is non-destructive until the application explicitly applies the resulting plan.

## Single Setup

All functionality remains part of the normal application bundle. GitHub releases continue to publish exactly `AI_Director_Setup.exe`; no user-side Python, FFmpeg, Whisper, llama.cpp or model installation is required.

## Runtime path

The Windows installer still packages the application as an internal PyInstaller payload and then publishes only the Inno Setup executable. The portable PyInstaller directory is removed from `dist` before the final CI verification.
