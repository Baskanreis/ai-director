"""GPU/CPU-aware render admission control for AI Director.

The scheduler is deliberately conservative: when GPU telemetry is unavailable it
falls back to CPU/load limits and never blocks the editor indefinitely.
"""
from __future__ import annotations
from dataclasses import dataclass
from threading import Condition, Event
from time import monotonic
from typing import Callable

from .monitor import cpu_percent, gpu_percent, gpu_memory_percent

@dataclass(frozen=True)
class ResourceSnapshot:
    cpu: float | None
    gpu: float | None
    vram: float | None = None

@dataclass
class SchedulerPolicy:
    max_parallel: int = 1
    max_gpu_percent: float = 85.0
    max_vram_percent: float = 90.0
    max_cpu_percent: float = 90.0
    poll_seconds: float = 0.25
    reserve_editor: bool = True

class RenderAdmission:
    """Bounded resource gate shared by render workers."""
    def __init__(self, policy: SchedulerPolicy | None = None,
                 sample: Callable[[], ResourceSnapshot] | None = None):
        self.policy = policy or SchedulerPolicy()
        if self.policy.max_parallel < 1:
            raise ValueError("max_parallel must be >= 1")
        self._sample = sample or (lambda: ResourceSnapshot(cpu_percent(), gpu_percent(), gpu_memory_percent()))
        self._active = 0
        self._cv = Condition()

    @property
    def active(self) -> int:
        with self._cv:
            return self._active

    def snapshot(self) -> ResourceSnapshot:
        return self._sample()

    def _allowed(self, s: ResourceSnapshot) -> bool:
        if self._active >= self.policy.max_parallel:
            return False
        # Unknown telemetry is non-blocking; Windows machines without nvidia-smi
        # must still be able to render.
        if s.cpu is not None and s.cpu >= self.policy.max_cpu_percent:
            return False
        if s.gpu is not None and s.gpu >= self.policy.max_gpu_percent:
            return False
        if s.vram is not None and s.vram >= self.policy.max_vram_percent:
            return False
        return True

    def acquire(self, cancel: Event | None = None, timeout: float | None = None) -> bool:
        deadline = None if timeout is None else monotonic() + timeout
        with self._cv:
            while True:
                if cancel is not None and cancel.is_set():
                    return False
                if self._allowed(self.snapshot()):
                    self._active += 1
                    return True
                if deadline is not None:
                    remaining = deadline - monotonic()
                    if remaining <= 0:
                        return False
                    self._cv.wait(min(self.policy.poll_seconds, remaining))
                else:
                    self._cv.wait(self.policy.poll_seconds)

    def release(self) -> None:
        with self._cv:
            if self._active:
                self._active -= 1
            self._cv.notify_all()

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError("Render admission denied")
        return self

    def __exit__(self, *_):
        self.release()
