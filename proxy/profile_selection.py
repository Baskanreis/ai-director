"""Adaptive proxy profile selection from media and current workload metadata."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class ProxyProfileChoice:
    height: int
    crf: int
    preset: str
    reason: str
    score: float

class SmartProxyProfileSelector:
    """Choose a proxy size/quality that balances playback load and disk cost.

    The selector is intentionally metadata-only: callers may provide live system
    pressure (cpu/gpu/VRAM/storage) and timeline pressure without touching the
    media decoder.  Explicit profile overrides remain authoritative.
    """
    def choose(self, metadata: dict[str, Any] | None = None) -> ProxyProfileChoice:
        m = metadata or {}
        width = max(0, int(m.get("width", 0) or 0))
        height = max(0, int(m.get("height", 0) or 0))
        fps = max(0.0, float(m.get("fps", 0) or 0))
        bitrate = max(0.0, float(m.get("bitrate_mbps", 0) or 0))
        effects = max(0.0, min(1.0, float(m.get("effect_score", 0) or 0)))
        cpu = max(0.0, min(1.0, float(m.get("cpu_pressure", 0) or 0)))
        gpu = max(0.0, min(1.0, float(m.get("gpu_pressure", 0) or 0)))
        vram = max(0.0, min(1.0, float(m.get("vram_pressure", 0) or 0)))
        timeline = max(0.0, min(1.0, float(m.get("timeline_pressure", 0) or 0)))
        storage = max(0.0, min(1.0, float(m.get("storage_pressure", 0) or 0)))
        source_pixels = width * height
        load = max(cpu, gpu, vram, timeline)
        heavy_source = source_pixels >= 3840 * 2160 or fps >= 50 or bitrate >= 60 or effects >= .75

        if height <= 720 or width <= 1280:
            return ProxyProfileChoice(height=max(360, min(height or 540, 720)), crf=23,
                                      preset="ultrafast", reason="source_already_light", score=0.15)
        if load >= .82 or storage >= .88:
            return ProxyProfileChoice(height=540 if height >= 1080 else 360, crf=24,
                                      preset="ultrafast", reason="high_system_or_storage_pressure", score=0.95)
        if heavy_source or load >= .60:
            return ProxyProfileChoice(height=720 if height >= 1440 else 540, crf=22,
                                      preset="ultrafast", reason="heavy_source_or_timeline_load", score=0.80)
        if height >= 2160:
            return ProxyProfileChoice(height=720, crf=21, preset="veryfast",
                                      reason="high_resolution_quality_balance", score=0.65)
        return ProxyProfileChoice(height=720, crf=22, preset="ultrafast",
                                  reason="balanced_default", score=0.45)

    def to_dict(self) -> dict[str, Any]:
        return {"version": 1}
