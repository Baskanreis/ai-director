"""Advanced SubStation Alpha (.ass) üretimi — stilli / animasyonlu / kelime vurgulu
altyazılar (v0.7 Subtitle Engine: Subtitle styles, Animated subtitles, Highlighted words).

SRT/VTT (bkz. `formats.py`) yalnızca düz metin + zamanlama taşıyabilir; renk, font,
konum, animasyon ve kelime bazlı vurgu için ffmpeg'in `subtitles=` filtresinin de
(libass üzerinden) native olarak anladığı .ass biçimi kullanılır — yani
`embed.burn_in_ass()` ekstra bir bağımlılık gerektirmez, var olan
`subtitles=...:force_style=...` yoluyla aynı şekilde yakılır.

Bu modül saf Pythondur (ffmpeg/Qt gerektirmez) — bağımsız test edilebilir.

Emoji desteği: metin UTF-8 olarak yazılır (dosya `encoding="utf-8"` ile açılır);
emoji karakterleri normal Unicode metin gibi davranır. Renkli emoji glifi render
kalitesi, seçilen fonta bağlıdır (bkz. `style.SubtitleStyle.emoji_font`).
"""
from __future__ import annotations

from .models import Segment, Transcript, Word
from .style import Animation, SubtitleStyle

# Referans oynatım alanı: libass, gerçek video çözünürlüğüne göre bunu otomatik
# ölçekler (`subtitles=` filtresi `original_size` olmasa da PlayResX/Y'yi okur).
PLAY_RES_X = 1920
PLAY_RES_Y = 1080

_STYLE_NAME_DEFAULT = "Default"
_STYLE_NAME_HIGHLIGHT = "Highlight"


def _ass_timestamp(seconds: float) -> str:
    """ASS zaman damgası: `H:MM:SS.CC` (yüzüncü saniye hassasiyeti)."""
    total_cs = max(round(seconds * 100), 0)
    h, rem = divmod(total_cs, 360_000)
    m, rem = divmod(rem, 6_000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _escape(text: str) -> str:
    """ASS metin alanı için kaçış: `\\N` satır sonu, `{`/`}` override bloğu olarak
    algılanmasın diye kaçışlanır."""
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")


def _border_style(style: SubtitleStyle) -> int:
    return 3 if style.background_box else 1  # 1 = dış çizgi+gölge, 3 = opak kutu


def build_styles_section(style: SubtitleStyle) -> str:
    bold = -1 if style.bold else 0
    border = _border_style(style)
    lines = [
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    ]
    base = (
        f"{{name}}, {style.font}, {style.font_size}, {{primary}}, {{primary}}, "
        f"{style.ass_outline_colour()}, "
        f"{style.ass_back_colour() if style.background_box else '&H00000000&'}, "
        f"{bold}, 0, 0, 0, 100, 100, 0, 0, {border}, {style.outline_width}, {style.shadow}, "
        f"{style.align()}, 20, 20, {style.margin_v}, 1"
    )
    lines.append("Style: " + base.format(name=_STYLE_NAME_DEFAULT, primary=style.ass_primary_colour()))
    lines.append("Style: " + base.format(name=_STYLE_NAME_HIGHLIGHT, primary=style.ass_highlight_colour()))
    return "\n".join(lines)


def _entrance_tag(style: SubtitleStyle) -> str:
    """Satır/kelime girişinde uygulanacak animasyon override etiketi (varsa)."""
    ms = max(style.animation_ms, 0)
    if style.animation == Animation.FADE or ms == 0 and style.animation != Animation.NONE:
        return f"\\fad({ms},0)"
    if style.animation == Animation.POP:
        scale = round(style.highlight_scale * 100)
        return f"\\fscx70\\fscy70\\t(0,{ms},\\fscx100\\fscy100)\\fad({max(ms // 2, 1)},0)"
    if style.animation == Animation.SLIDE_UP:
        y = PLAY_RES_Y - style.margin_v
        return f"\\move({PLAY_RES_X // 2},{y + 40},{PLAY_RES_X // 2},{y},0,{ms})\\fad({ms},0)"
    return ""


def _render_segment_text(
    seg: Segment,
    current_word_idx: int | None,
    style: SubtitleStyle,
    always_highlight: set[str] | None,
) -> str:
    """Bir satırın tüm kelimelerini, `current_word_idx`'teki kelime (varsa) ve
    `always_highlight`'ta geçen kelimeler vurgulanmış olacak şekilde tek bir ASS
    metin dizgesine (override blokları dahil) oluşturur."""
    always_highlight = always_highlight or set()
    parts: list[str] = []
    for i, w in enumerate(seg.words):
        text = _escape(w.text.strip())
        if not text:
            continue
        is_current = current_word_idx is not None and i == current_word_idx
        is_pinned = w.text.strip().lower() in always_highlight
        if is_current or is_pinned:
            scale = round(style.highlight_scale * 100) if is_current else 100
            parts.append(f"{{\\c{style.ass_highlight_colour()}\\fscx{scale}\\fscy{scale}}}{text}{{\\r}}")
        else:
            parts.append(text)
    return " ".join(parts)


def _segment_events(
    seg_idx: int,
    seg: Segment,
    style: SubtitleStyle,
    always_highlight: set[str] | None,
) -> list[str]:
    events: list[str] = []
    entrance = _entrance_tag(style)

    if style.highlight_words and seg.words:
        # kelime bazlı: her kelime kendi süresince "o an konuşulan" olarak vurgulanır
        # (karaoke tarzı); her kelime değişimi kendi başına küçük bir "animasyon karesi"dir.
        for wi, w in enumerate(seg.words):
            if w.end <= w.start:
                continue
            text = _render_segment_text(seg, wi, style, always_highlight)
            if not text:
                continue
            tag = entrance if wi == 0 else (f"\\fad({min(style.animation_ms, 60)},0)" if style.animation != Animation.NONE else "")
            override = f"{{{tag}}}" if tag else ""
            events.append(
                f"Dialogue: 0,{_ass_timestamp(w.start)},{_ass_timestamp(w.end)},{_STYLE_NAME_DEFAULT},,0,0,0,,{override}{text}"
            )
    else:
        text = _escape(seg.text.strip())
        if always_highlight:
            text = _render_segment_text(seg, None, style, always_highlight) or text
        override = f"{{{entrance}}}" if entrance else ""
        events.append(
            f"Dialogue: 0,{_ass_timestamp(seg.start)},{_ass_timestamp(seg.end)},{_STYLE_NAME_DEFAULT},,0,0,0,,{override}{text}"
        )
    return events


def to_ass(
    segments: list[Segment] | Transcript,
    style: SubtitleStyle,
    always_highlight: set[str] | None = None,
) -> str:
    """Segment listesini (veya bir `Transcript`'i) stilli/animasyonlu bir .ass dizgesine çevirir.

    `always_highlight`: her zaman vurgulanacak kelimeler (küçük harfe çevrilmiş, kesin eşleşme) —
    ör. AI Basic Editor'ün "önemli kelimeleri vurgula" önerisinden gelen kelime listesi.
    `style.highlight_words=True` ise AYRICA o an konuşulan kelime de (geçici olarak) vurgulanır.
    """
    segs = segments.segments if isinstance(segments, Transcript) else segments
    always_highlight = {w.lower() for w in always_highlight} if always_highlight else None

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "Collisions: Normal\n"
        f"PlayResX: {PLAY_RES_X}\n"
        f"PlayResY: {PLAY_RES_Y}\n"
        "WrapStyle: 2\n"
        "ScaledBorderAndShadow: yes\n"
    )
    styles = build_styles_section(style)
    events_header = (
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    )
    all_events: list[str] = []
    for i, seg in enumerate(segs):
        all_events.extend(_segment_events(i, seg, style, always_highlight))

    return "\n\n".join([header, styles, events_header + "\n" + "\n".join(all_events)]) + "\n"


__all__ = ["to_ass", "build_styles_section", "PLAY_RES_X", "PLAY_RES_Y"]
