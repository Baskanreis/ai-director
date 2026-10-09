from pathlib import Path


def test_timeline_has_smart_drag_preview_signal_and_ghost_state():
    text = Path(__file__).parents[1].joinpath("ui", "timeline_view.py").read_text()
    assert "creative_asset_preview = Signal(str, float, str, float)" in text
    assert "self._asset_ghost" in text
    assert "def _update_asset_ghost" in text
    assert "def dragLeaveEvent" in text


def test_smart_drag_is_non_destructive_until_drop():
    text = Path(__file__).parents[1].joinpath("ui", "timeline_view.py").read_text()
    block = text[text.index("def _update_asset_ghost"):text.index("def dragEnterEvent")]
    assert "self._asset_ghost =" in block
    assert "self.creative_asset_preview.emit" in block
    assert "self._timeline." not in block


def test_studio_connects_preview_feedback():
    text = Path(__file__).parents[1].joinpath("ui", "studio_page.py").read_text()
    assert "creative_asset_preview.connect(self._on_creative_asset_preview)" in text
    assert "def _on_creative_asset_preview" in text
