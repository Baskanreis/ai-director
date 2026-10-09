"""Sahne tespitini UI'yi dondurmadan çalıştıran QThread sarmalayıcısı."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from .detector import SceneDetectionError, detect_scene_changes


class SceneDetectWorker(QThread):
    finished_ok = Signal(list)  # list[float] (kaynak zamanina gore sahne zaman damgalari)
    failed = Signal(str)

    def __init__(self, media_path: str, threshold: float, parent=None) -> None:
        super().__init__(parent)
        self._media_path = media_path
        self._threshold = threshold

    def run(self) -> None:  # noqa: D102 (Qt API)
        try:
            times = detect_scene_changes(self._media_path, threshold=self._threshold)
            self.finished_ok.emit(times)
        except SceneDetectionError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # beklenmeyen hatalar da UI'de gorunsun
            self.failed.emit(f"Beklenmeyen hata: {exc}")
