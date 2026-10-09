"""Otomatik Kayıt (Autosave) + Çökme Sonrası Kurtarma (Crash Recovery).

Tasarim:
- Her calisma oturumu (`MainWindow` acilisindan kapanisina kadar), projenin
  `session_id`'si ile anilan bir OTURUM KAYDI (`SessionRegistry`) tutar:
  {session_id, project_name, project_path (varsa), autosave_file, pid,
  started, updated, clean_exit}. Bu kayit `~/.ai_director/autosave/sessions.json`
  icindedir (tum oturumlar tek dosyada, kucuk ve JSON).
- Oturum ACIKKEN periyodik olarak (varsayilan 2 dakika, yalniz proje "dirty"
  ise) projenin TAM anlik goruntusu `~/.ai_director/autosave/<session_id>.aidproj`
  dosyasina YAZILIR. Bu, kullanicinin KENDI `Dosya > Kaydet` akisini (Ctrl+S,
  hedef dosya, "Son Projeler") hic etkilemez — ayri, sessiz bir arka plan
  kopyasidir.
- Pencere TEMIZ kapatildiginda (`mark_clean_exit`) oturum kaydi `clean_exit=True`
  olarak isaretlenir ve autosave dosyasi silinir (artik gereksiz).
- Bir sonraki ACILISTA, `find_recoverable_sessions()` kayit dosyasini tarar:
  `clean_exit=False` olan (yani uygulamanin cokup/guc kesintisiyle/zorla
  kapanip TEMIZ kapanmadigi) ve autosave dosyasi hala diskte duran oturumlari
  dondurur. UI bunlari kullaniciya "kurtarilabilir oturum" olarak sunar.
- Eski (ör. 30 gunden uzun suredir güncellenmeyen, zaten temiz kapanmis ya da
  dosyasi kaybolmus) kayitlar `prune_stale_sessions()` ile sessizce temizlenir.

Bu modul kasitli olarak Qt'den BAGIMSIZDIR (PySide6 import etmez) — boylece
tamamen Qt event loop'u olmadan, pytest ile dogrudan test edilebilir. Qt'ye
bagli periyodik tetikleme (`QTimer`) `app/ui/main_window.py` icinde, bu
moduldeki saf fonksiyonlari cagiran ince bir katman olarak yasar.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.project.project import Project, ProjectError, write_project_snapshot
from app.runtime.paths import autosave_dir, session_registry_file

log = logging.getLogger(__name__)

REGISTRY_FORMAT = "aidirector-sessions"
STALE_DAYS = 30


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


@dataclass
class SessionRecord:
    session_id: str
    project_name: str
    project_path: str  # bos string = hic kaydedilmemis proje
    autosave_file: str
    pid: int
    started: str
    updated: str
    clean_exit: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SessionRecord":
        return cls(
            session_id=str(data["session_id"]),
            project_name=str(data.get("project_name", "")),
            project_path=str(data.get("project_path", "")),
            autosave_file=str(data["autosave_file"]),
            pid=int(data.get("pid", 0)),
            started=str(data.get("started", "")),
            updated=str(data.get("updated", "")),
            clean_exit=bool(data.get("clean_exit", False)),
        )


class SessionRegistry:
    """`sessions.json` icin kucuk, atomik bir okuma/yazma katmani."""

    def __init__(self, registry_path: Path | None = None) -> None:
        self.path = registry_path or session_registry_file()

    def _load_all(self) -> dict[str, SessionRecord]:
        if not self.path.is_file():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            log.warning("Oturum kaydı okunamadı (%s): %s", self.path, exc)
            return {}
        if not isinstance(data, dict) or data.get("format") != REGISTRY_FORMAT:
            return {}
        out: dict[str, SessionRecord] = {}
        for raw in data.get("sessions", []):
            try:
                rec = SessionRecord.from_dict(raw)
                out[rec.session_id] = rec
            except (KeyError, TypeError, ValueError):
                continue
        return out

    def _save_all(self, sessions: dict[str, SessionRecord]) -> None:
        payload = {"format": REGISTRY_FORMAT, "sessions": [r.to_dict() for r in sessions.values()]}
        tmp = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.path)
        except OSError as exc:
            log.error("Oturum kaydı yazılamadı (%s): %s", self.path, exc)

    def upsert(self, record: SessionRecord) -> None:
        sessions = self._load_all()
        sessions[record.session_id] = record
        self._save_all(sessions)

    def get(self, session_id: str) -> SessionRecord | None:
        return self._load_all().get(session_id)

    def remove(self, session_id: str) -> None:
        sessions = self._load_all()
        if session_id in sessions:
            del sessions[session_id]
            self._save_all(sessions)

    def all(self) -> list[SessionRecord]:
        return list(self._load_all().values())


class AutosaveManager:
    """Tek bir calisma oturumu icin autosave + oturum kaydi yasam dongusu.

    Qt'den bagimsizdir: `tick()` metodu disaridan (ör. bir `QTimer`) periyodik
    olarak cagrilir; `start_session()`/`mark_clean_exit()` sirasiyla pencere
    acilista/temiz kapanista cagrilir.
    """

    def __init__(self, project: Project, registry: SessionRegistry | None = None) -> None:
        self.project = project
        self.registry = registry or SessionRegistry()
        self._autosave_path = autosave_dir() / f"{project.session_id}.aidproj"

    # ---------------- yasam dongusu ----------------
    def start_session(self) -> None:
        now = _now_iso()
        self.registry.upsert(
            SessionRecord(
                session_id=self.project.session_id,
                project_name=self.project.name,
                project_path=str(self.project.path) if self.project.path else "",
                autosave_file=str(self._autosave_path),
                pid=os.getpid(),
                started=now,
                updated=now,
                clean_exit=False,
            )
        )

    def set_project(self, project: Project) -> None:
        """Proje degistiginde (Yeni/Ac) ONCEKI oturumu temiz kapat, YENISI icin baslat."""
        self.mark_clean_exit()
        self.project = project
        self._autosave_path = autosave_dir() / f"{project.session_id}.aidproj"
        self.start_session()

    def tick(self) -> bool:
        """Proje "dirty" ise anlik goruntuyu autosave dosyasina yazar.

        Dondurulen deger: gercekten yazma yapildiysa True (UI, durum cubugunda
        "Otomatik kaydedildi" gibi kisa bir bilgi gosterebilir).
        """
        if not self.project.dirty:
            return False
        try:
            write_project_snapshot(self.project, self._autosave_path)
        except ProjectError as exc:
            log.warning("Autosave başarısız: %s", exc)
            return False
        rec = self.registry.get(self.project.session_id)
        if rec is not None:
            rec.project_name = self.project.name
            rec.project_path = str(self.project.path) if self.project.path else ""
            rec.updated = _now_iso()
            self.registry.upsert(rec)
        return True

    def mark_clean_exit(self) -> None:
        """Pencere DUZGUN kapatildiginda cagrilir: autosave artik gereksiz."""
        rec = self.registry.get(self.project.session_id)
        if rec is not None:
            rec.clean_exit = True
            rec.updated = _now_iso()
            self.registry.upsert(rec)
        try:
            if self._autosave_path.is_file():
                self._autosave_path.unlink()
        except OSError:
            pass
        self.registry.remove(self.project.session_id)

    @property
    def autosave_path(self) -> Path:
        return self._autosave_path


# ---------------- crash recovery (baslangicta cagrilir) ----------------
def find_recoverable_sessions(registry: SessionRegistry | None = None) -> list[SessionRecord]:
    """`clean_exit=False` olan VE autosave dosyasi gercekten diskte duran
    (dolayisiyla kurtarilabilir icerigi olan) oturumlari dondurur.

    Suan calisan PID ile ayni olan kayitlar (ayni surecin ikinci kez taranmasi
    gibi bir durum olmaz normalde ama guvenlik icin) dahil edilir — crash
    recovery, "bu PID hala calisiyor mu" kontrolune guvenmez, cunku bu platform
    bagimli ve guvenilmezdir; bunun yerine yalnizca `clean_exit` bayragina ve
    dosyanin varligina bakar.
    """
    reg = registry or SessionRegistry()
    out = []
    for rec in reg.all():
        if rec.clean_exit:
            continue
        if Path(rec.autosave_file).is_file():
            out.append(rec)
    return sorted(out, key=lambda r: r.updated, reverse=True)


def discard_session(session_id: str, registry: SessionRegistry | None = None) -> None:
    """Kullanici bir kurtarma onerisini REDDEDERSE: autosave dosyasini ve kaydi sil."""
    reg = registry or SessionRegistry()
    rec = reg.get(session_id)
    if rec is not None:
        try:
            p = Path(rec.autosave_file)
            if p.is_file():
                p.unlink()
        except OSError:
            pass
    reg.remove(session_id)


def load_recovered_project(record: SessionRecord) -> Project:
    """Bir kurtarma kaydindaki autosave dosyasini yukler ve `Project` olarak dondurur.

    Geri yuklenen projenin `path`'i, orijinal (autosave'DEN ONCEKI) kayit
    konumuna ayarlanir (varsa) — boylece kullanici "Kaydet" dediginde dosya
    kendi asil yerine yazilir, autosave klasorune degil. `dirty=True` birakilir
    ki kullanici kurtarilan hali ACIKCA kaydetmeden kaybetmesin.
    """
    autosave_file = Path(record.autosave_file)
    if not autosave_file.is_file():
        raise ProjectError(f"Kurtarma dosyası bulunamadı: {autosave_file}")
    project = Project.load(autosave_file)
    project.session_id = record.session_id
    project.path = Path(record.project_path) if record.project_path else None
    project.name = record.project_name or project.name
    project.dirty = True
    return project


def prune_stale_sessions(registry: SessionRegistry | None = None, max_age_days: int = STALE_DAYS) -> None:
    """Cok eski ve/veya zaten temiz kapanmis kayitlari (varsa artik gereksiz
    autosave dosyalariyla birlikte) sessizce temizler. Baslangicta bir kez
    cagrilmasi yeterlidir; kullaniciyi hicbir sekilde etkilemez/uyarmaz.
    """
    reg = registry or SessionRegistry()
    now = datetime.now(timezone.utc)
    for rec in reg.all():
        stale = False
        try:
            updated = datetime.fromisoformat(rec.updated)
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            stale = (now - updated).days > max_age_days
        except ValueError:
            stale = True
        missing_file = not Path(rec.autosave_file).is_file()
        if rec.clean_exit or stale or missing_file:
            if not rec.clean_exit and not missing_file:
                # cok eski ama hic kurtarilmamis: dosyayi da temizle
                try:
                    Path(rec.autosave_file).unlink()
                except OSError:
                    pass
            reg.remove(rec.session_id)


__all__ = [
    "SessionRecord",
    "SessionRegistry",
    "AutosaveManager",
    "find_recoverable_sessions",
    "discard_session",
    "load_recovered_project",
    "prune_stale_sessions",
]
