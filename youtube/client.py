from __future__ import annotations
import json
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from .config import load_runtime_config

class YouTubeAPIError(RuntimeError):
    pass

@dataclass(frozen=True)
class PublicVideo:
    video_id: str = ""
    title: str = ""
    description: str = ""
    published_at: str = ""
    duration_iso: str = ""
    duration_seconds: float = 0.0
    views: int = 0
    likes: int = 0
    comments: int = 0
    channel_id: str = ""
    tags: tuple[str, ...] = ()
    category_id: str = ""
    definition: str = ""
    caption_available: bool = False
    live_broadcast: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class PublicChannel:
    channel_id: str = ""
    title: str = ""
    description: str = ""
    custom_url: str = ""
    published_at: str = ""
    uploads_playlist_id: str = ""
    subscriber_count: int = 0
    view_count: int = 0
    video_count: int = 0
    hidden_subscriber_count: bool = False
    country: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    def to_dict(self): return asdict(self)

def _duration_seconds(value: str) -> float:
    import re
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not m: return 0.0
    h, mi, s = (int(x or 0) for x in m.groups())
    return float(h * 3600 + mi * 60 + s)

class YouTubeDataClient:
    """Small stdlib-only YouTube Data API v3 client.

    A transport callback can be injected for tests, so no network is required by
    the core test suite. API keys should be restricted to YouTube Data API and the
    application's allowed origins/IPs where supported.
    """
    BASE = "https://www.googleapis.com/youtube/v3"
    def __init__(self, api_key: str | None = None, transport: Callable[[str], dict] | None = None):
        self.api_key = (api_key if api_key is not None else load_runtime_config()[0]).strip()
        self.transport = transport or self._http
    def _http(self, url: str) -> dict:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AI-Director/2.50"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:
            raise YouTubeAPIError(str(exc)) from exc
    def _get(self, resource: str, **params) -> dict:
        if not self.api_key: raise YouTubeAPIError("YouTube Data API anahtarı yapılandırılmamış.")
        params["key"] = self.api_key
        url = self.BASE + "/" + resource + "?" + urllib.parse.urlencode(params)
        data = self.transport(url)
        if "error" in data: raise YouTubeAPIError(json.dumps(data["error"], ensure_ascii=False))
        return data
    def get_channel(self, channel_id: str) -> PublicChannel:
        data = self._get("channels", part="snippet,statistics,contentDetails", id=channel_id, maxResults=1)
        items = data.get("items", [])
        if not items: raise YouTubeAPIError("Kanal bulunamadı: " + channel_id)
        x = items[0]; sn = x.get("snippet", {}); st = x.get("statistics", {}); cd = x.get("contentDetails", {})
        return PublicChannel(channel_id=x.get("id", channel_id), title=sn.get("title", ""),
            description=sn.get("description", ""), custom_url=sn.get("customUrl", ""),
            published_at=sn.get("publishedAt", ""), uploads_playlist_id=cd.get("relatedPlaylists", {}).get("uploads", ""),
            subscriber_count=int(st.get("subscriberCount", 0) or 0), view_count=int(st.get("viewCount", 0) or 0),
            video_count=int(st.get("videoCount", 0) or 0), hidden_subscriber_count=bool(st.get("hiddenSubscriberCount", False)),
            country=sn.get("country", ""))
    def list_video_ids(self, uploads_playlist_id: str, limit: int = 50) -> list[str]:
        ids, token = [], ""
        while len(ids) < limit:
            params = {"part":"contentDetails", "playlistId":uploads_playlist_id, "maxResults":min(50, limit-len(ids))}
            if token: params["pageToken"] = token
            data = self._get("playlistItems", **params)
            ids.extend([x.get("contentDetails", {}).get("videoId", "") for x in data.get("items", [])])
            token = data.get("nextPageToken", "")
            if not token: break
        return [x for x in ids if x]
    def get_videos(self, video_ids: list[str]) -> list[PublicVideo]:
        out=[]
        for i in range(0, len(video_ids), 50):
            data=self._get("videos", part="snippet,contentDetails,statistics", id=",".join(video_ids[i:i+50]))
            for x in data.get("items", []):
                sn=x.get("snippet",{}); cd=x.get("contentDetails",{}); st=x.get("statistics",{})
                out.append(PublicVideo(video_id=x.get("id",""), title=sn.get("title",""), description=sn.get("description",""),
                    published_at=sn.get("publishedAt",""), duration_iso=cd.get("duration",""), duration_seconds=_duration_seconds(cd.get("duration","")),
                    views=int(st.get("viewCount",0) or 0), likes=int(st.get("likeCount",0) or 0), comments=int(st.get("commentCount",0) or 0),
                    channel_id=sn.get("channelId",""), tags=tuple(sn.get("tags",[]) or ()), category_id=sn.get("categoryId",""),
                    definition=cd.get("definition",""), caption_available=cd.get("caption","none") != "none",
                    live_broadcast=sn.get("liveBroadcastContent","none")))
        return out
    def snapshot_channel(self, channel_id: str, limit: int = 50) -> tuple[PublicChannel, list[PublicVideo]]:
        channel=self.get_channel(channel_id)
        ids=self.list_video_ids(channel.uploads_playlist_id, limit)
        return channel, self.get_videos(ids)
