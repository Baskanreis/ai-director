"""Caption animation planning for short-form exports."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class CaptionAnimationCue:
    start: float
    end: float
    style: str
    emphasized_words: tuple[str, ...]
    safe_area: str = "lower_safe"
    animation: str = "pop"


def build_caption_animation(captions: Sequence[object], style: str = "dynamic_bold") -> tuple[CaptionAnimationCue, ...]:
    out=[]
    for c in captions:
        emph=tuple(getattr(c, "emphasis", ()) or ())
        out.append(CaptionAnimationCue(float(c.start), float(c.end), style, emph,
                                       getattr(c, "position", "lower_safe"),
                                       "pop" if emph else "fade"))
    return tuple(out)

__all__=["CaptionAnimationCue","build_caption_animation"]
