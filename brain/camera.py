"""CAMERA — AI Pipeline'in "Camera" aşaması (v1.4, kural-tabanlı ilk sürüm).

Yüz/nesne takibine dayalı akıllı yeniden kadraj (bkz. `docs/ROADMAP.md`
v1.4 "Smart Reframe") henüz uygulanmadı; bunun yerine, Sahne Algılama
aşamasının zaman damgalarını kullanan, doğal ve öngörülebilir iki kamera
stili sunar ve bunları doğrudan KEYFRAME ENGINE üzerinden
(`clip.keyframes["scale"]`/`["pos_x"]`/`["pos_y"]`) uygular. Bu modül, bu
iki özelliğin (Keyframe Engine + AI Pipeline) nasıl bir araya geldiğinin
somut bir örneğidir: AI, render motorunun zaten anladığı aynı keyframe
dilini üretir.

- `"kenburns"`: klip boyunca yavaş ve sürekli bir yakınlaşma.
- `"scene_recenter"`: her sahne kesiminde hafif, yön değiştiren bir kaydırma
  (pan) + hafif yakınlaşma; kesitler arası `ease_in_out` ile yumuşak geçiş.
- `"none"`: hiçbir keyframe üretmez.
"""
from __future__ import annotations

from app.timeline.model import Clip, Keyframe

CAMERA_STYLES = ("none", "kenburns", "scene_recenter")


def plan_camera_keyframes(
    duration: float,
    scene_times: list[float] | None = None,
    style: str = "kenburns",
    zoom_amount: float = 0.12,
    pan_amount: float = 40.0,
) -> dict[str, list[Keyframe]]:
    """`style`e göre `{"scale": [...], "pos_x": [...]}` keyframe'leri üretir.

    SAF fonksiyondur: klibi DEĞİŞTİRMEZ, yalnızca üretilen planı döndürür.
    Uygulamak için `apply_camera_plan` kullanılır.
    """
    if style not in CAMERA_STYLES or style == "none" or duration <= 0:
        return {}

    if style == "kenburns":
        return {
            "scale": [
                Keyframe(time=0.0, value=1.0, easing="ease_in_out"),
                Keyframe(time=duration, value=1.0 + zoom_amount),
            ],
        }

    # "scene_recenter": her sahne sınırında hafif, alternatif yönlü bir pan.
    times = sorted(t for t in (scene_times or []) if 0.0 < t < duration)
    boundaries = [0.0, *times, duration]
    pos_x_kfs = [
        Keyframe(time=t, value=(pan_amount if i % 2 == 0 else -pan_amount), easing="ease_in_out")
        for i, t in enumerate(boundaries)
    ]
    return {
        "pos_x": pos_x_kfs,
        "scale": [
            Keyframe(time=0.0, value=1.0 + zoom_amount * 0.5, easing="ease_in_out"),
            Keyframe(time=duration, value=1.0 + zoom_amount * 0.5),
        ],
    }


def apply_camera_plan(clip: Clip, plan: dict[str, list[Keyframe]]) -> None:
    """Üretilen planı klibe yazar (aynı isimli mevcut keyframe parçalarının üzerine yazar)."""
    for prop, kfs in plan.items():
        if kfs:
            clip.keyframes[prop] = kfs


__all__ = ["CAMERA_STYLES", "plan_camera_keyframes", "apply_camera_plan"]
