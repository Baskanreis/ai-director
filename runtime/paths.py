"""Application and user-data paths with packaged/installed Windows support."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "app"
DOCS_DIR = ROOT / "docs"


def install_dir() -> Path:
    """Return the read-only application installation directory.

    In a PyInstaller onedir build this is the directory containing the EXE. In
    source mode it falls back to the repository root. Models, FFmpeg and other
    runtime assets shipped by Setup live below this directory.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return ROOT.resolve()


def bundled_dir(name: str) -> Path:
    return install_dir() / name


def user_data_dir() -> Path:
    """Writable per-user data; never write mutable state into Program Files."""
    if os.name == "nt":
        base = os.getenv("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
        path = Path(base) / "AI Director"
    else:
        path = Path.home() / ".ai_director"
    path.mkdir(parents=True, exist_ok=True)
    return path


def model_dir() -> Path:
    """Read-only bundled model root. Setup creates it before first launch."""
    return bundled_dir("models")


def whisper_model_dir() -> Path:
    return model_dir() / "whisper"


def log_dir() -> Path:
    path = user_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_file() -> Path:
    return user_data_dir() / "config.json"


def provider_config_file() -> Path:
    return user_data_dir() / "providers.json"


def autosave_dir() -> Path:
    path = user_data_dir() / "autosave"
    path.mkdir(parents=True, exist_ok=True)
    return path


def session_registry_file() -> Path:
    return autosave_dir() / "sessions.json"


def learning_db_file() -> Path:
    """Persistent local feedback/calibration database."""
    return user_data_dir() / "learning.db"


def youtube_dna_file() -> Path:
    path = user_data_dir() / "youtube"
    path.mkdir(parents=True, exist_ok=True)
    return path / "channel_dna.json"


def youtube_token_file() -> Path:
    path = user_data_dir() / "youtube"
    path.mkdir(parents=True, exist_ok=True)
    return path / "oauth_token.json"
