"""AI PIPELINE UI — v1.4.

İçe Aktar -> Analiz -> Transkripsiyon -> Sahne Algılama -> Kurgu Analizi ->
Kamera -> Efektler -> Altyazı -> Render zincirini, her aşamanın durumunu canlı
gösteren tek bir diyalogda yapılandırıp çalıştırır. Gerçek iş `app.brain`
paketinde (Qt'siz, iş kuyruğu tabanlı); bu dosya yalnızca ince bir arayüzdür.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.brain.camera import CAMERA_STYLES
from app.brain.effects_preset import preset_names as effects_preset_names
from app.brain.pipeline import PIPELINE_ORDER, STAGE_LABELS, PipelineConfig, PipelineContext, PipelineStage
from app.brain.worker import PipelineWorker
from app.export.presets import export_settings_for, preset_names as export_preset_names
from app.subtitle.transcribe import SUPPORTED_LANGUAGES
from app.timeline.model import Timeline

STAGE_TOGGLE_FIELDS: dict[PipelineStage, str] = {
    PipelineStage.TRANSCRIPTION: "run_transcription",
    PipelineStage.SCENE_DETECTION: "run_scene_detection",
    PipelineStage.EDIT_ANALYSIS: "run_edit_analysis",
    PipelineStage.CAMERA: "run_camera",
    PipelineStage.EFFECTS: "run_effects",
    PipelineStage.SUBTITLE: "run_subtitle",
    PipelineStage.RENDER: "run_render",
}

STATUS_BADGES = {
    "pending": "Bekliyor", "running": "Çalışıyor…", "done": "Tamam",
    "failed": "Hata", "cancelled": "İptal",
}


class _StageRow(QWidget):
    def __init__(self, stage: PipelineStage) -> None:
        super().__init__()
        self.stage = stage
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        self.name_label = QLabel(STAGE_LABELS[stage])
        self.name_label.setMinimumWidth(140)
        self.status_label = QLabel("Bekliyor")
        self.status_label.setObjectName("Muted")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.setFixedWidth(120)
        lay.addWidget(self.name_label)
        lay.addWidget(self.bar)
        lay.addWidget(self.status_label, 1)

    def set_pending(self) -> None:
        self.bar.setValue(0)
        self.status_label.setText("Bekliyor")

    def set_running(self, frac: float, message: str) -> None:
        self.bar.setValue(int(frac * 100))
        self.status_label.setText(message or "Çalışıyor…")

    def set_done(self) -> None:
        self.bar.setValue(100)
        self.status_label.setText("Tamam")

    def set_failed(self, error: str) -> None:
        self.status_label.setText(f"Hata: {error.splitlines()[0][:80]}")


class PipelineDialog(QDialog):
    """`AIPipeline`yi, Studio'daki timeline/medya üzerinde çalıştıran diyalog."""

    def __init__(self, timeline: Timeline, media_paths: dict[str, str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.timeline = timeline
        self.media_paths = media_paths
        self.worker: PipelineWorker | None = None
        self._export_output_path: str | None = None
        self.setWindowTitle("AI Pipeline — Import → Analysis → … → Render")
        self.setMinimumSize(620, 620)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        layout.addLayout(form)

        self.source_box = QComboBox()
        self._source_clip_ids: list[str] = []
        self._source_media_ids: list[str] = []
        for clip_id, media_id, label in self._candidate_sources():
            self._source_clip_ids.append(clip_id)
            self._source_media_ids.append(media_id)
            self.source_box.addItem(label)
        form.addRow("Kaynak klip", self.source_box)

        self.lang_box = QComboBox()
        self._lang_keys = [k for k in SUPPORTED_LANGUAGES if k != "auto"]
        self.lang_box.addItems([SUPPORTED_LANGUAGES[k] for k in self._lang_keys])
        form.addRow("Dil (Transkripsiyon)", self.lang_box)

        self.camera_box = QComboBox()
        self.camera_box.addItems(CAMERA_STYLES)
        self.camera_box.setCurrentText("kenburns")
        form.addRow("Kamera stili", self.camera_box)

        self.effects_box = QComboBox()
        self.effects_box.addItems(effects_preset_names())
        form.addRow("Efekt ön ayarı", self.effects_box)

        stages_label = QLabel("Çalıştırılacak aşamalar")
        stages_label.setObjectName("CardTitle")
        layout.addWidget(stages_label)

        self._toggles: dict[PipelineStage, QCheckBox] = {}
        toggles_row1 = QHBoxLayout()
        toggles_row2 = QHBoxLayout()
        for i, (stage, field_name) in enumerate(STAGE_TOGGLE_FIELDS.items()):
            cb = QCheckBox(STAGE_LABELS[stage])
            cb.setChecked(stage != PipelineStage.RENDER)
            self._toggles[stage] = cb
            (toggles_row1 if i < 4 else toggles_row2).addWidget(cb)
        layout.addLayout(toggles_row1)
        layout.addLayout(toggles_row2)
        self._toggles[PipelineStage.RENDER].toggled.connect(self._on_render_toggled)

        render_row = QHBoxLayout()
        self.export_preset_box = QComboBox()
        self.export_preset_box.addItems(export_preset_names())
        self.choose_output_btn = QPushButton("Çıktı dosyası seç…")
        self.choose_output_btn.clicked.connect(self._choose_output)
        self.output_label = QLabel("(seçilmedi)")
        self.output_label.setObjectName("Muted")
        render_row.addWidget(QLabel("Render ayarı:"))
        render_row.addWidget(self.export_preset_box)
        render_row.addWidget(self.choose_output_btn)
        render_row.addWidget(self.output_label, 1)
        layout.addLayout(render_row)
        self._on_render_toggled(self._toggles[PipelineStage.RENDER].isChecked())

        stage_list_label = QLabel("İlerleme")
        stage_list_label.setObjectName("CardTitle")
        layout.addWidget(stage_list_label)
        self.stage_rows: dict[PipelineStage, _StageRow] = {}
        for stage in PIPELINE_ORDER:
            row = _StageRow(stage)
            self.stage_rows[stage] = row
            layout.addWidget(row)

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        buttons = QHBoxLayout()
        self.start_btn = QPushButton("Pipeline'ı Başlat")
        self.start_btn.clicked.connect(self._start)
        self.cancel_btn = QPushButton("İptal")
        self.cancel_btn.clicked.connect(self._cancel)
        self.cancel_btn.setEnabled(False)
        self.close_btn = QPushButton("Kapat")
        self.close_btn.clicked.connect(self.accept)
        buttons.addWidget(self.start_btn)
        buttons.addWidget(self.cancel_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.close_btn)
        layout.addLayout(buttons)

    # ---- yardimcilar ----
    def _candidate_sources(self) -> list[tuple[str, str, str]]:
        out: list[tuple[str, str, str]] = []
        for clip in self.timeline.all_clips():
            if clip.media_id in self.media_paths:
                out.append((clip.id, clip.media_id, f"{clip.name or clip.media_id}  [{clip.start:.1f}s]"))
        return out

    def _on_render_toggled(self, checked: bool) -> None:
        self.export_preset_box.setEnabled(checked)
        self.choose_output_btn.setEnabled(checked)

    def _choose_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Render Çıktısı", "", "MP4 (*.mp4)")
        if path:
            self._export_output_path = path
            self.output_label.setText(path)

    def _build_config(self) -> PipelineConfig | None:
        export_settings = None
        if self._toggles[PipelineStage.RENDER].isChecked():
            if not self._export_output_path:
                QMessageBox.warning(self, "Çıktı seçilmedi", "Render için bir çıktı dosyası seçin.")
                return None
            export_settings = export_settings_for(self.export_preset_box.currentText(), self._export_output_path)
        kwargs = {field: cb.isChecked() for stage, cb in self._toggles.items() for field in [STAGE_TOGGLE_FIELDS[stage]]}
        return PipelineConfig(
            language=self._lang_keys[self.lang_box.currentIndex()],
            camera_style=self.camera_box.currentText(),
            effects_preset=self.effects_box.currentText(),
            export_settings=export_settings,
            **kwargs,
        )

    # ---- calistirma ----
    def _start(self) -> None:
        if not self._source_clip_ids:
            QMessageBox.information(self, "Klip yok", "Pipeline çalıştırmak için timeline'da bir klip olmalı.")
            return
        config = self._build_config()
        if config is None:
            return
        idx = self.source_box.currentIndex()
        clip_id = self._source_clip_ids[idx]
        media_path = self.media_paths[self._source_media_ids[idx]]

        for row in self.stage_rows.values():
            row.set_pending()
        self.summary_label.setText("")

        context = PipelineContext(
            timeline=self.timeline, clip_id=clip_id, media_path=media_path, media_paths=self.media_paths,
        )
        self.worker = PipelineWorker(context, config, self)
        self.worker.stage_started.connect(self._on_stage_started)
        self.worker.stage_progress.connect(self._on_stage_progress)
        self.worker.stage_finished.connect(self._on_stage_finished)
        self.worker.stage_failed.connect(self._on_stage_failed)
        self.worker.pipeline_finished.connect(self._on_pipeline_finished)
        self.worker.pipeline_failed.connect(self._on_pipeline_failed)
        self.worker.start()

        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

    def _cancel(self) -> None:
        if self.worker:
            self.worker.request_cancel()
        self.cancel_btn.setEnabled(False)

    def _on_stage_started(self, stage_value: str, _label: str) -> None:
        self.stage_rows[PipelineStage(stage_value)].set_running(0.0, "Başladı…")

    def _on_stage_progress(self, stage_value: str, frac: float, message: str) -> None:
        self.stage_rows[PipelineStage(stage_value)].set_running(frac, message)

    def _on_stage_finished(self, stage_value: str, _result) -> None:
        self.stage_rows[PipelineStage(stage_value)].set_done()

    def _on_stage_failed(self, stage_value: str, error: str) -> None:
        self.stage_rows[PipelineStage(stage_value)].set_failed(error)

    def _on_pipeline_finished(self, _results: dict) -> None:
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        if not self.summary_label.text():
            self.summary_label.setText("Pipeline tamamlandı.")

    def _on_pipeline_failed(self, message: str) -> None:
        self.summary_label.setText(message)


__all__ = ["PipelineDialog"]
