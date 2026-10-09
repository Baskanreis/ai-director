from pathlib import Path
import json

def test_sidebar_features_are_real_routes():
    source = Path('app/ui/main_window.py').read_text(encoding='utf-8')
    assert 'key in ("shorts", "reframe")' in source
    assert 'ShortsDirectorDialog' in source
    assert 'SmartReframeDialog' in source

def test_youtube_runtime_config_roundtrip(tmp_path, monkeypatch):
    from app.youtube import config
    monkeypatch.setattr(config, 'config_file', lambda: tmp_path / 'youtube-config.json')
    config.save_runtime_config('demo-key', json.dumps({'installed': {'client_id': 'demo'}}))
    key, oauth = config.load_runtime_config()
    assert key == 'demo-key'
    assert json.loads(oauth)['installed']['client_id'] == 'demo'

def test_render_facade_exports_real_engine():
    from app.render import export_timeline, ExportSettings
    assert callable(export_timeline)
    assert ExportSettings is not None
