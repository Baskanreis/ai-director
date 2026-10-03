"""KEYFRAME ENGINE — saf Python deger ornekleme (v1.4).

`app.effects.video_effects`, keyframe'leri ffmpeg `eval=frame` ifadelerine
derler (gercek render icin). Bu modul AYNI matematigi saf Python'da uygular:
- Egri editoru (UI) bir klibin keyframe egrisini ekrana cizmek icin (ffmpeg
  calistirmadan, canli) bu modulu kullanir.
- Test paketi, PySide6/ffmpeg kurulu olmayan bir ortamda bile keyframe
  interpolasyonunu dogrulayabilir.

Iki modulun de AYNI sonucu uretmesi onemlidir; `easing`/`bezier` formulleri
kasitli olarak `video_effects._ease_u_expr` ile birebir aynidir.
"""
from __future__ import annotations

from app.timeline.model import Keyframe

EPS = 1e-9


def _clip01(u: float) -> float:
    return 0.0 if u < 0.0 else (1.0 if u > 1.0 else u)


def ease_u(u: float, easing: str, bezier: tuple[float, float] | None = None) -> float:
    """0..1 araligindaki `u` segment-ici zamanini, `easing`e gore 0..1 araliginda
    yumusatilmis bir degere esler. `video_effects._ease_u_expr` ile ayni formuller.
    """
    u = _clip01(u)
    if easing == "ease_in":
        return u * u
    if easing == "ease_out":
        return 1 - (1 - u) * (1 - u)
    if easing == "ease_in_out":
        return u * u * (3 - 2 * u)
    if easing == "bezier":
        y1, y2 = bezier if bezier else (0.42, 0.58)
        return 3 * (1 - u) * (1 - u) * u * y1 + 3 * (1 - u) * u * u * y2 + u * u * u
    return u  # linear


def sample(keyframes: list[Keyframe], t: float, default: float = 0.0) -> float:
    """`keyframes` listesinden, `t` zamanindaki (klibin kendi basina gore,
    saniye) parcali deger. Keyframe yoksa `default` dondurur; tek keyframe
    varsa sabit degerini dondurur; aksi halde komsu iki keyframe arasinda
    `easing`e gore interpolasyon yapar (ilk/son keyframe'den once/sonra sabit).
    """
    if not keyframes:
        return default
    kfs = sorted(keyframes, key=lambda k: k.time)
    if len(kfs) == 1:
        return kfs[0].value
    if t <= kfs[0].time:
        return kfs[0].value
    if t >= kfs[-1].time:
        return kfs[-1].value
    for a, b in zip(kfs, kfs[1:]):
        if a.time <= t < b.time:
            if a.easing == "hold":
                return a.value
            dt = max(b.time - a.time, EPS)
            u = (t - a.time) / dt
            eased = ease_u(u, a.easing, a.bezier)
            return a.value + (b.value - a.value) * eased
    return kfs[-1].value  # pragma: no cover - kayan nokta kenar durumu


def sample_curve(keyframes: list[Keyframe], default: float, duration: float, steps: int = 200) -> list[tuple[float, float]]:
    """UI egri ciziminde kullanilmak uzere `[0, duration]` araliginda esit
    araliklarla ornekli `(t, value)` noktalari uretir."""
    if duration <= 0 or steps < 2:
        return [(0.0, sample(keyframes, 0.0, default))]
    step = duration / (steps - 1)
    return [(i * step, sample(keyframes, i * step, default)) for i in range(steps)]


def add_or_update_keyframe(
    keyframes: list[Keyframe], time: float, value: float, easing: str = "linear",
    bezier: tuple[float, float] | None = None,
) -> list[Keyframe]:
    """`time`de zaten bir keyframe varsa (EPS toleransla) degerini gunceller,
    yoksa yeni bir keyframe ekler; sonucu zamana gore sirali dondurur. Girdi
    listesini degistirmez (yeni liste dondurur)."""
    out = [k for k in keyframes if abs(k.time - time) > 1e-3]
    out.append(Keyframe(time=max(0.0, time), value=value, easing=easing, bezier=bezier))
    out.sort(key=lambda k: k.time)
    return out


def remove_keyframe(keyframes: list[Keyframe], time: float) -> list[Keyframe]:
    return [k for k in keyframes if abs(k.time - time) > 1e-3]


__all__ = ["ease_u", "sample", "sample_curve", "add_or_update_keyframe", "remove_keyframe"]
