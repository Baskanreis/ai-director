"""Visual/audio delivery QC for rendered videos.

The checks are intentionally conservative: they flag likely problems without
pretending to understand creative intent. OpenCV is optional; when unavailable
or a codec cannot be decoded, the structural FFprobe QC remains authoritative.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import math
import subprocess

from app.runtime.ffmpeg import executable as ffmpeg_executable

@dataclass(frozen=True)
class VisualCheck:
    name: str
    status: str  # pass / warning / fail / skipped
    message: str
    value: float | str | None = None

@dataclass(frozen=True)
class VisualQCReport:
    path: str
    checks: list[VisualCheck]
    score: float
    passed: bool
    samples: int = 0

    def to_dict(self):
        return {"path": self.path, "checks": [asdict(c) for c in self.checks],
                "score": self.score, "passed": self.passed, "samples": self.samples}


def _sample_times(duration: float, count: int = 12) -> list[float]:
    if duration <= 0:
        return [0.0]
    count = max(3, min(count, int(duration * 2) + 1))
    return [duration * i / (count - 1) for i in range(count)]


def inspect_visual_export(path: str | Path, *, expected_duration: float | None = None,
                          sample_count: int = 12) -> VisualQCReport:
    p = Path(path)
    if not p.is_file() or p.stat().st_size <= 0:
        return VisualQCReport(str(p), [VisualCheck("file", "fail", "Görüntü QC için çıktı yok")], 0.0, False, 0)
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except Exception:
        return VisualQCReport(str(p), [VisualCheck("opencv", "skipped", "OpenCV kurulu değil; yapısal QC kullanıldı")], 100.0, True, 0)

    cap = cv2.VideoCapture(str(p))
    if not cap.isOpened():
        return VisualQCReport(str(p), [VisualCheck("decode", "fail", "Video örnekleme için açılamadı")], 0.0, False, 0)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
    frames = float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = frames / fps if fps > 0 else 0.0
    times = _sample_times(duration or (expected_duration or 1.0), sample_count)
    decoded = []
    variances = []
    black = 0
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000.0)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean = float(np.mean(gray))
        dark_ratio = float(np.mean(gray < 8))
        # Laplacian variance is a useful blur/focus heuristic, not a creative score.
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        decoded.append(frame)
        variances.append(sharpness)
        if mean < 10.0 and dark_ratio > 0.92:
            black += 1
    cap.release()

    checks: list[VisualCheck] = []
    n = len(decoded)
    if n == 0:
        return VisualQCReport(str(p), [VisualCheck("decode", "fail", "Hiçbir örnek kare çözülemedi")], 0.0, False, 0)
    checks.append(VisualCheck("decode", "pass", f"{n}/{len(times)} örnek kare çözüldü", n))

    black_ratio = black / n
    if black_ratio >= 0.25:
        checks.append(VisualCheck("black_frames", "fail", f"Örneklerin %{black_ratio*100:.0f}'i neredeyse siyah", black_ratio))
    elif black_ratio > 0:
        checks.append(VisualCheck("black_frames", "warning", f"{black} siyah/çok karanlık örnek kare", black_ratio))
    else:
        checks.append(VisualCheck("black_frames", "pass", "Siyah kare belirtisi yok", 0.0))

    if len(decoded) >= 2:
        diffs = []
        for a, b in zip(decoded, decoded[1:]):
            ga = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
            gb = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)
            diffs.append(float(np.mean(cv2.absdiff(ga, gb))))
        # A completely frozen export often has near-zero changes across many samples.
        frozen_ratio = sum(d < 0.7 for d in diffs) / max(1, len(diffs))
        if frozen_ratio >= 0.65 and duration > 2:
            checks.append(VisualCheck("freeze", "warning", "Uzun süreli donmuş kare şüphesi", frozen_ratio))
        else:
            checks.append(VisualCheck("freeze", "pass", "Donmuş kare paterni bulunmadı", frozen_ratio))
    else:
        checks.append(VisualCheck("freeze", "skipped", "Yeterli örnek yok"))

    median_sharp = float(np.median(variances)) if variances else 0.0
    low_blur_ratio = sum(v < 18.0 for v in variances) / max(1, len(variances))
    if low_blur_ratio >= 0.75 and duration > 2:
        checks.append(VisualCheck("blur", "warning", "Örneklerin çoğu düşük keskinlik gösteriyor", median_sharp))
    else:
        checks.append(VisualCheck("blur", "pass", f"Medyan keskinlik {median_sharp:.1f}", median_sharp))

    if expected_duration and expected_duration > 0:
        delta = abs(duration - expected_duration)
        checks.append(VisualCheck("visual_duration", "pass" if delta <= 0.35 else "warning",
                                   f"Görüntü süresi {duration:.2f}s (fark {delta:.2f}s)", duration))

    fails = sum(c.status == "fail" for c in checks)
    warns = sum(c.status == "warning" for c in checks)
    score = max(0.0, 100.0 - fails * 40.0 - warns * 10.0)
    return VisualQCReport(str(p), checks, score, fails == 0, n)


def inspect_audio_levels(path: str | Path) -> VisualCheck:
    """Use FFmpeg volumedetect to catch obvious clipping without decoding audio in Python."""
    try:
        ffmpeg = ffmpeg_executable()
        proc = subprocess.run([ffmpeg, "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                              capture_output=True, text=True, timeout=120)
        text = (proc.stderr or "")
        peak = None
        for line in text.splitlines():
            if "max_volume:" in line:
                try:
                    peak = float(line.split("max_volume:", 1)[1].strip().split()[0])
                except ValueError:
                    pass
        if peak is None:
            return VisualCheck("audio_clipping", "skipped", "Ses seviyesi okunamadı")
        if peak >= -0.1:
            return VisualCheck("audio_clipping", "warning", f"Peak {peak:.1f} dBFS; clipping riski", peak)
        return VisualCheck("audio_clipping", "pass", f"Peak {peak:.1f} dBFS", peak)
    except Exception as exc:
        return VisualCheck("audio_clipping", "skipped", f"Ses analizi kullanılamadı: {exc}")
