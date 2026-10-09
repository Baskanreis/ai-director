"""Runtime YouTube configuration.

CI may provide non-secret/build-time defaults through ``build_config.py``.
End users can override them from Connection Center; mutable data is stored in
per-user app data rather than Program Files.
"""
from __future__ import annotations
import json
from pathlib import Path
from app.runtime.paths import user_data_dir

try:
    from .build_config import YOUTUBE_API_KEY as _BUILD_API_KEY, OAUTH_CLIENT_JSON as _BUILD_OAUTH
except Exception:
    _BUILD_API_KEY, _BUILD_OAUTH = "", ""

YOUTUBE_API_KEY = _BUILD_API_KEY
OAUTH_CLIENT_JSON = _BUILD_OAUTH

def config_file() -> Path:
    path = user_data_dir() / "youtube"
    path.mkdir(parents=True, exist_ok=True)
    return path / "config.json"

def load_runtime_config() -> tuple[str, str]:
    key, oauth = YOUTUBE_API_KEY, OAUTH_CLIENT_JSON
    try:
        data = json.loads(config_file().read_text(encoding="utf-8"))
        key = str(data.get("api_key", key) or key).strip()
        oauth = str(data.get("oauth_client_json", oauth) or oauth).strip()
    except Exception:
        pass
    return key, oauth

def save_runtime_config(api_key: str, oauth_client_json: str) -> Path:
    api_key = str(api_key or "").strip()
    oauth_client_json = str(oauth_client_json or "").strip()
    if oauth_client_json:
        parsed = json.loads(oauth_client_json)
        if not isinstance(parsed, dict):
            raise ValueError("OAuth JSON bir nesne olmalı.")
    path = config_file()
    path.write_text(json.dumps({"api_key": api_key, "oauth_client_json": oauth_client_json}, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        import os
        if os.name != "nt":
            os.chmod(path, 0o600)
    except OSError:
        pass
    return path
