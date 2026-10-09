"""Altyazıyı dosyaya yazma ve videoya ekleme (v0.8 Subtitle Engine).

İki farklı "gömme" biçimi desteklenir:
- `mux_soft_subtitles`: altyazıyı ayrı bir akış (mov_text) olarak videoya
  paketler — oynatıcıda açıp kapatılabilir, video yeniden encode edilmez (hızlı).
- `burn_in_subtitles`: altyazıyı görüntünün üzerine "yakar" (her zaman görünür,
  kapatılamaz) — video yeniden encode edilir (daha yavaş).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from .ass_format import to_ass
from .formats import to_srt, to_vtt
from .models import SubtitleError, Segment, Transcript
from .style import SubtitleStyle

# Whisper/UI dil kodlarından (ISO 639-1) ffmpeg/mov_text'in beklediği ISO 639-2'ye.
LANG_ISO_639_2: dict[str, str] = {"tr": "tur", "en": "eng", "de": "deu", "fr": "fra"}


def export_srt(transcript: Transcript, path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_srt(transcript.segments), encoding="utf-8")
    return out


def export_vtt(transcript: Transcript, path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_vtt(transcript.segments), encoding="utf-8")
    return out


def export_ass(
    transcript: Transcript, path: str | Path, style: SubtitleStyle, always_highlight: set[str] | None = None
) -> Path:
    """Stilli/animasyonlu/kelime-vurgulu .ass altyazı dosyası üretir (v0.7 Subtitle Engine).

    `always_highlight`, her zaman vurgulanacak kelimeleri verir (ör. AI Basic
    Editor'ün önerdiği "önemli kelimeler"); `style.highlight_words=True` ise
    ayrıca o an konuşulan kelime de dinamik olarak vurgulanır.
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_ass(transcript.segments, style, always_highlight=always_highlight), encoding="utf-8")
    return out


def _run_ffmpeg(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SubtitleError(f"ffmpeg başarısız oldu:\n{proc.stderr[-2000:]}")


def mux_soft_subtitles(
    video_path: str | Path, srt_path: str | Path, output_path: str | Path, language: str = "tr"
) -> Path:
    """Var olan bir SRT dosyasını videoya, video/sesi yeniden encode etmeden
    ayrı bir altyazı akışı (mov_text) olarak ekler. Sonuç bir MP4'tür."""
    video_path, srt_path, output_path = Path(video_path), Path(srt_path), Path(output_path)
    if not video_path.is_file():
        raise SubtitleError(f"Video bulunamadı: {video_path}")
    if not srt_path.is_file():
        raise SubtitleError(f"Altyazı dosyası bulunamadı: {srt_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    iso_lang = LANG_ISO_639_2.get(language, "und")
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(video_path), "-i", str(srt_path),
        "-map", "0:v", "-map", "0:a?", "-map", "1:s",
        "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text",
        "-metadata:s:s:0", f"language={iso_lang}",
        str(output_path),
    ]
    _run_ffmpeg(cmd)
    return output_path


def _escape_filter_path(path: Path) -> str:
    """`subtitles=` filtresine verilecek dosya yolunu ffmpeg filtergraph
    sözdizimine göre kaçışlar (özellikle Windows sürücü harfindeki `:` ve `\\`)."""
    s = str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    return s


def burn_in_subtitles(
    video_path: str | Path,
    srt_path: str | Path,
    output_path: str | Path,
    font_size: int = 24,
    crf: int = 20,
) -> Path:
    """Altyazıyı görüntünün üzerine kalıcı olarak "yakar" (video yeniden encode edilir)."""
    video_path, srt_path, output_path = Path(video_path), Path(srt_path), Path(output_path)
    if not video_path.is_file():
        raise SubtitleError(f"Video bulunamadı: {video_path}")
    if not srt_path.is_file():
        raise SubtitleError(f"Altyazı dosyası bulunamadı: {srt_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sub_filter = f"subtitles='{_escape_filter_path(srt_path)}':force_style='FontSize={font_size}'"
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(video_path),
        "-vf", sub_filter,
        "-c:v", "libx264", "-crf", str(crf), "-preset", "medium",
        "-c:a", "copy",
        str(output_path),
    ]
    _run_ffmpeg(cmd)
    return output_path


def burn_in_ass(
    video_path: str | Path,
    ass_path: str | Path,
    output_path: str | Path,
    crf: int = 20,
) -> Path:
    """Stilli bir .ass altyazı dosyasını görüntünün üzerine kalıcı olarak yakar.

    `burn_in_subtitles`'tan farkı: `force_style` uygulanmaz — renk/font/konum/animasyon
    zaten .ass dosyasının `[V4+ Styles]` bölümünden (libass tarafından) okunur.
    """
    video_path, ass_path, output_path = Path(video_path), Path(ass_path), Path(output_path)
    if not video_path.is_file():
        raise SubtitleError(f"Video bulunamadı: {video_path}")
    if not ass_path.is_file():
        raise SubtitleError(f"Altyazı dosyası bulunamadı: {ass_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sub_filter = f"ass='{_escape_filter_path(ass_path)}'"
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(video_path),
        "-vf", sub_filter,
        "-c:v", "libx264", "-crf", str(crf), "-preset", "medium",
        "-c:a", "copy",
        str(output_path),
    ]
    _run_ffmpeg(cmd)
    return output_path
