"""Low-latency preview engine primitives.

The engine keeps timeline resolution, media prefetch and playback decisions out of
widget paint/event handlers.  It is intentionally Qt-light: the UI owns the actual
QMediaPlayer while this class owns state, prefetch order and seek coalescing.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Callable

from app.preview.compositor import PreviewFrame, resolve_preview
from app.timeline.model import Timeline


@dataclass(frozen=True)
class PreviewDecision:
    frame: PreviewFrame
    media_path: str | None
    should_switch_source: bool
    should_seek: bool
    target_ms: int
    request_proxy: bool


class PreviewEngine:
    """Stateful preview coordinator for smooth play/seek behavior."""

    def __init__(self, seek_threshold: float = 0.15) -> None:
        self.seek_threshold = max(0.01, float(seek_threshold))
        self.timeline = Timeline()
        self.media_paths: dict[str, str] = {}
        self.current_media: str | None = None
        self.current_clip: str | None = None
        self.last_resolved: PreviewFrame | None = None
        self.last_target: float | None = None
        self.pending_seek: float | None = None
        self._last_seek_at = 0.0

    def set_project(self, timeline: Timeline, media_paths: dict[str, str]) -> None:
        self.timeline = timeline
        self.media_paths = dict(media_paths)
        self.current_media = None
        self.current_clip = None
        self.last_resolved = None
        self.pending_seek = None
        self.last_target = None

    def resolve(self, t: float) -> PreviewFrame:
        frame = resolve_preview(self.timeline, self.media_paths, t)
        self.last_resolved = frame
        self.current_clip = frame.clip_id
        return frame

    def queue_seek(self, seconds: float) -> None:
        self.pending_seek = max(0.0, min(float(seconds), self.timeline.duration))

    def consume_seek(self) -> float | None:
        value = self.pending_seek
        self.pending_seek = None
        if value is not None:
            self._last_seek_at = monotonic()
        return value

    def decide(self, t: float, player_position: float | None, force: bool = False) -> PreviewDecision:
        frame = self.resolve(t)
        if not frame.has_video or not frame.media_path:
            return PreviewDecision(frame, None, self.current_media is not None, False, 0, False)

        target_ms = int(round(frame.source_time * 1000))
        source_changed = frame.media_path != self.current_media
        drift = abs((player_position or 0.0) - frame.source_time)
        should_seek = force or source_changed or drift > self.seek_threshold
        self.current_media = frame.media_path
        self.last_target = frame.source_time

        # Requesting the proxy is cheap when already cached; the manager de-dupes
        # background jobs.  The UI can ignore it during active playback if desired.
        return PreviewDecision(
            frame=frame,
            media_path=frame.media_path,
            should_switch_source=source_changed,
            should_seek=should_seek,
            target_ms=target_ms,
            request_proxy=True,
        )

    def prefetch_adjacent(self, t: float, request: Callable[[str], None], radius: int = 1) -> list[str]:
        """Request proxies for neighboring clips without decoding them on the UI thread."""
        try:
            track = self.timeline.first_track("video")
        except Exception:
            return []
        clips = track.sorted_clips()
        active = self.current_clip
        idx = next((i for i, c in enumerate(clips) if c.id == active), None)
        if idx is None:
            return []
        paths: list[str] = []
        for i in range(max(0, idx - radius), min(len(clips), idx + radius + 1)):
            if i == idx:
                continue
            path = self.media_paths.get(clips[i].media_id)
            if path and path not in paths:
                paths.append(path)
                request(path)
        return paths
