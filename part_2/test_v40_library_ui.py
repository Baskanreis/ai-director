import importlib.util
import pytest

if importlib.util.find_spec("PySide6") is None:
    pytest.skip("PySide6 unavailable in this environment", allow_module_level=True)

from app.effects.pro_asset_library import catalog, search
from app.ui.creative_library_dialog import CreativeLibraryDialog

def test_library_ui_search_scale():
    assert len(catalog()) == 50000
    assert len(search('gaming glitch', limit=250)) > 0

def test_library_ui_class_importable():
    assert CreativeLibraryDialog.__name__ == 'CreativeLibraryDialog'
