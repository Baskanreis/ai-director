"""Professional render controller: validation, preview and queued final render."""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from app.export.command_builder import BuildError, ExportSettings, build_export_command, available_hardware_acceleration
from app.export.ffmpeg_export import RenderProgress, export_timeline
from app.timeline.model import Timeline
from .director_pipeline import collect_timeline_captions
from .karaoke import write_karaoke_ass
from .unified_pipeline import RenderOptions


@dataclass(frozen=True)
class RenderValidation:
    ok: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class RenderJob:
    timeline: Timeline
    media_paths: dict[str, str]
    settings: ExportSettings
    options: RenderOptions | None = None


class RenderController:
    """Owns the render lifecycle without duplicating FFmpeg execution logic."""

    def __init__(self, ffmpeg: str | None = None):
        self.ffmpeg = ffmpeg or "ffmpeg"

    def validate(self, job: RenderJob) -> RenderValidation:
        errors: list[str] = []
        warnings: list[str] = []
        try:
            video = job.timeline.first_track("video")
            if not video.sorted_clips():
                errors.append("Timeline'da video klibi yok.")
        except Exception as exc:
            errors.append(f"Timeline doğrulanamadı: {exc}")
        for track in job.timeline.tracks:
            for clip in track.clips:
                path = job.media_paths.get(clip.media_id)
                if not path or not Path(path).is_file():
                    errors.append(f"Kaynak bulunamadı: {clip.media_id} ({clip.name})")
        if job.settings.width <= 0 or job.settings.height <= 0:
            errors.append("Çıkış çözünürlüğü geçersiz.")
        if job.settings.fps <= 0:
            errors.append("FPS geçersiz.")
        try:
            options = job.options or RenderOptions(captions=collect_timeline_captions(job.timeline))
            build_export_command(self.ffmpeg, job.timeline, job.media_paths, job.settings, options)
        except BuildError as exc:
            errors.append(str(exc))
        return RenderValidation(not errors, tuple(errors), tuple(warnings))

    def prepare_options(self, job: RenderJob, work_dir: str | Path) -> RenderOptions:
        options = job.options or RenderOptions(captions=collect_timeline_captions(job.timeline))
        work = Path(work_dir); work.mkdir(parents=True, exist_ok=True)
        if options.captions and not options.ass_path:
            ass = work / "captions_karaoke.ass"
            write_karaoke_ass(options.captions, ass, style=options.caption_style,
                              always_highlight=options.always_highlight)
            options = replace(options, ass_path=str(ass))
        return options

    def render(
        self, job: RenderJob, *, work_dir: str | Path | None = None,
        on_progress: Callable[[float, str], None] | None = None,
        on_progress_detail: Callable[[RenderProgress], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> Path:
        validation = self.validate(job)
        if not validation.ok:
            raise BuildError("; ".join(validation.errors))
        options = self.prepare_options(job, work_dir or Path(job.settings.output_path).parent / ".render")
        return export_timeline(job.timeline, job.media_paths, job.settings,
                               on_progress=on_progress,
                               on_progress_detail=on_progress_detail,
                               is_cancelled=is_cancelled,
                               render_options=options)

    def render_profile(self, preferred: str = "auto") -> dict[str, object]:
        """Describe the encoder path that will be used by this controller."""
        available = available_hardware_acceleration(self.ffmpeg)
        mode = preferred.lower()
        if mode == "auto":
            mode = "nvidia" if "nvidia" in available else ("videotoolbox" if "videotoolbox" in available else "cpu")
        if mode not in available:
            mode = "cpu"
        return {"hardware_accel": mode, "available": available, "preview_supported": True}

    def preview_job(self, job: RenderJob, output_path: str | Path) -> RenderJob:
        """Create a low-quality preview job using the exact same filtergraph."""
        w = min(job.settings.width, 540)
        h = max(1, round(job.settings.height * w / job.settings.width))
        settings = replace(job.settings, output_path=str(output_path), width=w, height=h,
                            crf=30, video_bitrate="2M", preset_name="Preview")
        return replace(job, settings=settings)


class RenderQueue:
    """Deterministic FIFO render queue; jobs execute sequentially."""

    def __init__(self, controller: RenderController | None = None):
        self.controller = controller or RenderController()
        self.jobs: list[RenderJob] = []

    def add(self, job: RenderJob) -> None:
        self.jobs.append(job)

    def clear(self) -> None:
        self.jobs.clear()

    def run(self, on_job: Callable[[int, int, Path], None] | None = None) -> list[Path]:
        outputs: list[Path] = []
        total = len(self.jobs)
        for index, job in enumerate(self.jobs, 1):
            output = self.controller.render(job)
            outputs.append(output)
            if on_job:
                on_job(index, total, output)
        return outputs
