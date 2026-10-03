"""Export ayar diyalogu ve ilerleme gostergesi."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.export.ffmpeg_export import ExportSettings, RenderProgress, available_codecs
from app.export.presets import PRESETS as PLATFORM_PRESETS
from app.export.worker import ExportWorker
from app.project.project import Project

# Çözünürlük ön ayarları (platform preset'i "Özel" dışına ayarlanınca FPS/kodek/
# bit hızı da platform presetinden gelir; bu sözlük yalnızca çözünürlük seçimini
# serbestçe değiştirmek isteyenler için ayrı bir kısayoldur).
PRESETS: dict[str, tuple[int, int]] = {
    "1080p (1920x1080)": (1920, 1080),
    "720p (1280x720)": (1280, 720),
    "Dikey 1080x1920 (Shorts)": (1080, 1920),
    "480p (854x480)": (854, 480),
}

CODEC_LABELS: dict[str, str] = {
    "h264": "H.264 (uyumlu, hızlı)",
    "h265": "H.265 / HEVC (küçük dosya)",
    "av1": "AV1 (en küçük, en yavaş)",
}

AUDIO_CODEC_LABELS: dict[str, str] = {
    "aac": "AAC (önerilen, uyumlu)",
    "mp3": "MP3",
    "wav": "WAV (sıkıştırmasız / PCM)",
}

# Platform (çıktı hedefi) ön ayarları: YouTube / Shorts / TikTok / Instagram / Özel.
PLATFORM_LABELS: dict[str, str] = {p.name: p.label for p in PLATFORM_PRESETS}


class ExportDialog(QDialog):
    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.worker: ExportWorker | None = None
        self.setWindowTitle("Video Dışa Aktar")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        # v1.1: platform ön ayarı (YouTube/Shorts/TikTok/Instagram/Özel). "Özel"
        # dışındaki bir seçim; çözünürlük/FPS/kodek/CRF/bit hızını otomatik
        # doldurur ve ilgili kutucukları salt-okunur yapar ("Özel" bunları
        # tekrar serbest birakir).
        self._platform_keys = [p.name for p in PLATFORM_PRESETS]
        self._platform_presets = {p.name: p for p in PLATFORM_PRESETS}
        self.platform_box = QComboBox()
        self.platform_box.addItems([PLATFORM_LABELS[k] for k in self._platform_keys])
        try:
            self.platform_box.setCurrentIndex(self._platform_keys.index("custom"))
        except ValueError:
            pass
        self.platform_box.currentIndexChanged.connect(self._on_platform_changed)
        form.addRow("Platform", self.platform_box)

        self.preset_box = QComboBox()
        self.preset_box.addItems(PRESETS.keys())
        form.addRow("Çözünürlük", self.preset_box)

        self.fps_box = QComboBox()
        self.fps_box.addItems(["24", "25", "30", "60"])
        self.fps_box.setCurrentText("30")
        form.addRow("FPS", self.fps_box)

        self.codec_box = QComboBox()
        codecs = available_codecs() or ["h264"]
        self._codec_keys = codecs
        self.codec_box.addItems([CODEC_LABELS.get(c, c) for c in codecs])
        form.addRow("Video Kodeği", self.codec_box)

        self._audio_codec_keys = list(AUDIO_CODEC_LABELS.keys())
        self.audio_codec_box = QComboBox()
        self.audio_codec_box.addItems([AUDIO_CODEC_LABELS[k] for k in self._audio_codec_keys])
        form.addRow("Ses Kodeği", self.audio_codec_box)

        # Platform presetinden gelen (UI'da ayrı gösterilmeyen) degerler.
        self._preset_crf: int | None = 20
        self._preset_video_bitrate = "8M"
        self._preset_audio_bitrate = "192k"
        self._preset_fit_mode = "contain"
        self._platform_resolution: tuple[int, int] | None = None

        path_row = QWidget()
        from PySide6.QtWidgets import QHBoxLayout

        path_lay = QHBoxLayout(path_row)
        path_lay.setContentsMargins(0, 0, 0, 0)
        default_name = f"{project.name or 'export'}.mp4"
        default_dir = str(Path(project.path).parent) if project.path else str(Path.home())
        self.path_edit = QLineEdit(str(Path(default_dir) / default_name))
        browse = QPushButton("Gözat…")
        browse.clicked.connect(self._browse)
        path_lay.addWidget(self.path_edit, 1)
        path_lay.addWidget(browse)
        form.addRow("Çıktı dosyası", path_row)

        self.status_label = QLabel(f"Timeline süresi: {project.timeline.duration:.1f} sn")
        self.status_label.setObjectName("Muted")
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # v1.1: render sirasinda FPS / hiz (Nx) / tahmini kalan sure (ETA) / CPU / GPU.
        self.detail_label = QLabel("")
        self.detail_label.setObjectName("Muted")
        self.detail_label.setVisible(False)
        layout.addWidget(self.detail_label)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.export_btn = QPushButton("Dışa Aktar")
        self.export_btn.setDefault(True)
        self.buttons.addButton(self.export_btn, QDialogButtonBox.AcceptRole)
        self.buttons.rejected.connect(self._on_cancel_or_close)
        self.export_btn.clicked.connect(self._start_export)
        layout.addWidget(self.buttons)

    # ---------------- islemler ----------------
    def _on_platform_changed(self, _index: int) -> None:
        key = self._platform_keys[self.platform_box.currentIndex()]
        preset = self._platform_presets[key]
        is_custom = key == "custom"
        if not is_custom:
            # Çözünürlük kutusu sabit etiketlerle çalıştığından, platform preseti
            # oradaki en yakın etiketi degil dogrudan genislik/yukseklik kullanir;
            # bu nedenle çözünürlük/FPS/kodek kutuları salt-okunur yapılır.
            self.fps_box.setCurrentText(str(int(preset.fps)))
            if preset.codec in self._codec_keys:
                self.codec_box.setCurrentIndex(self._codec_keys.index(preset.codec))
            self._preset_crf = preset.crf
            self._preset_video_bitrate = preset.video_bitrate
            self._preset_audio_bitrate = preset.audio_bitrate
            self._preset_fit_mode = getattr(preset, "fit_mode", "contain")
            self._platform_resolution = (preset.width, preset.height)
        else:
            self._preset_crf = 20
            self._preset_video_bitrate = "8M"
            self._preset_audio_bitrate = "192k"
            self._preset_fit_mode = "contain"
            self._platform_resolution = None
        self.preset_box.setEnabled(is_custom)
        self.fps_box.setEnabled(is_custom)
        self.codec_box.setEnabled(is_custom)

    def _browse(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Çıktı dosyası seç", self.path_edit.text(), "MP4 video (*.mp4)"
        )
        if path:
            if not path.lower().endswith(".mp4"):
                path += ".mp4"
            self.path_edit.setText(path)

    def _start_export(self) -> None:
        if not self.project.timeline.all_clips():
            QMessageBox.warning(self, "Timeline boş", "Dışa aktarılacak klip yok.")
            return
        missing = self.project.missing_media()
        if missing:
            QMessageBox.warning(
                self, "Eksik medya",
                "Bazı kaynak dosyalar bulunamadığı için export başlatılamıyor.",
            )
            return
        out_path = self.path_edit.text().strip()
        if not out_path:
            QMessageBox.warning(self, "Yol eksik", "Bir çıktı dosyası yolu belirtin.")
            return

        if self._platform_resolution is not None:
            width, height = self._platform_resolution
        else:
            width, height = PRESETS[self.preset_box.currentText()]
        codec = self._codec_keys[self.codec_box.currentIndex()]
        audio_codec = self._audio_codec_keys[self.audio_codec_box.currentIndex()]
        platform_key = self._platform_keys[self.platform_box.currentIndex()]
        settings = ExportSettings(
            output_path=out_path,
            width=width,
            height=height,
            fps=float(self.fps_box.currentText()),
            codec=codec,
            audio_codec=audio_codec,
            crf=self._preset_crf,
            video_bitrate=self._preset_video_bitrate,
            audio_bitrate=self._preset_audio_bitrate,
            preset_name=PLATFORM_LABELS.get(platform_key, "Custom"),
            fit_mode=self._preset_fit_mode,
        )
        media_paths = {m.id: m.path for m in self.project.media}

        self.export_btn.setEnabled(False)
        self.platform_box.setEnabled(False)
        self.preset_box.setEnabled(False)
        self.fps_box.setEnabled(False)
        self.codec_box.setEnabled(False)
        self.audio_codec_box.setEnabled(False)
        self.path_edit.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.detail_label.setVisible(True)
        self.detail_label.setText("")
        self.status_label.setText("Başlatılıyor…")

        self.worker = ExportWorker(self.project.timeline, media_paths, settings, self)
        self.worker.progress.connect(self._on_progress)
        self.worker.progress_detail.connect(self._on_progress_detail)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.cancelled.connect(self._on_cancelled)
        self.worker.start()

    def _on_progress(self, frac: float, message: str) -> None:
        self.progress.setValue(int(frac * 100))
        self.status_label.setText(message)

    def _on_progress_detail(self, rp: RenderProgress) -> None:
        bits: list[str] = []
        if rp.fps:
            bits.append(f"{rp.fps:.1f} FPS")
        if rp.speed:
            bits.append(f"{rp.speed:.2f}x hız")
        if rp.eta_seconds is not None:
            m, s = divmod(int(rp.eta_seconds), 60)
            bits.append(f"kalan ~{m:02d}:{s:02d}")
        if rp.cpu_percent is not None:
            bits.append(f"CPU %{rp.cpu_percent:.0f}")
        if rp.gpu_percent is not None:
            bits.append(f"GPU %{rp.gpu_percent:.0f}")
        self.detail_label.setText(" · ".join(bits))

    def _on_finished(self, out_path: str) -> None:
        self.status_label.setText(f"Tamamlandı: {out_path}")
        QMessageBox.information(self, "Dışa aktarma tamamlandı", f"Video kaydedildi:\n{out_path}")
        self.accept()

    def _on_failed(self, message: str) -> None:
        self.status_label.setText("Hata oluştu")
        QMessageBox.critical(self, "Dışa aktarma başarısız", message)
        self._reset_controls()

    def _on_cancelled(self) -> None:
        self.status_label.setText("İptal edildi")
        self._reset_controls()

    def _reset_controls(self) -> None:
        self.export_btn.setEnabled(True)
        self.platform_box.setEnabled(True)
        is_custom = self._platform_keys[self.platform_box.currentIndex()] == "custom"
        self.preset_box.setEnabled(is_custom)
        self.fps_box.setEnabled(is_custom)
        self.codec_box.setEnabled(is_custom)
        self.audio_codec_box.setEnabled(True)
        self.path_edit.setEnabled(True)
        self.progress.setVisible(False)
        self.detail_label.setVisible(False)

    def _on_cancel_or_close(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.request_cancel()
            self.status_label.setText("İptal ediliyor…")
        else:
            self.reject()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.worker and self.worker.isRunning():
            self.worker.request_cancel()
            self.worker.wait(5000)
        super().closeEvent(event)
