"""Platform cikti onayarlari (v1.1 Real FFmpeg Render).

Her preset, `ExportSettings` icin makul varsayilan genislik/yukseklik/fps/
kodek/bit hizi degerleri sunar. Kullanici bunlari diledigi gibi degistirebilir
("Custom" / Ozel preset'i degisiklik yapilmamis varsayilanlari temsil eder).
"""
from __future__ import annotations

from dataclasses import dataclass

from .command_builder import ExportSettings


@dataclass(frozen=True)
class Preset:
    name: str
    label: str          # kullanicIya gosterilecek ad
    width: int
    height: int
    fps: float
    codec: str
    crf: int | None
    video_bitrate: str
    audio_bitrate: str
    description: str
    fit_mode: str = "contain"


PRESETS: list[Preset] = [
    Preset(
        "youtube", "YouTube (1080p, 16:9)", 1920, 1080, 30.0, "h264", 18, "12M", "192k",
        "YouTube'un onerdigi yuksek kaliteli 1080p yatay format.",
    ),
    Preset(
        "youtube_4k", "YouTube (4K, 16:9)", 3840, 2160, 30.0, "h265", 18, "45M", "192k",
        "4K yatay; H.265 ile daha kucuk dosya boyutu.",
    ),
    Preset(
        "shorts", "YouTube Shorts (1080x1920)", 1080, 1920, 30.0, "h264", 20, "10M", "192k",
        "Dikey (9:16) kisa video formati, YouTube Shorts icin.",
    ),
    Preset(
        "tiktok", "TikTok (1080x1920)", 1080, 1920, 30.0, "h264", 20, "10M", "192k",
        "Dikey (9:16), TikTok'un onerdigi bit hizi araliginda.",
    ),
    Preset(
        "instagram_reels", "Instagram Reels (1080x1920)", 1080, 1920, 30.0, "h264", 20, "10M", "192k",
        "Dikey (9:16) Reels/Story formati.",
    ),
    Preset(
        "instagram_feed", "Instagram Feed (1080x1080)", 1080, 1080, 30.0, "h264", 20, "8M", "192k",
        "Kare (1:1) besleme (feed) gonderisi.",
    ),
    Preset(
        "custom", "Özel (Custom)", 1920, 1080, 30.0, "h264", 20, "8M", "192k",
        "Tum ayarlari serbestce degistirin.",
    ),
]

# Extended multi-platform delivery profiles.
_EXTENDED = [
    Preset("youtube_16x9", "YouTube — 16:9", 1920, 1080, 30.0, "h264", 18, "12M", "192k", "Standard YouTube master.", "contain"),
    Preset("youtube_4k", "YouTube — 4K", 3840, 2160, 30.0, "h265", 18, "45M", "192k", "4K YouTube delivery.", "contain"),
    Preset("youtube_shorts", "YouTube Shorts — 9:16", 1080, 1920, 30.0, "h264", 20, "10M", "192k", "Vertical Shorts delivery.", "cover"),
    Preset("tiktok", "TikTok — 9:16", 1080, 1920, 30.0, "h264", 20, "10M", "192k", "Vertical TikTok delivery.", "cover"),
    Preset("instagram_reels", "Instagram Reels — 9:16", 1080, 1920, 30.0, "h264", 20, "10M", "192k", "Reels/Stories delivery.", "cover"),
    Preset("instagram_feed_portrait", "Instagram Feed — 4:5", 1080, 1350, 30.0, "h264", 20, "8M", "192k", "Portrait feed delivery.", "cover"),
    Preset("instagram_feed_square", "Instagram Feed — 1:1", 1080, 1080, 30.0, "h264", 20, "8M", "192k", "Square feed delivery.", "cover"),
    Preset("facebook_feed", "Facebook Feed — 4:5", 1080, 1350, 30.0, "h264", 20, "8M", "192k", "Portrait Facebook delivery.", "cover"),
    Preset("facebook_landscape", "Facebook — 16:9", 1920, 1080, 30.0, "h264", 18, "10M", "192k", "Landscape Facebook delivery.", "contain"),
    Preset("x_landscape", "X — 16:9", 1920, 1080, 30.0, "h264", 20, "8M", "192k", "Landscape X delivery.", "contain"),
    Preset("linkedin_landscape", "LinkedIn — 16:9", 1920, 1080, 30.0, "h264", 20, "8M", "192k", "Landscape LinkedIn delivery.", "contain"),
    Preset("linkedin_portrait", "LinkedIn — 4:5", 1080, 1350, 30.0, "h264", 20, "8M", "192k", "Portrait LinkedIn delivery.", "cover"),
    Preset("pinterest", "Pinterest — 2:3", 1000, 1500, 30.0, "h264", 20, "8M", "192k", "Pinterest video pin.", "cover"),
    Preset("snapchat", "Snapchat — 9:16", 1080, 1920, 30.0, "h264", 20, "10M", "192k", "Vertical Snapchat delivery.", "cover"),
    Preset("whatsapp_status", "WhatsApp Status — 9:16", 1080, 1920, 30.0, "h264", 20, "8M", "192k", "Vertical WhatsApp status.", "cover"),
    Preset("telegram", "Telegram — 16:9", 1920, 1080, 30.0, "h264", 20, "8M", "192k", "General Telegram delivery.", "contain"),
]
PRESETS.extend(_EXTENDED)

_BY_NAME = {p.name: p for p in PRESETS}


def get_preset(name: str) -> Preset:
    try:
        return _BY_NAME[name]
    except KeyError as exc:
        raise KeyError(f"Bilinmeyen preset: {name!r}") from exc


def preset_names() -> list[str]:
    return [p.name for p in PRESETS]


def export_settings_for(preset_name: str, output_path: str, **overrides) -> ExportSettings:
    """`preset_name` icin bir `ExportSettings` olusturur; `overrides` ile tek tek alanlar ezilebilir."""
    p = get_preset(preset_name)
    kwargs = dict(
        output_path=output_path,
        width=p.width,
        height=p.height,
        fps=p.fps,
        codec=p.codec,
        crf=p.crf,
        video_bitrate=p.video_bitrate,
        audio_bitrate=p.audio_bitrate,
        preset_name=p.label,
        fit_mode=p.fit_mode,
    )
    kwargs.update(overrides)
    return ExportSettings(**kwargs)
