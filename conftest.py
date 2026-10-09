"""Lightweight pytest bootstrap and environment-aware Qt test collection."""
from pathlib import Path
import importlib.util
import sys
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def pytest_ignore_collect(collection_path, config):
    """Skip Qt-only tests when PySide6 is unavailable; run them on Windows builds."""
    if importlib.util.find_spec("PySide6") is not None:
        return False
    path = Path(str(collection_path))
    if path.suffix == ".py":
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "PySide6" in text and ("test_" in path.name or path.name.startswith("test")):
                return True
        except OSError:
            pass
    return False
