"""Multi-platform delivery profiles for one master timeline.

The matrix keeps editorial content unchanged while describing platform-specific
framing, safe areas, codec, bitrate and file naming. It is intentionally data-
driven so new destinations can be added without changing the editor core.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class DeliveryProfile:
    key: str
    label: str
    width: int
    height: int
    fps: float
    codec: str = "h264"
    crf: int | None = 20
    video_bitrate: str = "8M"
    audio_bitrate: str = "192k"
    container: str = "mp4"
    fit_mode: str = "cover"  # cover | contain
    safe_left: float = 0.05
    safe_right: float = 0.05
    safe_top: float = 0.08
    safe_bottom: float = 0.12
    description: str = ""

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height

    def safe_rect(self) -> tuple[float, float, float, float]:
        return (self.safe_left, self.safe_top, 1.0 - self.safe_right, 1.0 - self.safe_bottom)


# Major publishing destinations. Values are conservative production defaults;
# platform apps may transcode uploaded files, so users can override them.
DELIVERY_PROFILES: tuple[DeliveryProfile, ...] = (
    DeliveryProfile("youtube_16x9", "YouTube — 16:9", 1920, 1080, 30, "h264", 18, "12M", description="Standard YouTube master."),
    DeliveryProfile("youtube_4k", "YouTube — 4K", 3840, 2160, 30, "h265", 18, "45M", description="4K YouTube delivery."),
    DeliveryProfile("youtube_shorts", "YouTube Shorts — 9:16", 1080, 1920, 30, "h264", 20, "10M", safe_top=0.14, safe_bottom=0.18, description="Vertical short-form delivery."),
    DeliveryProfile("tiktok", "TikTok — 9:16", 1080, 1920, 30, "h264", 20, "10M", safe_top=0.16, safe_bottom=0.20, description="Vertical TikTok delivery with UI-safe margins."),
    DeliveryProfile("instagram_reels", "Instagram Reels — 9:16", 1080, 1920, 30, "h264", 20, "10M", safe_top=0.14, safe_bottom=0.20, description="Reels/Stories framing."),
    DeliveryProfile("instagram_feed_portrait", "Instagram Feed — 4:5", 1080, 1350, 30, "h264", 20, "8M", safe_top=0.08, safe_bottom=0.12, description="Portrait feed post."),
    DeliveryProfile("instagram_feed_square", "Instagram Feed — 1:1", 1080, 1080, 30, "h264", 20, "8M", description="Square feed post."),
    DeliveryProfile("facebook_feed", "Facebook Feed — 4:5", 1080, 1350, 30, "h264", 20, "8M", description="Portrait feed delivery."),
    DeliveryProfile("facebook_landscape", "Facebook — 16:9", 1920, 1080, 30, "h264", 18, "10M", description="Landscape Facebook delivery."),
    DeliveryProfile("x_landscape", "X — 16:9", 1920, 1080, 30, "h264", 20, "8M", description="Landscape social post."),
    DeliveryProfile("linkedin_landscape", "LinkedIn — 16:9", 1920, 1080, 30, "h264", 20, "8M", description="Landscape professional post."),
    DeliveryProfile("linkedin_portrait", "LinkedIn — 4:5", 1080, 1350, 30, "h264", 20, "8M", description="Portrait professional post."),
    DeliveryProfile("pinterest", "Pinterest — 2:3", 1000, 1500, 30, "h264", 20, "8M", description="Vertical Pinterest video pin."),
    DeliveryProfile("snapchat", "Snapchat — 9:16", 1080, 1920, 30, "h264", 20, "10M", safe_top=0.15, safe_bottom=0.20, description="Vertical Snapchat delivery."),
    DeliveryProfile("whatsapp_status", "WhatsApp Status — 9:16", 1080, 1920, 30, "h264", 20, "8M", safe_top=0.12, safe_bottom=0.16, description="Vertical status video."),
    DeliveryProfile("telegram", "Telegram — 16:9", 1920, 1080, 30, "h264", 20, "8M", description="General Telegram video."),
)

_BY_KEY = {p.key: p for p in DELIVERY_PROFILES}


def get_delivery_profile(key: str) -> DeliveryProfile:
    try:
        return _BY_KEY[key]
    except KeyError as exc:
        raise KeyError(f"Unknown delivery profile: {key!r}") from exc


def delivery_profiles() -> list[DeliveryProfile]:
    return list(DELIVERY_PROFILES)


def build_delivery_matrix(keys: Iterable[str] | None = None) -> list[DeliveryProfile]:
    selected = list(keys) if keys is not None else list(_BY_KEY)
    return [get_delivery_profile(k) for k in selected]


def output_path_for(profile: DeliveryProfile, master_path: str, directory: str | None = None) -> str:
    master = Path(master_path)
    root = Path(directory) if directory else master.parent
    stem = master.stem
    return str(root / f"{stem}__{profile.key}.{profile.container}")


def safe_area_pixels(profile: DeliveryProfile) -> tuple[int, int, int, int]:
    l, t, r, b = profile.safe_rect()
    return (round(profile.width*l), round(profile.height*t), round(profile.width*r), round(profile.height*b))
