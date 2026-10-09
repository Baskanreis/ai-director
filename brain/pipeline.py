"""AI PIPELINE — v1.4.

    İçe Aktar (Import) -> Analiz (Analysis) -> Transkripsiyon (Transcription)
    -> Sahne Algılama (Scene Detection) -> Kurgu Analizi (Edit Analysis)
    -> Kamera (Camera) -> Efektler (Effects) -> Altyazı (Subtitle) -> Render

Bu modül SAF PYTHON'dur (Qt'ye bağlı değildir) ve her aşamayı
`app.brain.jobs.Job` olarak `app.brain.jobs.JobQueue`ya ekler — yani AI
Pipeline, kendi İŞ KUYRUĞU üzerine kuruludur. UI sarmalayıcısı:
`app.brain.worker.PipelineWorker` (QThread).

Her aşama, projedeki TEK bir video klibi (`clip_id`) ve onun kaynak medya
dosyası (`media_path`) üzerinde çalışır; yalnızca son aşama (Render) tüm
timeline'ı dışa aktarır. Aşamalar, zaten var olan alt sistemleri
(`app.subtitle.transcribe`, `app.scene.detector`, `app.ai.analyzer`,
`app.export.ffmpeg_export`) ve bu sürümde eklenen KEYFRAME ENGINE'i
(`app.brain.camera`, `app.brain.effects_preset`) yeniden kullanır.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.brain.camera import apply_camera_plan, plan_camera_keyframes
from app.brain.effects_preset import apply_effects_preset
from app.brain.jobs import Job, JobQueue
from app.timeline.model import Timeline

if TYPE_CHECKING:
    from app.export.command_builder import ExportSettings


class PipelineError(RuntimeError):
    pass


class PipelineStage(str, Enum):
    IMPORT = "import"
    ANALYSIS = "analysis"
    TRANSCRIPTION = "transcription"
    SCENE_DETECTION = "scene_detection"
    EDIT_ANALYSIS = "edit_analysis"
    CAMERA = "camera"
    EFFECTS = "effects"
    SUBTITLE = "subtitle"
    RENDER = "render"


STAGE_LABELS: dict[PipelineStage, str] = {
    PipelineStage.IMPORT: "İçe Aktar",
    PipelineStage.ANALYSIS: "Analiz",
    PipelineStage.TRANSCRIPTION: "Transkripsiyon",
    PipelineStage.SCENE_DETECTION: "Sahne Algılama",
    PipelineStage.EDIT_ANALYSIS: "Kurgu Analizi",
    PipelineStage.CAMERA: "Kamera",
    PipelineStage.EFFECTS: "Efektler",
    PipelineStage.SUBTITLE: "Altyazı",
    PipelineStage.RENDER: "Render",
}

PIPELINE_ORDER: tuple[PipelineStage, ...] = tuple(STAGE_LABELS.keys())


@dataclass
class PipelineConfig:
    language: str = "tr"
    model_size: str = "small"
    scene_threshold: float = 0.4
    camera_style: str = "kenburns"      # bkz. app.brain.camera.CAMERA_STYLES
    effects_preset: str = "none"        # bkz. app.brain.effects_preset.EFFECTS_PRESETS
    write_subtitle_file: bool = True
    subtitle_format: str = "srt"        # "srt" | "vtt"
    subtitle_style: str = "modern_bold" # ASS burn-in style when rendering
    run_transcription: bool = True
    run_scene_detection: bool = True
    run_edit_analysis: bool = True
    run_camera: bool = True
    run_effects: bool = True
    run_subtitle: bool = True
    run_render: bool = False            # varsayılan kapalı: export_settings gerektirir
    export_settings: "ExportSettings | None" = None
    output_dir: str | None = None

    def enabled_stages(self) -> list[PipelineStage]:
        flags = {
            PipelineStage.IMPORT: True,
            PipelineStage.ANALYSIS: True,
            PipelineStage.TRANSCRIPTION: self.run_transcription,
            PipelineStage.SCENE_DETECTION: self.run_scene_detection,
            PipelineStage.EDIT_ANALYSIS: self.run_edit_analysis,
            PipelineStage.CAMERA: self.run_camera,
            PipelineStage.EFFECTS: self.run_effects,
            PipelineStage.SUBTITLE: self.run_subtitle,
            PipelineStage.RENDER: self.run_render,
        }
        return [s for s in PIPELINE_ORDER if flags[s]]


@dataclass
class PipelineContext:
    """Aşamalar arasında paylaşılan, biriken durum."""
    timeline: Timeline
    clip_id: str
    media_path: str
    media_paths: dict[str, str] = field(default_factory=dict)  # render için: media_id -> yol
    ffmpeg_exe: str | None = None
    results: dict[PipelineStage, Any] = field(default_factory=dict)

    @property
    def clip(self):
        found = self.timeline.find(self.clip_id)
        if not found:
            raise PipelineError(f"Klip bulunamadı: {self.clip_id}")
        return found[1]


# ---- aşama uygulamaları -----------------------------------------------------

def _stage_import(ctx: PipelineContext, _config: PipelineConfig, progress) -> dict:
    progress(0.2, "Dosya kontrol ediliyor…")
    p = Path(ctx.media_path)
    if not p.is_file():
        raise PipelineError(f"Medya dosyası bulunamadı: {p}")
    from app.video.media_info import probe_media

    progress(0.6, "Medya bilgisi okunuyor…")
    info = probe_media(p, thumbnail=False)
    progress(1.0, "Tamam")
    return {
        "duration": info.duration, "width": info.width, "height": info.height,
        "has_audio": info.has_audio, "codec": info.codec,
    }


def _stage_analysis(ctx: PipelineContext, _config: PipelineConfig, progress) -> dict:
    progress(0.5, "Teknik özellikler değerlendiriliyor…")
    imp = ctx.results.get(PipelineStage.IMPORT) or {}
    out = {
        "source_duration": imp.get("duration", ctx.clip.duration),
        "clip_duration": ctx.clip.duration,
        "has_audio": imp.get("has_audio", True),
    }
    progress(1.0, "Tamam")
    return out


def _stage_transcription(ctx: PipelineContext, config: PipelineConfig, progress):
    from app.subtitle.transcribe import SubtitleError, transcribe

    try:
        return transcribe(
            ctx.media_path, language=config.language, model_size=config.model_size,
            on_progress=lambda frac, msg: progress(frac, msg),
        )
    except SubtitleError as exc:
        progress(1.0, f"Atlandı: {exc}")
        return None


def _stage_scene_detection(ctx: PipelineContext, config: PipelineConfig, progress) -> list[float]:
    from app.scene.detector import SceneDetectionError, detect_scene_changes

    progress(0.2, "Sahneler taranıyor…")
    try:
        times = detect_scene_changes(ctx.media_path, threshold=config.scene_threshold, ffmpeg_exe=ctx.ffmpeg_exe)
    except SceneDetectionError as exc:
        progress(1.0, f"Atlandı: {exc}")
        return []
    progress(1.0, f"{len(times)} sahne kesimi bulundu")
    return times


def _stage_edit_analysis(ctx: PipelineContext, config: PipelineConfig, progress):
    from app.ai.analyzer import build_report

    transcript = ctx.results.get(PipelineStage.TRANSCRIPTION)
    progress(0.3, "Öneriler oluşturuluyor…")
    report = build_report(
        ctx.clip_id, ctx.media_path, transcript, language=config.language,
        include_silence=True, include_scenes=False, ffmpeg_exe=ctx.ffmpeg_exe,
    )
    progress(1.0, f"{len(report.suggestions)} öneri")
    return report


def _stage_camera(ctx: PipelineContext, config: PipelineConfig, progress) -> dict:
    progress(0.3, "Kamera hareketi planlanıyor…")
    scene_times = ctx.results.get(PipelineStage.SCENE_DETECTION) or []
    plan = plan_camera_keyframes(ctx.clip.duration, scene_times, style=config.camera_style)
    apply_camera_plan(ctx.clip, plan)
    progress(1.0, "Tamam")
    return {"style": config.camera_style, "properties": list(plan.keys())}


def _stage_effects(ctx: PipelineContext, config: PipelineConfig, progress) -> dict:
    progress(0.3, f"'{config.effects_preset}' ön ayarı uygulanıyor…")
    applied = apply_effects_preset(ctx.clip, config.effects_preset)
    progress(1.0, "Tamam")
    return applied


def _stage_subtitle(ctx: PipelineContext, config: PipelineConfig, progress) -> str | None:
    transcript = ctx.results.get(PipelineStage.TRANSCRIPTION)
    if transcript is None or not getattr(transcript, "segments", None):
        progress(1.0, "Transkript yok, atlandı")
        return None
    from app.subtitle.ass_format import to_ass
    from app.subtitle.formats import to_srt, to_vtt
    from app.subtitle.style import get_preset

    progress(0.35, "Altyazı metni oluşturuluyor…")
    text = to_srt(transcript.segments) if config.subtitle_format == "srt" else to_vtt(transcript.segments)
    out_dir = Path(config.output_dir) if config.output_dir else Path(ctx.media_path).parent
    # Render açıkken ASS dosyası export filtergraph'ına bağlanacağı için,
    # `write_subtitle_file=False` olsa bile geçici/çıktı yanında bir ASS gerekir.
    needs_render_ass = bool(config.run_render and config.export_settings is not None)
    if not config.write_subtitle_file and not needs_render_ass:
        progress(1.0, "Tamam (dosyaya yazılmadı)")
        return text

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(ctx.media_path).stem
    out_path = out_dir / f"{stem}.{config.subtitle_format}"
    if config.write_subtitle_file:
        out_path.write_text(text, encoding="utf-8")

    if needs_render_ass:
        ass_path = out_dir / f"{stem}.ai_director.ass"
        ass_path.write_text(to_ass(transcript.segments, get_preset(config.subtitle_style)), encoding="utf-8")
        # ExportSettings immutable/yeniden kullanilabilir kabul edilir; mevcut
        # nesneyi yan etkili değiştirmek yerine yalnızca bu pipeline için kopyala.
        config.export_settings = replace(config.export_settings, subtitle_path=str(ass_path))
        progress(0.85, f"Render altyazı katmanı hazır: {ass_path.name}")

    progress(1.0, f"Yazıldı: {out_path.name}" if config.write_subtitle_file else "Render altyazı katmanı hazır")
    return str(out_path) if config.write_subtitle_file else text


def _stage_render(ctx: PipelineContext, config: PipelineConfig, progress) -> str:
    from app.export.ffmpeg_export import ExportCancelled, ExportError, export_timeline

    if config.export_settings is None:
        raise PipelineError("Render için PipelineConfig.export_settings gerekli")
    try:
        out = export_timeline(
            ctx.timeline, ctx.media_paths, config.export_settings,
            on_progress=lambda frac, msg: progress(frac, msg),
        )
    except ExportCancelled as exc:
        raise PipelineError("Render iptal edildi") from exc
    except ExportError as exc:
        raise PipelineError(f"Render başarısız: {exc}") from exc
    return str(out)


_STAGE_FUNCS = {
    PipelineStage.IMPORT: _stage_import,
    PipelineStage.ANALYSIS: _stage_analysis,
    PipelineStage.TRANSCRIPTION: _stage_transcription,
    PipelineStage.SCENE_DETECTION: _stage_scene_detection,
    PipelineStage.EDIT_ANALYSIS: _stage_edit_analysis,
    PipelineStage.CAMERA: _stage_camera,
    PipelineStage.EFFECTS: _stage_effects,
    PipelineStage.SUBTITLE: _stage_subtitle,
    PipelineStage.RENDER: _stage_render,
}


class AIPipeline:
    """`PipelineContext` + `PipelineConfig`den bir `JobQueue` inşa eder ve çalıştırır.

    Her `Job.fn`, karşılık gelen aşama fonksiyonunu çağırır, sonucu
    `ctx.results[stage]`e yazar (bir sonraki aşamalar bunu okuyabilsin diye)
    ve aşamanın adını/etiketini taşır.
    """

    def __init__(self, context: PipelineContext, config: PipelineConfig | None = None) -> None:
        self.context = context
        self.config = config or PipelineConfig()
        self.stage_of_job: dict[str, PipelineStage] = {}
        self.queue = JobQueue()

    def build(self) -> JobQueue:
        for stage in self.config.enabled_stages():
            job = Job(name=STAGE_LABELS[stage], fn=self._make_runner(stage))
            self.stage_of_job[job.id] = stage
            self.queue.enqueue(job)
        return self.queue

    def _make_runner(self, stage: PipelineStage):
        func = _STAGE_FUNCS[stage]

        def run(progress):
            result = func(self.context, self.config, progress)
            self.context.results[stage] = result
            return result

        return run

    def run_sync(self) -> JobQueue:
        """Pipeline'ı eşzamanlı (mevcut iş parçacığında) çalıştırır; test/CLI için."""
        self.build()
        self.queue.run_sync()
        return self.queue


__all__ = [
    "PipelineError", "PipelineStage", "STAGE_LABELS", "PIPELINE_ORDER",
    "PipelineConfig", "PipelineContext", "AIPipeline",
]
