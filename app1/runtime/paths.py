"""Proje ve kullanici dizin yollari."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "app"
DOCS_DIR = ROOT / "docs"


def user_data_dir() -> Path:
    """Kullaniciya ait veri klasoru (~/.ai_director). Yoksa olusturur."""
    path = Path.home() / ".ai_director"
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_dir() -> Path:
    path = user_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_file() -> Path:
    return user_data_dir() / "config.json"


def autosave_dir() -> Path:
    """Oturum bazlı otomatik kayıt (crash recovery) dosyalarının tutulduğu klasör."""
    path = user_data_dir() / "autosave"
    path.mkdir(parents=True, exist_ok=True)
    return path


def session_registry_file() -> Path:
    """Açık/kapatılmamış oturumları izleyen kayıt dosyası (crash recovery için)."""
    return autosave_dir() / "sessions.json"
