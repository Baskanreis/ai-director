"""Proje kaydet/yukle testleri."""
import subprocess

import pytest

from app.project.project import Project, ProjectError
from app.video.media_info import MediaProbeError, probe_video


def _make_video(path, duration=2.0, w=64, h=64):
    """ffmpeg ile kucuk bir test videosu uretir (sessiz)."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=blue:s={w}x{h}:d={duration}",
            "-pix_fmt", "yuv420p", str(path),
        ],
        check=True, capture_output=True,
    )


@pytest.fixture
def sample_video(tmp_path):
    p = tmp_path / "sample.mp4"
    _make_video(p)
    return p


def test_probe_video_reads_duration(sample_video):
    info = probe_video(sample_video)
    assert info.duration == pytest.approx(2.0, abs=0.2)
    assert info.width == 64 and info.height == 64


def test_probe_missing_file(tmp_path):
    with pytest.raises(MediaProbeError):
        probe_video(tmp_path / "yok.mp4")


def test_add_media_and_timeline(sample_video):
    proj = Project("Test")
    info = probe_video(sample_video)
    item, created = proj.add_media(info)
    assert created is True
    proj.timeline.add_media(item.id, item.name, item.duration, item.has_audio)
    assert proj.timeline.duration == pytest.approx(info.duration)

    item2, created2 = proj.add_media(info)
    assert created2 is False and item2.id == item.id


def test_save_and_load_roundtrip(tmp_path, sample_video):
    proj = Project("Test")
    info = probe_video(sample_video)
    item, _ = proj.add_media(info)
    proj.timeline.add_media(item.id, item.name, item.duration, item.has_audio)

    out = tmp_path / "proje.aidproj"
    saved_path = proj.save(out)
    assert saved_path.exists()
    assert proj.dirty is False

    loaded = Project.load(saved_path)
    assert loaded.name == "Test"
    assert len(loaded.media) == 1
    assert loaded.media[0].exists
    assert loaded.timeline.duration == pytest.approx(info.duration)


def test_load_rejects_foreign_json(tmp_path):
    p = tmp_path / "x.aidproj"
    p.write_text('{"format": "other", "schema": 1}', encoding="utf-8")
    with pytest.raises(ProjectError):
        Project.load(p)


def test_load_rejects_future_schema(tmp_path):
    p = tmp_path / "x.aidproj"
    p.write_text(
        '{"format": "aidirector-project", "schema": 99, "name": "x",'
        ' "media": [], "timeline": {"fps": 30, "tracks": ['
        '{"id":"V1","kind":"video","clips":[]}]}}',
        encoding="utf-8",
    )
    with pytest.raises(ProjectError):
        Project.load(p)


def test_save_relative_media_path_survives_move(tmp_path, sample_video):
    """Proje dosyasi ile video ayni klasordeyse, klasor tasinsa bile bulunur."""
    proj = Project("Test")
    info = probe_video(sample_video)
    item, _ = proj.add_media(info)
    proj.timeline.add_media(item.id, item.name, item.duration, item.has_audio)
    proj.save(tmp_path / "proje.aidproj")

    new_dir = tmp_path.parent / (tmp_path.name + "_moved")
    tmp_path.rename(new_dir)

    loaded = Project.load(new_dir / "proje.aidproj")
    assert loaded.media[0].exists
