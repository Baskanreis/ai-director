from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

class YouTubePublishError(RuntimeError):
    pass

@dataclass(frozen=True)
class PublishQC:
    ok: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class PublishPlan:
    video_path: str
    title: str
    description: str = ""
    tags: tuple[str, ...] = ()
    privacy_status: str = "private"
    publish_at: str | None = None
    category_id: str = "22"
    language: str = ""
    made_for_kids: bool = False
    playlist_id: str = ""
    thumbnail_path: str = ""
    is_shorts: bool = False
    notify_subscribers: bool = True
    def to_dict(self): return asdict(self)

def validate_publish_plan(plan: PublishPlan, now: datetime | None = None) -> PublishQC:
    errors=[]; warnings=[]
    p=Path(plan.video_path)
    if not plan.video_path or not p.exists(): errors.append("Video dosyası bulunamadı.")
    if not plan.title.strip(): errors.append("Başlık boş olamaz.")
    if len(plan.title.strip()) > 100: errors.append("YouTube başlığı 100 karakteri aşamaz.")
    if plan.privacy_status not in {"private","unlisted","public"}: errors.append("Geçersiz gizlilik durumu.")
    if plan.publish_at:
        if plan.privacy_status != "private": errors.append("Planlı yayın için gizlilik durumu private olmalıdır.")
        try:
            dt=datetime.fromisoformat(plan.publish_at.replace("Z","+00:00"))
            ref=now or datetime.now(timezone.utc)
            if dt.tzinfo is None: errors.append("publish_at timezone içermelidir.")
            elif dt <= ref: errors.append("Planlı yayın zamanı gelecekte olmalıdır.")
        except ValueError: errors.append("publish_at ISO-8601 formatında olmalıdır.")
    if plan.thumbnail_path and not Path(plan.thumbnail_path).exists(): errors.append("Thumbnail dosyası bulunamadı.")
    if len(plan.tags) > 500: errors.append("Tag sayısı sınırı aşıldı.")
    if plan.is_shorts and p.exists() and p.stat().st_size == 0: errors.append("Shorts videosu boş.")
    if not plan.description.strip(): warnings.append("Açıklama boş; SEO puanı düşebilir.")
    if len(plan.tags) < 5: warnings.append("En az 5 alakalı tag önerilir; alakasız tag doldurmayın.")
    return PublishQC(not errors, tuple(errors), tuple(warnings))

class YouTubePublishClient:
    """First-party YouTube Data API uploader.

    Uses the same OAuth token store as Analytics. No scraping or downloader is used.
    A transport/uploader callback can be injected for deterministic tests.
    """
    def __init__(self, token_path: str, oauth_client_json: str = "", service=None, uploader: Callable[..., Any] | None = None):
        self.token_path=token_path; self.oauth_client_json=oauth_client_json; self.service=service; self.uploader=uploader
    def authenticate(self) -> bool:
        if self.service is not None: return True
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except Exception as exc:
            raise YouTubePublishError("YouTube upload için Google OAuth paketleri Setup'a dahil edilmemiş.") from exc
        scopes=["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]
        creds=None
        try: creds=Credentials.from_authorized_user_file(self.token_path, scopes)
        except Exception: pass
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            else:
                if not self.oauth_client_json: raise YouTubePublishError("OAuth istemci yapılandırması eksik.")
                flow=InstalledAppFlow.from_client_config(json.loads(self.oauth_client_json), scopes)
                creds=flow.run_local_server(port=0, open_browser=True)
            Path(self.token_path).parent.mkdir(parents=True,exist_ok=True)
            Path(self.token_path).write_text(creds.to_json(),encoding="utf-8")
        self.service=build("youtube","v3",credentials=creds,cache_discovery=False)
        return True
    def upload(self, plan: PublishPlan, progress: Callable[[float],None] | None = None) -> dict[str,Any]:
        qc=validate_publish_plan(plan)
        if not qc.ok: raise YouTubePublishError("; ".join(qc.errors))
        if self.uploader is not None: return dict(self.uploader(plan, progress))
        self.authenticate()
        try:
            from googleapiclient.http import MediaFileUpload
            body={"snippet":{"title":plan.title.strip(),"description":plan.description,"tags":list(plan.tags),"categoryId":plan.category_id},
                  "status":{"privacyStatus":plan.privacy_status,"selfDeclaredMadeForKids":plan.made_for_kids,"notifySubscribers":plan.notify_subscribers}}
            if plan.language: body["snippet"]["defaultLanguage"]=plan.language
            if plan.publish_at: body["status"]["publishAt"]=plan.publish_at
            media=MediaFileUpload(plan.video_path,resumable=True)
            req=self.service.videos().insert(part="snippet,status",body=body,media_body=media)
            response=None
            while response is None:
                status,response=req.next_chunk()
                if status and progress: progress(float(status.progress()))
            video_id=response.get("id","")
            if plan.thumbnail_path and video_id:
                self.service.thumbnails().set(videoId=video_id,media_body=MediaFileUpload(plan.thumbnail_path)).execute()
            return {"video_id":video_id,"url":f"https://www.youtube.com/watch?v={video_id}" if video_id else "","warnings":list(qc.warnings)}
        except Exception as exc:
            raise YouTubePublishError(str(exc)) from exc
