from pathlib import Path


def test_main_window_does_not_import_heavy_pages_at_module_import():
    source = Path("app/ui/main_window.py").read_text(encoding="utf-8")
    assert "from .studio_page import StudioPage" not in source.split("class MainWindow", 1)[0]
    assert "from .pages import" not in source.split("class MainWindow", 1)[0]


def test_studio_refresh_defers_thumbnail_generation():
    source = Path("app/ui/studio_page.py").read_text(encoding="utf-8")
    refresh = source.split("def refresh(self)", 1)[1]
    assert "generate_thumbnail" not in refresh.split("def _", 1)[0]
    assert "QTimer.singleShot" in refresh


def test_preview_has_cache_path():
    source = Path("app/ui/preview_widget.py").read_text(encoding="utf-8")
    assert "_preview_cache" in source
    assert "resolve_preview" in source
