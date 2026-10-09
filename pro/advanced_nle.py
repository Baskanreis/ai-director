"""Advanced NLE primitives: compound clips, adjustment layers, proxies and multicam.

UI-independent and JSON-safe so these features can be adopted incrementally by the
Qt timeline without making the project format depend on widgets.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from uuid import uuid4


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


@dataclass
class CompoundClip:
    """A nested sequence represented as an independent internal timeline."""
    name: str
    duration: float
    sequence_id: str = field(default_factory=lambda: _id("seq"))
    source_project: str = ""
    clip_ids: list[str] = field(default_factory=list)
    enabled: bool = True
    id: str = field(default_factory=lambda: _id("compound"))

    def add_clip(self, clip_id: str) -> bool:
        if clip_id in self.clip_ids:
            return False
        self.clip_ids.append(str(clip_id)); return True

    def remove_clip(self, clip_id: str) -> bool:
        if clip_id not in self.clip_ids:
            return False
        self.clip_ids.remove(clip_id); return True

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict) -> "CompoundClip":
        return cls(name=str(d.get("name", "Compound")), duration=max(0.0, float(d.get("duration", 0))),
                   sequence_id=str(d.get("sequence_id") or _id("seq")), source_project=str(d.get("source_project", "")),
                   clip_ids=[str(x) for x in d.get("clip_ids", [])], enabled=bool(d.get("enabled", True)),
                   id=str(d.get("id") or _id("compound")))


@dataclass
class AdjustmentLayer:
    """Timeline-spanning effect layer; effects apply to clips below it."""
    name: str
    start: float
    end: float
    effects: dict = field(default_factory=dict)
    opacity: float = 1.0
    id: str = field(default_factory=lambda: _id("adj"))
    enabled: bool = True

    def __post_init__(self):
        self.start = max(0.0, float(self.start)); self.end = max(self.start, float(self.end))
        self.opacity = max(0.0, min(1.0, float(self.opacity)))

    @property
    def duration(self): return max(0.0, self.end - self.start)

    def covers(self, time: float) -> bool:
        return self.enabled and self.start <= time < self.end

    def to_dict(self):
        return {"id": self.id, "name": self.name, "start": self.start, "end": self.end,
                "effects": self.effects, "opacity": self.opacity, "enabled": self.enabled}

    @classmethod
    def from_dict(cls, d):
        return cls(str(d.get("name", "Adjustment Layer")), float(d.get("start", 0)), float(d.get("end", 0)),
                   dict(d.get("effects") or {}), float(d.get("opacity", 1)), str(d.get("id") or _id("adj")), bool(d.get("enabled", True)))


@dataclass
class ProxyAsset:
    media_id: str
    proxy_path: str
    codec: str = "prores_proxy"
    width: int = 0
    height: int = 0
    fps: float = 0.0
    ready: bool = False
    id: str = field(default_factory=lambda: _id("proxy"))

    @property
    def exists(self) -> bool:
        return bool(self.proxy_path) and Path(self.proxy_path).is_file()

    def to_dict(self): return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d):
        return cls(str(d["media_id"]), str(d["proxy_path"]), str(d.get("codec", "prores_proxy")),
                   int(d.get("width", 0)), int(d.get("height", 0)), float(d.get("fps", 0)), bool(d.get("ready", False)),
                   str(d.get("id") or _id("proxy")))


class ProxyManager:
    def __init__(self, assets=None):
        self.assets = {a.media_id: a for a in (assets or [])}

    def set(self, asset: ProxyAsset):
        self.assets[asset.media_id] = asset; return asset

    def remove(self, media_id): return self.assets.pop(str(media_id), None) is not None

    def get(self, media_id): return self.assets.get(str(media_id))

    def active_path(self, media_id, original_path: str, use_proxies=True):
        p = self.get(media_id)
        if use_proxies and p and (p.ready or p.exists): return p.proxy_path
        return original_path

    def to_dict(self): return [a.to_dict() for a in self.assets.values()]

    @classmethod
    def from_dict(cls, d): return cls(ProxyAsset.from_dict(x) for x in (d or []))


@dataclass
class MulticamAngle:
    name: str
    media_id: str
    offset: float = 0.0
    audio: bool = False
    enabled: bool = True
    id: str = field(default_factory=lambda: _id("angle"))

    def to_dict(self): return self.__dict__.copy()
    @classmethod
    def from_dict(cls, d):
        return cls(str(d.get("name", "Angle")), str(d.get("media_id", "")), float(d.get("offset", 0)), bool(d.get("audio", False)), bool(d.get("enabled", True)), str(d.get("id") or _id("angle")))


@dataclass
class CameraSwitch:
    time: float
    angle_id: str
    duration: float = 0.0
    id: str = field(default_factory=lambda: _id("cut"))

    def to_dict(self): return self.__dict__.copy()
    @classmethod
    def from_dict(cls, d): return cls(max(0.0, float(d.get("time", 0))), str(d.get("angle_id", "")), max(0.0, float(d.get("duration", 0))), str(d.get("id") or _id("cut")))


@dataclass
class MulticamSequence:
    name: str
    angles: list[MulticamAngle] = field(default_factory=list)
    switches: list[CameraSwitch] = field(default_factory=list)
    id: str = field(default_factory=lambda: _id("multi"))

    def add_angle(self, angle: MulticamAngle):
        self.angles.append(angle); return angle

    def switch(self, time: float, angle_id: str):
        if not any(a.id == angle_id and a.enabled for a in self.angles):
            return False
        self.switches.append(CameraSwitch(time, angle_id)); self.switches.sort(key=lambda x: x.time); return True

    def angle_at(self, time: float):
        current = None
        for cut in self.switches:
            if cut.time <= time: current = cut.angle_id
            else: break
        return next((a for a in self.angles if a.id == current), None)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "angles": [a.to_dict() for a in self.angles], "switches": [s.to_dict() for s in self.switches]}

    @classmethod
    def from_dict(cls, d):
        return cls(str(d.get("name", "Multicam")), [MulticamAngle.from_dict(x) for x in d.get("angles", [])],
                   [CameraSwitch.from_dict(x) for x in d.get("switches", [])], str(d.get("id") or _id("multi")))


@dataclass
class AdvancedEditorState:
    compounds: list[CompoundClip] = field(default_factory=list)
    adjustments: list[AdjustmentLayer] = field(default_factory=list)
    proxies: ProxyManager = field(default_factory=ProxyManager)
    multicam: list[MulticamSequence] = field(default_factory=list)
    use_proxies: bool = False

    def to_dict(self):
        return {"compounds": [x.to_dict() for x in self.compounds], "adjustments": [x.to_dict() for x in self.adjustments],
                "proxies": self.proxies.to_dict(), "multicam": [x.to_dict() for x in self.multicam], "use_proxies": self.use_proxies}

    @classmethod
    def from_dict(cls, d):
        d = d or {}
        return cls([CompoundClip.from_dict(x) for x in d.get("compounds", [])],
                   [AdjustmentLayer.from_dict(x) for x in d.get("adjustments", [])], ProxyManager.from_dict(d.get("proxies", [])),
                   [MulticamSequence.from_dict(x) for x in d.get("multicam", [])], bool(d.get("use_proxies", False)))
