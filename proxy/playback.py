"""Playhead-aware proxy prioritization and automatic source switching."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.timeline.model import Clip, Timeline
from app.pro.advanced_nle import ProxyManager
from .cache import ProxyCache


@dataclass(frozen=True)
class ProxyPriority:
    clip_id: str
    media_id: str
    distance_s: float
    priority: int
    reason: str


class PlayheadProxyPlanner:
    """Ranks timeline clips by proximity to the playhead.

    Visible/current clips receive the strongest boost, followed by clips just ahead
    of the playhead. The planner is deterministic and does not touch media files.
    """
    def __init__(self, lookahead_s: float = 30.0, behind_s: float = 8.0):
        self.lookahead_s = max(0.0, float(lookahead_s))
        self.behind_s = max(0.0, float(behind_s))

    @staticmethod
    def _distance(clip: Clip, time_s: float) -> float:
        if clip.start <= time_s < clip.end:
            return 0.0
        if time_s < clip.start:
            return clip.start - time_s
        return time_s - clip.end

    def rank(self, timeline: Timeline, playhead_s: float, *, video_only: bool = True) -> list[ProxyPriority]:
        ranked: list[ProxyPriority] = []
        for clip in timeline.all_clips():
            if video_only and not any(t.kind == "video" and clip in t.clips for t in timeline.tracks):
                continue
            distance = self._distance(clip, float(playhead_s))
            if distance == 0:
                priority = 1000; reason = "playhead_active"
            elif clip.start >= playhead_s and distance <= self.lookahead_s:
                priority = max(1, 800 - int(distance * 10)); reason = "playhead_lookahead"
            elif clip.end <= playhead_s and distance <= self.behind_s:
                priority = max(1, 500 - int(distance * 10)); reason = "playhead_behind"
            else:
                continue
            ranked.append(ProxyPriority(clip.id, clip.media_id, round(distance, 4), priority, reason))
        return sorted(ranked, key=lambda x: (-x.priority, x.distance_s, x.clip_id))


class ProxyAutoSwitch:
    """Resolves the active playback source without mutating the timeline."""
    def __init__(self, manager: ProxyManager, cache: ProxyCache | None = None):
        self.manager = manager
        self.cache = cache
        self.enabled = True

    def source_for(self, clip: Clip, original_path: str) -> str:
        if not self.enabled:
            return original_path
        path = self.manager.active_path(clip.media_id, original_path, use_proxies=True)
        if self.cache and path != original_path:
            self.cache.touch(clip.media_id)
        return path

    def is_using_proxy(self, clip: Clip, original_path: str) -> bool:
        return self.source_for(clip, original_path) != original_path

    def ready_media(self) -> set[str]:
        return {media_id for media_id, asset in self.manager.assets.items() if asset.ready or asset.exists}
