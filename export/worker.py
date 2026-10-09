"""Export islemini UI'yi dondurmadan calistiran QThread sarmalayicisi."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.timeline.model import Timeline

from app.ai.export_qc import inspect_export
from app.ai.export_repair import repair_export
from app.ai.visual_qc import inspect_visual_export, inspect_audio_levels

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
            report = inspect_export(str(out), self._settings.width, self._settings.height, self._timeline.duration)
            if not report.passed:
                repairable = any(c.name in {"resolution", "duration", "audio"} and c.status == "fail" for c in report.checks)
                if repairable:
                    self.progress.emit(0.995, "QC: teslimat hatası bulundu — otomatik ikinci pass…")
                    repaired = repair_export(
                        out, report,
                        expected_width=self._settings.width,
                        expected_height=self._settings.height,
                        expected_duration=self._timeline.duration,
                    )
                    report = inspect_export(str(repaired), self._settings.width, self._settings.height, self._timeline.duration)
                if not report.passed:
                    details = "; ".join(c.message for c in report.checks if c.status == "fail")
                    self.failed.emit("Export kalite kontrolü başarısız: " + details)
                    return

            # v2.31: delivery sonrası görüntü/ses örnekleme. Bunlar yaratıcı
            # niyeti değiştirmeden yalnızca şüpheli çıktıyı işaretler.
            self.progress.emit(0.997, "AI Visual QC: kareler, donma, blur ve ses seviyesi kontrol ediliyor…")
            visual = inspect_visual_export(
                str(out), expected_duration=self._timeline.duration, sample_count=12
            )
            audio_level = inspect_audio_levels(str(out))
            warnings = [c.message for c in visual.checks if c.status == "warning"]
            if audio_level.status == "warning":
                warnings.append(audio_level.message)
            hard_visual_fail = [c.message for c in visual.checks if c.status == "fail" and c.name in {"decode", "black_frames"}]
            if hard_visual_fail:
                self.failed.emit("Görüntü kalite kontrolü başarısız: " + "; ".join(hard_visual_fail))
                return
            if warnings:
                self.progress.emit(1.0, "Tamamlandı — kalite kontrolü uyarıları mevcut, çıktı kullanılabilir.")
            else:
                self.progress.emit(1.0, "Tamamlandı — export ve AI Visual QC başarılı.")
            self.finished_ok.emit(str(out))
        except ExportCancelled:
            self.cancelled.emit()
        except ExportError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # beklenmeyen hatalar da UI'de gorunsun
            self.failed.emit(f"Beklenmeyen hata: {exc}")
