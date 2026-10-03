"""EFFECTS — AI Pipeline'in "Effects" aşaması: hazır renk/görsel ön ayarları.

KEYFRAME ENGINE'in "effect:*" parçalarını (brightness/contrast/saturation/gamma,
bkz. `app.timeline.model.EFFECT_KEYFRAME_NAMES`) kullanarak klibe tek bir sabit
(zamanla değişmeyen) değer kümesi uygular — yani her biri için tek bir
keyframe (t=0) atanır. Böylece render motoru (ffmpeg `eq` filtresi,
`app.effects.video_effects.effects_fragment`) için ayrı bir kod yolu gerekmez.
"""
from __future__ import annotations

from app.timeline.model import Clip, Keyframe

EFFECTS_PRESETS: dict[str, dict[str, float]] = {
    "none": {},
    "cinematic": {"brightness": -0.02, "contrast": 1.18, "saturation": 0.88, "gamma": 1.05},
    "vivid": {"brightness": 0.02, "contrast": 1.12, "saturation": 1.35, "gamma": 1.0},
    "soft": {"brightness": 0.03, "contrast": 0.92, "saturation": 0.95, "gamma": 1.1},
}


def preset_names() -> list[str]:
    from app.effects.effect_library import ALL_EFFECTS
    return list(ALL_EFFECTS.keys())


def apply_effects_preset(clip: Clip, preset_name: str) -> dict[str, float]:
    """`preset_name`deki değerleri klibe `effect:*` keyframe'leri olarak yazar.

    `"none"` (veya bilinmeyen bir isim) için hiçbir şey yapmaz. Uygulanan
    değerlerin bir kopyasını döndürür (raporlama/log için).
    """
    from app.effects.effect_library import ALL_EFFECTS
    values = ALL_EFFECTS.get(preset_name, EFFECTS_PRESETS.get(preset_name, {}))
    for name, value in values.items():
        clip.keyframes[f"effect:{name}"] = [Keyframe(time=0.0, value=value)]
    return dict(values)


__all__ = ["EFFECTS_PRESETS", "preset_names", "apply_effects_preset"]
