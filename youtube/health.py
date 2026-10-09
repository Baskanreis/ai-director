from __future__ import annotations
from dataclasses import dataclass, asdict
import importlib
from .config import load_runtime_config
from app.runtime.paths import youtube_token_file

@dataclass(frozen=True)
class YouTubeHealth:
    data_api_configured: bool
    oauth_configured: bool
    google_packages_available: bool
    critical_modules_ok: bool
    oauth_token_present: bool
    messages: tuple[str, ...] = ()
    def to_dict(self): return asdict(self)


def check_youtube_health() -> YouTubeHealth:
    messages: list[str] = []
    try:
        importlib.import_module("google.oauth2.credentials")
        importlib.import_module("google_auth_oauthlib.flow")
        importlib.import_module("googleapiclient.discovery")
        google_ok = True
    except Exception as exc:
        google_ok = False
        messages.append(f"Google API paketleri eksik: {exc}")

    critical = (
        "app.youtube.client", "app.youtube.analytics", "app.youtube.publish",
        "app.youtube.creator", "app.youtube.studio", "app.youtube.production_queue",
        "app.youtube.production_manager", "app.youtube.thumbnail_render",
    )
    critical_ok = True
    for module in critical:
        try:
            importlib.import_module(module)
        except Exception as exc:
            critical_ok = False
            messages.append(f"Modül yüklenemedi: {module}: {exc}")

    api_key, oauth_json = load_runtime_config()
    data_ok = bool(api_key)
    oauth_ok = bool(oauth_json)
    token_path = youtube_token_file()
    token_ok = token_path.exists() and token_path.stat().st_size > 0

    if not data_ok:
        messages.append("YouTube Data API anahtarı yapılandırılmamış; herkese açık kanal analizi çalışmaz.")
    if not oauth_ok:
        messages.append("Google OAuth istemci yapılandırması yok; ilk Analytics/Upload bağlantısı kurulamaz.")
    if token_ok:
        messages.append("Google OAuth oturumu kayıtlı.")
    else:
        messages.append("Google OAuth oturumu henüz bağlanmamış.")
    if google_ok and oauth_ok:
        messages.append("Google OAuth bileşenleri hazır.")
    if data_ok:
        messages.append("YouTube Data API anahtarı hazır.")
    if critical_ok:
        messages.append("YouTube modülleri hazır.")
    return YouTubeHealth(data_ok, oauth_ok, google_ok, critical_ok, token_ok, tuple(messages))
