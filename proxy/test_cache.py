from pathlib import Path

from app.proxy.cache import ProxyCache


def _file(path: Path, size: int):
    path.write_bytes(b"x" * size)
    return path


def test_lru_evicts_oldest(tmp_path):
    cache = ProxyCache(tmp_path, max_bytes=10)
    a = _file(tmp_path / "a.mp4", 6)
    b = _file(tmp_path / "b.mp4", 6)
    cache.register("a", a)
    cache.touch("a")
    cache.register("b", b)
    removed = cache.cleanup()
    assert removed == ["a"]
    assert not a.exists() and b.exists()


def test_protected_is_not_evicted(tmp_path):
    cache = ProxyCache(tmp_path, max_bytes=10)
    a = _file(tmp_path / "a.mp4", 8)
    b = _file(tmp_path / "b.mp4", 8)
    cache.register("a", a)
    cache.register("b", b)
    removed = cache.cleanup(protected_media_ids={"a"})
    assert removed == ["b"]
    assert a.exists()


def test_reconcile_and_persistence(tmp_path):
    cache = ProxyCache(tmp_path, max_bytes=100)
    a = _file(tmp_path / "a.mp4", 7)
    cache.register("a", a, pinned=True)
    payload = cache.to_dict()
    restored = ProxyCache.from_dict(payload, root=tmp_path)
    assert restored.entries["a"].size_bytes == 7
    a.unlink()
    assert restored.reconcile() == 1
    assert "a" not in restored.entries
