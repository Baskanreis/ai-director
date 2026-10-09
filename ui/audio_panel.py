"""Ses özellikleri diyalogları: klip (kazanç/fade/mute) ve iz (rol/kazanç/
normalizasyon/ducking) — v0.7 Audio Engine."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.timeline.model import Clip, Timeline, Track

ROLE_LABELS: dict[str, str] = {"": "Jenerik", "music": "Müzik", "voice": "Seslendirme"}
ROLE_KEYS = list(ROLE_LABELS.keys())


class ClipAudioDialog(QDialog):
    """Tek bir ses klibi için kazanç, mute, fade in/out ayarları."""

    def __init__(self, clip: Clip, parent=None) -> None:
        super().__init__(parent)
        self.clip = clip
        self.setWindowTitle(f"Ses Klibi — {clip.name}")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.gain_spin = QDoubleSpinBox()
        self.gain_spin.setRange(-60.0, 24.0)
        self.gain_spin.setSuffix(" dB")
        self.gain_spin.setSingleStep(0.5)
        self.gain_spin.setValue(clip.gain_db)
        form.addRow("Kazanç / Ses seviyesi", self.gain_spin)

        self.mute_check = QCheckBox("Bu klibi sessize al")
        self.mute_check.setChecked(clip.muted)
        form.addRow("", self.mute_check)

        max_fade = max(clip.duration / 2, 0.0)
        self.fade_in_spin = QDoubleSpinBox()
        self.fade_in_spin.setRange(0.0, max(max_fade, 0.1))
        self.fade_in_spin.setSuffix(" sn")
        self.fade_in_spin.setSingleStep(0.1)
        self.fade_in_spin.setValue(min(clip.fade_in, max_fade))
        form.addRow("Fade In (açılış)", self.fade_in_spin)

        self.fade_out_spin = QDoubleSpinBox()
        self.fade_out_spin.setRange(0.0, max(max_fade, 0.1))
        self.fade_out_spin.setSuffix(" sn")
        self.fade_out_spin.setSingleStep(0.1)
        self.fade_out_spin.setValue(min(clip.fade_out, max_fade))
        form.addRow("Fade Out (kapanış)", self.fade_out_spin)

        hint = QLabel(f"Klip süresi: {clip.duration:.2f} sn")
        hint.setObjectName("Muted")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def apply(self) -> None:
        """Diyalogdaki değerleri klibe yazar (yalnızca `Ok` ile kapatıldıysa çağırın)."""
        self.clip.gain_db = self.gain_spin.value()
        self.clip.muted = self.mute_check.isChecked()
        self.clip.fade_in = self.fade_in_spin.value()
        self.clip.fade_out = self.fade_out_spin.value()


class TrackAudioDialog(QDialog):
    """Bir ses izinin (Track) rolü, kazancı, mute/normalizasyon/ducking ayarları."""

    def __init__(self, track: Track, timeline: Timeline, parent=None) -> None:
        super().__init__(parent)
        self.track = track
        self.timeline = timeline
        self.setWindowTitle(f"Ses İzi — {track.name}")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.role_box = QComboBox()
        self.role_box.addItems([ROLE_LABELS[k] for k in ROLE_KEYS])
        self.role_box.setCurrentIndex(ROLE_KEYS.index(track.role if track.role in ROLE_KEYS else ""))
        self.role_box.currentIndexChanged.connect(self._update_duck_enabled)
        form.addRow("İz türü", self.role_box)

        self.gain_spin = QDoubleSpinBox()
        self.gain_spin.setRange(-60.0, 24.0)
        self.gain_spin.setSuffix(" dB")
        self.gain_spin.setSingleStep(0.5)
        self.gain_spin.setValue(track.gain_db)
        form.addRow("İz kazancı", self.gain_spin)

        self.mute_check = QCheckBox("Bu izi sessize al")
        self.mute_check.setChecked(track.muted)
        form.addRow("", self.mute_check)

        self.normalize_check = QCheckBox("Yüksek sesliliği normalize et (loudnorm, -16 LUFS)")
        self.normalize_check.setChecked(track.normalize)
        form.addRow("", self.normalize_check)

        self.duck_check = QCheckBox("Seslendirme (voice) izleri konuşurken otomatik kıs (ducking)")
        self.duck_check.setChecked(track.duck)
        form.addRow("", self.duck_check)

        hint = QLabel(
            "Ducking yalnızca \"Müzik\" türündeki izler için, ve yalnızca timeline'da en "
            "az bir \"Seslendirme\" izi olduğunda uygulanır."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._update_duck_enabled()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_duck_enabled(self) -> None:
        is_music = ROLE_KEYS[self.role_box.currentIndex()] == "music"
        self.duck_check.setEnabled(is_music)
        if not is_music:
            self.duck_check.setChecked(False)

    def apply(self) -> None:
        self.track.role = ROLE_KEYS[self.role_box.currentIndex()]
        self.track.gain_db = self.gain_spin.value()
        self.track.muted = self.mute_check.isChecked()
        self.track.normalize = self.normalize_check.isChecked()
        self.track.duck = self.duck_check.isChecked() and self.track.role == "music"


class AudioTracksDialog(QDialog):
    """Timeline'daki ses izlerini listeler; yeni müzik/seslendirme izi eklemeyi ve
    seçili izi (rol/kazanç/mute/normalizasyon/ducking) düzenlemeyi sağlar."""

    def __init__(self, timeline: Timeline, parent=None) -> None:
        super().__init__(parent)
        self.timeline = timeline
        self.changed = False
        self.setWindowTitle("Ses İzleri")
        self.setMinimumSize(420, 320)

        layout = QVBoxLayout(self)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _: self._edit_selected())
        layout.addWidget(self.list)

        add_row = QHBoxLayout()
        add_music = QPushButton("+ Müzik İzi Ekle")
        add_music.clicked.connect(lambda: self._add_track("music"))
        add_voice = QPushButton("+ Seslendirme İzi Ekle")
        add_voice.clicked.connect(lambda: self._add_track("voice"))
        add_row.addWidget(add_music)
        add_row.addWidget(add_voice)
        layout.addLayout(add_row)

        edit_row = QHBoxLayout()
        edit_btn = QPushButton("Düzenle…")
        edit_btn.clicked.connect(self._edit_selected)
        edit_row.addWidget(edit_btn)
        edit_row.addStretch(1)
        layout.addLayout(edit_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self._refresh()

    def _refresh(self) -> None:
        self.list.clear()
        for t in self.timeline.tracks:
            if t.kind != "audio":
                continue
            bits = [ROLE_LABELS.get(t.role, t.role or "Jenerik")]
            if t.muted:
                bits.append("sessiz")
            if t.gain_db:
                bits.append(f"{t.gain_db:+.1f}dB")
            if t.normalize:
                bits.append("normalize")
            if t.duck:
                bits.append("ducking")
            item = QListWidgetItem(f"{t.name}  ({', '.join(bits)})")
            item.setData(Qt.UserRole, t.id)
            self.list.addItem(item)

    def _selected_track(self) -> Track | None:
        item = self.list.currentItem()
        if item is None:
            return None
        track_id = item.data(0x0100)
        for t in self.timeline.tracks:
            if t.id == track_id:
                return t
        return None

    def _add_track(self, role: str) -> None:
        self.timeline.add_audio_track(role=role)
        self.changed = True
        self._refresh()

    def _edit_selected(self) -> None:
        track = self._selected_track()
        if track is None:
            QMessageBox.information(self, "İz seçilmedi", "Önce listeden bir ses izi seçin.")
            return
        dialog = TrackAudioDialog(track, self.timeline, self)
        if dialog.exec() == QDialog.Accepted:
            dialog.apply()
            self.changed = True
            self._refresh()
