"""JOB QUEUE — v1.4 AI Pipeline.

Genel amaçlı, iş parçacıklarıyla çalışan bir görev kuyruğu. AI Pipeline'daki
her aşama (Import, Analysis, Transcription, ...) bir `Job` olarak kuyruğa
eklenir ve `JobQueue` bunları FIFO sırayla, arka plandaki TEK bir çalışan
iş parçacığında yürütür (aşamalar birbirine bağımlı olduğu için sıra önemlidir;
aynı kuyruk ileride bağımsız/paralel işler için de kullanılabilir).

Qt'den bağımsızdır; GUI'siz (headless) test edilebilir — ince bir QThread
sarmalayıcı (`app.brain.worker.PipelineWorker`) ayrı bir dosyada durur.
"""
from __future__ import annotations

import queue
import threading
import time
import traceback
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


ProgressCB = Callable[[float, str], None]
JobFn = Callable[[ProgressCB], Any]  # iş gövdesi: ilerleme callback'i alır, sonuç döndürür


@dataclass
class Job:
    """Kuyruğa eklenebilen tek bir iş birimi.

    `fn(report_progress)` şeklinde çağrılır; `report_progress(frac, mesaj)`
    ile 0..1 arası ilerleme ve kısa bir durum mesajı bildirebilir.
    """
    name: str
    fn: JobFn
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    message: str = ""
    result: Any = None
    error: str | None = None
    started_at: float | None = None
    finished_at: float | None = None

    @property
    def duration(self) -> float | None:
        if self.started_at is None or self.finished_at is None:
            return None
        return self.finished_at - self.started_at


class JobQueue:
    """FIFO iş kuyruğu; tek bir arka plan iş parçacığında sırayla çalışır.

    Kullanım::

        q = JobQueue(on_job_started=..., on_job_progress=..., on_job_finished=...)
        q.enqueue(job1); q.enqueue(job2)
        q.start()       # arka planda çalışmaya başlar
        q.join()        # (isteğe bağlı) kuyruk boşalana kadar bekle
        q.cancel()      # bekleyen işleri iptal et (çalışanı yarıda kesmez)

    `run_sync()`, aynı iş parçacığında (arka plan olmadan) kuyruğu tüketir;
    Qt kurulu olmayan ortamlarda testler için kullanışlıdır.
    """

    def __init__(
        self,
        on_job_started: Callable[[Job], None] | None = None,
        on_job_progress: Callable[[Job], None] | None = None,
        on_job_finished: Callable[[Job], None] | None = None,
        on_job_failed: Callable[[Job], None] | None = None,
    ) -> None:
        self._queue: queue.Queue[Job | None] = queue.Queue()
        self._jobs: list[Job] = []
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._cancelled = False
        self.on_job_started = on_job_started
        self.on_job_progress = on_job_progress
        self.on_job_finished = on_job_finished
        self.on_job_failed = on_job_failed

    def enqueue(self, job: Job) -> Job:
        with self._lock:
            self._jobs.append(job)
        self._queue.put(job)
        return job

    def jobs(self) -> list[Job]:
        with self._lock:
            return list(self._jobs)

    def start(self) -> None:
        """Arka planda, ayrı bir iş parçacığında kuyruğu tüketmeye başlar."""
        if self._thread and self._thread.is_alive():
            return
        self._cancelled = False
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def run_sync(self) -> None:
        """Mevcut iş parçacığında (arka plan olmadan) kuyruk boşalana kadar çalıştırır."""
        self._cancelled = False
        self._run_loop()

    def cancel(self) -> None:
        """Henüz başlamamış işleri iptal eder; o an çalışan iş tamamlanır."""
        self._cancelled = True
        with self._lock:
            for job in self._jobs:
                if job.status == JobStatus.PENDING:
                    job.status = JobStatus.CANCELLED

    def join(self, timeout: float | None = None) -> None:
        if self._thread:
            self._thread.join(timeout)

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def all_done(self) -> bool:
        return all(j.status in (JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED) for j in self.jobs())

    def any_failed(self) -> bool:
        return any(j.status == JobStatus.FAILED for j in self.jobs())

    def _run_loop(self) -> None:
        while True:
            try:
                job = self._queue.get_nowait()
            except queue.Empty:
                return
            if job is None:
                return
            if self._cancelled:
                if job.status == JobStatus.PENDING:
                    job.status = JobStatus.CANCELLED
                continue
            if job.status == JobStatus.CANCELLED:
                continue
            self._execute(job)

    def _execute(self, job: Job) -> None:
        job.status = JobStatus.RUNNING
        job.started_at = time.monotonic()
        if self.on_job_started:
            self.on_job_started(job)

        def progress(frac: float, message: str = "") -> None:
            job.progress = min(max(frac, 0.0), 1.0)
            if message:
                job.message = message
            if self.on_job_progress:
                self.on_job_progress(job)

        try:
            job.result = job.fn(progress)
            job.status = JobStatus.DONE
            job.progress = 1.0
            job.finished_at = time.monotonic()
            if self.on_job_finished:
                self.on_job_finished(job)
        except Exception as exc:  # pragma: no cover - genel yakalama kasıtlı: bir aşama patlasa bile kuyruk bilgilendirilir
            job.status = JobStatus.FAILED
            job.error = f"{exc}\n{traceback.format_exc(limit=3)}"
            job.finished_at = time.monotonic()
            if self.on_job_failed:
                self.on_job_failed(job)


__all__ = ["Job", "JobStatus", "JobQueue", "ProgressCB", "JobFn"]
