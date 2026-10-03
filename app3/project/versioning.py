"""Surum Gecmisi (Versioning) — adlandirilmis, kalici kontrol noktalari.

Undo/redo (`app.timeline.history.TimelineHistory`) oturum ICI, dogrusal ve
GECICI bir gecmistir (uygulama kapatilinca kaybolur). Versioning ise bunun
tamamlayicisidir: kullanicinin istedigi an ("AI duzenlemeden once",
"ilk taslak", "muzik eklenmeden once" vb.) ELLE isimlendirip DISKE kaydettigi,
proje kapatilip acilsa bile kalici kalan kontrol noktalaridir. Herhangi bir
surume, undo gecmisini bozmadan (geri yukleme islemi de undo'ya kendi basina
bir adim olarak eklenir) geri donulebilir.

Depolama: `<proje>.aidproj` dosyasinin yaninda `<proje_stem>.aidversions/`
klasoru. Her surum kendi `.aidproj` anlik goruntusunu tasir (`project.py`
`write_project_snapshot` ile, ATOMIK yazma); ayrica okunmasi ucuz, tek bir
`index.json` dosyasinda metadata (id/etiket/not/zaman/boyut) tutulur.

Proje henuz hic kaydedilmemisse (path=None) surumler, kullanici veri
klasorundeki `~/.ai_director/autosave/versions/<session_id>/` altinda tutulur
ve proje ilk kez kaydedildiginde (`relocate_after_save`) asil konumuna
tasinir — boylece "once surum olustur, sonra kaydet" sirasi da calisir.
"""
from __future__ import annotations

import json
import logging
import shutil
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.project.project import PROJECT_EXT, Project, ProjectError, write_project_snapshot
from app.runtime.paths import autosave_dir

log = logging.getLogger(__name__)

INDEX_FILE = "index.json"
INDEX_FORMAT = "aidirector-versions"
MAX_VERSIONS = 200  # guvenlik siniri; UI'da zaten kullanicinin kendi temizlemesi beklenir


class VersioningError(RuntimeError):
    """Surum olusturulamadi/okunamadi/geri yuklenemedi."""


def _now_iso() -> str:
    # Mikrosaniye hassasiyeti: ayni saniye icinde art arda olusturulan surumlerin
    # (ör. testlerde ya da hizli ardisik "Surum Olustur" tiklamalarinda) `created`
    # alanina gore DOGRU sirada (en yeni basta) listelenebilmesi icin onemlidir.
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


@dataclass
class VersionEntry:
    id: str
    label: str
    note: str
    created: str
    file: str  # klasore GORE dosya adi (tasinabilirlik icin)
    auto: bool = False  # True ise sistem tarafindan otomatik olusturuldu (ör. "AI Düzenle" öncesi)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "VersionEntry":
        return cls(
            id=str(data["id"]),
            label=str(data.get("label", "")),
            note=str(data.get("note", "")),
            created=str(data.get("created", "")),
            file=str(data["file"]),
            auto=bool(data.get("auto", False)),
        )


class VersionManager:
    """Bir `Project` icin surum (named snapshot) olusturma/listeleme/geri yukleme."""

    def __init__(self, project: Project) -> None:
        self.project = project

    # ---------------- konum ----------------
    def versions_dir(self, create: bool = False) -> Path:
        if self.project.path is not None:
            base = Path(self.project.path).resolve()
            path = base.parent / f"{base.stem}.aidversions"
        else:
            # Proje henuz kaydedilmedi: gecici olarak kullanici veri klasorunde,
            # bu oturuma ozel bir klasorde tut.
            path = autosave_dir() / "versions" / self.project.session_id
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path

    def _index_path(self, create: bool = False) -> Path:
        return self.versions_dir(create=create) / INDEX_FILE

    def _load_index(self) -> list[VersionEntry]:
        idx = self._index_path()
        if not idx.is_file():
            return []
        try:
            data = json.loads(idx.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            log.warning("Sürüm dizini okunamadı (%s): %s", idx, exc)
            return []
        if not isinstance(data, dict) or data.get("format") != INDEX_FORMAT:
            return []
        out = []
        for raw in data.get("versions", []):
            try:
                out.append(VersionEntry.from_dict(raw))
            except (KeyError, TypeError, ValueError):
                continue
        return out

    def _save_index(self, entries: list[VersionEntry]) -> None:
        idx = self._index_path(create=True)
        payload = {"format": INDEX_FORMAT, "versions": [e.to_dict() for e in entries]}
        tmp = idx.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(idx)
        except OSError as exc:
            raise VersioningError(f"Sürüm dizini yazılamadı: {exc}") from exc

    # ---------------- islemler ----------------
    def list(self) -> list[VersionEntry]:
        """En yeni surum basta olacak sekilde dondurur."""
        return sorted(self._load_index(), key=lambda e: e.created, reverse=True)

    def create(self, label: str, note: str = "", auto: bool = False) -> VersionEntry:
        """Projenin GUNCEL durumunun adlandirilmis bir anlik goruntusunu diske yazar.

        Not: bu islem `Project`'in dirty/path durumunu DEGISTIRMEZ — kullanicinin
        ana kaydetme akisindan tamamen bagimsizdir (kaydedilmemis bir calismanin
        da surumu alinabilir).
        """
        label = label.strip() or "Adsız sürüm"
        entries = self._load_index()
        vid = uuid.uuid4().hex[:12]
        fname = f"v_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{vid}{PROJECT_EXT}"
        target = self.versions_dir(create=True) / fname
        write_project_snapshot(self.project, target)
        entry = VersionEntry(id=vid, label=label, note=note, created=_now_iso(), file=fname, auto=auto)
        entries.append(entry)
        if len(entries) > MAX_VERSIONS:
            # en eski (manuel olmayanlari once olmak uzere) surumleri diskten de sil
            entries.sort(key=lambda e: e.created)
            overflow = entries[: len(entries) - MAX_VERSIONS]
            for old in overflow:
                self._delete_file(old)
            entries = entries[len(entries) - MAX_VERSIONS :]
        self._save_index(entries)
        return entry

    def restore(self, version_id: str) -> Project:
        """Bir surumu YUKLER ve yeni bir `Project` nesnesi olarak dondurur.

        Cagiran taraf (UI), bunu uygulamadan ONCE kendi undo/version akisina
        (ör. "geri yuklemeden once mevcut durumu da bir surum olarak kaydet")
        entegre etmekle sorumludur; bu metot yalnizca OKUMA yapar, mevcut proje
        dosyasina DOKUNMAZ.
        """
        entry = self._find(version_id)
        if entry is None:
            raise VersioningError("Sürüm bulunamadı (silinmiş olabilir).")
        src = self.versions_dir() / entry.file
        if not src.is_file():
            raise VersioningError(f"Sürüm dosyası eksik: {src}")
        try:
            restored = Project.load(src)
        except ProjectError as exc:
            raise VersioningError(f"Sürüm okunamadı: {exc}") from exc
        # Geri yuklenen proje, anlik goruntunun DOSYASINI degil ASIL projenin
        # kaydetme hedefini isaret etmeli (yoksa "Kaydet" yanlislikla surum
        # klasorune yazar). `restored.name`'e DOKUNULMAZ: surum anindaki ismi
        # (snapshot'ta ne kaydedildiyse) korumak dogru olandir.
        restored.path = self.project.path
        restored.session_id = self.project.session_id
        restored.dirty = True
        return restored

    def delete(self, version_id: str) -> bool:
        entries = self._load_index()
        keep = [e for e in entries if e.id != version_id]
        if len(keep) == len(entries):
            return False
        removed = next(e for e in entries if e.id == version_id)
        self._delete_file(removed)
        self._save_index(keep)
        return True

    def relocate_after_save(self, old_project_path: Path | None) -> None:
        """Proje ILK KEZ kaydedildiginde (path None -> gercek dosya), o ana kadar
        gecici session klasorunde biriken surumleri asil `.aidversions` klasorune
        tasir. Zaten kaydedilmis bir proje icin (old_project_path verilmisse ve
        klasor zaten dogru yerdeyse) hicbir sey yapmaz.
        """
        if self.project.path is None:
            return
        tmp_dir = autosave_dir() / "versions" / self.project.session_id
        if not tmp_dir.is_dir() or not any(tmp_dir.iterdir()):
            return
        real_dir = self.versions_dir(create=True)
        for item in tmp_dir.iterdir():
            dest = real_dir / item.name
            if not dest.exists():
                shutil.move(str(item), str(dest))
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # ---------------- yardimci ----------------
    def _find(self, version_id: str) -> VersionEntry | None:
        return next((e for e in self._load_index() if e.id == version_id), None)

    def _delete_file(self, entry: VersionEntry) -> None:
        path = self.versions_dir() / entry.file
        try:
            if path.is_file():
                path.unlink()
        except OSError as exc:
            log.warning("Sürüm dosyası silinemedi (%s): %s", path, exc)


__all__ = ["VersionEntry", "VersionManager", "VersioningError"]
