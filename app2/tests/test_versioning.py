"""Sürüm Geçmişi (Versioning) testleri (app/project/versioning.py)."""
from __future__ import annotations

import pytest

from app.project import versioning as versioning_mod
from app.project.project import Project
from app.project.versioning import VersionManager, VersioningError
from app.timeline.model import Timeline


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / ".ai_director"

    def _autosave_dir():
        p = data_dir / "autosave"
        p.mkdir(parents=True, exist_ok=True)
        return p

    monkeypatch.setattr(versioning_mod, "autosave_dir", _autosave_dir)
    return data_dir


def test_create_and_list_versions_for_unsaved_project(isolated_paths):
    project = Project("Kaydedilmemiş")
    manager = VersionManager(project)
    assert manager.list() == []

    entry = manager.create("ilk taslak", "başlangıç notu")
    versions = manager.list()
    assert len(versions) == 1
    assert versions[0].id == entry.id
    assert versions[0].label == "ilk taslak"
    assert versions[0].note == "başlangıç notu"


def test_versions_ordered_newest_first(isolated_paths):
    project = Project("Sıra Testi")
    manager = VersionManager(project)
    manager.create("birinci")
    manager.create("ikinci")
    manager.create("üçüncü")

    labels = [v.label for v in manager.list()]
    assert labels == ["üçüncü", "ikinci", "birinci"]


def test_restore_returns_independent_project_with_same_content(isolated_paths):
    project = Project("İçerik")
    project.timeline = Timeline()
    manager = VersionManager(project)
    v1 = manager.create("boş timeline")

    # projeyi "değiştir" (gerçek bir klip eklemeden, sadece isim değişikliğiyle
    # bu testte yalnızca "sürümdeki hal korunuyor mu" sorusunu izole ediyoruz)
    project.name = "Değişti"

    restored = manager.restore(v1.id)
    assert restored.name == "İçerik"  # sürüm anındaki isim korunmuş
    assert project.name == "Değişti"  # orijinal proje nesnesi ETKİLENMEMİŞ
    assert restored.dirty is True
    assert restored.session_id == project.session_id


def test_restore_unknown_version_raises(isolated_paths):
    project = Project("Yok")
    manager = VersionManager(project)
    with pytest.raises(VersioningError):
        manager.restore("olmayan-id")


def test_delete_removes_entry_and_file(isolated_paths):
    project = Project("Silme Testi")
    manager = VersionManager(project)
    entry = manager.create("silinecek")
    file_path = manager.versions_dir() / entry.file
    assert file_path.is_file()

    assert manager.delete(entry.id) is True
    assert not file_path.is_file()
    assert manager.list() == []
    assert manager.delete(entry.id) is False  # ikinci silme: artık yok


def test_relocate_after_save_moves_temp_versions_to_project_folder(isolated_paths, tmp_path):
    project = Project("Taşınacak")
    manager = VersionManager(project)
    manager.create("kaydetmeden önce")

    temp_dir = manager.versions_dir()
    assert temp_dir.exists()

    project_file = tmp_path / "workdir" / "deneme.aidproj"
    project.save(project_file)
    manager.relocate_after_save(None)

    real_dir = manager.versions_dir()
    assert real_dir == project_file.parent / "deneme.aidversions"
    assert real_dir.is_dir()
    assert len(manager.list()) == 1
    assert manager.list()[0].label == "kaydetmeden önce"


def test_restore_sets_path_to_current_project_target_not_snapshot_file(isolated_paths, tmp_path):
    project = Project("Yol Testi")
    project_file = tmp_path / "workdir2" / "proje.aidproj"
    project.save(project_file)
    manager = VersionManager(project)
    entry = manager.create("kayıtlı hal")

    restored = manager.restore(entry.id)
    assert restored.path == project.path  # snapshot dosyasına değil, asıl projeye işaret eder


def test_auto_flag_is_preserved(isolated_paths):
    project = Project("Otomatik")
    manager = VersionManager(project)
    entry = manager.create("geri yüklemeden önce", auto=True)
    assert manager.list()[0].auto is True
    assert entry.auto is True
