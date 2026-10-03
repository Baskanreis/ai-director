"""Kucuk yardimci fonksiyonlar."""
from __future__ import annotations


def fmt_time(seconds: float, ms: bool = True) -> str:
    """Saniyeyi MM:SS.mmm (veya HH:MM:SS.mmm) bicimine cevirir."""
    seconds = max(0.0, float(seconds))
    total_ms = int(round(seconds * 1000))
    h, rem = divmod(total_ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1000)
    base = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
    return f"{base}.{milli:03d}" if ms else base


def fmt_timecode(seconds: float, fps: float = 30.0) -> str:
    """Saniyeyi SMPTE benzeri HH:MM:SS:FF timecode bicimine cevirir (FF = kare no)."""
    seconds = max(0.0, float(seconds))
    fps = fps if fps and fps > 0 else 30.0
    total_frames = int(round(seconds * fps))
    frames_per_hour = int(round(fps * 3600))
    frames_per_min = int(round(fps * 60))
    frames_per_sec = int(round(fps))
    h, rem = divmod(total_frames, frames_per_hour)
    m, rem = divmod(rem, frames_per_min)
    s, f = divmod(rem, frames_per_sec)
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"
