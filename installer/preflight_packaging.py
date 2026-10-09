"""Windows packaging preflight.

The application deliberately lazy-loads many feature modules. A GUI that opens
is therefore not sufficient proof that the frozen application is usable. This
script verifies that critical feature files exist, compile, and that the
subtitle package can be imported before PyInstaller runs.
"""
from __future__ import annotations

import compileall
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CRITICAL_FILES = [
    "app/subtitle/__init__.py",
    "app/subtitle/models.py",
    "app/subtitle/formats.py",
    "app/subtitle/style.py",
    "app/subtitle/editor.py",
    "app/subtitle/embed.py",
    "app/subtitle/emoji.py",
    "app/subtitle/typography.py",
    "app/subtitle/transcribe.py",
    "app/subtitle/worker.py",
    "app/ui/ai_editor_dialog.py",
    "app/ui/pipeline_dialog.py",
    "app/ui/subtitle_dialog.py",
    "app/ui/youtube_connection_dialog.py",
]

missing = [p for p in CRITICAL_FILES if not (ROOT / p).is_file()]
if missing:
    raise SystemExit("Missing critical source files:\n" + "\n".join(missing))

if not compileall.compile_dir(str(ROOT / "app"), quiet=1):
    raise SystemExit("Python compile preflight failed")

# Lazy-loaded feature pages must not hide broken app imports until runtime.
from installer.api_contract_audit import audit as run_api_contract_audit
_api_issues, _api_deferred = run_api_contract_audit()
if _api_issues:
    raise SystemExit("API contract preflight failed:\n" + "\n".join(
        f"- {i.source}: {i.target} [{i.kind}] {i.detail}" for i in _api_issues
    ))

try:
    import PySide6  # type: ignore
    HAVE_PYSIDE6 = True
except Exception:
    HAVE_PYSIDE6 = False

for module in (
    "app.subtitle",
    "app.subtitle.models",
    "app.subtitle.formats",
    "app.subtitle.style",
    "app.subtitle.editor",
    "app.subtitle.embed",
    "app.subtitle.emoji",
    "app.subtitle.typography",
    "app.subtitle.transcribe",
    "app.subtitle.worker",
    "app.youtube",
    "app.youtube.client",
    "app.youtube.analytics",
    "app.youtube.publish",
    "app.youtube.creator",
    "app.youtube.dna",
    "app.youtube.studio",
    "app.youtube.thumbnail_render",
    "app.youtube.production_queue",
    "app.youtube.production_manager",
    "app.youtube.manager",
    "app.youtube.health",
):
    if not HAVE_PYSIDE6 and module in {"app.subtitle.worker"}:
        continue
    importlib.import_module(module)

print("Packaging preflight OK: critical non-Qt lazy-loaded modules are present and importable.")
if not HAVE_PYSIDE6:
    print("NOTE: PySide6 is not installed in this environment; Qt-dependent imports are deferred to the Windows build environment.")
