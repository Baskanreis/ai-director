"""CapCut-inspired *categories* of video effect presets.

These are deterministic FFmpeg-compatible parameter presets; no proprietary
CapCut assets are copied. Names describe the visual treatment, not a claim of
being the CapCut implementation.
"""
from __future__ import annotations
from app.brain.effects_preset import EFFECTS_PRESETS

EXTRA_EFFECTS = {
    "clean_pop": {"brightness": 0.01, "contrast": 1.06, "saturation": 1.08, "gamma": 1.0},
    "social_vivid": {"brightness": 0.02, "contrast": 1.16, "saturation": 1.28, "gamma": 0.98},
    "warm_story": {"brightness": 0.02, "contrast": 1.04, "saturation": 1.08, "gamma": 1.04},
    "cool_tech": {"brightness": 0.0, "contrast": 1.14, "saturation": 0.9, "gamma": 1.0},
    "noir": {"brightness": -0.04, "contrast": 1.35, "saturation": 0.05, "gamma": 0.92},
    "dream": {"brightness": 0.06, "contrast": 0.86, "saturation": 0.9, "gamma": 1.12},
    "moody": {"brightness": -0.05, "contrast": 1.22, "saturation": 0.78, "gamma": 0.94},
    "punch": {"brightness": 0.0, "contrast": 1.28, "saturation": 1.22, "gamma": 0.98},
    "pastel": {"brightness": 0.04, "contrast": 0.88, "saturation": 0.78, "gamma": 1.08},
    "film_soft": {"brightness": 0.01, "contrast": 0.96, "saturation": 0.84, "gamma": 1.03},
    "orange_teal": {"brightness": 0.01, "contrast": 1.15, "saturation": 1.12, "gamma": 1.0},
    "night_boost": {"brightness": 0.08, "contrast": 1.08, "saturation": 0.92, "gamma": 1.18},
    "product_clean": {"brightness": 0.03, "contrast": 1.10, "saturation": 1.04, "gamma": 1.02},
    "food_crisp": {"brightness": 0.03, "contrast": 1.18, "saturation": 1.34, "gamma": 1.0},
    "travel_sunny": {"brightness": 0.05, "contrast": 1.08, "saturation": 1.24, "gamma": 1.04},
    "retro_fade": {"brightness": 0.03, "contrast": 0.86, "saturation": 0.72, "gamma": 1.08},
    "high_contrast": {"brightness": -0.02, "contrast": 1.42, "saturation": 1.06, "gamma": 0.96},
    "skin_soft": {"brightness": 0.02, "contrast": 0.94, "saturation": 0.98, "gamma": 1.05},
    "shorts_energy": {"brightness": 0.01, "contrast": 1.22, "saturation": 1.32, "gamma": 0.98},
    "documentary": {"brightness": 0.0, "contrast": 1.06, "saturation": 0.9, "gamma": 1.02},
    "dark_cinematic": {"brightness": -0.07, "contrast": 1.28, "saturation": 0.72, "gamma": 0.9},
    "bright_cinematic": {"brightness": 0.05, "contrast": 1.12, "saturation": 0.92, "gamma": 1.08},
    "vlog": {"brightness": 0.03, "contrast": 1.06, "saturation": 1.12, "gamma": 1.03},
    "gaming": {"brightness": 0.0, "contrast": 1.26, "saturation": 1.42, "gamma": 0.96},
    "minimal": {"brightness": 0.0, "contrast": 1.02, "saturation": 0.96, "gamma": 1.01},
}

ALL_EFFECTS = {**EFFECTS_PRESETS, **EXTRA_EFFECTS}

def effect_names() -> list[str]:
    return list(ALL_EFFECTS)
