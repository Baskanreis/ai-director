"""Export islemini UI'yi dondurmadan calistiran QThread sarmalayicisi."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.timeline.model import Timeline

from .ffmpeg_export import (
    ExportCancelled,
    ExportError,
    ExportSettings,
    RenderProgress,
    export_timeline,
)


class ExportWorker(QThread):
    progress = Signal(float, str)
    # v1.1: FPS/bit hizi/hiz/ETA/CPU/GPU dahil detayli ilerleme (bkz. RenderProgress)
    progress_detail = Signal(object)
    finished_ok = Signal(str)   # cikti yolu
    failed = Signal(str)        # hata mesaji
    cancelled = Signal()

    def __init__(
        self,
        timeline: Timeline,
        media_paths: dict[str, str],
        settings: ExportSettings,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._timeline = timeline
        self._media_paths = media_paths
        self._settings = settings
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def run(self) -> None:  # noqa: D102 (Qt API)
        try:
            out = export_timeline(
                self._timeline,
                self._media_paths,
                self._settings,
                on_progress=lambda f, m: self.progress.emit(f, m),
                is_cancelled=lambda: self._cancel_requested,
                on_progress_detail=lambda rp: self.progress_detail.emit(rp),
            )
            self.finished_ok.emit(str(out))
        except ExportCancelled:
            self.cancelled.emit()
        except ExportError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # beklenmeyen hatalar da UI'de gorunsun
            self.failed.emit(f"Beklenmeyen hata: {exc}")
