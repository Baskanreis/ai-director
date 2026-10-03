from pathlib import Path
from app.render.proxy_cache import ProxyCache, ProxySpec
from app.render.transition_presets import get_preset, resolve_duration, list_presets

def test_proxy_cache_is_deterministic(tmp_path):
    src = tmp_path / "a.mp4"; src.write_bytes(b"video")
    cache = ProxyCache(tmp_path / "proxy")
    a = cache.artifact(src, ProxySpec(width=320, height=180))
    b = cache.artifact(src, ProxySpec(width=320, height=180))
    assert a.key == b.key and a.path == b.path
    assert "scale=320:180" in " ".join(cache.command(src, a.spec))

def test_transition_presets():
    assert get_preset("beat_punch").beat_aligned
    assert resolve_duration("clean") == .35
    assert len(list_presets()) >= 5
