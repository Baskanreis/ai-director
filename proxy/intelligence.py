"""Smart, conservative proxy decisions for heavy media.

The decision engine is UI/FFmpeg independent. It only recommends proxies when the
measured media characteristics justify the background cost; the caller still owns
actual proxy generation and can enforce machine resource limits.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class ProxyPolicy:
    min_width: int = 1920
    min_height: int = 1080
    min_duration_s: float = 20.0
    min_bitrate_mbps: float = 45.0
    heavy_effect_score: float = 0.70
    high_fps: float = 50.0
    score_threshold: float = 0.55

@dataclass(frozen=True)
class ProxyDecision:
    media_id: str
    needed: bool
    score: float
    reasons: tuple[str, ...]
    estimated_priority: int = 0

class SmartProxyIntelligence:
    """Scores proxy benefit from metadata without decoding the whole media."""
    def __init__(self, policy: ProxyPolicy | None = None):
        self.policy = policy or ProxyPolicy()

    def decide(self, media_id: str, metadata: dict[str, Any]) -> ProxyDecision:
        p = self.policy
        width = max(0, int(metadata.get("width", 0) or 0))
        height = max(0, int(metadata.get("height", 0) or 0))
        duration = max(0.0, float(metadata.get("duration_s", metadata.get("duration", 0)) or 0))
        fps = max(0.0, float(metadata.get("fps", 0) or 0))
        bitrate = max(0.0, float(metadata.get("bitrate_mbps", 0) or 0))
        effects = max(0.0, min(1.0, float(metadata.get("effect_score", 0) or 0)))
        codec = str(metadata.get("codec", "")).lower()
        score = 0.0; reasons: list[str] = []
        if width >= p.min_width and height >= p.min_height:
            score += 0.22; reasons.append("high_resolution")
        if width * height >= 3840 * 2160:
            score += 0.25; reasons.append("4k_or_higher")
        if duration >= p.min_duration_s:
            score += min(0.18, 0.18 * duration / 60.0); reasons.append("long_clip")
        if bitrate >= p.min_bitrate_mbps:
            score += 0.18; reasons.append("high_bitrate")
        if fps >= p.high_fps:
            score += 0.10; reasons.append("high_fps")
        if effects >= p.heavy_effect_score:
            score += 0.12; reasons.append("heavy_effects")
        if codec in {"hevc", "h265", "av1", "vp9"}:
            score += 0.08; reasons.append("decode_heavy_codec")
        # A proxy is more valuable when the timeline is expected to reuse the clip.
        reuse = max(0.0, min(1.0, float(metadata.get("timeline_reuse", 0) or 0)))
        if reuse >= 0.5:
            score += 0.10; reasons.append("timeline_reuse")
        score = min(1.0, score)
        needed = score >= p.score_threshold
        priority = int(round(score * 100)) if needed else 0
        return ProxyDecision(str(media_id), needed, round(score, 4), tuple(reasons), priority)

    def rank(self, clips: list[tuple[str, dict[str, Any]]]) -> list[ProxyDecision]:
        return sorted((self.decide(mid, meta) for mid, meta in clips), key=lambda x: x.score, reverse=True)

    def to_dict(self) -> dict[str, Any]:
        return {"version": 1, "policy": asdict(self.policy)}
