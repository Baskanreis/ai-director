"""Real FFmpeg-backed proxy worker with cancellation, progress and resource admission."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Event
from subprocess import Popen, PIPE
from shutil import which
from typing import Callable, Any
import os
import tempfile

from .queue import ProxyJob, ProxyJobState
from .profile_selection import SmartProxyProfileSelector


@dataclass(frozen=True)
class ProxyProfile:
    height: int = 720
    video_codec: str = "libx264"
    crf: int = 22
    preset: str = "ultrafast"
    audio_codec: str = "aac"
    audio_bitrate: str = "128k"


class FFmpegProxyWorker:
    """Generate one proxy using FFmpeg without invoking a shell.

    The worker is intentionally independent from Qt. A UI can run it in its own
    executor/thread and consume progress callbacks. A scheduler may be injected
    to prevent proxy generation from starving interactive rendering.
    """

    def __init__(self, ffmpeg: str | None = None, scheduler: Any = None,
                 profile: ProxyProfile | None = None, selector: SmartProxyProfileSelector | None = None):
        self.ffmpeg = ffmpeg or which("ffmpeg") or "ffmpeg"
        self.scheduler = scheduler
        self.profile = profile
        self.selector = selector or SmartProxyProfileSelector()

    def selected_profile(self, job: ProxyJob) -> ProxyProfile:
        if self.profile is not None:
            return self.profile
        choice = self.selector.choose(job.metadata)
        return ProxyProfile(height=choice.height, crf=choice.crf, preset=choice.preset)

    def command(self, job: ProxyJob) -> list[str]:
        p = self.selected_profile(job)
        return [self.ffmpeg, "-hide_banner", "-nostdin", "-y", "-i", job.source,
                "-vf", f"scale=-2:{int(p.height)}:flags=bicubic",
                "-c:v", p.video_codec, "-preset", p.preset, "-crf", str(p.crf),
                "-pix_fmt", "yuv420p", "-c:a", p.audio_codec, "-b:a", p.audio_bitrate,
                "-movflags", "+faststart", "-progress", "pipe:1", "-nostats", job.output]

    @staticmethod
    def _progress_seconds(line: str) -> float | None:
        if not line.startswith("out_time_ms="):
            return None
        try:
            # FFmpeg names this field *_ms but values are microseconds in practice.
            return max(0.0, float(line.split("=", 1)[1]) / 1_000_000.0)
        except (TypeError, ValueError):
            return None

    def run(self, job: ProxyJob, *, cancel: Event | None = None,
            duration_s: float | None = None,
            progress: Callable[[float], None] | None = None) -> ProxyJob:
        cancel = cancel or Event()
        progress = progress or (lambda _p: None)
        output = Path(job.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=output.stem + ".", suffix=output.suffix, dir=str(output.parent))
        os.close(fd)
        temp = Path(temp_name)
        # FFmpeg writes to a temp path so a cancelled/failed encode never becomes
        # a seemingly valid proxy in the project cache.
        cmd = self.command(ProxyJob(job.media_id, job.source, str(temp), job.priority, job.id))
        admitted = False
        proc: Popen[str] | None = None
        try:
            if self.scheduler is not None:
                acquire = getattr(self.scheduler, "acquire_for", None)
                if acquire is not None:
                    admitted = bool(acquire(job, cancel))
                else:
                    admitted = bool(self.scheduler.acquire(cancel))
                if not admitted:
                    job.state = ProxyJobState.CANCELLED if cancel.is_set() else ProxyJobState.FAILED
                    job.error = "Proxy resource admission denied"
                    return job

            if cancel.is_set():
                job.state = ProxyJobState.CANCELLED
                return job
            job.state = ProxyJobState.RUNNING
            job.progress = 0.0
            proc = Popen(cmd, stdout=PIPE, stderr=PIPE, text=True, encoding="utf-8", errors="replace", bufsize=1)
            stderr_lines: list[str] = []
            # FFmpeg emits progress records to stdout; stderr is drained after the
            # process exits to avoid introducing a second reader thread here.
            assert proc.stdout is not None
            for line in proc.stdout:
                if cancel.is_set():
                    proc.terminate()
                    try:
                        proc.wait(timeout=2.0)
                    except Exception:
                        proc.kill(); proc.wait(timeout=2.0)
                    job.state = ProxyJobState.CANCELLED
                    return job
                seconds = self._progress_seconds(line.strip())
                if seconds is not None and duration_s and duration_s > 0:
                    value = min(0.99, seconds / float(duration_s))
                    job.progress = value
                    progress(value)
            stderr = proc.stderr.read() if proc.stderr is not None else ""
            code = proc.wait()
            if code != 0:
                job.state = ProxyJobState.FAILED
                job.error = stderr.strip()[-4000:] or f"FFmpeg exited with code {code}"
                return job
            if not temp.exists() or temp.stat().st_size <= 0:
                job.state = ProxyJobState.FAILED
                job.error = "FFmpeg completed without a valid proxy output"
                return job
            os.replace(temp, output)
            job.progress = 1.0
            progress(1.0)
            job.state = ProxyJobState.DONE
            return job
        except FileNotFoundError:
            job.state = ProxyJobState.FAILED
            job.error = "FFmpeg executable was not found"
            return job
        except Exception as exc:
            if cancel.is_set():
                job.state = ProxyJobState.CANCELLED
            else:
                job.state = ProxyJobState.FAILED
                job.error = str(exc)
            return job
        finally:
            if proc is not None and proc.poll() is None:
                try: proc.kill()
                except Exception: pass
            try:
                if temp.exists(): temp.unlink()
            except OSError:
                pass
            if admitted and self.scheduler is not None:
                try: self.scheduler.release()
                except Exception: pass
