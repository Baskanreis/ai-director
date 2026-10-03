"""Unified FFmpeg render helpers: structured captions and timed SFX.

The command builder consumes the resulting RenderOptions in the same FFmpeg
filter_complex graph as video transitions, Smart Reframe keyframes and audio
track ducking. No intermediate media render is required.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
import re

from app.subtitle.style import SubtitleStyle

@dataclass(frozen=True)
class SFXEvent:
    path: str
    start: float
    end: float
    gain_db: float = -12.0
    fade_in: float = 0.03
    fade_out: float = 0.08

@dataclass
class RenderOptions:
    """Optional render-layer inputs; timestamps are timeline seconds."""
    ass_path: str | None = None
    captions: list[dict[str, Any]] = field(default_factory=list)
    sfx: list[SFXEvent] = field(default_factory=list)
    music_duck_db: float = -10.0
    duck_threshold: float = 0.06
    duck_ratio: float = 8.0
    duck_attack_ms: float = 5.0
    duck_release_ms: float = 300.0
    normalize_final_audio: bool = False
    caption_style: SubtitleStyle | str | None = "karaoke_highlight"
    always_highlight: set[str] | None = None

def _ass_time(seconds: float) -> str:
    cs = max(0, round(float(seconds) * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"

def _ass_escape(value: str) -> str:
    return (str(value).replace("\\", r"\\").replace("{", r"\{")
            .replace("}", r"\}").replace("\n", r"\N"))

def write_caption_ass(captions: Iterable[dict[str, Any]], output_path: str | Path,
                      width: int = 1080, height: int = 1920) -> Path:
    """Serialize caption metadata into animated ASS dialogue events."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {int(width)}",
        f"PlayResY: {int(height)}", "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        "Style: Default,Arial,64,&H00FFFFFF,&H0000FFFF,&H00101010,&H80000000,-1,0,1,4,2,2,80,80,180,1",
        "", "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
    ]
    for item in captions:
        try:
            start, end = float(item["start"]), float(item["end"])
            text = str(item.get("text", "")).strip()
        except (KeyError, TypeError, ValueError):
            continue
        if end <= start or not text:
            continue
        animation = str(item.get("animation", "pop")).lower()
        if animation == "pop":
            fx = r"{\fscx70\fscy70\t(0,120,\fscx100\fscy100)}"
        elif animation == "fade":
            fx = r"{\fad(120,100)}"
        elif animation == "karaoke":
            fx = r"{\fad(50,80)\c&H00FFFF&}"
        else:
            fx = ""
        position = str(item.get("position", "lower_safe"))
        if position == "center":
            fx += r"{\an5\pos(%d,%d)}" % (width // 2, height // 2)
        elif position == "upper_safe":
            fx += r"{\an8\pos(%d,%d)}" % (width // 2, int(height * .18))
        else:
            fx += r"{\an2\pos(%d,%d)}" % (width // 2, int(height * .82))
        emphasis = item.get("emphasis_words") or item.get("emphasis") or []
        rendered = _ass_escape(text)
        for word in sorted((str(x) for x in emphasis if x), key=len, reverse=True):
            rendered = re.sub(
                rf"(?<!\\w)({re.escape(_ass_escape(word))})(?!\\w)",
                lambda match: r"{\c&H0000FF&}" + match.group(1) + r"{\c&HFFFFFF&}",
                rendered, flags=re.IGNORECASE)
        lines.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,,0,0,0,,{fx}{rendered}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return out

def options_from_director(captions=(), sound_plan=None, duration=None,
                          ass_path=None, music_duck_db=-10.0) -> RenderOptions:
    """Normalize Director caption and SFX decisions into render options."""
    cues = []
    for cue in (sound_plan or {}).get("cues", []):
        try:
            start = max(0.0, float(cue.get("start", 0)))
            end = min(float(duration), float(cue.get("end", start + .5))) if duration is not None else float(cue.get("end", start + .5))
            asset = str(cue.get("path") or cue.get("asset_path") or "")
            if asset and end > start:
                cues.append(SFXEvent(asset, start, end, float(cue.get("gain_db", -12)),
                                     float(cue.get("fade_in", .03)), float(cue.get("fade_out", .08))))
        except (TypeError, ValueError):
            continue
    return RenderOptions(ass_path=str(ass_path) if ass_path else None,
                         captions=list(captions), sfx=cues,
                         music_duck_db=float(music_duck_db))
