"""Lightweight visual-style signatures for the 50K Asset Browser.

The signature is derived from the same recipe/preview descriptors used to render
micro-previews. It gives visual-character similarity without shipping 50K media files
or requiring a second AI model. A future GPU embedding backend can replace this
module without changing the discovery API.
"""
from __future__ import annotations
from math import sqrt
from typing import Iterable

# Coarse axes intentionally describe visible/temporal character rather than names.
_AXES = (
    "motion", "scale", "rotation", "blur", "glow", "contrast", "saturation",
    "sharpness", "energy", "rhythm", "complexity", "softness", "warmth", "density",
)


def _num(params: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(params.get(key, default))
    except (TypeError, ValueError):
        return default


def visual_signature(asset) -> tuple[float, ...]:
    p = asset.params
    tags = {str(x).lower() for x in asset.tags}
    kind = str(asset.kind).lower()

    energy = max(0.0, min(1.0, _num(p, "energy", 0.5)))
    motion = max(0.0, min(1.0, _num(p, "motion", energy)))
    scale = max(0.0, min(1.0, _num(p, "scale", 0.5)))
    rotation = max(0.0, min(1.0, _num(p, "rotation", 0.15 if "rotate" in tags else 0.0)))
    blur = max(0.0, min(1.0, _num(p, "blur", 0.35 if "soft" in tags or "cinematic" in tags else 0.05)))
    glow = max(0.0, min(1.0, _num(p, "glow", 0.75 if "neon" in tags or "glow" in tags else 0.1)))
    contrast = max(0.0, min(1.0, _num(p, "contrast", 0.75 if "impact" in tags or "cinematic" in tags else 0.45)))
    saturation = max(0.0, min(1.0, _num(p, "saturation", 0.8 if "neon" in tags or "colorful" in tags else 0.45)))
    sharpness = max(0.0, min(1.0, _num(p, "sharpness", 0.8 if "crisp" in tags or "impact" in tags else 0.5)))
    rhythm = max(0.0, min(1.0, _num(p, "rhythm", energy)))
    complexity = max(0.0, min(1.0, _num(p, "complexity", 0.8 if "glitch" in tags or "particle" in tags else 0.35)))
    softness = 1.0 - sharpness
    warmth = max(0.0, min(1.0, _num(p, "warmth", 0.7 if "warm" in tags or "travel" in tags else 0.45)))
    density = max(0.0, min(1.0, _num(p, "density", 0.8 if kind in {"overlay", "sticker", "particle"} else 0.45)))
    values = {
        "motion": motion, "scale": scale, "rotation": rotation, "blur": blur,
        "glow": glow, "contrast": contrast, "saturation": saturation, "sharpness": sharpness,
        "energy": energy, "rhythm": rhythm, "complexity": complexity, "softness": softness,
        "warmth": warmth, "density": density,
    }
    return tuple(values[axis] for axis in _AXES)


def cosine(a: Iterable[float], b: Iterable[float]) -> float:
    av, bv = tuple(a), tuple(b)
    dot = sum(x*y for x, y in zip(av, bv))
    na = sqrt(sum(x*x for x in av)); nb = sqrt(sum(y*y for y in bv))
    if not na or not nb:
        return 0.0
    return max(0.0, min(1.0, dot / (na * nb)))
