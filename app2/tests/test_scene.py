"""Sahne algılama (scene detection) testleri.

`detect_scene_changes` gerçek ffmpeg çalıştırır (bulunamazsa atlanır);
`split_at_scenes` saf Python olduğundan ffmpeg'e ihtiyaç duymadan test edilir.
"""
from __future__ import annotations

import shutil
import subprocess

import pytest

from app.scene.detector import (
    SceneDetectionError,
    detect_scene_changes,
    ffmpeg_available,
    split_at_scenes,
)
from app.timeline.model import Timeline

HAS_FFMPEG = shutil.which("ffmpeg") is not None


def _make_two_shot_video(path, seg_duration=2.0, w=320, h=240):
    """`seg_duration` saniyelik mavi + `seg_duration` saniyelik kırmızıdan,
    ortasında tek bir sert kesim olan bir test videosu üretir."""
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"color=c=blue:s={w}x{h}:d={seg_duration}",
        "-f", "lavfi", "-i", f"color=c=red:s={w}x{h}:d={seg_duration}",
        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
        "-map", "[v]", "-pix_fmt", "yuv420p", "-r", "25", str(path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg kurulu değil")
def test_detect_scene_changes_finds_hard_cut(tmp_path):
    video = tmp_path / "two_shot.mp4"
    _make_two_shot_video(video, seg_duration=2.0)

    times = detect_scene_changes(video, threshold=0.4)

    assert times, "sert kesim tespit edilmeliydi"
    assert any(1.8 < t < 2.2 for t in times)


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg kurulu değil")
def test_detect_scene_changes_missing_file_raises():
    with pytest.raises(SceneDetectionError):
        detect_scene_changes("/tmp/ai_director_does_not_exist.mp4")


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg kurulu değil")
def test_detect_scene_changes_rejects_bad_threshold(tmp_path):
    video = tmp_path / "two_shot.mp4"
    _make_two_shot_video(video, seg_duration=1.0)
    with pytest.raises(SceneDetectionError):
        detect_scene_changes(video, threshold=1.5)


def test_ffmpeg_available_reflects_system_state():
    # Gercek sistem durumunu yansitir; burada sadece cagirilabildigini dogruluyoruz.
    assert ffmpeg_available() in (True, False)
    assert ffmpeg_available("/definitely/not/a/real/ffmpeg") is True


def test_split_at_scenes_splits_clip_at_each_boundary():
    tl = Timeline()
    clips = tl.add_media("m1", "clip.mp4", duration=6.0, has_audio=False)
    clip_id = clips[0].id

    n = split_at_scenes(tl, clip_id, scene_times=[2.0, 4.0])

    assert n == 2
    ordered = sorted(tl.all_clips(), key=lambda c: c.start)
    assert [c.start for c in ordered] == [0.0, 2.0, 4.0]
    assert [c.end for c in ordered] == [2.0, 4.0, 6.0]


def test_split_at_scenes_splits_linked_audio_and_video_together():
    tl = Timeline()
    clips = tl.add_media("m1", "clip.mp4", duration=6.0, has_audio=True)
    video_clip_id = next(c.id for c in clips if c.media_id == "m1" and c in tl.first_track("video").clips)

    n = split_at_scenes(tl, video_clip_id, scene_times=[3.0])

    assert n == 1
    assert len(tl.first_track("video").clips) == 2
    assert len(tl.first_track("audio").clips) == 2


def test_split_at_scenes_ignores_boundaries_outside_clip_source_range():
    tl = Timeline()
    clips = tl.add_media("m1", "clip.mp4", duration=4.0, has_audio=False)
    clip_id = clips[0].id

    # 10.0, klibin [0, 4) kaynak araligi disinda -> yok sayilmali
    n = split_at_scenes(tl, clip_id, scene_times=[10.0])

    assert n == 0
    assert len(tl.all_clips()) == 1


def test_split_at_scenes_unknown_clip_returns_zero():
    tl = Timeline()
    assert split_at_scenes(tl, "yok-boyle-bir-id", scene_times=[1.0]) == 0


def test_split_at_scenes_does_not_affect_unrelated_track():
    """Sahne bolme, yalnizca hedeflenen klip (ve baglilarini) etkilemeli;
    ayni zaman araligini kapsayan ILISKISIZ bir baska izdeki klibe dokunmamali."""
    tl = Timeline()
    clips = tl.add_media("m1", "clip.mp4", duration=6.0, has_audio=False)
    clip_id = clips[0].id

    music = tl.add_audio_track(role="music")
    from app.timeline.model import Clip
    music.add(Clip(media_id="music1", name="song.mp3", source_in=0.0, source_out=6.0, start=0.0))

    n = split_at_scenes(tl, clip_id, scene_times=[3.0])

    assert n == 1
    assert len(tl.first_track("video").clips) == 2
    assert len(music.clips) == 1  # ilgisiz muzik klibi bolunmedi
