# v2.99 — YouTube Runtime & Packaging Hardening

This release addresses failures where the YouTube feature can open but lazy-loaded
modules or Google runtime configuration are unavailable in the frozen Windows build.

## Guards
- `installer/AI_Director.spec` explicitly collects all YouTube modules.
- `installer/preflight_packaging.py` imports all critical YouTube modules before PyInstaller runs.
- `app/youtube/health.py` reports Data API key, OAuth client, Google package and module status.
- The YouTube dialog displays actionable configuration/module status.
