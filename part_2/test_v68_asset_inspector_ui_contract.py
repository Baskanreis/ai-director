from pathlib import Path

ROOT = Path(__file__).parents[1]

def test_timeline_exposes_asset_inspector_action():
    text = (ROOT / 'ui' / 'timeline_view.py').read_text()
    assert 'asset_inspector_requested = Signal(str)' in text
    assert 'Asset Inspector…' in text
    assert 'asset_inspector_requested.emit(clip.id)' in text


def test_studio_wraps_inspector_in_single_history_transaction():
    text = (ROOT / 'ui' / 'studio_page.py').read_text()
    assert 'self.timeline_view.asset_inspector_requested.connect(self._open_asset_inspector)' in text
    assert 'self.history.push()' in text[text.index('def _open_asset_inspector'):text.index('def _on_creative_asset_preview')]
    assert 'AssetInspectorDialog' in text
