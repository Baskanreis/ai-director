"""Production FFmpeg renderer for Shorts Remix plans.

Features:
- 9:16 platform presets
- real ``-progress pipe:1`` progress reporting
- cancellation support
- atomic output (partial files are removed on failure/cancel)
- optional hardware H.264 encoder when available
- non-destructive source handling
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import time
import html
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .remix import RemixPlan
from .autoframe import analyze_segment_focus
from app.subtitle.models import Segment, Word
from app.subtitle.style import get_preset
from app.subtitle.ass_format import to_ass
from app.runtime.ffmpeg import executable as ffmpeg_executable


@dataclass(frozen=True)
class ShortsRenderPreset:
    name: str
    width: int
    height: int
    fps: int
    crf: int
    audio_bitrate: str


PRESETS = {
    "youtube_shorts": ShortsRenderPreset("YouTube Shorts", 1080, 1920, 30, 18, "192k"),
    "tiktok": ShortsRenderPreset("TikTok", 1080, 1920, 30, 18, "192k"),
    "instagram_reel": ShortsRenderPreset("Instagram Reels", 1080, 1920, 30, 18, "192k"),
}


class RemixRenderCancelled(RuntimeError):
    """Raised when the user cancels a Remix render."""


def _ffmpeg() -> str:
    return ffmpeg_executable()


def _encoder(ffmpeg: str) -> tuple[str, list[str]]:
    """Select a tested hardware encoder; fall back to CPU x264 safely."""
    try:
        probe = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=8)
        text = probe.stdout + probe.stderr
    except Exception:
        text = ""
    candidates = (
        ("h264_nvenc", ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "20"]),
        ("h264_qsv", ["-c:v", "h264_qsv", "-global_quality", "20"]),
        ("h264_amf", ["-c:v", "h264_amf", "-quality", "quality"]),
    )
    for name, args in candidates:
        if name not in text:
            continue
        try:
            test = subprocess.run(
                [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=16x16:r=2",
                 "-t", "0.1", *args, "-f", "null", "-"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
            )
            if test.returncode == 0:
                return name, args
        except Exception:
            pass
    return "libx264", ["-c:v", "libx264", "-preset", "medium", "-crf", "18"]


def _write_ass(cues: list[dict], path: Path, style_name: str = "bold_hook") -> None:
    """Render Shorts captions through the shared Typography/ASS engine."""
    style = get_preset(style_name)
    segments: list[Segment] = []
    for cue in cues:
        start = float(cue.get("start", 0.0))
        end = max(start + 0.05, float(cue.get("end", start + 0.1)))
        text = str(cue.get("text", "")).strip()
        if not text:
            continue
        # When only cue-level emphasis words are available, synthesize lightweight
        # word timing across the cue so the shared ASS engine can render real
        # per-word highlight tags. Whisper word timings are still preferred when
        # a full Transcript is available elsewhere in the pipeline.
        tokens = [t for t in text.split() if t]
        words: list[Word] = []
        if tokens:
            span = max(end - start, 0.05)
            step = span / len(tokens)
            for i, token in enumerate(tokens):
                ws = start + i * step
                we = end if i == len(tokens) - 1 else start + (i + 1) * step
                words.append(Word(token, ws, we))
        segments.append(Segment(text, start, end, words))
    highlighted = {str(w).strip().lower() for cue in cues for w in cue.get("emphasis_words", []) if str(w).strip()}
    path.write_text(to_ass(segments, style, always_highlight=highlighted), encoding="utf-8")


def render_remix(
    source: str | Path,
    plan: RemixPlan,
    output: str | Path,
    *,
    width: int | None = None,
    height: int | None = None,
    crf: int | None = None,
    preset: str = "medium",
    on_progress: Callable[[float, str], None] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
    caption_cues: list[dict] | None = None,
    caption_style: str = "bold_hook",
    dynamic_captions: bool = True,
    smart_reframe: bool = True,
) -> Path:
    """Render a RemixPlan to a vertical MP4 with real progress and cancellation."""
    if not plan.segments:
        raise ValueError("Render edilecek Remix bölümü yok.")
    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(f"Kaynak video bulunamadı: {source}")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    profile = PRESETS.get(plan.target, PRESETS["youtube_shorts"])
    width = width or profile.width
    height = height or profile.height
    crf = crf or profile.crf
    ffmpeg = _ffmpeg()
    encoder_name, encoder_args = _encoder(ffmpeg)
    temp_output = output.with_name(output.stem + ".rendering" + output.suffix)
    temp_output.unlink(missing_ok=True)
    ass_path: Path | None = None
    if dynamic_captions and caption_cues:
        fd, ass_name = tempfile.mkstemp(prefix="aid_short_", suffix=".ass")
        os.close(fd)
        ass_path = Path(ass_name)
        _write_ass(caption_cues, ass_path, caption_style)

    filters: list[str] = []
    focus_notes = []
    for i, seg in enumerate(plan.segments):
        if smart_reframe:
            fx, fy, zoom, method = analyze_segment_focus(source, seg.source_start, seg.source_end)
            focus_notes.append(method)
        else:
            fx, fy, zoom, method = 0.5, 0.5, 1.0, "disabled"
        # Scale first, then crop around the detected focus point. This is stable and
        # deterministic per segment; the fallback remains a safe center crop.
        scale_w = int(width * max(1.0, zoom))
        scale_h = int(height * max(1.0, zoom))
        filters.append(
            f"[0:v]trim=start={seg.source_start:.3f}:end={seg.source_end:.3f},"
            f"setpts=PTS-STARTPTS,scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height}:x='(iw-ow)*{fx:.4f}':y='(ih-oh)*{fy:.4f}',setsar=1,fps={profile.fps}[v{i}]"
        )
        filters.append(
            f"[0:a]atrim=start={seg.source_start:.3f}:end={seg.source_end:.3f},"
            f"asetpts=PTS-STARTPTS,aresample=48000[a{i}]"
        )
    concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(len(plan.segments)))
    filters.append(f"{concat_inputs}concat=n={len(plan.segments)}:v=1:a=1[v][a]")
    if ass_path:
        ass_escaped = str(ass_path).replace(chr(92), "/").replace(":", r"\:")
        filters.append(f"[v]subtitles=filename='{ass_escaped}'[vcap]")
        video_map = "[vcap]"
    else:
        video_map = "[v]"

    cmd = [
        ffmpeg, "-hide_banner", "-y", "-i", str(source),
        "-filter_complex", ";".join(filters),
        "-map", video_map, "-map", "[a]",
        *encoder_args,
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", profile.audio_bitrate,
        "-movflags", "+faststart", "-progress", "pipe:1", "-nostats", str(temp_output),
    ]
    if on_progress:
        on_progress(0.0, f"Remix render başlatılıyor • {profile.name} • {encoder_name} • Smart Reframe: {" + ",".join(focus_notes) + "}")

    total = max(plan.total_duration, 0.001)
    started = time.monotonic()
    stderr_file = tempfile.NamedTemporaryFile(prefix="aid_remix_", suffix=".log", delete=False)
    stderr_path = Path(stderr_file.name)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=stderr_file, text=True, bufsize=1)
    assert proc.stdout is not None
    block: dict[str, str] = {}

    try:
        for line in proc.stdout:
            if is_cancelled and is_cancelled():
                proc.terminate()
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    proc.kill(); proc.wait(timeout=4)
                raise RemixRenderCancelled("Remix render kullanıcı tarafından iptal edildi.")
            line = line.strip()
            if not line or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key != "progress":
                block[key] = value
                continue
            out_time = block.get("out_time", "00:00:00").split(":")
            try:
                seconds = int(out_time[0]) * 3600 + int(out_time[1]) * 60 + float(out_time[2])
            except Exception:
                seconds = 0.0
            frac = min(seconds / total, 0.995)
            speed = block.get("speed", "")
            elapsed = max(time.monotonic() - started, 0.001)
            eta = ""
            if seconds > 0 and frac > 0 and frac < 1:
                eta_s = max(0.0, (total - seconds) / max(float(speed.rstrip("x")) if speed.rstrip("x") else elapsed / seconds, 0.01))
                eta = f" • kalan ~{int(eta_s)}s"
            if on_progress:
                on_progress(frac, f"Render ediliyor • %{int(frac*100)}{eta}")
            block = {}
        code = proc.wait()
        stderr_file.flush()
        stderr_file.close()
        stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        if proc.poll() is None:
            proc.kill(); proc.wait(timeout=4)
        try:
            stderr_file.flush(); stderr_file.close()
        except Exception:
            pass
        temp_output.unlink(missing_ok=True)
        if ass_path: ass_path.unlink(missing_ok=True)
        stderr_path.unlink(missing_ok=True)
        raise

    if code != 0:
        temp_output.unlink(missing_ok=True)
        if ass_path: ass_path.unlink(missing_ok=True)
        stderr_path.unlink(missing_ok=True)
        tail = "\n".join(stderr.splitlines()[-25:])
        raise RuntimeError(f"FFmpeg Remix render başarısız (kod {code}).\n{tail}")
    stderr_path.unlink(missing_ok=True)
    if ass_path: ass_path.unlink(missing_ok=True)
    if not temp_output.is_file() or temp_output.stat().st_size == 0:
        temp_output.unlink(missing_ok=True)
        raise RuntimeError("Remix render çıktı dosyası oluşturmadı.")
    os.replace(temp_output, output)
    if on_progress:
        on_progress(1.0, "Remix render tamamlandı.")
    return output
