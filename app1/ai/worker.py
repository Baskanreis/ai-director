"""Analiz islemini UI'yi dondurmadan calistiran QThread sarmalayicisi (v0.8 AI Basic Editor)."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.subtitle.models import Transcript

from .analyzer import build_report
from .models import AnalysisReport


class AnalyzeWorker(QThread):
    finished_ok = Signal(object)  # AnalysisReport
    failed = Signal(str)

    def __init__(
        self,
        clip_id: str,
        media_path: str,
        transcript: Transcript | None,
        language: str = "tr",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._clip_id = clip_id
        self._media_path = media_path
        self._transcript = transcript
        self._language = language

    def run(self) -> None:  # noqa: D102 (Qt API)
        try:
            report: AnalysisReport = build_report(
                self._clip_id, self._media_path, self._transcript, language=self._language
            )
            self.finished_ok.emit(report)
        except Exception as exc:  # beklenmeyen hatalar da UI'de gorunsun
            self.failed.emit(f"Analiz başarısız: {exc}")


__all__ = ["AnalyzeWorker"]
