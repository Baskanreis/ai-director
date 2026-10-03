"""Proje modeli ve .aidproj dosyasi (JSON) okuma/yazma."""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app import __version__
from app.timeline.model import Timeline, TimelineError, new_id
from app.video.media_info import MediaInfo

PROJECT_EXT = ".aidproj"
FORMAT_NAME = "aidirector-project"
SCHEMA_VERSION = 1


class ProjectError(RuntimeError):
    """Proje dosyasi okunamadi/yazilamadi."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def atomic_write_json(target: Path, payload: dict) -> Path:
    """`payload`'i `target`'a ATOMIK olarak (gecici dosya + `os.replace`) yazar.

    Autosave, versioning (snapshot) ve normal proje kaydi hepsi bu tek, test edilmis
    yoldan gecer; boylece yarim/bozuk dosya kalma riski (crash/guc kesintisi) her
    yazma islemi icin ayni sekilde ele alinmis olur.
    """
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".aid_", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(text)
            os.replace(tmp, target)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
    except OSError as exc:
        raise ProjectError(f"Dosya yazılamadı ({target}): {exc}") from exc
    return target


def write_project_snapshot(project: "Project", target: Path) -> Path:
    """Projenin GUNCEL durumunu `target` yoluna yazar; `project` nesnesini DEGISTIRMEZ.

    `Project.save()`'den farki budur: `project.path`/`project.dirty`/`project.modified`
    aynen kalir. Autosave (crash recovery) ve versioning (adli snapshot) bu fonksiyonu
    kullanir, boylece "otomatik kaydet" ya da "surum olustur" kullanicinin asil
    kaydetme akisini (Ctrl+S, Son Projeler, "kaydedilmemis degisiklik" uyarisi) hic
    etkilemez.
    """
    target = Path(target).resolve()
    data = project.to_dict(target.parent)
    data["modified"] = _now()
    atomic_write_json(target, data)
    return target


@dataclass
class MediaItem:
    id: str
    path: str
    duration: float
    width: int
    height: int
    fps: float
    has_audio: bool
    codec: str = ""
    media_type: str = "video"
    audio_codec: str = ""
    audio_channels: int = 0
    sample_rate: int = 0
    thumbnail: str = ""

    @property
    def name(self) -> str:
        return Path(self.path).name

    @property
    def exists(self) -> bool:
        return Path(self.path).is_file()

    @classmethod
    def from_info(cls, info: MediaInfo) -> "MediaItem":
        return cls(
            new_id(), info.path, info.duration, info.width, info.height, info.fps,
            info.has_audio, info.codec, info.media_type, info.audio_codec,
            info.audio_channels, info.sample_rate, info.thumbnail,
        )


class Project:
    def __init__(self, name: str = "Adsız Proje") -> None:
        self.name = name
        self.path: Path | None = None
        self.media: list[MediaItem] = []
        self.timeline = Timeline()
        self.created = _now()
        self.modified = self.created
        self.dirty = False
        # Kaydedilmemis projeler de (path=None) autosave/crash-recovery ile
        # izlenebilsin diye her Project nesnesi, uretildigi andan itibaren
        # kalici (ayni calisma oturumu boyunca sabit) bir session_id tasir.
        self.session_id = uuid.uuid4().hex
        # Professional editor state is additive and backward-compatible with old .aidproj files.
        self.editor_data: dict = {"markers": [], "selection": {"start": None, "end": None}, "workspace": {}, "render_queue": []}

    # ---- medya havuzu ----
    def get_media(self, media_id: str) -> MediaItem | None:
        return next((m for m in self.media if m.id == media_id), None)

    def find_media_by_path(self, path: str | Path) -> MediaItem | None:
        target = os.path.normcase(str(Path(path).resolve()))
        for m in self.media:
            if os.path.normcase(str(Path(m.path).resolve())) == target:
                return m
        return None

    def add_media(self, info: MediaInfo) -> tuple[MediaItem, bool]:
        """(medya, yeni_mi). Ayni dosya ikinci kez eklenmez."""
        existing = self.find_media_by_path(info.path)
        if existing:
            return existing, False
        item = MediaItem.from_info(info)
        self.media.append(item)
        self.touch()
        return item, True

    def missing_media(self) -> list[MediaItem]:
        return [m for m in self.media if not m.exists]

    def touch(self) -> None:
        self.dirty = True
        self.modified = _now()

    # ---- serilestirme ----
    def to_dict(self, base_dir: Path | None = None) -> dict:
        media = []
        for m in self.media:
            entry = {
                "id": m.id,
                "path": m.path,
                "duration": m.duration,
                "width": m.width,
                "height": m.height,
                "fps": m.fps,
                "has_audio": m.has_audio,
                "codec": m.codec,
                "media_type": m.media_type,
                "audio_codec": m.audio_codec,
                "audio_channels": m.audio_channels,
                "sample_rate": m.sample_rate,
                # thumbnail bilinerek kaydedilmez: onbellek gecici dizinde, path'e
                # bagli olarak yeniden uretilir (bkz. media_info.generate_thumbnail).
            }
            if base_dir is not None:
                try:
                    entry["relative"] = os.path.relpath(m.path, base_dir)
                except ValueError:  # Windows'ta farkli surucu
                    pass
            media.append(entry)
        return {
            "format": FORMAT_NAME,
            "schema": SCHEMA_VERSION,
            "app_version": __version__,
            "name": self.name,
            "created": self.created,
            "modified": self.modified,
            "media": media,
            "timeline": self.timeline.to_dict(),
            "editor_data": self.editor_data,
        }

    @classmethod
    def from_dict(cls, data: dict, base_dir: Path | None = None) -> "Project":
        if data.get("format") != FORMAT_NAME:
            raise ProjectError("Bu bir AI Director proje dosyası değil")
        schema = data.get("schema", 0)
        if not isinstance(schema, int) or schema < 1 or schema > SCHEMA_VERSION:
            raise ProjectError(
                f"Desteklenmeyen proje sürümü (schema={schema}). Uygulamayı güncelleyin."
            )
        proj = cls(str(data.get("name", "Adsız Proje")))
        proj.created = str(data.get("created", proj.created))
        proj.modified = str(data.get("modified", proj.modified))
        try:
            for md in data.get("media", []):
                path = str(md["path"])
                rel = md.get("relative")
                if base_dir is not None and rel:
                    candidate = (base_dir / rel).resolve()
                    if candidate.is_file():
                        path = str(candidate)
                    elif not Path(path).is_file():
                        path = str(candidate)  # kayip: en azindan goreli konumu goster
                proj.media.append(
                    MediaItem(
                        id=str(md["id"]),
                        path=path,
                        duration=float(md["duration"]),
                        width=int(md["width"]),
                        height=int(md["height"]),
                        fps=float(md.get("fps", 0)),
                        has_audio=bool(md.get("has_audio", False)),
                        codec=str(md.get("codec", "")),
                        media_type=str(md.get("media_type", "video")),
                        audio_codec=str(md.get("audio_codec", "")),
                        audio_channels=int(md.get("audio_channels", 0)),
                        sample_rate=int(md.get("sample_rate", 0)),
                    )
                )
            proj.timeline = Timeline.from_dict(data["timeline"])
        except (KeyError, TypeError, ValueError, TimelineError) as exc:
            raise ProjectError(f"Proje verisi bozuk: {exc}") from exc
        known = {m.id for m in proj.media}
        for clip in proj.timeline.all_clips():
            if clip.media_id not in known:
                raise ProjectError(f"Klip bilinmeyen medyaya bağlı: {clip.media_id}")
        proj.editor_data = dict(data.get("editor_data") or {"markers": [], "selection": {"start": None, "end": None}, "workspace": {}, "render_queue": []})
        proj.dirty = False
        return proj

    # ---- dosya islemleri ----
    def save(self, path: str | Path | None = None) -> Path:
        target = Path(path) if path else self.path
        if target is None:
            raise ProjectError("Kaydedilecek yol belirtilmedi")
        if target.suffix.lower() != PROJECT_EXT:
            target = target.with_suffix(PROJECT_EXT)
        target = target.resolve()
        self.modified = _now()
        atomic_write_json(target, self.to_dict(target.parent))
        self.path = target
        if self.name == "Adsız Proje":
            self.name = target.stem
        self.dirty = False
        return target

    @classmethod
    def load(cls, path: str | Path) -> "Project":
        p = Path(path).resolve()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ProjectError(f"Dosya okunamadı: {exc}") from exc
        except ValueError as exc:
            raise ProjectError(f"Geçersiz JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ProjectError("Proje dosyası beklenen biçimde değil")
        proj = cls.from_dict(data, p.parent)
        proj.path = p
        return proj
