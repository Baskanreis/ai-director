"""BRAIN — v1.4 AI PIPELINE.

İçe Aktar -> Analiz -> Transkripsiyon -> Sahne Algılama -> Kurgu Analizi ->
Kamera -> Efektler -> Altyazı -> Render zincirini, bir İŞ KUYRUĞU (`jobs.JobQueue`)
üzerinde yürüten orkestratör (`pipeline.AIPipeline`). Qt'siz çekirdek
(`jobs.py`, `pipeline.py`, `camera.py`, `effects_preset.py`) + ince bir QThread
arayüzü (`worker.PipelineWorker`).
"""
from app.brain.jobs import Job, JobQueue, JobStatus
from app.brain.pipeline import (
    PIPELINE_ORDER,
    STAGE_LABELS,
    AIPipeline,
    PipelineConfig,
    PipelineContext,
    PipelineError,
    PipelineStage,
)

__all__ = [
    "Job", "JobQueue", "JobStatus",
    "AIPipeline", "PipelineConfig", "PipelineContext", "PipelineError", "PipelineStage",
    "PIPELINE_ORDER", "STAGE_LABELS",
]
