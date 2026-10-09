"""YouTube intelligence adapters: public channel data, authorized analytics, and edit-DNA fusion."""
from .client import YouTubeDataClient, YouTubeAPIError
from .analytics import YouTubeAnalyticsClient, OAuthConfig, YouTubeAnalyticsError
from .dna import build_youtube_channel_dna, YouTubeChannelDNA

__all__ = [
    "YouTubeDataClient", "YouTubeAPIError", "YouTubeAnalyticsClient", "OAuthConfig",
    "YouTubeAnalyticsError", "build_youtube_channel_dna", "YouTubeChannelDNA",
]

from .creator import YouTubeURL, SEOResult, ShortsCandidate, CreatorPackage, parse_youtube_url, score_seo, build_creator_package
from .studio import ThumbnailConcept, ShortsFactoryItem, StudioQC, YouTubeStudioPackage, build_thumbnail_concepts, build_shorts_factory, run_studio_qc, build_studio_package
