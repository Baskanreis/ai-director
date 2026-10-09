"""Timeline'ı FFmpeg ile tek bir video dosyasına işleme (v0.6 — gerçek export motoru).

Mimari (bkz. `command_builder.py`):
- Tüm klipler (kesme/kırpma dahil) ve boşluklar tek bir `-filter_complex` grafiğinde
  ifade edilir; ara dosya üretilmez.
- Video: trim + scale/pad + fps + concat.
- Ses: her iz kendi içinde atrim + concat edilip sessizlikle boşluklar doldurulur,
  birden fazla ses izi varsa `amix` ile karıştırılır (audio mixing).
- Kodek H.264/H.265/AV1 arasından seçilebilir; sistemde kurulu ilk uygun encoder
  kullanılır (`resolve_codec`).
- Tek bir `ffmpeg` süreci `-progress pipe:1` ile çalıştırılır; ilerleme yüzdesi
  gerçek `out_time` değerinden hesaplanır, iptal `SIGTERM`/`SIGKILL` ile yapılır.
"""
from __future__ import annotations

import logging
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.performance.monitor import cpu_percent, gpu_percent
from app.runtime.ffmpeg import executable as ffmpeg_executable
from app.timeline.model import Timeline

from .command_builder import BuildError, ExportSettings, available_codecs, build_export_command

__all__ = [
    "ExportError",
    "ExportCancelled",
    "ExportSettings",
    "RenderProgress",
    "available_codecs",
    "export_timeline",
]

log = logging.getLogger(__name__)

ProgressCB = Callable[[float, str], None]  # (0..1, mesaj) — geriye donuk uyumluluk icin
# Detayli ilerleme geri cagirisi: render sirasinda FPS, bit hizi, hiz (Nx),
# tahmini kalan sure (ETA) ve CPU/GPU kullanimi gosterilebilmesi icin (v1.1).
DetailCB = Callable[["RenderProgress"], None]

_GPU_SAMPLE_INTERVAL_S = 1.0  # nvidia-smi'yi her ilerleme satirinda degil, en fazla bu sikilikta cagir
EPS_FRACTION = 1e-6


@dataclass
class RenderProgress:
    """Render sirasinda `-progress pipe:1` cikisindan turetilen anlik durum."""
    fraction: float        # 0..1 (bilinmiyorsa en son bilinen deger)
    message: str
    frame: int | None = None
    fps: float | None = None
    bitrate_kbits: float | None = None
    out_time_seconds: float | None = None
    total_duration: float = 0.0
    speed: float | None = None          # ör. 2.5 => gercek zamanin 2.5 kati hizda
    elapsed_seconds: float = 0.0
    eta_seconds: float | None = None
    cpu_percent: float | None = None
    gpu_percent: float | None = None


class ExportError(RuntimeError):
    """Export başarısız oldu."""


class ExportCancelled(ExportError):
    """Kullanıcı export'u iptal etti."""


def _require_ffmpeg() -> str:
    try:
        return ffmpeg_executable()
    except RuntimeError as exc:
        raise ExportError(str(exc)) from exc


def _parse_out_time_seconds(value: str) -> float | None:
    """`out_time=00:00:12.345678` -> 12.345678 saniye."""
    value = value.strip()
    if not value or value == "N/A":
        return None
    try:
        h, m, s = value.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    except (ValueError, IndexError):
        return None


def _parse_float(value: str) -> float | None:
    value = value.strip()
    if not value or value == "N/A":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def export_timeline(
    timeline: Timeline,
    media_paths: dict[str, str],
    settings: ExportSettings,
    on_progress: ProgressCB | None = None,
    is_cancelled: Callable[[], bool] | None = None,
    on_progress_detail: DetailCB | None = None,
) -> Path:
    """Timeline'ı tek bir ffmpeg çağrısıyla `settings.output_path`'e render eder.

    `on_progress(frac, mesaj)` geriye donuk uyumlu basit geri cagiridir.
    `on_progress_detail(RenderProgress)` ise FPS/bit hizi/hiz/ETA/CPU/GPU dahil
    tam render durumunu saglar (v1.1 Real FFmpeg Render).
    """
    ffmpeg = _require_ffmpeg()
    try:
        built = build_export_command(ffmpeg, timeline, media_paths, settings)
    except BuildError as exc:
        raise ExportError(str(exc)) from exc

    out_path = Path(settings.output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    start_time = time.monotonic()
    last_gpu_sample = 0.0
    last_gpu_value: float | None = None

    def report(frac: float, msg: str, **fields) -> None:
        frac = min(max(frac, 0.0), 1.0)
        if on_progress:
            on_progress(frac, msg)
        if on_progress_detail:
            nonlocal last_gpu_sample, last_gpu_value
            elapsed = time.monotonic() - start_time
            now = time.monotonic()
            if now - last_gpu_sample >= _GPU_SAMPLE_INTERVAL_S:
                last_gpu_value = gpu_percent()
                last_gpu_sample = now
            eta = None
            out_time = fields.get("out_time_seconds")
            if out_time is not None and frac > EPS_FRACTION and frac < 1.0 - EPS_FRACTION:
                remaining = max(built.total_duration - out_time, 0.0)
                speed = fields.get("speed")
                if speed and speed > 0:
                    eta = remaining / speed
                elif elapsed > 0 and out_time > 0:
                    eta = remaining * (elapsed / out_time)
            on_progress_detail(
                RenderProgress(
                    fraction=frac,
                    message=msg,
                    frame=fields.get("frame"),
                    fps=fields.get("fps"),
                    bitrate_kbits=fields.get("bitrate_kbits"),
                    out_time_seconds=out_time,
                    total_duration=built.total_duration,
                    speed=fields.get("speed"),
                    elapsed_seconds=elapsed,
                    eta_seconds=eta,
                    cpu_percent=cpu_percent(),
                    gpu_percent=last_gpu_value,
                )
            )

    def cancelled() -> bool:
        return bool(is_cancelled and is_cancelled())

    log.debug("ffmpeg: %s", " ".join(built.cmd))
    report(0.0, f"Başlatılıyor ({built.encoder_used})…")

    with tempfile.NamedTemporaryFile(
        prefix="aid_export_stderr_", suffix=".log", delete=False
    ) as stderr_file:
        stderr_path = Path(stderr_file.name)

    proc: subprocess.Popen | None = None
    try:
        with open(stderr_path, "w", encoding="utf-8") as errf:
            proc = subprocess.Popen(
                built.cmd, stdout=subprocess.PIPE, stderr=errf, text=True, bufsize=1
            )
            assert proc.stdout is not None
            block: dict[str, str] = {}
            for line in proc.stdout:
                if cancelled():
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=5)
                    raise ExportCancelled("Export kullanıcı tarafından iptal edildi")
                line = line.strip()
                if not line or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                if key == "progress":
                    # Blok sonu: biriken alanlari tek bir RenderProgress'e cevirip bildir.
                    out_time = _parse_out_time_seconds(block.get("out_time", ""))
                    frame_s = block.get("frame", "").strip()
                    fps_v = _parse_float(block.get("fps", ""))
                    bitrate_s = block.get("bitrate", "").strip()
                    bitrate_v = None
                    if bitrate_s and bitrate_s != "N/A":
                        bitrate_v = _parse_float(bitrate_s.replace("kbits/s", "").strip())
                    speed_s = block.get("speed", "").strip()
                    speed_v = _parse_float(speed_s.rstrip("x")) if speed_s else None
                    if value == "end":
                        report(
                            0.99, "Sonlandırılıyor…",
                            out_time_seconds=out_time, fps=fps_v,
                            bitrate_kbits=bitrate_v, speed=speed_v,
                            frame=int(frame_s) if frame_s.isdigit() else None,
                        )
                    elif out_time is not None:
                        frac = min(out_time / built.total_duration, 0.99)
                        report(
                            frac, "Render ediliyor…",
                            out_time_seconds=out_time, fps=fps_v,
                            bitrate_kbits=bitrate_v, speed=speed_v,
                            frame=int(frame_s) if frame_s.isdigit() else None,
                        )
                    block = {}
                else:
                    block[key] = value
            proc.wait()
    finally:
        if proc is not None and proc.poll() is None:
            proc.kill()

    if proc is None or proc.returncode != 0:
        tail = ""
        try:
            tail = "\n".join(stderr_path.read_text(encoding="utf-8", errors="replace")
                              .strip().splitlines()[-20:])
        finally:
            stderr_path.unlink(missing_ok=True)
        code = proc.returncode if proc is not None else -1
        raise ExportError(f"FFmpeg hata kodu {code}:\n{tail}")

    stderr_path.unlink(missing_ok=True)
    if not out_path.is_file() or out_path.stat().st_size == 0:
        raise ExportError("FFmpeg çıktı dosyası üretmedi.")

    report(1.0, "Tamamlandı")
    return out_path
