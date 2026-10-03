"""Studio sayfasi: medya havuzu, proje ozeti ve timeline (v0.2)."""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QSize, QTimer, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.project.project import MediaItem, Project
from app.runtime.util import fmt_time, fmt_timecode
from app.timeline.history import TimelineHistory
from app.video.media_info import MEDIA_EXTENSIONS, MediaProbeError, generate_thumbnail, probe_media

from .audio_panel import AudioTracksDialog, ClipAudioDialog
from .effects_music_dialog import EffectsMusicDialog
from .keyframe_editor import KeyframeEditorDialog
from .export_dialog import ExportDialog
from .preview_widget import PreviewPlayer
from .ai_editor_dialog import AIEditorDialog
from .scene_dialog import SceneDetectDialog
from .subtitle_dialog import SubtitleDialog
from .timeline_view import TimelineView
from .professional_tools_dialog import ProfessionalToolsDialog
from .shorts_director_dialog import ShortsDirectorDialog
from .widgets import Card, row

log = logging.getLogger(__name__)

THUMB_ICON_SIZE = QSize(96, 54)


def _icon_for(media: MediaItem) -> QIcon:
    if media.thumbnail and Path(media.thumbnail).is_file():
        pix = QPixmap(media.thumbnail)
        if not pix.isNull():
            return QIcon(pix)
    # Ses-yalnizca (ya da onizlemesi olmayan) medya icin jenerik simge.
    placeholder = QPixmap(THUMB_ICON_SIZE)
    placeholder.fill(Qt.transparent)
    return QIcon(placeholder)


def _muted(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Muted")
    return lbl


class StudioPage(QWidget):
    project_changed = Signal()

    def __init__(self, project: Project) -> None:
        super().__init__()
        self.project = project
        self.history = TimelineHistory(project.timeline)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        inner = QWidget()
        scroll.setWidget(inner)
        content = QVBoxLayout(inner)
        content.setContentsMargins(32, 28, 32, 28)
        content.setSpacing(18)

        title = QLabel("Studio")
        title.setObjectName("PageTitle")
        self.subtitle = _muted("")
        self.subtitle.setWordWrap(True)
        content.addWidget(title)
        content.addWidget(self.subtitle)

        content.addWidget(self._build_media_card())
        content.addWidget(self._build_preview_card())
        content.addWidget(self._build_timeline_card())
        content.addStretch(1)

        self._thumb_job_token = 0
        self._import_job_token = 0
        self._pending_imports = 0
        self.refresh()

    # ---------------- medya havuzu ----------------
    def _build_media_card(self) -> QWidget:
        self.media_card = Card("Medya Havuzu")

        btn_row = QWidget()
        btn_lay = QHBoxLayout(btn_row)
        btn_lay.setContentsMargins(0, 0, 0, 0)
        add_btn = QPushButton("+ Medya Ekle")
        add_btn.clicked.connect(self.add_video_dialog)
        add_timeline_btn = QPushButton("Timeline'a Ekle")
        add_timeline_btn.clicked.connect(self._add_selected_to_timeline)
        btn_lay.addWidget(add_btn)
        btn_lay.addWidget(add_timeline_btn)
        btn_lay.addStretch(1)
        self.media_card.body.addWidget(btn_row)

        self.media_list = QListWidget()
        self.media_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.media_list.setFixedHeight(140)
        self.media_list.setIconSize(THUMB_ICON_SIZE)
        self.media_list.itemDoubleClicked.connect(lambda _: self._add_selected_to_timeline())
        self.media_card.body.addWidget(self.media_list)

        self.media_empty_hint = _muted(
            "Henüz medya yok. \"+ Video Ekle\" ile seçin ya da dosyaları buraya sürükleyip bırakın."
        )
        self.media_card.body.addWidget(self.media_empty_hint)

        # Drag & drop: hem karta hem listeye dosya birakilabilir.
        self.media_card.setAcceptDrops(True)
        self.media_card.dragEnterEvent = self._drag_enter_event
        self.media_card.dropEvent = self._drop_event
        self.media_list.setAcceptDrops(True)
        self.media_list.dragEnterEvent = self._drag_enter_event
        self.media_list.dropEvent = self._drop_event
        return self.media_card

    def _drag_enter_event(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def _drop_event(self, event: QDropEvent) -> None:
        paths = [
            url.toLocalFile()
            for url in event.mimeData().urls()
            if url.isLocalFile()
        ]
        event.acceptProposedAction()
        if paths:
            self._import_paths(paths)

    def add_video_dialog(self) -> None:
        exts = " ".join(f"*{e}" for e in MEDIA_EXTENSIONS)
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Medya Ekle", self._start_dir(), f"Medya dosyaları ({exts});;Tüm dosyalar (*)"
        )
        if paths:
            self._import_paths(paths)

    def _import_paths(self, paths: list[str]) -> None:
        """Medya analizini arka plana alır; dosya seciminden sonra UI donmaz."""
        supported = [p for p in paths if Path(p).suffix.lower() in MEDIA_EXTENSIONS]
        unsupported = [p for p in paths if Path(p).suffix.lower() not in MEDIA_EXTENSIONS]
        if unsupported:
            QMessageBox.warning(self, "Desteklenmeyen dosya", "\n".join(f"{p}: desteklenmeyen dosya türü" for p in unsupported[:8]))
        if not supported:
            return

        self._import_job_token += 1
        token = self._import_job_token
        self._pending_imports = len(supported)
        self.subtitle.setText(f"Medya analiz ediliyor… 0/{len(supported)}")
        self.media_list.setEnabled(False)

        from .background import BackgroundTask, pool
        for path in supported:
            task = BackgroundTask(lambda p=path: probe_media(p, thumbnail=False))
            task.signals.result.connect(lambda info, tok=token: self._import_result(tok, info))
            task.signals.error.connect(lambda exc, p=path, tok=token: self._import_error(tok, p, exc))
            pool().start(task)

    def _import_result(self, token: int, info) -> None:
        if token != self._import_job_token:
            return
        self.project.add_media(info)
        self._pending_imports -= 1
        self._finish_import_if_ready(token)

    def _import_error(self, token: int, path: str, exc: Exception) -> None:
        if token != self._import_job_token:
            return
        self._pending_imports -= 1
        log.warning("Medya analiz edilemedi: %s: %s", path, exc)
        self._finish_import_if_ready(token)

    def _finish_import_if_ready(self, token: int) -> None:
        if token != self._import_job_token or self._pending_imports > 0:
            return
        self.media_list.setEnabled(True)
        self.project.touch()
        self.refresh()

    def _start_dir(self) -> str:
        if self.project.media:
            from pathlib import Path

            return str(Path(self.project.media[-1].path).parent)
        return ""

    @staticmethod
    def _media_label(m: MediaItem) -> str:
        parts = [m.name, f"({fmt_time(m.duration, ms=False)}"]
        if m.media_type == "video":
            parts[-1] += f", {m.width}x{m.height}"
            if m.fps:
                parts[-1] += f", {m.fps:g}fps"
            if m.codec:
                parts[-1] += f", {m.codec}"
        else:
            parts[-1] += ", ses"
            if m.audio_codec:
                parts[-1] += f", {m.audio_codec}"
        if m.audio_channels == 1:
            parts[-1] += ", mono"
        elif m.audio_channels == 2:
            parts[-1] += ", stereo"
        elif m.audio_channels > 2:
            parts[-1] += f", {m.audio_channels}ch"
        parts[-1] += ")"
        label = "  ".join(parts)
        if not m.exists:
            label += "  [BULUNAMADI]"
        return label

    def _selected_media(self) -> MediaItem | None:
        item = self.media_list.currentItem()
        if item is None:
            return None
        return self.project.get_media(item.data(Qt.UserRole))

    def _add_selected_to_timeline(self) -> None:
        media = self._selected_media()
        if media is None:
            QMessageBox.information(self, "Medya seçilmedi", "Önce listeden bir video seçin.")
            return
        if not media.exists:
            QMessageBox.warning(self, "Dosya bulunamadı", f"Dosya artık mevcut değil:\n{media.path}")
            return
        self.history.push()
        if media.media_type == "audio":
            self.project.timeline.add_audio_media(media.id, media.name, media.duration)
        else:
            self.project.timeline.add_media(media.id, media.name, media.duration, media.has_audio)
        self.project.touch()
        self.refresh()

    # ---------------- onizleme (v0.5) ----------------
    def _build_preview_card(self) -> QWidget:
        self.preview_card = Card("Önizleme")
        self.preview_player = PreviewPlayer()
        self.preview_player.position_changed.connect(self._on_preview_position)
        self.preview_card.body.addWidget(self.preview_player)
        return self.preview_card

    def _on_preview_position(self, seconds: float) -> None:
        """Oynatma ilerledikce (veya seek/scrub ile) timeline playhead'ini takip ettirir."""
        self.timeline_view.set_playhead(seconds, emit=False)
        self._update_timecode()

    # ---------------- timeline ----------------
    def _build_timeline_card(self) -> QWidget:
        self.timeline_card = Card("Timeline")

        toolbar = QWidget()
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(0, 0, 0, 0)
        self.undo_btn = QPushButton("↶ Geri Al")
        self.undo_btn.setToolTip("Son düzenlemeyi geri alır (Ctrl+Z)")
        self.undo_btn.clicked.connect(self._undo)
        self.redo_btn = QPushButton("↷ İleri Al")
        self.redo_btn.setToolTip("Geri alınan düzenlemeyi tekrar uygular (Ctrl+Y)")
        self.redo_btn.clicked.connect(self._redo)
        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self._undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, activated=self._redo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, activated=self._redo)
        self.split_btn = QPushButton("Böl (ortadan)")
        self.split_btn.clicked.connect(self._split_selected)
        self.delete_btn = QPushButton("Sil")
        self.delete_btn.clicked.connect(self._delete_selected)
        self.ripple_delete_btn = QPushButton("Ripple Sil")
        self.ripple_delete_btn.setToolTip("Klibi siler, sonraki klipleri sola kaydırır.")
        self.ripple_delete_btn.clicked.connect(lambda: self._delete_selected(ripple=True))
        self.clip_audio_btn = QPushButton("Ses Klibi…")
        self.clip_audio_btn.setToolTip("Seçili ses klibi için kazanç, mute, fade in/out.")
        self.clip_audio_btn.clicked.connect(self._open_clip_audio_dialog)
        self.tracks_btn = QPushButton("Ses İzleri…")
        self.tracks_btn.setToolTip("Müzik/seslendirme izi ekle, kazanç/normalize/ducking ayarla.")
        self.tracks_btn.clicked.connect(self._open_audio_tracks_dialog)
        self.effects_music_btn = QPushButton("Efekt & Müzik…")
        self.effects_music_btn.setToolTip("Hazır görsel efektler, SFX ve müzik starter pack kütüphanesi.")
        self.effects_music_btn.clicked.connect(self._open_effects_music_dialog)
        self.subtitle_btn = QPushButton("Altyazı…")
        self.subtitle_btn.setToolTip("Whisper ile otomatik altyazı oluştur, SRT/VTT dışa aktar veya videoya göm.")
        self.subtitle_btn.clicked.connect(self._open_subtitle_dialog)
        self.scene_btn = QPushButton("Sahne Algıla…")
        self.scene_btn.setToolTip("Seçili video klibini, tespit edilen sahne kesimlerinde otomatik böler.")
        self.scene_btn.clicked.connect(self._open_scene_dialog)
        self.ai_edit_btn = QPushButton("AI Düzenle…")
        self.ai_edit_btn.setToolTip(
            "Sessizlik, uzun duraklama, tekrar ve dolgu kelimeleri tespit edip "
            "kabul ettiklerinizi timeline'dan otomatik keser."
        )
        self.ai_edit_btn.clicked.connect(self._open_ai_editor_dialog)
        self.keyframe_btn = QPushButton("Keyframe'ler…")
        self.keyframe_btn.setToolTip(
            "Seçili klip için Konum/Ölçek/Döndürme/Opaklık/Kırpma/Ses/Efekt keyframe'lerini "
            "grafik editörde düzenle (Bezier/easing destekli)."
        )
        self.keyframe_btn.clicked.connect(self._open_keyframe_dialog)
        self.pro_tools_btn = QPushButton("⚙ Profesyonel Araçlar…")
        self.pro_tools_btn.setToolTip("Marker, medya relink ve render kuyruğu gibi profesyonel kurgu araçları.")
        self.pro_tools_btn.clicked.connect(self._open_professional_tools)
        self.export_btn = QPushButton("Dışa Aktar…")
        self.export_btn.clicked.connect(self._open_export_dialog)
        self.shorts_btn = QPushButton("✦ AI Shorts Director")
        self.shorts_btn.setToolTip("Uzun videodan profesyonel Shorts adayları çıkarır; hook, payoff, pacing ve yeniden izleme sinyallerini optimize eder.")
        self.shorts_btn.clicked.connect(self._open_shorts_director)
        self.duration_label = _muted("")
        tb.addWidget(self.undo_btn)
        tb.addWidget(self.redo_btn)
        tb.addWidget(self.split_btn)
        tb.addWidget(self.delete_btn)
        tb.addWidget(self.ripple_delete_btn)
        tb.addWidget(self.clip_audio_btn)
        tb.addWidget(self.tracks_btn)
        tb.addWidget(self.effects_music_btn)
        tb.addWidget(self.subtitle_btn)
        tb.addWidget(self.scene_btn)
        tb.addWidget(self.ai_edit_btn)
        tb.addWidget(self.keyframe_btn)
        tb.addWidget(self.pro_tools_btn)
        tb.addWidget(self.shorts_btn)
        tb.addWidget(self.export_btn)
        tb.addStretch(1)
        tb.addWidget(self.duration_label)
        self.timeline_card.body.addWidget(toolbar)

        zoom_row = QWidget()
        zr = QHBoxLayout(zoom_row)
        zr.setContentsMargins(0, 0, 0, 0)
        self.snap_check = QCheckBox("Yapış (Snap)")
        self.snap_check.setChecked(True)
        self.snap_check.toggled.connect(lambda v: self.timeline_view.set_snap_enabled(v))
        zoom_out_btn = QPushButton("−")
        zoom_out_btn.setFixedWidth(28)
        zoom_out_btn.clicked.connect(lambda: self.timeline_view.zoom_out())
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedWidth(28)
        zoom_in_btn.clicked.connect(lambda: self.timeline_view.zoom_in())
        zoom_fit_btn = QPushButton("Sığdır")
        zoom_fit_btn.clicked.connect(lambda: self.timeline_view.zoom_fit())
        self.timecode_label = _muted("00:00:00:00 / 00:00:00:00")
        self.timecode_label.setStyleSheet("font-family: monospace;")
        zr.addWidget(self.snap_check)
        zr.addWidget(zoom_out_btn)
        zr.addWidget(zoom_in_btn)
        zr.addWidget(zoom_fit_btn)
        zr.addStretch(1)
        zr.addWidget(self.timecode_label)
        self.timeline_card.body.addWidget(zoom_row)

        self.timeline_view = TimelineView()
        self.timeline_view.clip_clicked.connect(self._on_clip_clicked)
        self.timeline_view.edited.connect(self._on_timeline_edited)
        self.timeline_view.playhead_changed.connect(self._on_playhead_changed)
        self.timeline_view.before_edit.connect(self.history.push)

        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setWidgetResizable(False)
        self.timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.timeline_scroll.setFixedHeight(180)
        self.timeline_scroll.setWidget(self.timeline_view)
        self.timeline_card.body.addWidget(self.timeline_scroll)

        self.timeline_empty_hint = _muted(
            "Timeline boş. Medya havuzundan bir video seçip \"Timeline'a Ekle\" deyin."
        )
        self.timeline_card.body.addWidget(self.timeline_empty_hint)
        return self.timeline_card

    def _on_clip_clicked(self, clip_id: str) -> None:
        self._update_toolbar()

    def _on_timeline_edited(self) -> None:
        """Timeline'da surukle-birak ile move/trim yapildiginda cagrilir."""
        self.project.touch()
        total = self.project.timeline.duration
        self.duration_label.setText(f"Süre: {fmt_time(total, ms=False)}")
        self.preview_player.seek_slider.setRange(0, int(round(total * 1000)))
        self._update_timecode()
        star = "•" if self.project.dirty else ""
        self.subtitle.setText(f"{self.project.name} {star}".strip())
        self._update_toolbar()

    def _on_playhead_changed(self, seconds: float) -> None:
        self.preview_player.seek(seconds)
        self._update_timecode()

    def _update_timecode(self) -> None:
        fps = self.project.timeline.fps
        cur = fmt_timecode(self.timeline_view.playhead(), fps)
        total = fmt_timecode(self.project.timeline.duration, fps)
        self.timecode_label.setText(f"{cur} / {total}")

    def _split_selected(self) -> None:
        cid = self.timeline_view.selected_clip_id()
        if not cid:
            QMessageBox.information(self, "Klip seçilmedi", "Bölmek için önce bir klip seçin.")
            return
        found = self.project.timeline.find(cid)
        if not found:
            return
        _track, clip = found
        mid = clip.start + clip.duration / 2
        self.history.push()
        if self.project.timeline.split(mid, clip_id=cid):
            self.project.touch()
            self.refresh()
        else:
            self.history.undo()  # bos islem: bosa alinan snapshot'i geri al
            QMessageBox.information(self, "Bölünemedi", "Klip bölmek için çok kısa.")

    def _delete_selected(self, ripple: bool = False) -> None:
        cid = self.timeline_view.selected_clip_id()
        if not cid:
            QMessageBox.information(self, "Klip seçilmedi", "Silmek için önce bir klip seçin.")
            return
        self.history.push()
        if self.project.timeline.remove(cid, ripple=ripple):
            self.project.touch()
            self.refresh()
        else:
            self.history.undo()

    def _undo(self) -> None:
        if not self.history.can_undo():
            return
        restored = self.history.undo()
        if restored is None:
            return
        self.project.timeline = restored
        self.project.touch()
        self.refresh()

    def _redo(self) -> None:
        if not self.history.can_redo():
            return
        restored = self.history.redo()
        if restored is None:
            return
        self.project.timeline = restored
        self.project.touch()
        self.refresh()

    def _update_toolbar(self) -> None:
        self.undo_btn.setEnabled(self.history.can_undo())
        self.redo_btn.setEnabled(self.history.can_redo())
        has_selection = self.timeline_view.selected_clip_id() is not None
        self.split_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.ripple_delete_btn.setEnabled(has_selection)
        self.clip_audio_btn.setEnabled(self._selected_audio_clip() is not None)
        self.subtitle_btn.setEnabled(bool(self.project.timeline.all_clips()))
        self.scene_btn.setEnabled(self._selected_video_clip() is not None)
        self.keyframe_btn.setEnabled(self._selected_any_clip() is not None)
        self.export_btn.setEnabled(bool(self.project.timeline.all_clips()))

    def _selected_video_clip(self):
        """Secili klip video izinde ve kaynak dosyasi diskte mevcutsa (track, clip, path) dondurur."""
        cid = self.timeline_view.selected_clip_id()
        if not cid:
            return None
        found = self.project.timeline.find(cid)
        if not found:
            return None
        track, clip = found
        if track.kind != "video":
            return None
        media = next((m for m in self.project.media if m.id == clip.media_id), None)
        if media is None or not media.exists:
            return None
        return track, clip, media.path

    def _selected_audio_clip(self):
        """Secili klip bir ses izindeyse (track, clip) dondurur, degilse None."""
        cid = self.timeline_view.selected_clip_id()
        if not cid:
            return None
        found = self.project.timeline.find(cid)
        if not found:
            return None
        track, clip = found
        return (track, clip) if track.kind == "audio" else None

    def _selected_any_clip(self):
        """Secili klip (izi fark etmeksizin) varsa (track, clip) dondurur. Keyframe
        editoru hem video hem ses klipleri icin gecerlidir (ör. ses klibinde yalnizca
        Ses sekmesi anlamlidir, video klibinde Donusum/Kirpma/Efektler de)."""
        cid = self.timeline_view.selected_clip_id()
        if not cid:
            return None
        return self.project.timeline.find(cid)

    def _open_professional_tools(self) -> None:
        dialog = ProfessionalToolsDialog(self.project, self.history, self.refresh, self)
        dialog.exec()

    def _open_keyframe_dialog(self) -> None:
        found = self._selected_any_clip()
        if found is None:
            QMessageBox.information(
                self, "Klip seçilmedi", "Keyframe düzenlemek için önce timeline'dan bir klip seçin.",
            )
            return
        _track, clip = found
        dialog = KeyframeEditorDialog(clip, self)
        if dialog.exec():
            self.history.push()
            dialog.apply()
            self.project.touch()
            self.refresh()

    def _open_effects_music_dialog(self) -> None:
        dialog = EffectsMusicDialog(self.project, self.history, self.refresh, self)
        dialog.exec()

    def _open_clip_audio_dialog(self) -> None:
        found = self._selected_audio_clip()
        if found is None:
            QMessageBox.information(
                self, "Ses klibi seçilmedi",
                "Kazanç/fade/mute ayarlamak için önce bir SES izindeki klibi seçin "
                "(video izindeki bağlı klip değil).",
            )
            return
        _track, clip = found
        dialog = ClipAudioDialog(clip, self)
        if dialog.exec():
            self.history.push()
            dialog.apply()
            self.project.touch()
            self.refresh()

    def _open_audio_tracks_dialog(self) -> None:
        self.history.push()
        dialog = AudioTracksDialog(self.project.timeline, self)
        dialog.exec()
        if dialog.changed:
            self.project.touch()
            self.refresh()
        else:
            self.history.undo()

    def _open_subtitle_dialog(self) -> None:
        media_paths = {m.id: m.path for m in self.project.media}
        dialog = SubtitleDialog(self.project.timeline, media_paths, self)
        dialog.exec()

    def _open_scene_dialog(self) -> None:
        found = self._selected_video_clip()
        if found is None:
            QMessageBox.information(
                self, "Klip seçilmedi",
                "Sahne algılamak için önce timeline'daki bir VİDEO klibini seçin "
                "(kaynak dosyası diskte mevcut olmalı).",
            )
            return
        _track, clip, media_path = found
        self.history.push()
        dialog = SceneDetectDialog(self.project.timeline, clip.id, media_path, self)
        if dialog.exec() and dialog.splits_applied:
            self.project.touch()
            self.refresh()
        else:
            self.history.undo()

    def _open_ai_editor_dialog(self) -> None:
        if not self.project.timeline.all_clips():
            QMessageBox.information(self, "Timeline boş", "Önce timeline'a en az bir klip ekleyin.")
            return
        media_paths = {m.id: m.path for m in self.project.media}
        self.history.push()
        dialog = AIEditorDialog(self.project.timeline, media_paths, self)
        dialog.exec()
        if dialog.changed:
            self.project.touch()
            self.refresh()
        else:
            self.history.undo()

    def _open_shorts_director(self) -> None:
        if not self.project.media:
            QMessageBox.information(self, "Medya yok", "Önce uzun videoyu medya havuzuna ekleyin.")
            return
        dialog = ShortsDirectorDialog(self.project, self)
        if dialog.exec() and dialog.changed:
            self.project.touch()
            self.refresh()

    def _open_export_dialog(self) -> None:
        if not self.project.timeline.all_clips():
            QMessageBox.information(self, "Timeline boş", "Önce timeline'a en az bir klip ekleyin.")
            return
        dialog = ExportDialog(self.project, self)
        dialog.exec()

    # ---------------- genel yenileme ----------------
    def set_project(self, project: Project) -> None:
        self.project = project
        self.history.set_timeline(project.timeline)
        self.refresh()

    def _queue_missing_thumbnails(self, token: int) -> None:
        if token != self._thumb_job_token:
            return
        for media in self.project.media:
            if media.media_type == "video" and media.exists and not media.thumbnail:
                self._queue_thumbnail(media, token)

    def _queue_thumbnail(self, media: MediaItem, token: int) -> None:
        """Thumbnail'i FFmpeg ile UI thread'i disinda uret."""
        from .background import BackgroundTask, pool
        task = BackgroundTask(lambda: generate_thumbnail(media.path, media.duration, media.media_type) or "")
        task.signals.result.connect(lambda thumb, tok=token, mid=media.id: self._thumbnail_ready(tok, mid, thumb))
        pool().start(task)

    def _thumbnail_ready(self, token: int, media_id: str, thumb: str) -> None:
        if token != self._thumb_job_token:
            return
        media = self.project.get_media(media_id)
        if media is not None:
            media.thumbnail = thumb
        for index in range(self.media_list.count()):
            item = self.media_list.item(index)
            if item.data(Qt.UserRole) == media_id:
                item.setIcon(_icon_for(media))
                break

    def refresh(self) -> None:
        star = "•" if self.project.dirty else ""
        self.subtitle.setText(f"{self.project.name} {star}".strip())

        # Kritik performans kuralı: refresh() içinde ffmpeg çalıştırma.
        # Eski sürüm her yenilemede thumbnail üretimini ana Qt thread'inde
        # yapıyordu; büyük projelerde bu, timeline işlemlerini de donduruyordu.
        self._thumb_job_token += 1
        token = self._thumb_job_token
        self.media_list.clear()
        for m in self.project.media:
            label = self._media_label(m)
            item = QListWidgetItem(_icon_for(m), label)
            item.setData(Qt.UserRole, m.id)
            self.media_list.addItem(item)
        self.media_empty_hint.setVisible(not self.project.media)
        # Mevcut eski projelerde eksik thumbnail'lar da thread pool'da uretilir.
        # İlk event-loop turuna bırakmak refresh()'in layout işini mümkün olduğunca
        # kısa tutar; asıl FFmpeg işi BackgroundTask'tadır.
        QTimer.singleShot(0, lambda tok=token: self._queue_missing_thumbnails(tok))

        self.timeline_view.set_timeline(self.project.timeline)
        media_paths = {m.id: m.path for m in self.project.media}
        self.timeline_view.set_media_paths(media_paths)
        self.preview_player.set_timeline(self.project.timeline, media_paths)
        has_clips = bool(self.project.timeline.all_clips())
        self.timeline_empty_hint.setVisible(not has_clips)
        total = self.project.timeline.duration
        self.duration_label.setText(f"Süre: {fmt_time(total, ms=False)}")
        self._update_timecode()
        self._update_toolbar()
