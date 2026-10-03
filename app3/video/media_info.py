"""Medya dosyasi bilgisi okuma (ffprobe, yoksa OpenCV) ve thumbnail uretimi."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

VIDEO_EXTENSIONS = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".flv", ".wmv", ".mts", ".ts")
AUDIO_EXTENSIONS = (".wav", ".mp3", ".m4a")
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS + AUDIO_EXTENSIONS

THUMBNAIL_SIZE = (320, 180)
_THUMB_CACHE_DIR = Path(tempfile.gettempdir()) / "ai_director_thumbs"


class MediaProbeError(RuntimeError):
    """Medya dosyasi okunamadi."""


@dataclass
class MediaInfo:
    path: str
    duration: float
    width: int
    height: int
    fps: float
    has_audio: bool
    codec: str = ""
    media_type: str = "video"  # "video" | "audio"
    audio_codec: str = ""
    audio_channels: int = 0
    sample_rate: int = 0
    thumbnail: str = ""


def _parse_rate(text: str) -> float:
    try:
        if "/" in text:
            num, den = text.split("/")
            return float(num) / float(den) if float(den) else 0.0
        return float(text)
    except (ValueError, ZeroDivisionError):
        return 0.0


def _probe_ffprobe(path: Path, exe: str) -> MediaInfo:
    proc = subprocess.run(
        [exe, "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise MediaProbeError(proc.stderr.strip() or "ffprobe hata verdi")
    data = json.loads(proc.stdout or "{}")
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video is None and audio is None:
        raise MediaProbeError("Dosyada video veya ses akışı bulunamadı")

    fmt = data.get("format", {})

    def _duration_of(src: dict) -> float:
        try:
            return float(src.get("duration") or 0)
        except ValueError:
            return 0.0

    audio_codec = audio.get("codec_name", "") if audio else ""
    audio_channels = int(audio.get("channels", 0)) if audio else 0
    try:
        sample_rate = int(audio.get("sample_rate", 0)) if audio else 0
    except ValueError:
        sample_rate = 0

    if video is not None:
        duration = 0.0
        for src in (fmt, video):
            duration = _duration_of(src)
            if duration > 0:
                break
        fps = _parse_rate(video.get("avg_frame_rate", "0")) or _parse_rate(video.get("r_frame_rate", "0"))
        return MediaInfo(
            path=str(path),
            duration=duration,
            width=int(video.get("width", 0)),
            height=int(video.get("height", 0)),
            fps=round(fps, 3),
            has_audio=audio is not None,
            codec=video.get("codec_name", ""),
            media_type="video",
            audio_codec=audio_codec,
            audio_channels=audio_channels,
            sample_rate=sample_rate,
        )

    # Yalnizca ses akisi var: audio-only medya (WAV/MP3/M4A vb.)
    duration = 0.0
    for src in (fmt, audio):
        duration = _duration_of(src)
        if duration > 0:
            break
    return MediaInfo(
        path=str(path),
        duration=duration,
        width=0,
        height=0,
        fps=0.0,
        has_audio=True,
        codec="",
        media_type="audio",
        audio_codec=audio_codec,
        audio_channels=audio_channels,
        sample_rate=sample_rate,
    )


def _probe_opencv(path: Path) -> MediaInfo:
    try:
        import cv2
    except ImportError as exc:
        raise MediaProbeError("ffprobe ve OpenCV bulunamadı; medya bilgisi okunamıyor") from exc
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise MediaProbeError("Video açılamadı")
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    finally:
        cap.release()
    if not (fps > 0 and frames > 0):
        raise MediaProbeError("Video süresi belirlenemedi")
    # OpenCV ses bilgisini vermez: bilinmiyor -> False (guvenli taraf)
    return MediaInfo(str(path), frames / fps, width, height, round(fps, 3), False, "", "video")


def probe_media(path: str | Path, thumbnail: bool = True) -> MediaInfo:
    """Medya bilgisini okur (video veya ses). Sirasiyla ffprobe, sonra OpenCV denenir.

    ffprobe olmadan (OpenCV yedegiyle) ses-yalnizca dosyalar okunamaz.
    """
    p = Path(path)
    if not p.is_file():
        raise MediaProbeError(f"Dosya bulunamadı: {p}")
    exe = shutil.which("ffprobe")
    if exe:
        try:
            info = _probe_ffprobe(p, exe)
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            raise MediaProbeError(f"ffprobe çalıştırılamadı: {exc}") from exc
    elif p.suffix.lower() in AUDIO_EXTENSIONS:
        raise MediaProbeError("Ses dosyaları için ffprobe gerekli (OpenCV yalnızca video okuyabilir)")
    else:
        info = _probe_opencv(p)

    if info.media_type == "video" and (info.duration <= 0 or info.width <= 0 or info.height <= 0):
        raise MediaProbeError("Video geçersiz görünüyor (süre/boyut okunamadı)")
    if info.media_type == "audio" and info.duration <= 0:
        raise MediaProbeError("Ses dosyası geçersiz görünüyor (süre okunamadı)")

    if thumbnail:
        info.thumbnail = generate_thumbnail(p, info.duration, info.media_type) or ""
    return info


def probe_video(path: str | Path) -> MediaInfo:
    """Geriye donuk uyumluluk icin: probe_media'nin eski adi."""
    return probe_media(path)


def _thumb_cache_path(path: Path) -> Path:
    _THUMB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    stat = path.stat()
    key = f"{path.resolve()}|{stat.st_size}|{stat.st_mtime}"
    digest = hashlib.sha1(key.encode("utf-8", errors="ignore")).hexdigest()
    return _THUMB_CACHE_DIR / f"{digest}.jpg"


def generate_thumbnail(path: str | Path, duration: float = 0.0, media_type: str = "video") -> str | None:
    """Video icin kucuk bir onizleme karesi uretir; ffmpeg gerektirir.

    Sonuc diskte onbelleklenir; ayni dosya icin tekrar uretilmez.
    Ses-yalnizca dosyalar (WAV/MP3/M4A) icin None doner (thumbnail yok).
    Basarisiz olursa None doner; cagiran taraf gorseli atlayip devam etmeli.
    """
    if media_type != "video":
        return None
    exe = shutil.which("ffmpeg")
    if not exe:
        return None
    p = Path(path)
    try:
        cache = _thumb_cache_path(p)
    except OSError:
        return None
    if cache.is_file() and cache.stat().st_size > 0:
        return str(cache)

    seek = min(max(duration * 0.1, 0.0), 3.0) if duration > 0 else 0.0
    w, h = THUMBNAIL_SIZE
    scale = f"scale={w}:{h}:force_original_aspect_ratio=decrease"
    cmd = [
        exe, "-y", "-v", "error",
        "-ss", f"{seek:.3f}", "-i", str(p),
        "-frames:v", "1", "-vf", scale,
        str(cache),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0 or not cache.is_file() or cache.stat().st_size == 0:
        return None
    return str(cache)
