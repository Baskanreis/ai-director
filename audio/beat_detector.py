"""Lightweight audio beat detection without librosa.

The detector is deliberately conservative and optional. It uses FFmpeg to
decode mono PCM and NumPy to estimate an onset envelope, then selects a BPM
from autocorrelation. It is not intended to replace a dedicated MIR library.
"""
from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import numpy as np


def estimate_bpm_from_samples(
    samples: np.ndarray,
    sample_rate: int,
    min_bpm: float = 70.0,
    max_bpm: float = 180.0,
) -> float | None:
    x = np.asarray(samples, dtype=np.float32).reshape(-1)
    if sample_rate <= 0 or x.size < sample_rate * 2:
        return None
    x = x - float(np.mean(x))
    # 20 ms RMS frames, then positive spectral/energy changes.
    frame = max(128, int(sample_rate * 0.02))
    count = 1 + (len(x) - frame) // frame
    if count < 32:
        return None
    rms = np.array(
        [np.sqrt(np.mean(x[i * frame:(i + 1) * frame] ** 2) + 1e-12) for i in range(count)]
    )
    onset = np.maximum(0.0, np.diff(rms, prepend=rms[0]))
    onset -= onset.mean()
    onset = np.maximum(onset, 0)
    if np.allclose(onset, 0):
        return None
    fps = sample_rate / frame
    lo_lag = max(1, int(round(fps * 60.0 / max_bpm)))
    hi_lag = max(lo_lag + 1, int(round(fps * 60.0 / min_bpm)))
    if hi_lag >= len(onset):
        hi_lag = len(onset) - 1
    scores = []
    for lag in range(lo_lag, hi_lag + 1):
        scores.append((float(np.dot(onset[lag:], onset[:-lag])), lag))
    if not scores:
        return None
    score, lag = max(scores)
    if score <= 0:
        return None
    bpm = 60.0 * fps / lag
    # Prefer the musically common double/half-time equivalent only when it
    # falls into the requested range.
    while bpm < min_bpm:
        bpm *= 2.0
    while bpm > max_bpm:
        bpm /= 2.0
    return round(float(bpm), 2)


def detect_beats_from_samples(
    samples: np.ndarray,
    sample_rate: int,
    bpm: float | None = None,
    threshold: float = 1.35,
) -> list[float]:
    x = np.asarray(samples, dtype=np.float32).reshape(-1)
    if sample_rate <= 0 or x.size < sample_rate:
        return []
    frame = max(128, int(sample_rate * 0.02))
    count = 1 + (len(x) - frame) // frame
    rms = np.array(
        [np.sqrt(np.mean(x[i * frame:(i + 1) * frame] ** 2) + 1e-12) for i in range(count)]
    )
    onset = np.maximum(0.0, np.diff(rms, prepend=rms[0]))
    if onset.size < 3 or np.max(onset) <= 0:
        return []
    med = float(np.median(onset))
    mad = float(np.median(np.abs(onset - med))) + 1e-9
    gate = med + threshold * mad
    min_gap = 0.12
    if bpm:
        min_gap = max(min_gap, 30.0 / float(bpm))
    peaks: list[int] = []
    for i in range(1, len(onset) - 1):
        if onset[i] >= gate and onset[i] >= onset[i - 1] and onset[i] >= onset[i + 1]:
            t = i * frame / sample_rate
            if not peaks or t - peaks[-1] >= min_gap:
                peaks.append(t)
    return [round(float(t), 4) for t in peaks]


def read_wav_mono(path: str | Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        rate = wf.getframerate()
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        frames = wf.readframes(wf.getnframes())
    if width == 2:
        x = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 4:
        x = np.frombuffer(frames, dtype="<i4").astype(np.float32) / 2147483648.0
    elif width == 1:
        x = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128) / 128.0
    else:
        raise ValueError("Desteklenmeyen WAV sample genişliği")
    if channels > 1:
        x = x.reshape(-1, channels).mean(axis=1)
    return x, rate


def detect_audio_beats(path: str | Path, ffmpeg: str = "ffmpeg") -> dict:
    """Decode audio through FFmpeg and return BPM + detected beat times."""
    cmd = [
        ffmpeg, "-v", "error", "-i", str(path), "-vn",
        "-ac", "1", "-ar", "22050", "-f", "f32le", "pipe:1",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", "replace").strip() or "FFmpeg ses çözemedi.")
    samples = np.frombuffer(proc.stdout, dtype=np.float32)
    bpm = estimate_bpm_from_samples(samples, 22050)
    beats = detect_beats_from_samples(samples, 22050, bpm=bpm)
    return {
        "bpm": bpm,
        "beats": beats,
        "sample_rate": 22050,
        "beat_count": len(beats),
        "engine_version": "2.6",
    }


__all__ = [
    "estimate_bpm_from_samples", "detect_beats_from_samples",
    "read_wav_mono", "detect_audio_beats",
]
