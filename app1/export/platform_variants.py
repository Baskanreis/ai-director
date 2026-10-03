"""Platform delivery matrix for AI Director short-form variants."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class PlatformVariant:
    platform: str
    width: int
    height: int
    fps: int
    max_duration: float
    codec: str = "h264"
    crf: int = 20

PLATFORM_VARIANTS=(
    PlatformVariant("youtube_shorts",1080,1920,30,180),
    PlatformVariant("tiktok",1080,1920,30,180),
    PlatformVariant("instagram_reels",1080,1920,30,180),
    PlatformVariant("youtube",1920,1080,30,3600),
)

def get_platform_variant(platform: str) -> PlatformVariant:
    for p in PLATFORM_VARIANTS:
        if p.platform==platform: return p
    raise ValueError(f"Unknown platform: {platform}")

__all__=["PlatformVariant","PLATFORM_VARIANTS","get_platform_variant"]
