"""Threaded proxy generation service backed by ProxyQueue and FFmpegProxyWorker."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, Future
from threading import Event, RLock
from typing import Callable, Any

from .queue import ProxyJob, ProxyJobState, ProxyQueue
from .worker import FFmpegProxyWorker
from .cache import ProxyCache


class ProxyGenerationService:
    """Bounded background proxy service suitable for an editor UI."""
    def __init__(self, queue: ProxyQueue | None = None, worker: FFmpegProxyWorker | None = None,
                 max_workers: int = 1, cache: ProxyCache | None = None):
        if max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        self.queue = queue or ProxyQueue()
        self.worker = worker or FFmpegProxyWorker()
        self.cache = cache
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="aidir-proxy")
        self._lock = RLock()
        self._cancel: dict[str, Event] = {}
        self._futures: dict[str, Future] = {}
        self._background_paused = False

    def add(self, job: ProxyJob) -> ProxyJob:
        self.queue.add(job)
        with self._lock:
            self._cancel[job.id] = Event()
        return job

    def submit(self, job: ProxyJob, *, duration_s: float | None = None,
               progress: Callable[[ProxyJob, float], None] | None = None,
               complete: Callable[[ProxyJob], None] | None = None) -> Future:
        with self._lock:
            cancel = self._cancel.setdefault(job.id, Event())
        def run():
            def on_progress(value: float):
                if progress:
                    progress(job, value)
            result = self.worker.run(job, cancel=cancel, duration_s=duration_s, progress=on_progress)
            if result.state == ProxyJobState.DONE and self.cache:
                self.cache.register(job.media_id, job.output)
            if complete:
                complete(result)
            return result
        future = self.executor.submit(run)
        with self._lock:
            self._futures[job.id] = future
        return future

    def set_background_paused(self, paused: bool) -> None:
        """Governor hook: prevent new background proxy work while playback is stressed."""
        with self._lock:
            self._background_paused = bool(paused)

    @property
    def background_paused(self) -> bool:
        with self._lock:
            return self._background_paused

    def boost_queued_priorities(self, amount: int) -> None:
        """Governor hook: boost queued jobs without disturbing running work."""
        amount = max(0, int(amount))
        if not amount:
            return
        with self._lock:
            for job in self.queue.jobs:
                if job.state == ProxyJobState.QUEUED:
                    job.priority += amount
            self.queue.jobs.sort(key=lambda x: (-x.priority, x.id))

    def submit_next(self, *, duration_lookup: Callable[[ProxyJob], float | None] | None = None,
                    progress: Callable[[ProxyJob, float], None] | None = None,
                    complete: Callable[[ProxyJob], None] | None = None) -> Future | None:
        with self._lock:
            if self._background_paused:
                return None
        job = self.queue.next()
        if job is None:
            return None
        duration = duration_lookup(job) if duration_lookup else None
        return self.submit(job, duration_s=duration, progress=progress, complete=complete)

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            event = self._cancel.get(job_id)
            job = next((x for x in self.queue.jobs if x.id == job_id), None)
            if event is None or job is None:
                return False
            event.set()
            if job.state == ProxyJobState.QUEUED:
                job.state = ProxyJobState.CANCELLED
            return True

    def shutdown(self, wait: bool = True):
        self.executor.shutdown(wait=wait, cancel_futures=True)
