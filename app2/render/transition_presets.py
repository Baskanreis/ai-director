"""Safe, declarative transition presets mapped to the existing timeline contract."""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class TransitionPreset:
    id: str
    kind: str
    duration: float
    tags: tuple[str, ...]
    beat_aligned: bool = False

PRESETS = {
    "clean": TransitionPreset("clean", "crossfade", .35, ("clean", "cinematic")),
    "cinematic": TransitionPreset("cinematic", "crossfade", .55, ("film", "soft")),
    "beat_punch": TransitionPreset("beat_punch", "zoom", .18, ("beat", "shorts", "energy"), True),
    "flash_beat": TransitionPreset("flash_beat", "flash", .10, ("beat", "impact"), True),
    "dramatic": TransitionPreset("dramatic", "fade_black", .25, ("dramatic", "story")),
}

def get_preset(name: str) -> TransitionPreset:
    key = str(name).strip().lower()
    if key not in PRESETS:
        raise KeyError(f"Bilinmeyen transition preset: {name}")
    return PRESETS[key]

def list_presets() -> list[dict]:
    return [asdict(x) for x in PRESETS.values()]

def resolve_duration(name: str, duration: float | None = None) -> float:
    p = get_preset(name)
    return max(.05, min(1.5, float(duration if duration is not None else p.duration)))
