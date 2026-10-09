from app.performance.adaptive import BoundedLRU, resource_profile

def test_low_resource_profile_is_conservative():
    p = resource_profile(2, 4)
    assert (p.workers, p.proxy_height, p.cache_mb) == (1, 360, 128)

def test_balanced_and_performance_profiles_are_bounded():
    assert resource_profile(4, 8).label == "Balanced"
    p = resource_profile(32, 128)
    assert p.workers <= 3 and p.cache_mb <= 1024 and p.proxy_height == 720

def test_battery_mode_caps_resources():
    assert resource_profile(16, 64, True).workers == 1

def test_lru_evicts_oldest_and_refreshes_recent():
    c = BoundedLRU(2)
    c.put("a", 1); c.put("b", 2)
    assert c.get("a") == 1
    c.put("c", 3)
    assert c.get("b") is None and c.get("a") == 1 and len(c) == 2

def test_lru_clear():
    c = BoundedLRU(2); c.put(1, 1); c.clear()
    assert len(c) == 0
