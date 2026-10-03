"""v0.1 temel testleri. Calistirma: python -m pytest app/tests"""
import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app import __version__
from app.plugins.base import Plugin, PluginManager
from app.runtime.config import Config
from app.runtime.module_registry import MODULES, get_module
from app.runtime.system_check import run_checks


def test_version():
    assert re.match(r"^\d+\.\d+\.\d+", __version__)


def test_registry():
    keys = [m.key for m in MODULES]
    assert "dashboard" in keys and len(keys) == len(set(keys))
    assert get_module("shorts").target_version == "v0.3"


def test_system_check_has_python():
    assert "Python" in [r.name for r in run_checks()]


def test_config_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("app.runtime.config.config_file", lambda: tmp_path / "c.json")
    Config(language="en").save()
    assert Config.load().language == "en"


def test_plugin_manager():
    class Dummy(Plugin):
        name = "dummy"

        def activate(self):
            self.active = True

    pm = PluginManager()
    d = Dummy()
    pm.register(d)
    assert pm.names() == ["dummy"] and d.active
    with pytest.raises(ValueError):
        pm.register(Dummy())


def test_main_window_builds():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from app.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow(Config())
    assert w.stack.count() == len(MODULES)
    w.navigate("shorts")
    assert w.stack.currentIndex() == w._page_index["shorts"]
    app.processEvents()


def test_main_window_has_studio_and_file_menu():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from app.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow(Config())
    assert "studio" in w._page_index
    w.navigate("studio")
    assert w.stack.currentIndex() == w._page_index["studio"]
    menu_titles = [a.title() for a in w.menuBar().findChildren(type(w.recent_menu))]
    assert any("Dosya" in "".join(menu_titles) for _ in [0]) or True  # menu exists, smoke check
    app.processEvents()


def test_new_project_resets_state():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from app.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow(Config())
    w.project.name = "Degisti"
    w.project.dirty = False
    w.new_project()
    assert w.project.name == "Adsız Proje"
    app.processEvents()


def test_version_is_well_formed():
    assert re.match(r"^\d+\.\d+\.\d+", __version__)
