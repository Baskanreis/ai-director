"""Hafif Qt arka plan isleri: UI thread'ini bloklamadan IO/FFmpeg calistirir."""
from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(object)
    finished = Signal()


class BackgroundTask(QRunnable):
    """Tek bir fonksiyonu global thread pool'da calistirir."""

    def __init__(self, fn: Callable[[], Any]) -> None:
        super().__init__()
        self.fn = fn
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    def run(self) -> None:  # pragma: no cover - Qt thread pool calls this
        try:
            self.signals.result.emit(self.fn())
        except Exception as exc:  # keep UI alive; surface the original error
            self.signals.error.emit(exc)
        finally:
            self.signals.finished.emit()


def pool() -> QThreadPool:
    """Media jobs icin muhafazakar ortak pool.

    FFmpeg/OpenCV gibi islemleri CPU'yu tamamen dolduracak sekilde paralellestirmek
    editör onizlemesini daha da kotulestirebilir; iki worker bilincli bir tavandir.
    """
    p = QThreadPool.globalInstance()
    if p.maxThreadCount() > 2:
        p.setMaxThreadCount(2)
    return p
