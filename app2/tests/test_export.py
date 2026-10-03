"""FFmpeg export testleri (gercek ffmpeg calistirir; bulunamazsa atlanir)."""
import shutil
import subprocess

import pytest

from app.export.ffmpeg_export import (
    ExportCancelled,
    ExportError,
    ExportSettings,
    export_timeline,
)
from app.timeline.model import Timeline
from app.video.media_info import probe_video

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg kurulu değil")


def _make_video(path, duration=2.0, color="blue", with_audio=False, w=320, h=240):
    cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={color}:s={w}x{h}:d={duration}"]
    if with_audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}"]
    cmd += ["-pix_fmt", "yuv420p"]
    if with_audio:
        cmd += ["-shortest"]
    cmd += [str(path)]
    subprocess.run(cmd, check=True, capture_output=True)


@pytest.fixture
def two_clip_timeline(tmp_path):
    p1 = tmp_path / "a.mp4"
    p2 = tmp_path / "b.mp4"
    _make_video(p1, duration=2.0, color="blue", with_audio=False)
    _make_video(p2, duration=1.5, color="red", with_audio=True)

    info1, info2 = probe_video(p1), probe_video(p2)
    tl = Timeline()
    tl.add_media("m1", "a.mp4", info1.duration, info1.has_audio)
    tl.add_media("m2", "b.mp4", info2.duration, info2.has_audio)
    media_paths = {"m1": str(p1), "m2": str(p2)}
    return tl, media_paths, info1.duration + info2.duration


def test_export_creates_file_with_expected_duration(tmp_path, two_clip_timeline):
    tl, media_paths, total_dur = two_clip_timeline
    out = tmp_path / "out.mp4"
    settings = ExportSettings(str(out), width=320, height=240, fps=24, crf=28)

    progress_events = []
    export_timeline(tl, media_paths, settings, on_progress=lambda f, m: progress_events.append(f))

    assert out.is_file() and out.stat().st_size > 0
    result_info = probe_video(out)
    assert result_info.duration == pytest.approx(total_dur, abs=0.3)
    assert result_info.width == 320 and result_info.height == 240
    assert progress_events[-1] == pytest.approx(1.0)


def test_export_missing_media_raises(tmp_path, two_clip_timeline):
    tl, media_paths, _ = two_clip_timeline
    media_paths["m1"] = str(tmp_path / "yok.mp4")
    with pytest.raises(ExportError):
        export_timeline(tl, media_paths, ExportSettings(str(tmp_path / "out.mp4")))


def test_export_empty_timeline_raises(tmp_path):
    with pytest.raises(ExportError):
        export_timeline(Timeline(), {}, ExportSettings(str(tmp_path / "out.mp4")))


def test_export_cancel_stops_early(tmp_path, two_clip_timeline):
    tl, media_paths, _ = two_clip_timeline
    calls = {"n": 0}

    def cancelled():
        calls["n"] += 1
        return calls["n"] > 1  # ilk parcadan sonra iptal

    with pytest.raises(ExportCancelled):
        export_timeline(
            tl, media_paths, ExportSettings(str(tmp_path / "out.mp4")),
            is_cancelled=cancelled,
        )


def test_export_fills_gap_with_black_and_silence(tmp_path, two_clip_timeline):
    """Klipler arasinda bosluk varsa export suresi bosluk dahil olmali (v0.6)."""
    tl, media_paths, _ = two_clip_timeline
    vtrack = tl.first_track("video")
    clip2 = [c for c in vtrack.clips if c.media_id == "m2"][0]
    assert tl.move(clip2.id, clip2.start + 0.5)  # 0.5sn bosluk yarat

    out = tmp_path / "gap.mp4"
    export_timeline(tl, media_paths, ExportSettings(str(out), width=320, height=240, fps=24, crf=30))

    result_info = probe_video(out)
    assert result_info.duration == pytest.approx(tl.duration, abs=0.3)


def test_export_mixes_multiple_audio_clips(tmp_path, two_clip_timeline):
    """Ses izindeki (A1) klip export ciktisinda ses akisi olarak yer almali."""
    tl, media_paths, total_dur = two_clip_timeline
    out = tmp_path / "audio.mp4"
    export_timeline(tl, media_paths, ExportSettings(str(out), width=320, height=240, fps=24, crf=30))

    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
         "stream=codec_type", "-of", "csv=p=0", str(out)],
        capture_output=True, text=True, check=True,
    )
    assert "audio" in proc.stdout


def _mean_volume_db(path) -> float:
    """ffmpeg volumedetect ile ortalama ses seviyesini (dB) olcer."""
    proc = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    for line in proc.stderr.splitlines():
        if "mean_volume:" in line:
            return float(line.split("mean_volume:")[1].strip().split(" ")[0])
    raise AssertionError(f"mean_volume bulunamadi:\n{proc.stderr}")


def test_export_clip_mute_produces_silence(tmp_path, two_clip_timeline):
    """v0.7: klip mute edilince o klibin sesi export'ta duyulmamali."""
    tl, media_paths, _ = two_clip_timeline
    aclip = tl.first_track("audio").clips[0]
    aclip.muted = True

    out = tmp_path / "muted.mp4"
    export_timeline(tl, media_paths, ExportSettings(str(out), width=320, height=240, fps=24, crf=30))

    assert _mean_volume_db(out) <= -60.0  # neredeyse tam sessizlik


def test_export_clip_gain_reduces_volume(tmp_path, two_clip_timeline):
    """v0.7: negatif gain_db, olcumlenen ortalama sesi belirgin sekilde dusurmeli."""
    tl, media_paths, _ = two_clip_timeline
    out_ref = tmp_path / "ref.mp4"
    export_timeline(tl, media_paths, ExportSettings(str(out_ref), width=320, height=240, fps=24, crf=30))
    ref_db = _mean_volume_db(out_ref)

    aclip = tl.first_track("audio").clips[0]
    aclip.gain_db = -20.0
    out_quiet = tmp_path / "quiet.mp4"
    export_timeline(tl, media_paths, ExportSettings(str(out_quiet), width=320, height=240, fps=24, crf=30))
    quiet_db = _mean_volume_db(out_quiet)

    assert quiet_db < ref_db - 10.0


def test_export_track_mute_silences_whole_track(tmp_path, two_clip_timeline):
    tl, media_paths, _ = two_clip_timeline
    tl.first_track("audio").muted = True
    out = tmp_path / "track_muted.mp4"
    export_timeline(tl, media_paths, ExportSettings(str(out), width=320, height=240, fps=24, crf=30))
    assert _mean_volume_db(out) <= -60.0


def test_export_ducking_reduces_music_while_voice_present(tmp_path):
    """v0.7: duck=True olan muzik izi, sesli (voice) iz calarken kisilmali."""
    from app.timeline.model import Clip

    music_path = tmp_path / "music.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=200:duration=3",
         "-f", "lavfi", "-i", "color=c=black:s=320x240:d=3", "-shortest", str(music_path)],
        check=True, capture_output=True,
    )
    voice_path = tmp_path / "voice.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=1000:duration=3",
         str(voice_path)],
        check=True, capture_output=True,
    )

    tl = Timeline()
    tl.first_track("video").add(Clip("bg", "bg.mp4", 0.0, 3.0, start=0.0))
    music_track = tl.add_audio_track(role="music")
    music_track.duck = True
    music_track.add(Clip("music", "music.mp4", 0.0, 3.0, start=0.0))
    voice_track = tl.add_audio_track(role="voice")
    voice_track.add(Clip("voice", "voice.wav", 0.0, 3.0, start=0.0))

    media_paths = {"bg": str(music_path), "music": str(music_path), "voice": str(voice_path)}

    # referans: voice izi ayni sekilde calarken, ama muzik izinde duck KAPALI
    # (boylece iki export'taki tek fark ducking'in acik/kapali olmasi olur;
    # voice'un kendi katkisi her iki durumda da ayni).
    tl_no_duck = Timeline.from_dict(tl.to_dict())
    for t in tl_no_duck.tracks:
        if t.role == "music":
            t.duck = False
    out_ref = tmp_path / "ref.mp4"
    export_timeline(
        tl_no_duck, media_paths, ExportSettings(str(out_ref), width=320, height=240, fps=24, crf=30)
    )
    ref_db = _mean_volume_db(out_ref)

    out_ducked = tmp_path / "ducked.mp4"
    export_timeline(tl, media_paths, ExportSettings(str(out_ducked), width=320, height=240, fps=24, crf=30))
    ducked_db = _mean_volume_db(out_ducked)

    assert ducked_db < ref_db - 1.0


@pytest.mark.parametrize("codec", ["h264", "h265", "av1"])
def test_export_supports_codec_when_available(tmp_path, two_clip_timeline, codec):
    from app.export.command_builder import available_codecs

    if codec not in available_codecs():
        pytest.skip(f"{codec} encoder bu sistemde kurulu değil")
    tl, media_paths, _ = two_clip_timeline
    out = tmp_path / f"out_{codec}.mp4"
    export_timeline(
        tl, media_paths, ExportSettings(str(out), width=320, height=240, fps=24, crf=30, codec=codec)
    )
    assert out.is_file() and out.stat().st_size > 0
