"""app.audio.engine testleri: filtre parcasi uretimi (ffmpeg gerektirmez) +
waveform uretimi (gercek ffmpeg kullanir; bulunamazsa atlanir)."""
from __future__ import annotations

import shutil
import subprocess

import pytest

from app.audio.engine import (
    DUCK_RATIO,
    DUCK_THRESHOLD,
    clip_filter_fragment,
    duck_filter_fragment,
    generate_waveform_peaks,
    track_filter_fragment,
)
from app.timeline.model import Clip, Track


def _clip(**kw) -> Clip:
    base = dict(media_id="m1", name="a.mp4", source_in=0.0, source_out=4.0, start=0.0)
    base.update(kw)
    return Clip(**base)


def _track(**kw) -> Track:
    base = dict(id="A1", name="Ses 1", kind="audio")
    base.update(kw)
    return Track(**base)


# ---- clip_filter_fragment ----

def test_clip_no_properties_returns_none():
    assert clip_filter_fragment(_clip()) is None


def test_clip_muted_returns_volume_zero():
    assert clip_filter_fragment(_clip(muted=True)) == "volume=0"


def test_clip_muted_overrides_gain():
    """Mute acikken kazanc filtresi eklenmemeli (zaten sessiz)."""
    frag = clip_filter_fragment(_clip(muted=True, gain_db=6.0))
    assert frag == "volume=0"


def test_clip_gain_produces_volume_db_filter():
    frag = clip_filter_fragment(_clip(gain_db=-6.0))
    assert frag == "volume=-6dB"


def test_clip_fade_in_and_out():
    # duration = 4.0
    frag = clip_filter_fragment(_clip(fade_in=1.0, fade_out=0.5))
    assert "afade=t=in:st=0:d=1" in frag
    assert "afade=t=out:st=3.5:d=0.5" in frag


def test_clip_fade_out_start_time_relative_to_duration():
    frag = clip_filter_fragment(_clip(source_in=0.0, source_out=10.0, fade_out=2.0))
    assert "afade=t=out:st=8:d=2" in frag


def test_clip_fade_longer_than_duration_is_clamped():
    frag = clip_filter_fragment(_clip(source_in=0.0, source_out=1.0, fade_in=5.0))
    assert "afade=t=in:st=0:d=1" in frag


def test_clip_gain_and_fade_combined_order():
    frag = clip_filter_fragment(_clip(gain_db=3.0, fade_in=0.5, fade_out=0.5))
    parts = frag.split(",")
    assert parts[0] == "volume=3dB"
    assert parts[1].startswith("afade=t=in")
    assert parts[2].startswith("afade=t=out")


# ---- track_filter_fragment ----

def test_track_no_properties_returns_none():
    assert track_filter_fragment(_track()) is None


def test_track_muted_returns_volume_zero_and_skips_normalize():
    frag = track_filter_fragment(_track(muted=True, normalize=True, gain_db=5.0))
    assert frag == "volume=0"


def test_track_gain_only():
    assert track_filter_fragment(_track(gain_db=2.5)) == "volume=2.5dB"


def test_track_normalize_adds_loudnorm():
    frag = track_filter_fragment(_track(normalize=True))
    assert frag.startswith("loudnorm=I=-16:TP=-1.5:LRA=11")


def test_track_gain_and_normalize_combined():
    frag = track_filter_fragment(_track(gain_db=-2.0, normalize=True))
    assert frag == "volume=-2dB,loudnorm=I=-16:TP=-1.5:LRA=11"


# ---- duck_filter_fragment ----

def test_duck_filter_fragment_syntax():
    frag = duck_filter_fragment("[track0]", "[duckref]", "duck_A1")
    assert frag.startswith("[track0][duckref]sidechaincompress=")
    assert frag.endswith("[duck_A1]")
    assert f"threshold={DUCK_THRESHOLD}" in frag
    assert f"ratio={DUCK_RATIO}" in frag


# ---- waveform ----

pytestmark_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg kurulu değil")


@pytestmark_ffmpeg
def test_generate_waveform_peaks_for_tone(tmp_path):
    path = tmp_path / "tone.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
         "-i", "sine=frequency=440:duration=2", str(path)],
        check=True, capture_output=True,
    )
    peaks = generate_waveform_peaks(path, peaks_per_second=10)
    assert peaks is not None
    assert len(peaks) >= 15  # ~2sn * 10/sn
    assert all(0.0 <= p <= 1.0 for p in peaks)
    assert max(peaks) > 0.1  # sinüs sinyali sessiz olmamalı


@pytestmark_ffmpeg
def test_generate_waveform_peaks_is_cached(tmp_path):
    path = tmp_path / "tone.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
         "-i", "sine=frequency=220:duration=1", str(path)],
        check=True, capture_output=True,
    )
    first = generate_waveform_peaks(path, peaks_per_second=10)
    second = generate_waveform_peaks(path, peaks_per_second=10)
    assert first == second


def test_generate_waveform_peaks_missing_file_returns_none(tmp_path):
    assert generate_waveform_peaks(tmp_path / "yok.wav") is None
