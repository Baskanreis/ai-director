"""Altyazı diyaloğu — v0.7/v0.8 Subtitle Engine: Whisper ile transkripsiyon, satır
bazlı DÜZENLEME (metin/zamanlama), STİL/ANİMASYON/KELİME VURGUSU/EMOJİ ön ayarları,
SRT/VTT dışa aktarma, videoya gömme (yumuşak akış, düz "yakma" veya stilli .ass yakma).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.subtitle.editor import SubtitleEditor
from app.subtitle.embed import (
    SubtitleError,
    burn_in_ass,
    burn_in_subtitles,
    export_ass,
    export_srt,
    export_vtt,
    mux_soft_subtitles,
)
from app.subtitle.emoji import annotate_transcript
from app.subtitle.models import Transcript
from app.subtitle.style import DEFAULT_PRESET, PRESETS, Animation, get_preset
from app.subtitle.transcribe import DEFAULT_LANGUAGE, DEFAULT_MODEL_SIZE, MODEL_SIZES, SUPPORTED_LANGUAGES
from app.subtitle.worker import TranscribeWorker
from app.timeline.model import Timeline

_ANIMATION_LABELS: dict[Animation, str] = {
    Animation.NONE: "Yok",
    Animation.FADE: "Belirme (fade)",
    Animation.POP: "Büyüyerek belirme (pop)",
    Animation.SLIDE_UP: "Aşağıdan kayma",
}
_ANIMATION_ORDER = [Animation.NONE, Animation.FADE, Animation.POP, Animation.SLIDE_UP]


class SubtitleDialog(QDialog):
    def __init__(self, timeline: Timeline, media_paths: dict[str, str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.timeline = timeline
        self.media_paths = media_paths
        self.worker: TranscribeWorker | None = None
        self.transcript: Transcript | None = None
        self._loading_table = False
        self.setWindowTitle("Altyazı (AI Subtitle)")
        self.setMinimumSize(620, 620)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.source_box = QComboBox()
        self._source_media_ids: list[str] = []
        for media_id, label in self._candidate_sources():
            self._source_media_ids.append(media_id)
            self.source_box.addItem(label)
        form.addRow("Kaynak medya", self.source_box)

        self.lang_box = QComboBox()
        self._lang_keys = list(SUPPORTED_LANGUAGES.keys())
        self.lang_box.addItems([SUPPORTED_LANGUAGES[k] for k in self._lang_keys])
        self.lang_box.setCurrentIndex(self._lang_keys.index(DEFAULT_LANGUAGE))
        form.addRow("Dil", self.lang_box)

        self.model_box = QComboBox()
        self.model_box.addItems(MODEL_SIZES)
        self.model_box.setCurrentText(DEFAULT_MODEL_SIZE)
        form.addRow("Whisper modeli", self.model_box)

        hint = QLabel(
            "Not: Kaynak medyanın tamamı transkribe edilir. Whisper (openai-whisper) "
            "sisteminizde kurulu değilse önce kurmanız gerekir. Türkçe karakterler "
            "(ç ğ ı İ ö ş ü) ve emoji UTF-8 olarak tam desteklenir."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        run_row = QHBoxLayout()
        self.run_btn = QPushButton("Transkribe Et")
        self.run_btn.clicked.connect(self._start_transcribe)
        run_row.addWidget(self.run_btn)
        run_row.addStretch(1)
        layout.addLayout(run_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status_label = QLabel("")
        self.status_label.setObjectName("Muted")
        layout.addWidget(self.status_label)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.tabs.addTab(self._build_edit_tab(), "Satırlar (Düzenle)")
        self.tabs.addTab(self._build_style_tab(), "Stil / Animasyon / Vurgu / Emoji")

        export_row = QHBoxLayout()
        self.srt_btn = QPushButton("SRT Kaydet…")
        self.srt_btn.clicked.connect(lambda: self._export_file("srt"))
        self.vtt_btn = QPushButton("VTT Kaydet…")
        self.vtt_btn.clicked.connect(lambda: self._export_file("vtt"))
        self.mux_btn = QPushButton("Videoya Göm (yumuşak)…")
        self.mux_btn.setToolTip("Altyazıyı ayrı bir akış olarak ekler; video yeniden encode edilmez (hızlı).")
        self.mux_btn.clicked.connect(self._embed_soft)
        self.burn_btn = QPushButton("Videoya Yak (düz)…")
        self.burn_btn.setToolTip("Altyazıyı görüntüye kalıcı olarak basar (stilsiz); video yeniden encode edilir.")
        self.burn_btn.clicked.connect(self._embed_burn_plain)
        self.burn_styled_btn = QPushButton("Stilli Yak (ASS)…")
        self.burn_styled_btn.setToolTip(
            "Seçili stil/animasyon/kelime vurgusu/emoji ayarlarıyla, görüntüye kalıcı olarak basar."
        )
        self.burn_styled_btn.clicked.connect(self._embed_burn_styled)
        for b in (self.srt_btn, self.vtt_btn, self.mux_btn, self.burn_btn, self.burn_styled_btn):
            b.setEnabled(False)
            export_row.addWidget(b)
        layout.addLayout(export_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self._on_close)
        buttons.accepted.connect(self._on_close)
        layout.addWidget(buttons)

    # ---------------- duzenleme sekmesi ----------------
    def _build_edit_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        hint = QLabel(
            "Whisper her zaman mükemmel olmayabilir: metni veya zamanlamayı buradan düzeltebilirsiniz "
            "(hücreye çift tıklayıp düzenleyin, Enter'a basın)."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Başlangıç (sn)", "Bitiş (sn)", "Metin"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.itemChanged.connect(self._on_table_item_changed)
        lay.addWidget(self.table, 1)

        row = QHBoxLayout()
        self.merge_btn = QPushButton("Seçiliyi Önceki ile Birleştir")
        self.merge_btn.clicked.connect(self._merge_selected_with_previous)
        self.delete_row_btn = QPushButton("Seçili Satırı Sil")
        self.delete_row_btn.clicked.connect(self._delete_selected_row)
        for b in (self.merge_btn, self.delete_row_btn):
            b.setEnabled(False)
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        return w

    # ---------------- stil sekmesi ----------------
    def _build_style_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self.preset_box = QComboBox()
        self._preset_keys = list(PRESETS.keys())
        self.preset_box.addItems([PRESETS[k].name for k in self._preset_keys])
        self.preset_box.setCurrentIndex(self._preset_keys.index(DEFAULT_PRESET))
        self.preset_box.currentIndexChanged.connect(self._on_preset_changed)
        form.addRow("Stil ön ayarı", self.preset_box)

        self.animation_box = QComboBox()
        self.animation_box.addItems([_ANIMATION_LABELS[a] for a in _ANIMATION_ORDER])
        form.addRow("Animasyon", self.animation_box)

        self.highlight_check = QCheckBox("O an konuşulan kelimeyi vurgula (karaoke tarzı)")
        form.addRow("", self.highlight_check)

        self.emoji_check = QCheckBox("İçeriğe uygun emoji ekle (otomatik)")
        form.addRow("", self.emoji_check)

        self.always_highlight_edit = QLineEdit()
        self.always_highlight_edit.setPlaceholderText("ör. harika, önemli, dikkat (virgülle ayırın)")
        form.addRow("Her zaman vurgula", self.always_highlight_edit)

        self._on_preset_changed(self.preset_box.currentIndex())
        hint = QLabel(
            "Bu ayarlar yalnızca \"Stilli Yak (ASS)\" ile oluşturulan videoyu etkiler; "
            "SRT/VTT ve \"Videoya Göm (yumuşak)\" düz metin kullanır (oynatıcı stillerine tabidir)."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        form.addRow(hint)
        return w

    def _on_preset_changed(self, idx: int) -> None:
        if idx < 0:
            return
        style = get_preset(self._preset_keys[idx])
        self.animation_box.setCurrentIndex(_ANIMATION_ORDER.index(style.animation))
        self.highlight_check.setChecked(style.highlight_words)

    def _current_style(self):
        style = get_preset(self._preset_keys[self.preset_box.currentIndex()])
        style.animation = _ANIMATION_ORDER[self.animation_box.currentIndex()]
        style.highlight_words = self.highlight_check.isChecked()
        return style

    def _always_highlight_words(self) -> set[str]:
        raw = self.always_highlight_edit.text().strip()
        if not raw:
            return set()
        return {w.strip().lower() for w in raw.split(",") if w.strip()}

    # ---------------- kaynak medya listesi ----------------
    def _candidate_sources(self) -> list[tuple[str, str]]:
        """(media_id, gorunen_ad) ciftleri; timeline'daki klipler medya_id'ye gore benzersizlenir."""
        seen: dict[str, str] = {}
        for clip in self.timeline.all_clips():
            if clip.media_id in self.media_paths and clip.media_id not in seen:
                seen[clip.media_id] = clip.name or clip.media_id
        return list(seen.items())

    def _selected_source_path(self) -> str | None:
        if not self._source_media_ids:
            return None
        idx = self.source_box.currentIndex()
        if idx < 0 or idx >= len(self._source_media_ids):
            return None
        media_id = self._source_media_ids[idx]
        return self.media_paths.get(media_id)

    # ---------------- transkripsiyon ----------------
    def _start_transcribe(self) -> None:
        path = self._selected_source_path()
        if not path:
            QMessageBox.information(self, "Kaynak yok", "Transkribe edilecek bir medya bulunamadı.")
            return

        language = self._lang_keys[self.lang_box.currentIndex()]
        model_size = self.model_box.currentText()

        self.run_btn.setEnabled(False)
        self.source_box.setEnabled(False)
        self.lang_box.setEnabled(False)
        self.model_box.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.status_label.setText("Başlatılıyor…")
        self.table.setRowCount(0)

        self.worker = TranscribeWorker(path, language, model_size, self)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _on_progress(self, frac: float, message: str) -> None:
        self.progress.setValue(int(frac * 100))
        self.status_label.setText(message)

    def _on_finished(self, transcript: Transcript) -> None:
        self.transcript = transcript
        self.status_label.setText(f"Tamamlandı — {len(transcript.segments)} satır, dil: {transcript.language}")
        self._reload_table()
        for b in (self.srt_btn, self.vtt_btn, self.mux_btn, self.burn_btn, self.burn_styled_btn,
                  self.merge_btn, self.delete_row_btn):
            b.setEnabled(True)
        self._reset_run_controls()

    def _on_failed(self, message: str) -> None:
        self.status_label.setText("Hata oluştu")
        QMessageBox.critical(self, "Transkripsiyon başarısız", message)
        self._reset_run_controls()

    def _reset_run_controls(self) -> None:
        self.run_btn.setEnabled(True)
        self.source_box.setEnabled(True)
        self.lang_box.setEnabled(True)
        self.model_box.setEnabled(True)
        self.progress.setVisible(False)

    # ---------------- duzenleme tablosu ----------------
    def _reload_table(self) -> None:
        if not self.transcript:
            return
        self._loading_table = True
        self.table.setRowCount(len(self.transcript.segments))
        for i, seg in enumerate(self.transcript.segments):
            self.table.setItem(i, 0, QTableWidgetItem(f"{seg.start:.2f}"))
            self.table.setItem(i, 1, QTableWidgetItem(f"{seg.end:.2f}"))
            self.table.setItem(i, 2, QTableWidgetItem(seg.text))
        self._loading_table = False

    def _on_table_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading_table or not self.transcript:
            return
        row, col = item.row(), item.column()
        if row >= len(self.transcript.segments):
            return
        editor = SubtitleEditor(self.transcript)
        try:
            if col == 2:
                editor.update_text(row, item.text())
            else:
                start = float(self.table.item(row, 0).text())
                end = float(self.table.item(row, 1).text())
                editor.update_timing(row, start, end)
        except (SubtitleError, ValueError) as exc:
            QMessageBox.warning(self, "Geçersiz değer", str(exc))
            self._reload_table()

    def _merge_selected_with_previous(self) -> None:
        if not self.transcript:
            return
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        if not rows or rows[0] == 0:
            QMessageBox.information(self, "Birleştirilemiyor", "İlk satır veya seçim yok.")
            return
        row = rows[0]
        try:
            SubtitleEditor(self.transcript).merge(row - 1, row)
        except SubtitleError as exc:
            QMessageBox.warning(self, "Birleştirilemedi", str(exc))
            return
        self._reload_table()

    def _delete_selected_row(self) -> None:
        if not self.transcript:
            return
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            return
        editor = SubtitleEditor(self.transcript)
        for row in rows:
            try:
                editor.delete(row)
            except SubtitleError:
                pass
        self._reload_table()

    # ---------------- disa aktarma / gomme ----------------
    def _transcript_for_export(self) -> Transcript | None:
        if not self.transcript:
            return None
        return annotate_transcript(self.transcript) if self.emoji_check.isChecked() else self.transcript

    def _export_file(self, fmt: str) -> None:
        transcript = self._transcript_for_export()
        if not transcript:
            return
        filt = "SubRip (*.srt)" if fmt == "srt" else "WebVTT (*.vtt)"
        path, _ = QFileDialog.getSaveFileName(self, "Altyazı dosyasını kaydet", f"altyazi.{fmt}", filt)
        if not path:
            return
        try:
            if fmt == "srt":
                export_srt(transcript, path)
            else:
                export_vtt(transcript, path)
        except OSError as exc:
            QMessageBox.critical(self, "Kaydedilemedi", str(exc))
            return
        QMessageBox.information(self, "Kaydedildi", f"Altyazı kaydedildi:\n{path}")

    def _write_temp_srt(self, transcript: Transcript) -> Path:
        import tempfile

        tmp_dir = Path(tempfile.gettempdir()) / "ai_director_subtitles"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        return export_srt(transcript, tmp_dir / "preview.srt")

    def _write_temp_ass(self, transcript: Transcript) -> Path:
        import tempfile

        tmp_dir = Path(tempfile.gettempdir()) / "ai_director_subtitles"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        return export_ass(transcript, tmp_dir / "preview.ass", self._current_style(), self._always_highlight_words())

    def _embed_soft(self) -> None:
        transcript = self._transcript_for_export()
        source_path = self._selected_source_path()
        if not transcript or not source_path:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Çıktı videosunu kaydet", "video_altyazili.mp4", "MP4 (*.mp4)")
        if not path:
            return
        language = self._lang_keys[self.lang_box.currentIndex()]
        self._run_embed(
            lambda: mux_soft_subtitles(source_path, self._write_temp_srt(transcript), path, language=language), path
        )

    def _embed_burn_plain(self) -> None:
        transcript = self._transcript_for_export()
        source_path = self._selected_source_path()
        if not transcript or not source_path:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Çıktı videosunu kaydet", "video_altyazili.mp4", "MP4 (*.mp4)")
        if not path:
            return
        self._run_embed(lambda: burn_in_subtitles(source_path, self._write_temp_srt(transcript), path), path)

    def _embed_burn_styled(self) -> None:
        transcript = self._transcript_for_export()
        source_path = self._selected_source_path()
        if not transcript or not source_path:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Çıktı videosunu kaydet", "video_stilli_altyazi.mp4", "MP4 (*.mp4)"
        )
        if not path:
            return
        self._run_embed(lambda: burn_in_ass(source_path, self._write_temp_ass(transcript), path), path)

    def _run_embed(self, action, output_path: str) -> None:
        self.setEnabled(False)
        self.setCursor(Qt.WaitCursor)
        try:
            action()
        except SubtitleError as exc:
            QMessageBox.critical(self, "Gömme başarısız", str(exc))
            return
        finally:
            self.unsetCursor()
            self.setEnabled(True)
        QMessageBox.information(self, "Tamamlandı", f"Altyazılı video kaydedildi:\n{output_path}")

    def _on_close(self) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(
                self, "Transkripsiyon sürüyor",
                "Transkripsiyon bitene kadar bekleyin ya da pencereyi kapatmayın.",
            )
            return
        self.accept()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.worker and self.worker.isRunning():
            self.worker.wait(5000)
        super().closeEvent(event)
