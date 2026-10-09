"""Altyazı görsel stili: renk/font/konum + animasyon/vurgu ayarları.

Bu modül saf Python'dur (Qt/ffmpeg gerektirmez) — `ass_format.to_ass()` burada
tanımlanan `SubtitleStyle`'ı okuyarak bir .ass dosyası üretir, bunu da
`embed.burn_in_ass()` ffmpeg'in `subtitles=` filtresiyle (libass) videoya yakar.

v0.7 Subtitle Engine'de istenen ek özellikler burada karşılanır:
- **Subtitle styles**: font, boyut, renk, dış çizgi, konum (alt/üst/orta) — `SubtitleStyle`.
- **Animated subtitles**: giriş/çıkış efekti (`Animation`) — fade / pop(büyüyerek belir) / kaygan(slide-up).
- **Highlighted words**: o an konuşulan kelimenin farklı renk+ölçekle vurgulanması (`highlight_words=True`).
- **Emoji support**: metin UTF-8 olarak saklanır/yazılır; emoji glifleri için sistemde emoji
  destekli bir font varsa (`emoji_font`) o da force-font olarak biçime eklenebilir.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Position(str, Enum):
    BOTTOM = "bottom"
    TOP = "top"
    MIDDLE = "middle"


class Animation(str, Enum):
    NONE = "none"
    FADE = "fade"
    POP = "pop"
    SLIDE_UP = "slide_up"
    SLIDE_LEFT = "slide_left"
    BOUNCE = "bounce"
    TYPEWRITER = "typewriter"
    GLITCH = "glitch"
    NEON_PULSE = "neon_pulse"
    HIGHLIGHT_SWEEP = "highlight_sweep"
    SHAKE = "shake"
    ZOOM = "zoom"


# ASS alignment (numpad düzeni): 1-3 alt, 4-6 orta, 7-9 üst; burada hep ortalanmış (2/5/8) kullanılır.
_POSITION_TO_ALIGN: dict[Position, int] = {Position.BOTTOM: 2, Position.MIDDLE: 5, Position.TOP: 8}


def _hex_to_ass_bgr(hex_color: str, alpha: int = 0) -> str:
    """`#RRGGBB` (veya `RRGGBB`) rengini ASS'in bekledigi `&HAABBGGRR&` dizgesine çevirir.

    ASS renkleri BGR sıralıdır ve başına alfa baytı eklenir (`00` = tam opak,
    `FF` = tam saydam). `alpha` 0..255 aralığında verilir.
    """
    h = hex_color.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Geçersiz renk: {hex_color!r} (ör. '#FFFFFF' olmalı)")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b.upper()}{g.upper()}{r.upper()}&"


@dataclass
class SubtitleStyle:
    """Bir altyazı görünüm ön ayarı.

    `font_size`/konum ffmpeg'in "oynatım alanı" 384x288 referansına göre `PlayResY`
    ile ölçeklenir (`ass_format` bunu video en-boy oranına göre otomatik ayarlar).
    """

    name: str = "Varsayılan"
    font: str = "Arial"
    font_size: int = 20
    bold: bool = True
    text_color: str = "#FFFFFF"       # normal (vurgusuz) kelime rengi
    highlight_color: str = "#2FE37A"  # o an konuşulan / önemli kelime rengi
    outline_color: str = "#000000"
    outline_width: float = 2.5
    shadow: float = 0.0
    background_box: bool = False      # True: yarı saydam arka plan kutusu (BorderStyle=3)
    background_color: str = "#000000"
    background_alpha: int = 120       # 0 (opak) .. 255 (tam saydam)
    position: Position = Position.BOTTOM
    margin_v: int = 60                # alt/üst kenardan piksel boşluk (PlayResY'ye göre)
    animation: Animation = Animation.FADE
    animation_ms: int = 180
    highlight_words: bool = True      # o an konuşulan kelimeyi vurgula (karaoke tarzı)
    highlight_scale: float = 1.18     # vurgulu kelimenin ölçek çarpanı (pop efekti)
    emoji_enabled: bool = False       # anahtar kelimelere göre otomatik emoji ekle
    emoji_font: str | None = None     # ör. "Noto Color Emoji" (sistemde kuruluysa)

    def align(self) -> int:
        return _POSITION_TO_ALIGN[self.position]

    def ass_primary_colour(self) -> str:
        return _hex_to_ass_bgr(self.text_color)

    def ass_highlight_colour(self) -> str:
        return _hex_to_ass_bgr(self.highlight_color)

    def ass_outline_colour(self) -> str:
        return _hex_to_ass_bgr(self.outline_color)

    def ass_back_colour(self) -> str:
        return _hex_to_ass_bgr(self.background_color, alpha=self.background_alpha)


# ---- hazır ön ayarlar --------------------------------------------------------

PRESETS: dict[str, SubtitleStyle] = {
    "classic": SubtitleStyle(
        name="Klasik", font_size=20, bold=False, highlight_words=False, animation=Animation.NONE,
    ),
    "modern_bold": SubtitleStyle(
        name="Modern Kalın", font_size=24, bold=True, outline_width=3.0,
        animation=Animation.FADE, highlight_words=True,
    ),
    "karaoke_highlight": SubtitleStyle(
        name="Karaoke Vurgu", font_size=26, bold=True, text_color="#FFFFFF",
        highlight_color="#FFD400", animation=Animation.POP, highlight_words=True,
        highlight_scale=1.25,
    ),
    "neon": SubtitleStyle(
        name="Neon", font_size=24, bold=True, text_color="#00E5FF", highlight_color="#FF2FD0",
        outline_color="#0A0A1A", outline_width=3.5, animation=Animation.SLIDE_UP,
        highlight_words=True,
    ),
    "bold_hook": SubtitleStyle(
        name="Bold Hook", font="Arial", font_size=30, bold=True,
        text_color="#FFFFFF", highlight_color="#FFD400", outline_width=4.0,
        animation=Animation.POP, animation_ms=140, highlight_words=True, highlight_scale=1.22,
        position=Position.MIDDLE, margin_v=90,
    ),
    "kinetic_bounce": SubtitleStyle(
        name="Kinetic Bounce", font_size=26, bold=True, text_color="#FFFFFF",
        highlight_color="#00E5FF", outline_width=3.0, animation=Animation.BOUNCE,
        animation_ms=220, highlight_words=True, highlight_scale=1.18,
    ),
    "glitch_caption": SubtitleStyle(
        name="Glitch Caption", font_size=25, bold=True, text_color="#FFFFFF",
        highlight_color="#FF2FD0", outline_color="#101020", outline_width=3.0,
        animation=Animation.GLITCH, animation_ms=160, highlight_words=True,
    ),
    "neon_pulse": SubtitleStyle(
        name="Neon Pulse", font_size=25, bold=True, text_color="#00E5FF",
        highlight_color="#FF2FD0", outline_color="#081018", outline_width=3.0,
        animation=Animation.NEON_PULSE, animation_ms=400, highlight_words=True,
    ),
    "typewriter": SubtitleStyle(
        name="Typewriter", font="Courier New", font_size=22, bold=False,
        text_color="#FFFFFF", highlight_words=False, animation=Animation.TYPEWRITER,
        animation_ms=300,
    ),
    "highlight_sweep": SubtitleStyle(
        name="Highlight Sweep", font_size=24, bold=True, text_color="#FFFFFF",
        highlight_color="#FFD400", outline_width=3.0, animation=Animation.HIGHLIGHT_SWEEP,
        animation_ms=280, highlight_words=True,
    ),
    "minimal_box": SubtitleStyle(
        name="Minimal Kutu", font_size=20, bold=False, background_box=True,
        background_alpha=140, outline_width=0.0, animation=Animation.FADE, highlight_words=False,
    ),
}

DEFAULT_PRESET = "modern_bold"


def get_preset(key: str) -> SubtitleStyle:
    if key not in PRESETS:
        raise KeyError(f"Bilinmeyen stil ön ayarı: {key!r}. Seçenekler: {', '.join(PRESETS)}")
    # kopya döndür: çağıran değiştirirse ortak ön ayarı bozmasın
    import copy

    return copy.deepcopy(PRESETS[key])


__all__ = [
    "Position",
    "Animation",
    "SubtitleStyle",
    "PRESETS",
    "DEFAULT_PRESET",
    "get_preset",
]
