"""Disk-backed proxy cache with LRU eviction and timeline protection."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from threading import RLock
from time import time
from typing import Iterable
import json


@dataclass
class ProxyCacheEntry:
    media_id: str
    path: str
    size_bytes: int = 0
    last_access: float = 0.0
    pinned: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ProxyCacheEntry":
        return cls(str(data.get("media_id", "")), str(data.get("path", "")),
                   max(0, int(data.get("size_bytes", 0) or 0)),
                   float(data.get("last_access", 0) or 0), bool(data.get("pinned", False)))


class ProxyCache:
    """Bounded proxy cache.

    Eviction is least-recently-used, but protected/pinned media are never evicted.
    Missing files are reconciled automatically and metadata can be persisted as JSON.
    """
    def __init__(self, root: str | Path, max_bytes: int = 20 * 1024**3):
        if max_bytes <= 0:
            raise ValueError("max_bytes must be > 0")
        self.root = Path(root)
        self.max_bytes = int(max_bytes)
        self.entries: dict[str, ProxyCacheEntry] = {}
        self._lock = RLock()

    @property
    def used_bytes(self) -> int:
        with self._lock:
            return sum(max(0, e.size_bytes) for e in self.entries.values())

    @property
    def free_bytes(self) -> int:
        return max(0, self.max_bytes - self.used_bytes)

    def register(self, media_id: str, path: str | Path, *, pinned: bool = False) -> ProxyCacheEntry:
        p = Path(path)
        size = p.stat().st_size if p.is_file() else 0
        with self._lock:
            old = self.entries.get(str(media_id))
            entry = ProxyCacheEntry(str(media_id), str(p), size,
                                    time(), bool(pinned or (old.pinned if old else False)))
            self.entries[entry.media_id] = entry
            return entry

    def touch(self, media_id: str) -> bool:
        with self._lock:
            entry = self.entries.get(str(media_id))
            if not entry:
                return False
            entry.last_access = time()
            return True

    def pin(self, media_ids: Iterable[str]) -> None:
        protected = {str(x) for x in media_ids}
        with self._lock:
            for mid, entry in self.entries.items():
                entry.pinned = mid in protected

    def protect(self, media_ids: Iterable[str]) -> int:
        protected = {str(x) for x in media_ids}
        changed = 0
        with self._lock:
            for mid in protected:
                entry = self.entries.get(mid)
                if entry and not entry.pinned:
                    entry.pinned = True
                    changed += 1
        return changed

    def remove(self, media_id: str, *, delete_file: bool = True) -> bool:
        with self._lock:
            entry = self.entries.pop(str(media_id), None)
        if not entry:
            return False
        if delete_file:
            try:
                Path(entry.path).unlink(missing_ok=True)
            except OSError:
                pass
        return True

    def reconcile(self) -> int:
        """Refresh sizes and drop entries whose files disappeared."""
        removed = 0
        with self._lock:
            for mid in list(self.entries):
                entry = self.entries[mid]
                p = Path(entry.path)
                if not p.is_file():
                    del self.entries[mid]
                    removed += 1
                else:
                    entry.size_bytes = p.stat().st_size
        return removed

    def evict(self, *, required_bytes: int = 0, protected_media_ids: Iterable[str] = ()) -> list[str]:
        """Evict oldest unprotected entries until enough space is available."""
        required = max(0, int(required_bytes))
        protected = {str(x) for x in protected_media_ids}
        removed: list[str] = []
        with self._lock:
            candidates = sorted((e for e in self.entries.values()
                                 if not e.pinned and e.media_id not in protected),
                                key=lambda e: (e.last_access, e.media_id))
            freed = 0
            for entry in candidates:
                if self.free_bytes + freed >= required:
                    break
                self.entries.pop(entry.media_id, None)
                freed += max(0, entry.size_bytes)
                try:
                    Path(entry.path).unlink(missing_ok=True)
                except OSError:
                    pass
                removed.append(entry.media_id)
        return removed

    def cleanup(self, *, protected_media_ids: Iterable[str] = ()) -> list[str]:
        """Enforce the configured quota, preserving protected/pinned assets."""
        self.reconcile()
        over = max(0, self.used_bytes - self.max_bytes)
        return self.evict(required_bytes=over, protected_media_ids=protected_media_ids) if over else []

    def to_dict(self) -> dict:
        with self._lock:
            return {"version": 1, "max_bytes": self.max_bytes,
                    "entries": [e.to_dict() for e in self.entries.values()]}

    @classmethod
    def from_dict(cls, data: dict, root: str | Path | None = None) -> "ProxyCache":
        data = data or {}
        target = Path(root) if root is not None else Path(data.get("root", "."))
        cache = cls(target, int(data.get("max_bytes", 20 * 1024**3)))
        cache.entries = {e.media_id: e for e in
                         (ProxyCacheEntry.from_dict(x) for x in data.get("entries", [])) if e.media_id}
        return cache

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(target)

    @classmethod
    def load(cls, path: str | Path, *, root: str | Path | None = None) -> "ProxyCache":
        target = Path(path)
        if not target.is_file():
            return cls(root or target.parent)
        try:
            return cls.from_dict(json.loads(target.read_text(encoding="utf-8")), root=root)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return cls(root or target.parent)
