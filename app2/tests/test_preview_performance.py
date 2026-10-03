from pathlib import Path
from app.render.proxy_cache import ProxyCache, ProxySpec


def test_proxy_cache_command_is_deterministic(tmp_path):
    src = tmp_path / 'source.mp4'
    src.write_bytes(b'x' * 2048)
    cache = ProxyCache(tmp_path / 'cache')
    a = cache.artifact(src, ProxySpec(width=640, height=360))
    b = cache.artifact(src, ProxySpec(width=640, height=360))
    assert a.key == b.key
    cmd = cache.command(src, a.spec)
    assert '-preset' in cmd and 'veryfast' in cmd
    assert cmd[-1] == a.path
