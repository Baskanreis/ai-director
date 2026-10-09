from pathlib import Path


def test_media_import_does_not_probe_with_thumbnail_on_ui_path():
    source = Path("app/ui/studio_page.py").read_text(encoding="utf-8")
    block = source.split("def _import_paths", 1)[1].split("def _start_dir", 1)[0]
    assert "probe_media(p, thumbnail=False)" in block
    assert "probe_media(path)" not in block


def test_thumbnail_generation_uses_background_task():
    source = Path("app/ui/studio_page.py").read_text(encoding="utf-8")
    block = source.split("def _queue_thumbnail", 1)[1].split("def _thumbnail_ready", 1)[0]
    assert "BackgroundTask" in block
    assert "generate_thumbnail" in block


def test_dashboard_checks_are_deferred():
    source = Path("app/ui/pages.py").read_text(encoding="utf-8")
    dashboard = source.split("class DashboardPage", 1)[1].split("class PlaceholderPage", 1)[0]
    assert "QTimer.singleShot(0, self._load_checks)" in dashboard
    assert "BackgroundTask(run_checks)" in dashboard
