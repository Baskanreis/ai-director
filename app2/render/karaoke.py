"""Render-ready word-level karaoke caption adapter.

The UI/transcription layer can keep neutral Word/Segment metadata. This module
turns it into ASS events that libass/FFmpeg can burn in the same final render.
"""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from app.subtitle.ass_format import to_ass
from app.subtitle.models import Segment, Word
from app.subtitle.style import SubtitleStyle, get_preset


def _word(value: dict[str, Any]) -> Word | None:
    try:
        text = str(value.get("text", "")).strip()
        start = float(value["start"])
        end = float(value["end"])
        if not text or end <= start:
            return None
        return Word(text=text, start=start, end=end, prob=float(value.get("prob", 1.0)))
    except (TypeError, ValueError, KeyError):
        return None


def events_to_segments(events: Iterable[dict[str, Any]]) -> list[Segment]:
    """Group caption metadata into renderable segments.

    A caption event may contain ``words`` for true word-level karaoke. Without
    ``words`` it remains a normal timed caption. Adjacent events sharing
    ``segment_id`` are merged, preserving their word timings.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for item in events:
        try:
            start = float(item["start"]); end = float(item["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if end <= start:
            continue
        key = str(item.get("segment_id", f"event:{len(order)}:{start:.6f}"))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(dict(item))

    segments: list[Segment] = []
    for key in order:
        items = groups[key]
        words: list[Word] = []
        for item in items:
            for raw in item.get("words", []) or []:
                w = _word(raw)
                if w:
                    words.append(w)
            if not item.get("words"):
                w = _word(item)
                if w:
                    words.append(w)
        words.sort(key=lambda w: (w.start, w.end))
        start = min(float(x["start"]) for x in items)
        end = max(float(x["end"]) for x in items)
        text = " ".join(str(x.get("text", "")).strip() for x in items if str(x.get("text", "")).strip())
        if words:
            # Avoid duplicating text when the event itself is only a container.
            text = " ".join(w.text for w in words)
        segments.append(Segment(text=text, start=start, end=end, words=words))
    return segments


def write_karaoke_ass(
    events: Iterable[dict[str, Any]],
    output_path: str | Path,
    style: SubtitleStyle | str | None = None,
    always_highlight: set[str] | None = None,
) -> Path:
    """Write word-timed karaoke ASS for the unified FFmpeg renderer."""
    if style is None:
        style = get_preset("karaoke_highlight")
    elif isinstance(style, str):
        style = get_preset(style)
    segments = events_to_segments(events)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_ass(segments, style, always_highlight), encoding="utf-8")
    return path
