"""Interactive playback performance governor.

Keeps playback responsive by making conservative, deterministic decisions from
measured FPS/resource pressure. It never mutates timeline/media state; callers
apply the returned actions to preview quality, background work, and proxy jobs.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class GovernorAction(str, Enum):
    NORMAL = "normal"
    REDUCE_PREVIEW = "reduce_preview"
    PAUSE_BACKGROUND = "pause_background"
    FORCE_PROXY = "force_proxy"
    RECOVER = "recover"


@dataclass(frozen=True)
class PlaybackMetrics:
    fps: float
    target_fps: float = 30.0
    cpu_percent: float | None = None
    gpu_percent: float | None = None
    vram_percent: float | None = None
    dropped_frames: int = 0


@dataclass(frozen=True)
class GovernorDecision:
    action: GovernorAction
    preview_scale: float
    pause_background: bool
    proxy_priority_boost: int
    reason: str


@dataclass(frozen=True)
class PlaybackGovernorPolicy:
    critical_fps_ratio: float = 0.55
    low_fps_ratio: float = 0.80
    recover_fps_ratio: float = 0.95
    high_resource_percent: float = 88.0
    critical_resource_percent: float = 96.0
    max_proxy_boost: int = 400


class PlaybackPerformanceGovernor:
    """Hysteresis-based controller preventing quality oscillation."""

    def __init__(self, policy: PlaybackGovernorPolicy | None = None):
        self.policy = policy or PlaybackGovernorPolicy()
        self._degraded = False

    @staticmethod
    def _resource_pressure(m: PlaybackMetrics) -> float:
        values = [x for x in (m.cpu_percent, m.gpu_percent, m.vram_percent) if x is not None]
        return max(values) if values else 0.0

    def decide(self, metrics: PlaybackMetrics) -> GovernorDecision:
        target = max(1.0, float(metrics.target_fps))
        fps_ratio = max(0.0, float(metrics.fps)) / target
        pressure = self._resource_pressure(metrics)
        critical = fps_ratio < self.policy.critical_fps_ratio or pressure >= self.policy.critical_resource_percent
        low = fps_ratio < self.policy.low_fps_ratio or pressure >= self.policy.high_resource_percent or metrics.dropped_frames >= 3
        recovered = fps_ratio >= self.policy.recover_fps_ratio and pressure < self.policy.high_resource_percent and metrics.dropped_frames == 0

        if critical:
            self._degraded = True
            return GovernorDecision(GovernorAction.FORCE_PROXY, 0.5, True, self.policy.max_proxy_boost, "critical_playback_pressure")
        if low:
            self._degraded = True
            return GovernorDecision(GovernorAction.PAUSE_BACKGROUND, 0.67, True, min(250, self.policy.max_proxy_boost), "low_playback_headroom")
        if self._degraded and recovered:
            self._degraded = False
            return GovernorDecision(GovernorAction.RECOVER, 1.0, False, 0, "playback_recovered")
        if self._degraded:
            return GovernorDecision(GovernorAction.REDUCE_PREVIEW, 0.75, False, 100, "holding_reduced_preview")
        return GovernorDecision(GovernorAction.NORMAL, 1.0, False, 0, "healthy_playback")

    def reset(self) -> None:
        self._degraded = False
