"""Low-overhead adaptive resource and proxy planning utilities.

Pure functions: no device probing, subprocesses, or heavyweight imports occur at
module import time. Callers may pass measured/known hardware information.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ResourceProfile:
    workers: int
    proxy_height: int
    preview_fps: int
    cache_mb: int
    label: str

def resource_profile(cpu_count: int | None = None, memory_gb: float | None = None,
                     battery_mode: bool = False) -> ResourceProfile:
    """Choose conservative defaults; never saturate a low-end editing device."""
    cpus = max(1, int(cpu_count or 1))
    mem = max(1.0, float(memory_gb or 4.0))
    if battery_mode or cpus <= 2 or mem < 6:
        return ResourceProfile(1, 360, 24, 128, "Eco")
    if cpus <= 4 or mem < 12:
        return ResourceProfile(2, 540, 30, 256, "Balanced")
    return ResourceProfile(min(3, max(2, cpus // 4)), 720, 30,
                           min(1024, max(384, int(mem * 32))), "Performance")

class BoundedLRU:
    """Small generic LRU cache with deterministic item-count bound."""
    def __init__(self, max_items: int = 256):
        from collections import OrderedDict
        self.max_items = max(1, int(max_items))
        self._items = OrderedDict()
    def get(self, key, default=None):
        if key not in self._items:
            return default
        self._items.move_to_end(key)
        return self._items[key]
    def put(self, key, value):
        self._items[key] = value
        self._items.move_to_end(key)
        while len(self._items) > self.max_items:
            self._items.popitem(last=False)
    def clear(self):
        self._items.clear()
    def __len__(self):
        return len(self._items)

__all__ = ["ResourceProfile", "resource_profile", "BoundedLRU"]
