"""AI Pipeline'ı UI'yi dondurmadan çalıştıran QThread sarmalayıcısı.

Gerçek mantık `app.brain.pipeline.AIPipeline` ve `app.brain.jobs.JobQueue`de
(Qt'siz, saf Python); bu dosya yalnızca `JobQueue`nun geri çağrılarını Qt
sinyallerine çevirir.
"""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.brain.jobs import Job, JobQueue
from app.brain.pipeline import AIPipeline, PipelineConfig, PipelineContext, PipelineStage


class PipelineWorker(QThread):
    stage_started = Signal(str, str)        # stage_value, etiket
    stage_progress = Signal(str, float, str)  # stage_value, 0..1, mesaj
    stage_finished = Signal(str, object)    # stage_value, sonuç
    stage_failed = Signal(str, str)         # stage_value, hata mesajı
    pipeline_finished = Signal(dict)        # PipelineContext.results (stage.value -> sonuç)
    pipeline_failed = Signal(str)           # en az bir aşama başarısız olduysa özet mesaj

    def __init__(self, context: PipelineContext, config: PipelineConfig, parent=None) -> None:
        super().__init__(parent)
        self._pipeline = AIPipeline(context, config)
        self._queue: JobQueue | None = None

    def request_cancel(self) -> None:
        if self._queue:
            self._queue.cancel()

    def run(self) -> None:  # noqa: D102 (Qt API)
        stage_of = self._pipeline.stage_of_job

        def on_started(job: Job) -> None:
            stage = stage_of[job.id]
            self.stage_started.emit(stage.value, job.name)

        def on_progress(job: Job) -> None:
            stage = stage_of[job.id]
            self.stage_progress.emit(stage.value, job.progress, job.message)

        def on_finished(job: Job) -> None:
            stage = stage_of[job.id]
            self.stage_finished.emit(stage.value, job.result)

        def on_failed(job: Job) -> None:
            stage = stage_of[job.id]
            self.stage_failed.emit(stage.value, job.error or "Bilinmeyen hata")

        self._queue = JobQueue(
            on_job_started=on_started, on_job_progress=on_progress,
            on_job_finished=on_finished, on_job_failed=on_failed,
        )
        # AIPipeline.build() kendi JobQueue'sunu kullanır; burada onu, sinyallere
        # bağlı kendi kuyruğumuzla değiştiriyoruz (aynı Job nesneleri).
        self._pipeline.queue = self._queue
        self._pipeline.build()
        self._queue.run_sync()

        if self._queue.any_failed():
            failed_stages = [
                stage_of[j.id].value for j in self._queue.jobs() if j.status.value == "failed"
            ]
            self.pipeline_failed.emit(f"Başarısız aşama(lar): {', '.join(failed_stages)}")
        results = {stage.value: result for stage, result in self._pipeline.context.results.items()}
        self.pipeline_finished.emit(results)


__all__ = ["PipelineWorker"]
