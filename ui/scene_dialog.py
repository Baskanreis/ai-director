"""Sahne Algıla diyaloğu: seçili klibi, ffmpeg tabanlı sahne tespitiyle bulunan
kesim noktalarında otomatik olarak böler — v1.0 Scene Detection."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.scene.detector import DEFAULT_THRESHOLD, MAX_THRESHOLD, MIN_THRESHOLD, ffmpeg_available, split_at_scenes
from app.scene.worker import SceneDetectWorker
from app.timeline.model import Timeline


class SceneDetectDialog(QDialog):
    """Timeline'daki tek bir (video) klip için sahne tespiti + otomatik bölme."""

    def __init__(self, timeline: Timeline, clip_id: str, media_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.timeline = timeline
        self.clip_id = clip_id
        self.media_path = media_path
        self.worker: SceneDetectWorker | None = None
        self.splits_applied = 0

        self.setWindowTitle("Sahne Algıla (Scene Detection)")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.threshold_box = QDoubleSpinBox()
        self.threshold_box.setRange(MIN_THRESHOLD, MAX_THRESHOLD)
        self.threshold_box.setSingleStep(0.05)
        self.threshold_box.setDecimals(2)
        self.threshold_box.setValue(DEFAULT_THRESHOLD)
        form.addRow("Hassasiyet eşiği", self.threshold_box)

        hint = QLabel(
            "Klibin kaynak videosu analiz edilir (yalnızca okuma; klip veya video\n"
            "değişmez) ve bulunan her sahne kesimi noktasında klip otomatik olarak\n"
            "bölünür. Düşük eşik = daha fazla (daha hassas) kesim, yüksek eşik =\n"
            "yalnızca belirgin/sert kesimler."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # belirsiz ilerleme (sure onceden bilinmiyor)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status_label = QLabel("")
        self.status_label.setObjectName("Muted")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.detect_btn = QPushButton("Algıla ve Böl")
        self.detect_btn.clicked.connect(self._start)
        layout.addWidget(self.detect_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Close).clicked.connect(self.reject)
        layout.addWidget(buttons)

        if not ffmpeg_available():
            self.detect_btn.setEnabled(False)
            self.status_label.setText(
                "ffmpeg bulunamadı; sahne tespiti için ffmpeg kurulu olmalı."
            )

    def _start(self) -> None:
        if not self.timeline.find(self.clip_id):
            QMessageBox.warning(self, "Klip bulunamadı", "Seçili klip artık timeline'da yok.")
            self.reject()
            return
        self.detect_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status_label.setText("Sahneler analiz ediliyor…")
        self.worker = SceneDetectWorker(self.media_path, float(self.threshold_box.value()), self)
        self.worker.finished_ok.connect(self._on_done)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _on_done(self, scene_times: list[float]) -> None:
        self.progress.setVisible(False)
        n = split_at_scenes(self.timeline, self.clip_id, scene_times)
        self.splits_applied = n
        if n:
            self.status_label.setText(f"{n} sahne kesimi bulundu ve klip bölündü.")
            self.accept()
        else:
            self.status_label.setText("Bu klip içinde uygun bir sahne kesimi bulunamadı.")
            self.detect_btn.setEnabled(True)

    def _on_failed(self, message: str) -> None:
        self.progress.setVisible(False)
        self.detect_btn.setEnabled(True)
        QMessageBox.critical(self, "Sahne tespiti başarısız", message)
        self.status_label.setText("")
