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
    "bleach": {"brightness": -0.02, "contrast": 1.18, "saturation": 0.62, "gamma": 1.02},
}


# Expanded original look library (metadata-only; no third-party presets/assets).
EXPANDED_EFFECTS = {
    "viral_pop": {"brightness": 0.02, "contrast": 1.20, "saturation": 1.30, "gamma": 0.98},
    "creator_skin": {"brightness": 0.025, "contrast": 0.96, "saturation": 1.00, "gamma": 1.04},
    "studio_clean": {"brightness": 0.015, "contrast": 1.08, "saturation": 1.02, "gamma": 1.02},
    "golden_hour": {"brightness": 0.04, "contrast": 1.06, "saturation": 1.18, "gamma": 1.06},
    "sunset_glow": {"brightness": 0.03, "contrast": 1.04, "saturation": 1.24, "gamma": 1.05},
    "blue_hour": {"brightness": -0.01, "contrast": 1.12, "saturation": 0.96, "gamma": 0.98},
    "cyberpunk": {"brightness": -0.01, "contrast": 1.32, "saturation": 1.45, "gamma": 0.94},
    "vhs_fade": {"brightness": 0.02, "contrast": 0.84, "saturation": 0.82, "gamma": 1.08},
    "analog_warm": {"brightness": 0.025, "contrast": 0.92, "saturation": 1.06, "gamma": 1.06},
    "matte_film": {"brightness": 0.02, "contrast": 0.90, "saturation": 0.86, "gamma": 1.04},
    "crisp_portrait": {"brightness": 0.015, "contrast": 1.18, "saturation": 1.06, "gamma": 1.02},
    "beauty_soft": {"brightness": 0.035, "contrast": 0.88, "saturation": 0.96, "gamma": 1.10},
    "food_pop": {"brightness": 0.035, "contrast": 1.20, "saturation": 1.42, "gamma": 1.01},
    "product_white": {"brightness": 0.045, "contrast": 1.04, "saturation": 0.92, "gamma": 1.08},
    "travel_tropical": {"brightness": 0.045, "contrast": 1.10, "saturation": 1.36, "gamma": 1.04},
    "travel_cool": {"brightness": 0.015, "contrast": 1.12, "saturation": 1.08, "gamma": 1.00},
    "gaming_neon": {"brightness": -0.02, "contrast": 1.34, "saturation": 1.50, "gamma": 0.94},
    "gaming_dark": {"brightness": -0.06, "contrast": 1.38, "saturation": 1.24, "gamma": 0.88},
    "podcast_clean": {"brightness": 0.01, "contrast": 1.04, "saturation": 0.94, "gamma": 1.03},
    "podcast_warm": {"brightness": 0.02, "contrast": 1.02, "saturation": 1.04, "gamma": 1.06},
    "education_clear": {"brightness": 0.025, "contrast": 1.10, "saturation": 1.00, "gamma": 1.04},
    "dramatic_red": {"brightness": -0.035, "contrast": 1.34, "saturation": 1.18, "gamma": 0.92},
    "dreamy_glow": {"brightness": 0.075, "contrast": 0.82, "saturation": 0.96, "gamma": 1.14},
    "soft_morning": {"brightness": 0.06, "contrast": 0.90, "saturation": 1.02, "gamma": 1.10},
    "black_white_crisp": {"brightness": 0.0, "contrast": 1.30, "saturation": 0.0, "gamma": 1.0},
    "black_white_soft": {"brightness": 0.025, "contrast": 0.92, "saturation": 0.0, "gamma": 1.06},
    "teal_cinema": {"brightness": 0.0, "contrast": 1.18, "saturation": 1.08, "gamma": 0.98},
    "gold_cinema": {"brightness": 0.025, "contrast": 1.16, "saturation": 1.12, "gamma": 1.05},
    "night_neon": {"brightness": 0.04, "contrast": 1.20, "saturation": 1.28, "gamma": 1.10},
    "low_light_recover": {"brightness": 0.11, "contrast": 1.03, "saturation": 0.98, "gamma": 1.20},
    "high_key": {"brightness": 0.08, "contrast": 0.96, "saturation": 1.00, "gamma": 1.10},
    "low_key": {"brightness": -0.09, "contrast": 1.28, "saturation": 0.84, "gamma": 0.90},
}

ALL_EFFECTS = {**EFFECTS_PRESETS, **EXTRA_EFFECTS, **EXPANDED_EFFECTS}

def effect_names() -> list[str]:
    return list(ALL_EFFECTS)
