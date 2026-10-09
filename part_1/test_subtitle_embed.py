from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from app.subtitle.embed import burn_in_subtitles, export_srt, export_vtt, mux_soft_subtitles
from app.subtitle.models import Segment, SubtitleError, Transcript

pytestmark_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg kurulu değil")
pytestmark_ffprobe = pytest.mark.skipif(shutil.which("ffprobe") is None, reason="ffprobe kurulu değil")


def _transcript() -> Transcript:
    return Transcript(
        language="tr",
        segments=[Segment("Merhaba dünya", 0.0, 1.0), Segment("Test altyazısı", 1.0, 2.0)],
    )


def _make_video(path, duration=2.0):
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
         "-i", f"color=c=blue:s=160x120:d={duration}",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
         "-shortest", str(path)],
        check=True, capture_output=True,
    )


# ---- export_srt / export_vtt ----

def test_export_srt_writes_file(tmp_path):
    out = export_srt(_transcript(), tmp_path / "sub" / "out.srt")
    assert out.is_file()
    content = out.read_text(encoding="utf-8")
    assert "Merhaba dünya" in content
    assert "00:00:00,000 -->" in content


def test_export_vtt_writes_file(tmp_path):
    out = export_vtt(_transcript(), tmp_path / "out.vtt")
    content = out.read_text(encoding="utf-8")
    assert content.startswith("WEBVTT")
    assert "Test altyazısı" in content


# ---- mux_soft_subtitles ----

@pytestmark_ffmpeg
def test_mux_soft_subtitles_missing_video_raises(tmp_path):
    srt = export_srt(_transcript(), tmp_path / "a.srt")
    with pytest.raises(SubtitleError, match="Video bulunamadı"):
        mux_soft_subtitles(tmp_path / "yok.mp4", srt, tmp_path / "out.mp4")


@pytestmark_ffmpeg
def test_mux_soft_subtitles_missing_srt_raises(tmp_path):
    video = tmp_path / "v.mp4"
    _make_video(video)
    with pytest.raises(SubtitleError, match="Altyazı dosyası bulunamadı"):
        mux_soft_subtitles(video, tmp_path / "yok.srt", tmp_path / "out.mp4")


@pytestmark_ffmpeg
@pytestmark_ffprobe
def test_mux_soft_subtitles_adds_subtitle_stream(tmp_path):
    video = tmp_path / "v.mp4"
    _make_video(video)
    srt = export_srt(_transcript(), tmp_path / "a.srt")
    out = tmp_path / "muxed.mp4"

    result = mux_soft_subtitles(video, srt, out, language="tr")
    assert result == out
    assert out.is_file()

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", str(out)],
        capture_output=True, text=True, check=True,
    )
    streams = json.loads(probe.stdout)["streams"]
    kinds = [s["codec_type"] for s in streams]
    assert "subtitle" in kinds
    assert "video" in kinds and "audio" in kinds
    sub_stream = next(s for s in streams if s["codec_type"] == "subtitle")
    assert sub_stream.get("tags", {}).get("language") == "tur"


# ---- burn_in_subtitles ----

@pytestmark_ffmpeg
def test_burn_in_subtitles_missing_video_raises(tmp_path):
    srt = export_srt(_transcript(), tmp_path / "a.srt")
    with pytest.raises(SubtitleError, match="Video bulunamadı"):
        burn_in_subtitles(tmp_path / "yok.mp4", srt, tmp_path / "out.mp4")


@pytestmark_ffmpeg
@pytestmark_ffprobe
def test_burn_in_subtitles_produces_playable_video_same_duration(tmp_path):
    video = tmp_path / "v.mp4"
    _make_video(video, duration=2.0)
    srt = export_srt(_transcript(), tmp_path / "a.srt")
    out = tmp_path / "burned.mp4"

    result = burn_in_subtitles(video, srt, out, crf=30)
    assert result == out
    assert out.is_file()

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(out)],
        capture_output=True, text=True, check=True,
    )
    duration = float(probe.stdout.strip())
    assert duration == pytest.approx(2.0, abs=0.3)
