"""Timeline model testleri."""
import pytest

from app.timeline.model import Clip, Timeline, TimelineError


def test_add_media_creates_linked_clips():
    tl = Timeline()
    clips = tl.add_media("m1", "a.mp4", 10.0, has_audio=True)
    assert len(clips) == 2
    assert clips[0].link_id == clips[1].link_id
    assert tl.duration == 10.0


def test_add_media_without_audio():
    tl = Timeline()
    clips = tl.add_media("m1", "a.mp4", 5.0, has_audio=False)
    assert len(clips) == 1
    assert tl.first_track("audio").clips == []


def test_overlap_rejected():
    tl = Timeline()
    tl.add_media("m1", "a.mp4", 10.0, has_audio=False)
    with pytest.raises(TimelineError):
        tl.first_track("video").add(Clip("m2", "b.mp4", 0, 5, start=2.0))


def test_split_creates_two_clips_and_keeps_link():
    tl = Timeline()
    tl.add_media("m1", "a.mp4", 10.0, has_audio=True)
    assert tl.split(4.0) is True
    vtrack = tl.first_track("video")
    assert len(vtrack.clips) == 2
    left, right = vtrack.sorted_clips()
    assert left.duration == pytest.approx(4.0)
    assert right.duration == pytest.approx(6.0)
    # sesin de bolunmus olmasi lazim (link korunarak)
    atrack = tl.first_track("audio")
    assert len(atrack.clips) == 2


def test_split_too_close_to_edge_noop():
    tl = Timeline()
    tl.add_media("m1", "a.mp4", 10.0, has_audio=False)
    assert tl.split(0.01) is False
    assert len(tl.first_track("video").clips) == 1


def test_remove_with_ripple_shifts_next_clip():
    tl = Timeline()
    tl.add_media("m1", "a.mp4", 5.0, has_audio=False)
    tl.add_media("m2", "b.mp4", 5.0, has_audio=False)
    vtrack = tl.first_track("video")
    first_id = vtrack.sorted_clips()[0].id
    assert tl.remove(first_id, ripple=True) is True
    remaining = vtrack.clips[0]
    assert remaining.start == pytest.approx(0.0)


def test_roundtrip_dict():
    tl = Timeline()
    tl.add_media("m1", "a.mp4", 8.0, has_audio=True)
    tl.split(3.0)
    data = tl.to_dict()
    tl2 = Timeline.from_dict(data)
    assert tl2.duration == pytest.approx(tl.duration)
    assert len(tl2.all_clips()) == len(tl.all_clips())


def test_from_dict_rejects_missing_video_track():
    with pytest.raises(TimelineError):
        Timeline.from_dict({"fps": 30, "tracks": [{"id": "A1", "kind": "audio", "clips": []}]})


# ---- move ----

def test_move_shifts_linked_group_together():
    tl = Timeline()
    tl.add_media("m1", "a.mp4", 5.0, has_audio=True)
    vtrack, atrack = tl.first_track("video"), tl.first_track("audio")
    vclip = vtrack.clips[0]
    assert tl.move(vclip.id, 10.0) is True
    assert vtrack.clips[0].start == pytest.approx(10.0)
    assert atrack.clips[0].start == pytest.approx(10.0)


def test_move_rejects_overlap():
    tl = Timeline()
    tl.add_media("m1", "a.mp4", 5.0, has_audio=False)  # 0..5
    tl.add_media("m2", "b.mp4", 5.0, has_audio=False)  # 5..10
    vtrack = tl.first_track("video")
    first = vtrack.sorted_clips()[0]
    assert tl.move(first.id, 3.0) is False  # 3..8 cakisir m2 ile
    assert first.start == pytest.approx(0.0)  # degismemis olmali


def test_move_negative_clamped_to_zero():
    tl = Timeline()
    tl.add_media("m1", "a.mp4", 5.0, has_audio=False)
    vclip = tl.first_track("video").clips[0]
    tl.move(vclip.id, 8.0)
    assert tl.move(vclip.id, -3.0) is True
    assert vclip.start == pytest.approx(0.0)


def test_move_with_ripple_pushes_neighbour():
    tl = Timeline()
    tl.add_media("m1", "a.mp4", 5.0, has_audio=False)  # 0..5
    tl.add_media("m2", "b.mp4", 5.0, has_audio=False)  # 5..10
    vtrack = tl.first_track("video")
    first = vtrack.sorted_clips()[0]
    assert tl.move(first.id, 3.0, ripple=True) is True
    clips = vtrack.sorted_clips()
    assert clips[0].start == pytest.approx(3.0)
    assert clips[1].start == pytest.approx(8.0)  # 5 saniye kaydi


# ---- trim ----

def test_trim_end_shortens_clip_non_destructively():
    tl = Timeline()
    tl.add_media("m1", "a.mp4", 10.0, has_audio=False)
    clip = tl.first_track("video").clips[0]
    assert tl.trim(clip.id, "end", 6.0) is True
    assert clip.start == pytest.approx(0.0)
    assert clip.end == pytest.approx(6.0)
    assert clip.source_in == pytest.approx(0.0)
    assert clip.source_out == pytest.approx(6.0)


def test_trim_start_moves_in_point():
    tl = Timeline()
    tl.add_media("m1", "a.mp4", 10.0, has_audio=False)
    clip = tl.first_track("video").clips[0]
    assert tl.trim(clip.id, "start", 2.0) is True
    assert clip.start == pytest.approx(2.0)
    assert clip.source_in == pytest.approx(2.0)
    assert clip.duration == pytest.approx(8.0)


def test_trim_start_rejects_before_source_zero():
    tl = Timeline()
    tl.add_media("m1", "a.mp4", 10.0, has_audio=False)
    clip = tl.first_track("video").clips[0]
    tl.trim(clip.id, "start", 2.0)  # source_in artik 2.0
    assert tl.trim(clip.id, "start", -1.0) is False


def test_trim_rejects_too_short_result():
    tl = Timeline()
    tl.add_media("m1", "a.mp4", 10.0, has_audio=False)
    clip = tl.first_track("video").clips[0]
    assert tl.trim(clip.id, "end", 0.0) is False  # MIN_CLIP altinda kalirdi


def test_trim_rejects_overlap_with_neighbour():
    tl = Timeline()
    tl.add_media("m1", "a.mp4", 5.0, has_audio=False)  # 0..5
    tl.add_media("m2", "b.mp4", 5.0, has_audio=False)  # 5..10
    first = tl.first_track("video").sorted_clips()[0]
    assert tl.trim(first.id, "end", 7.0) is False  # m2'nin ustune tasar


def test_trim_only_affects_single_clip_not_linked_pair():
    tl = Timeline()
    tl.add_media("m1", "a.mp4", 10.0, has_audio=True)
    vclip = tl.first_track("video").clips[0]
    aclip = tl.first_track("audio").clips[0]
    tl.trim(vclip.id, "end", 6.0)
    assert vclip.end == pytest.approx(6.0)
    assert aclip.end == pytest.approx(10.0)  # linkli es klip etkilenmedi


# ---- snap ----

def test_snap_points_includes_zero_and_clip_edges():
    tl = Timeline()
    tl.add_media("m1", "a.mp4", 5.0, has_audio=False)
    tl.add_media("m2", "b.mp4", 3.0, has_audio=False)
    assert tl.snap_points() == [0.0, 5.0, 8.0]


def test_snap_points_excludes_given_clip_ids():
    tl = Timeline()
    tl.add_media("m1", "a.mp4", 5.0, has_audio=False)
    clip = tl.first_track("video").clips[0]
    assert tl.snap_points(frozenset({clip.id})) == [0.0]


# ---- ses ozellikleri (v0.7 Audio Engine) ----

def test_clip_default_audio_properties():
    tl = Timeline()
    tl.add_media("m1", "a.mp4", 5.0, has_audio=True)
    aclip = tl.first_track("audio").clips[0]
    assert aclip.gain_db == 0.0
    assert aclip.muted is False
    assert aclip.fade_in == 0.0
    assert aclip.fade_out == 0.0


def test_clip_audio_properties_roundtrip_dict():
    clip = Clip("m1", "a.mp4", 0.0, 5.0, start=0.0, gain_db=-6.0, muted=True, fade_in=0.5, fade_out=1.0)
    restored = Clip.from_dict(clip.to_dict())
    assert restored.gain_db == pytest.approx(-6.0)
    assert restored.muted is True
    assert restored.fade_in == pytest.approx(0.5)
    assert restored.fade_out == pytest.approx(1.0)


def test_clip_from_dict_defaults_audio_properties_when_missing():
    """Eski (v0.6 oncesi) proje dosyalarinda bu alanlar yoktur; varsayilanlar kullanilmali."""
    d = {"media_id": "m1", "name": "a.mp4", "source_in": 0.0, "source_out": 5.0, "start": 0.0}
    clip = Clip.from_dict(d)
    assert clip.gain_db == 0.0 and clip.muted is False
    assert clip.fade_in == 0.0 and clip.fade_out == 0.0


def test_add_audio_track_music_and_voice():
    tl = Timeline()
    music = tl.add_audio_track(role="music")
    voice = tl.add_audio_track(role="voice")
    assert music.kind == "audio" and music.role == "music"
    assert voice.kind == "audio" and voice.role == "voice"
    assert music.id != voice.id
    assert len({t.id for t in tl.tracks}) == len(tl.tracks)  # id'ler benzersiz


def test_add_audio_track_rejects_unknown_role():
    tl = Timeline()
    with pytest.raises(TimelineError):
        tl.add_audio_track(role="fx")


def test_track_audio_properties_roundtrip_dict():
    tl = Timeline()
    music = tl.add_audio_track(role="music")
    music.gain_db = -3.0
    music.normalize = True
    music.duck = True
    tl2 = Timeline.from_dict(tl.to_dict())
    restored = tl2.track(music.id)
    assert restored.role == "music"
    assert restored.gain_db == pytest.approx(-3.0)
    assert restored.normalize is True
    assert restored.duck is True


def test_track_from_dict_defaults_when_missing_role():
    """Eski proje dosyalarinda 'role' vb. alanlar yoktur; jenerik ('') olmali."""
    tl = Timeline()
    tl.add_media("m1", "a.mp4", 5.0, has_audio=True)
    data = tl.to_dict()
    del data["tracks"][1]["role"]
    del data["tracks"][1]["gain_db"]
    restored = Timeline.from_dict(data)
    atrack = restored.first_track("audio")
    assert atrack.role == ""
    assert atrack.gain_db == 0.0
