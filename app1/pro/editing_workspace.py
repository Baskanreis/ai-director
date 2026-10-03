"""Persistent professional editing state: selections, ranges and edit modes."""
from __future__ import annotations
from dataclasses import dataclass, field

EDIT_MODES = ("select", "ripple", "roll", "slip", "slide", "razor", "hand")

@dataclass
class EditingWorkspace:
    selected_clip_ids: list[str] = field(default_factory=list)
    selected_track_ids: list[str] = field(default_factory=list)
    range_start: float | None = None
    range_end: float | None = None
    playhead: float = 0.0
    edit_mode: str = "select"
    snap_enabled: bool = True
    snap_threshold: float = 0.08
    linked_selection: bool = True

    def set_mode(self, mode: str) -> str:
        if mode not in EDIT_MODES:
            raise ValueError(f"Bilinmeyen edit modu: {mode}")
        self.edit_mode = mode
        return mode

    def select(self, clip_ids, additive: bool = False) -> None:
        ids = list(dict.fromkeys(str(x) for x in clip_ids))
        if additive:
            self.selected_clip_ids = list(dict.fromkeys(self.selected_clip_ids + ids))
        else:
            self.selected_clip_ids = ids

    def clear_selection(self) -> None:
        self.selected_clip_ids.clear()

    def set_range(self, start: float | None, end: float | None) -> None:
        if start is None or end is None:
            self.range_start = self.range_end = None
            return
        a, b = sorted((max(0.0, float(start)), max(0.0, float(end))))
        if b <= a:
            self.range_start = self.range_end = None
        else:
            self.range_start, self.range_end = a, b

    @property
    def has_range(self) -> bool:
        return self.range_start is not None and self.range_end is not None and self.range_end > self.range_start

    def to_dict(self) -> dict:
        return {
            "selected_clip_ids": self.selected_clip_ids,
            "selected_track_ids": self.selected_track_ids,
            "range_start": self.range_start,
            "range_end": self.range_end,
            "playhead": self.playhead,
            "edit_mode": self.edit_mode,
            "snap_enabled": self.snap_enabled,
            "snap_threshold": self.snap_threshold,
            "linked_selection": self.linked_selection,
        }

    @classmethod
    def from_dict(cls, d: dict | None) -> "EditingWorkspace":
        d = d or {}
        w = cls(
            selected_clip_ids=list(d.get("selected_clip_ids") or []),
            selected_track_ids=list(d.get("selected_track_ids") or []),
            range_start=d.get("range_start"), range_end=d.get("range_end"),
            playhead=max(0.0, float(d.get("playhead", 0.0))),
            edit_mode=str(d.get("edit_mode", "select")),
            snap_enabled=bool(d.get("snap_enabled", True)),
            snap_threshold=max(0.0, float(d.get("snap_threshold", 0.08))),
            linked_selection=bool(d.get("linked_selection", True)),
        )
        if w.edit_mode not in EDIT_MODES: w.edit_mode = "select"
        return w
