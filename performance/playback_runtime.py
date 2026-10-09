"""Runtime bridge between measured preview cadence and the playback governor.

This module is Qt-independent so playback policy can be tested without a GUI.
It turns real tick timing into PlaybackMetrics and exposes deterministic hooks for
background workers/proxy prioritisation. UI layers may feed CPU/GPU/VRAM telemetry
when available; missing telemetry is deliberately treated as unknown.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Callable

from .playback_governor import (
    GovernorDecision,
    PlaybackGovernorPolicy,
    PlaybackMetrics,
    PlaybackPerformanceGovernor,
)


@dataclass(frozen=True)
class PlaybackTelemetry:
    fps: float
    target_fps: float
    dropped_frames: int
    cpu_percent: float | None = None
    gpu_percent: float | None = None
    vram_percent: float | None = None


class PlaybackRuntimeBridge:
    """Converts playback ticks into governor decisions and applies safe hooks."""

    def __init__(
        self,
        policy: PlaybackGovernorPolicy | None = None,
        *,
        background_pause: Callable[[bool], None] | None = None,
        proxy_boost: Callable[[int], None] | None = None,
        decision_sink: Callable[[GovernorDecision], None] | None = None,
    ):
        self.governor = PlaybackPerformanceGovernor(policy)
        self.background_pause = background_pause
        self.proxy_boost = proxy_boost
        self.decision_sink = decision_sink
        self._last_tick: float | None = None
        self._ema_interval: float | None = None
        self._dropped = 0
        self._running = False
        self.last_decision: GovernorDecision | None = None

    def start(self, now: float | None = None) -> None:
        self._last_tick = monotonic() if now is None else float(now)
        self._ema_interval = None
        self._dropped = 0
        self._running = True
        self.governor.reset()

    def stop(self) -> None:
        self._running = False
        self._last_tick = None
        self._ema_interval = None
        self._dropped = 0
        if self.background_pause:
            self.background_pause(False)
        self.last_decision = None

    def tick(
        self,
        *,
        target_fps: float = 30.0,
        now: float | None = None,
        cpu_percent: float | None = None,
        gpu_percent: float | None = None,
        vram_percent: float | None = None,
    ) -> tuple[PlaybackTelemetry, GovernorDecision]:
        if not self._running:
            self.start(now)
        current = monotonic() if now is None else float(now)
        if self._last_tick is None:
            self._last_tick = current
        interval = max(1e-6, current - self._last_tick)
        self._last_tick = current
        # EMA keeps one delayed Qt timer callback from causing a wild FPS jump.
        self._ema_interval = interval if self._ema_interval is None else (self._ema_interval * 0.75 + interval * 0.25)
        fps = min(float(target_fps) * 1.5, 1.0 / self._ema_interval)
        expected = 1.0 / max(1.0, float(target_fps))
        if interval > expected * 1.5:
            self._dropped += max(1, int(round(interval / expected)) - 1)
        elif self._dropped:
            self._dropped -= 1
        metrics = PlaybackMetrics(
            fps=fps,
            target_fps=float(target_fps),
            cpu_percent=cpu_percent,
            gpu_percent=gpu_percent,
            vram_percent=vram_percent,
            dropped_frames=self._dropped,
        )
        decision = self.governor.decide(metrics)
        self.last_decision = decision
        if self.background_pause:
            self.background_pause(decision.pause_background)
        if self.proxy_boost:
            self.proxy_boost(decision.proxy_priority_boost)
        if self.decision_sink:
            self.decision_sink(decision)
        return PlaybackTelemetry(fps, float(target_fps), self._dropped, cpu_percent, gpu_percent, vram_percent), decision

    def reset_dropped_frames(self) -> None:
        self._dropped = 0
