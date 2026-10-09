from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .client import YouTubeDataClient
from .dna import build_youtube_channel_dna, YouTubeChannelDNA
from .analytics import YouTubeAnalyticsClient
from app.runtime.paths import youtube_dna_file, youtube_token_file
from app.ai.channel_autopilot import AnalyticsPoint

class YouTubeIntelligenceManager:
    def __init__(self, api_key: str | None = None):
        self.data = YouTubeDataClient(api_key)
    def analyze_public_channel(self, channel_id: str, sample_size: int = 50) -> YouTubeChannelDNA:
        channel, videos = self.data.snapshot_channel(channel_id.strip(), max(1,min(200,sample_size)))
        dna = build_youtube_channel_dna(channel, videos)
        self.save(dna)
        return dna
    def parse_url(self, value: str):
        from .creator import parse_youtube_url
        return parse_youtube_url(value)

    def build_creator_package(self, title: str, description: str = "", tags=(), chapters=(), shorts=()):
        from .creator import build_creator_package
        return build_creator_package(title, description, tags, chapters, shorts)

    def connect_analytics(self) -> bool:
        client=YouTubeAnalyticsClient(str(youtube_token_file()))
        return client.authenticate()
    def analyze_owned_analytics(self, start_date: str, end_date: str) -> list[dict[str,Any]]:
        client=YouTubeAnalyticsClient(str(youtube_token_file()))
        client.authenticate()
        rows = client.query(start_date,end_date,
            "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,shares",
            dimensions="video",max_results=200)
        return rows

    def validate_publish_plan(self, plan):
        from .publish import validate_publish_plan
        return validate_publish_plan(plan)

    def upload(self, plan, progress=None):
        from .publish import YouTubePublishClient
        client=YouTubePublishClient(str(youtube_token_file()))
        return client.upload(plan, progress)

    @staticmethod
    def save(dna: YouTubeChannelDNA, path: str | Path | None = None):
        p=Path(path or youtube_dna_file()); p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(dna.to_dict(),ensure_ascii=False,indent=2),encoding="utf-8")
    @staticmethod
    def load(path: str | Path | None = None) -> dict[str,Any] | None:
        p=Path(path or youtube_dna_file())
        if not p.exists(): return None
        try: return json.loads(p.read_text(encoding="utf-8"))
        except Exception: return None
