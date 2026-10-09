from __future__ import annotations
import json, secrets, threading, webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except Exception:
    Credentials = None
    InstalledAppFlow = None
    build = None

from .config import load_runtime_config

class YouTubeAnalyticsError(RuntimeError): pass

@dataclass(frozen=True)
class OAuthConfig:
    client_json: str = ""
    scopes: tuple[str, ...] = ("https://www.googleapis.com/auth/yt-analytics.readonly", "https://www.googleapis.com/auth/youtube.readonly", "https://www.googleapis.com/auth/youtube.upload")

class YouTubeAnalyticsClient:
    """Authorized Analytics adapter. Tokens stay in the user's app-data directory."""
    def __init__(self, token_path: str, oauth: OAuthConfig | None = None, service=None):
        self.token_path=token_path; self.oauth=oauth or OAuthConfig(client_json=load_runtime_config()[1]); self.service=service
    def authenticate(self) -> bool:
        if Credentials is None or InstalledAppFlow is None or build is None:
            raise YouTubeAnalyticsError("Google OAuth paketleri Setup'a dahil edilmemiş.")
        creds=None
        try:
            creds=Credentials.from_authorized_user_file(self.token_path, list(self.oauth.scopes))
        except Exception: pass
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            else:
                if not self.oauth.client_json: raise YouTubeAnalyticsError("OAuth istemci yapılandırması eksik.")
                flow=InstalledAppFlow.from_client_config(json.loads(self.oauth.client_json), list(self.oauth.scopes))
                creds=flow.run_local_server(port=0, open_browser=True)
            with open(self.token_path,"w",encoding="utf-8") as f: f.write(creds.to_json())
            # OAuth credentials are sensitive local secrets. Tighten POSIX
            # permissions while remaining a no-op on Windows.
            try:
                import os
                if os.name != "nt":
                    os.chmod(self.token_path, 0o600)
            except OSError:
                pass
        self.service=build("youtubeAnalytics","v2",credentials=creds,cache_discovery=False)
        return True
    def query(self, start_date: str, end_date: str, metrics: str, dimensions: str = "video", filters: str | None = None, max_results: int = 200) -> list[dict[str,Any]]:
        if self.service is None: self.authenticate()
        kwargs=dict(ids="channel==MINE", startDate=start_date, endDate=end_date, metrics=metrics,
                    dimensions=dimensions, maxResults=max_results, sort="-views")
        if filters: kwargs["filters"]=filters
        try:
            result=self.service.reports().query(**kwargs).execute()
        except Exception as exc: raise YouTubeAnalyticsError(str(exc)) from exc
        headers=[h.get("name","") for h in result.get("columnHeaders",[])]
        return [dict(zip(headers,row)) for row in result.get("rows",[])]
