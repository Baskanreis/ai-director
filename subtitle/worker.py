"""Transkripsiyon islemini UI'yi dondurmadan calistiran QThread sarmalayicisi."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from .models import SubtitleError, Transcript
from .transcribe import transcribe


class TranscribeWorker(QThread):
    progress = Signal(float, str)
    finished_ok = Signal(object)  # Transcript
    failed = Signal(str)

    def __init__(
        self,
        media_path: str,
        language: str,
        model_size: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._media_path = media_path
        self._language = language
        self._model_size = model_size

    def run(self) -> None:  # noqa: D102 (Qt API)
        try:
            transcript: Transcript = transcribe(
                self._media_path,
                language=self._language,
                model_size=self._model_size,
                on_progress=lambda f, m: self.progress.emit(f, m),
            )
            self.finished_ok.emit(transcript)
        except SubtitleError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # beklenmeyen hatalar da UI'de gorunsun
            self.failed.emit(f"Beklenmeyen hata: {exc}")
