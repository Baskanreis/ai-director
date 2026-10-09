"""SRT/VTT üretimi ve kelime zaman damgalarından okunabilir altyazı satırlarına
segmentasyon (v0.8 Subtitle Engine).

Bu modül saf Pythondur: Whisper veya ffmpeg gerektirmez, bu yüzden gerçek bir
transkripsiyon çalıştırmadan da tam test edilebilir.
"""
from __future__ import annotations

from .models import Segment, Word

# Whisper'ın segment'leri genelde ekranda okumak icin fazla uzun olur; bu
# varsayılanlar tipik altyazı pratiğine (satır başına ~42 karakter, en fazla
# birkaç saniye) yakındır.
DEFAULT_MAX_CHARS = 42
DEFAULT_MAX_DURATION = 6.0
DEFAULT_MAX_WORDS = 16

_SENTENCE_END = (".", "?", "!", "…")


def segment_words_into_lines(
    words: list[Word],
    max_chars: int = DEFAULT_MAX_CHARS,
    max_duration: float = DEFAULT_MAX_DURATION,
    max_words: int = DEFAULT_MAX_WORDS,
) -> list[Segment]:
    """Düz kelime listesini, ekranda gösterime uygun `Segment` listesine böler.

    Kurallar (ilk uyan tetikler): toplam karakter sayısı `max_chars`'ı aşarsa,
    toplam süre `max_duration`'ı aşarsa, kelime sayısı `max_words`'ü aşarsa veya
    kelime cümle sonu noktalamasıyla (.?!…) bitiyorsa mevcut satır kapatılır.
    Boş girdi için boş liste döner.
    """
    segments: list[Segment] = []
    current: list[Word] = []

    def flush() -> None:
        if not current:
            return
        text = " ".join(w.text.strip() for w in current if w.text.strip())
        if text:
            segments.append(
                Segment(text=text, start=current[0].start, end=current[-1].end, words=list(current))
            )
        current.clear()

    for w in words:
        if current:
            prospective_text = " ".join(x.text.strip() for x in [*current, w])
            prospective_dur = w.end - current[0].start
            would_overflow = (
                len(prospective_text) > max_chars
                or prospective_dur > max_duration
                or len(current) + 1 > max_words
            )
            if would_overflow:
                flush()
        current.append(w)
        if w.text.strip().endswith(_SENTENCE_END):
            flush()
    flush()
    return segments


def _srt_timestamp(seconds: float) -> str:
    total_ms = max(round(seconds * 1000), 0)
    h, rem = divmod(total_ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _vtt_timestamp(seconds: float) -> str:
    total_ms = max(round(seconds * 1000), 0)
    h, rem = divmod(total_ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def to_srt(segments: list[Segment]) -> str:
    """Segment listesini SubRip (.srt) metnine dönüştürür."""
    lines: list[str] = []
    for i, seg in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(f"{_srt_timestamp(seg.start)} --> {_srt_timestamp(seg.end)}")
        lines.append(seg.text.strip())
        lines.append("")
    return "\n".join(lines).strip("\n") + "\n" if lines else ""


def to_vtt(segments: list[Segment]) -> str:
    """Segment listesini WebVTT (.vtt) metnine dönüştürür."""
    lines: list[str] = ["WEBVTT", ""]
    for seg in segments:
        lines.append(f"{_vtt_timestamp(seg.start)} --> {_vtt_timestamp(seg.end)}")
        lines.append(seg.text.strip())
        lines.append("")
    return "\n".join(lines).strip("\n") + "\n"
