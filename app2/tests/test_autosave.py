"""Autosave + Crash Recovery testleri (app/project/autosave.py).

Qt'ye bagimli DEGILDIR: `AutosaveManager`/`SessionRegistry` saf Python'dur,
bu yuzden QApplication/QTimer olmadan dogrudan test edilebilir.
"""
from __future__ import annotations

import pytest

from app.project import autosave as autosave_mod
from app.project.autosave import (
    AutosaveManager,
    SessionRegistry,
    discard_session,
    find_recoverable_sessions,
    load_recovered_project,
    prune_stale_sessions,
)
from app.project.project import Project
from app.timeline.model import Timeline


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    """`app.runtime.paths`'teki kullanıcı veri klasörünü geçici bir dizine yönlendirir."""
    data_dir = tmp_path / ".ai_director"

    def _autosave_dir():
        p = data_dir / "autosave"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _session_registry_file():
        return _autosave_dir() / "sessions.json"

    monkeypatch.setattr(autosave_mod, "autosave_dir", _autosave_dir)
    monkeypatch.setattr(autosave_mod, "session_registry_file", _session_registry_file)
    return data_dir


def test_tick_only_writes_when_dirty(isolated_paths):
    project = Project("Dirty Testi")
    manager = AutosaveManager(project)
    manager.start_session()

    assert manager.tick() is False  # yeni proje henuz degismedi -> yazma yok
    assert not manager.autosave_path.exists()

    project.touch()
    assert manager.tick() is True
    assert manager.autosave_path.is_file()


def test_clean_exit_removes_autosave_and_registry_entry(isolated_paths):
    project = Project("Temiz Kapanis")
    manager = AutosaveManager(project)
    manager.start_session()
    project.touch()
    manager.tick()
    assert manager.autosave_path.is_file()

    manager.mark_clean_exit()
    assert not manager.autosave_path.is_file()

    registry = SessionRegistry()
    assert registry.get(project.session_id) is None
    assert find_recoverable_sessions(registry) == []


def test_crash_leaves_recoverable_session(isolated_paths):
    project = Project("Çökme Testi")
    project.timeline = Timeline()
    manager = AutosaveManager(project)
    manager.start_session()
    project.touch()
    manager.tick()
    # mark_clean_exit() HİÇ çağrılmadı -> "çökme" simülasyonu.

    recs = find_recoverable_sessions()
    assert len(recs) == 1
    rec = recs[0]
    assert rec.session_id == project.session_id
    assert rec.project_name == "Çökme Testi"
    assert rec.clean_exit is False


def test_load_recovered_project_restores_content_and_dirty_flag(isolated_paths):
    project = Project("İçerik Testi")
    manager = AutosaveManager(project)
    manager.start_session()
    project.touch()
    manager.tick()

    rec = find_recoverable_sessions()[0]
    recovered = load_recovered_project(rec)
    assert recovered.name == "İçerik Testi"
    assert recovered.dirty is True  # kullanıcı açıkça kaydetmeden kaybetmesin
    assert recovered.session_id == project.session_id
    assert recovered.path is None  # orijinal proje de hiç kaydedilmemişti


def test_discard_session_removes_file_and_registry_entry(isolated_paths):
    project = Project("İptal Testi")
    manager = AutosaveManager(project)
    manager.start_session()
    project.touch()
    manager.tick()
    assert manager.autosave_path.is_file()

    discard_session(project.session_id)
    assert not manager.autosave_path.is_file()
    assert find_recoverable_sessions() == []


def test_set_project_closes_old_session_and_opens_new_one(isolated_paths):
    old_project = Project("Eski")
    manager = AutosaveManager(old_project)
    manager.start_session()
    old_project.touch()
    manager.tick()
    old_path = manager.autosave_path
    assert old_path.is_file()

    new_project = Project("Yeni")
    manager.set_project(new_project)

    assert not old_path.is_file()  # eski oturum temiz kapatıldı
    registry = SessionRegistry()
    assert registry.get(old_project.session_id) is None
    assert registry.get(new_project.session_id) is not None


def test_two_sessions_do_not_interfere(isolated_paths):
    p1, p2 = Project("Proje 1"), Project("Proje 2")
    m1, m2 = AutosaveManager(p1), AutosaveManager(p2)
    m1.start_session()
    m2.start_session()
    p1.touch()
    p2.touch()
    m1.tick()
    m2.tick()

    recs = {r.session_id: r for r in find_recoverable_sessions()}
    assert set(recs) == {p1.session_id, p2.session_id}
    assert recs[p1.session_id].project_name == "Proje 1"
    assert recs[p2.session_id].project_name == "Proje 2"


def test_prune_stale_sessions_removes_sessions_with_missing_autosave_file(isolated_paths):
    project = Project("Kayıp Dosya")
    manager = AutosaveManager(project)
    manager.start_session()
    project.touch()
    manager.tick()
    manager.autosave_path.unlink()  # dosya manuel silindi (ör. kullanıcı sildi)

    prune_stale_sessions()
    assert find_recoverable_sessions() == []


def test_recoverable_session_survives_prune_when_recent_and_file_present(isolated_paths):
    project = Project("Taze Oturum")
    manager = AutosaveManager(project)
    manager.start_session()
    project.touch()
    manager.tick()

    prune_stale_sessions()
    assert len(find_recoverable_sessions()) == 1
