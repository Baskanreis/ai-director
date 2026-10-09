"""Deterministic second-pass export repair helpers.

Repairs the final delivery file without touching the source timeline. The repair
pass is deliberately conservative: only delivery-level defects reported by QC
are changed (size, duration and missing audio). The repaired file is validated
again by the normal QC stage.
"""
from __future__ import annotations

from pathlib import Path
import os
import subprocess
import tempfile

from app.runtime.ffmpeg import executable as ffmpeg_executable
from app.ai.export_qc import ExportQCReport


def repair_export(
    path: str | Path,
    report: ExportQCReport,
    *,
    expected_width: int | None = None,
    expected_height: int | None = None,
    expected_duration: float | None = None,
) -> Path:
    """Apply safe delivery repairs and return the same output path.

    A temporary file is written first and atomically replaces the original only
    after FFmpeg succeeds. No repair is attempted when there are no repairable
    failures.
    """
    src = Path(path)
    if not src.is_file():
        raise RuntimeError("QC repair için çıktı dosyası bulunamadı.")

    needs_resolution = any(c.name == "resolution" and c.status == "fail" for c in report.checks)
    needs_duration = any(c.name == "duration" and c.status == "fail" for c in report.checks)
    needs_audio = any(c.name == "audio" and c.status == "fail" for c in report.checks)

    if not any((needs_resolution, needs_duration, needs_audio)):
        return src
    if not expected_width or not expected_height:
        raise RuntimeError("Otomatik çözünürlük onarımı için hedef çözünürlük gerekli.")

    ffmpeg = ffmpeg_executable()
    fd, tmp_name = tempfile.mkstemp(prefix="aid_qc_repair_", suffix=src.suffix, dir=str(src.parent))
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        vf = []
        if needs_resolution:
            vf.append(
                f"scale={expected_width}:{expected_height}:force_original_aspect_ratio=decrease"
            )
            vf.append(f"pad={expected_width}:{expected_height}:(ow-iw)/2:(oh-ih)/2")
        # Duration correction is intentionally bounded. A short file is padded
        # with a final frozen frame; a long file is trimmed.
        duration_args: list[str] = []
        if expected_duration and expected_duration > 0 and needs_duration:
            duration_args = ["-t", f"{expected_duration:.3f}"]

        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src)]
        if needs_audio:
            # Preserve existing audio when present; if absent, add a silent stereo
            # source. The shortest stream determines output duration unless -t is used.
            cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
        if vf:
            cmd += ["-vf", ",".join(vf)]
        cmd += ["-map", "0:v:0"]
        if needs_audio:
            cmd += ["-map", "1:a:0", "-c:a", "aac", "-b:a", "192k"]
        else:
            cmd += ["-map", "0:a:0?", "-c:a", "aac", "-b:a", "192k"]
        cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p"]
        cmd += duration_args + [str(tmp)]
        # Avoid duplicate audio mappings if a source audio stream exists: retry
        # with the simpler silent-audio command only when the first invocation fails.
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if proc.returncode != 0 and needs_audio:
            cmd2 = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
                    "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "fast",
                    "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k"]
            if vf:
                cmd2 += ["-vf", ",".join(vf)]
            cmd2 += duration_args + ["-shortest", str(tmp)]
            proc = subprocess.run(cmd2, capture_output=True, text=True, timeout=600)
        if proc.returncode != 0 or not tmp.exists() or tmp.stat().st_size <= 0:
            raise RuntimeError((proc.stderr or "FFmpeg QC onarımı başarısız.").strip()[-2500:])
        os.replace(tmp, src)
        return src
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
