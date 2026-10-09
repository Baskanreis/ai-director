"""Basit JSON tabanli uygulama ayarlari."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field

from .paths import config_file

log = logging.getLogger(__name__)

MAX_RECENT = 8


@dataclass
class Config:
    language: str = "tr"
    theme: str = "dark"
    window_width: int = 1280
    window_height: int = 800
    last_page: str = "dashboard"
    last_dir: str = ""
    recent_projects: list[str] = field(default_factory=list)

    def add_recent(self, path: str) -> None:
        if path in self.recent_projects:
            self.recent_projects.remove(path)
        self.recent_projects.insert(0, path)
        del self.recent_projects[MAX_RECENT:]

    @classmethod
    def load(cls) -> "Config":
        path = config_file()
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
            return cls(**known)
        except (OSError, ValueError, TypeError) as exc:
            log.warning("Ayar dosyası okunamadı, varsayılanlar kullanılıyor: %s", exc)
            return cls()

    def save(self) -> None:
        try:
            config_file().write_text(
                json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except OSError as exc:
            log.error("Ayarlar kaydedilemedi: %s", exc)
