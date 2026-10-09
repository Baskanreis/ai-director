"""Predictive proxy warmup around the moving playhead."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

from app.timeline.model import Clip, Timeline
from .cache import ProxyCache


@dataclass(frozen=True)
class WarmupTarget:
    clip_id: str
    media_id: str
    distance_s: float
    priority: int
    reason: str


class ProxyWarmupPredictor:
    """Predicts which video clips are likely to be needed next.

    Direction is inferred from consecutive playhead samples unless explicitly
    supplied. Warmup never mutates the timeline or media and skips cached media.
    """
    def __init__(self, lookahead_s: float = 45.0, active_boost: int = 1000):
        self.lookahead_s = max(0.0, float(lookahead_s))
        self.active_boost = int(active_boost)
        self._last_playhead: float | None = None

    def reset(self) -> None:
        self._last_playhead = None

    def direction(self, playhead_s: float, explicit: int | None = None) -> int:
        if explicit in (-1, 1):
            direction = explicit
        elif self._last_playhead is None:
            direction = 1
        else:
            delta = float(playhead_s) - self._last_playhead
            direction = 1 if delta >= 0 else -1
        self._last_playhead = float(playhead_s)
        return direction

    @staticmethod
    def _active(clips: Iterable[Clip], t: float) -> list[Clip]:
        return [c for c in clips if c.start <= t < c.end]

    def plan(self, timeline: Timeline, playhead_s: float, *, playback_speed: float = 1.0,
             direction: int | None = None, cache: ProxyCache | None = None,
             ready_media: set[str] | None = None) -> list[WarmupTarget]:
        direction = self.direction(playhead_s, direction)
        speed = max(0.1, abs(float(playback_speed)))
        horizon = self.lookahead_s * min(2.0, max(0.5, speed))
        ready = ready_media or set()
        candidates: list[WarmupTarget] = []
        video_clips = [c for tr in timeline.tracks if tr.kind == "video" for c in tr.clips]
        for clip in video_clips:
            if clip.media_id in ready or (cache and clip.media_id in cache.entries):
                continue
            if clip.start <= playhead_s < clip.end:
                candidates.append(WarmupTarget(clip.id, clip.media_id, 0.0, self.active_boost, "active_playhead"))
                continue
            distance = (clip.start - playhead_s) if direction > 0 else (playhead_s - clip.end)
            if distance < 0 or distance > horizon:
                continue
            # Closer clips win; reverse playback uses the same monotonic score.
            priority = max(1, 850 - int(distance * 10))
            reason = "forward_warmup" if direction > 0 else "reverse_warmup"
            candidates.append(WarmupTarget(clip.id, clip.media_id, round(distance, 4), priority, reason))
        return sorted(candidates, key=lambda x: (-x.priority, x.distance_s, x.clip_id))
