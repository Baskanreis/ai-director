"""KEYFRAME ENGINE — profesyonel animasyon editoru (v1.4).

`KeyframeEditorDialog`, bir klibin tum keyframe'lenebilir ozelliklerini
(Position/Scale/Rotation/Opacity/Crop/Volume/Effects) tek bir grafik
editorde duzenlemeyi saglar: ozellik sec, egri uzerinde tikla-ekle,
surukle-tasi, sag-tik ile kolaylik (easing) sec, Bezier kontrol agirliklarini
ayarla. Alttaki matematik `app.motion.engine` (saf Python, ffmpeg'den
bagimsiz) ile `app.effects.video_effects` (render) arasinda PAYLASILIR —
yani editorde gorulen egri, render'da uretilen egriyle birebir aynidir.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.motion.engine import add_or_update_keyframe, remove_keyframe, sample_curve
from app.timeline.model import EASINGS, Clip, Keyframe

ACCENT = "#7c5cff"
GRID = "#2a3042"
CURVE = "#7c5cff"
POINT = "#e6e9f2"
POINT_SEL = "#f5a623"

EASING_LABELS: dict[str, str] = {
    "linear": "Doğrusal",
    "hold": "Basamak (Hold)",
    "ease_in": "Yumuşak Giriş",
    "ease_out": "Yumuşak Çıkış",
    "ease_in_out": "Yumuşak Giriş/Çıkış",
    "bezier": "Bezier (özel)",
}


@dataclass(frozen=True)
class PropertySpec:
    key: str           # Clip.keyframes sozlugundeki anahtar
    label: str
    group: str
    vmin: float
    vmax: float
    step: float
    unit: str = ""

    def default_for(self, clip: Clip) -> float:
        if self.key == "volume":
            return clip.gain_db
        if self.key.startswith("effect:"):
            from app.timeline.model import EFFECT_KEYFRAME_DEFAULTS
            return EFFECT_KEYFRAME_DEFAULTS[self.key.split(":", 1)[1]]
        if self.key.startswith("crop_"):
            if clip.crop:
                idx = {"crop_x": 0, "crop_y": 1, "crop_w": 2, "crop_h": 3}[self.key]
                return clip.crop[idx]
            return 1.0 if self.key in ("crop_w", "crop_h") else 0.0
        return float(getattr(clip, self.key, 0.0))


PROPERTY_SPECS: list[PropertySpec] = [
    PropertySpec("pos_x", "Konum X", "Dönüşüm", -2000.0, 2000.0, 1.0, "px"),
    PropertySpec("pos_y", "Konum Y", "Dönüşüm", -2000.0, 2000.0, 1.0, "px"),
    PropertySpec("scale", "Ölçek", "Dönüşüm", 0.01, 10.0, 0.01),
    PropertySpec("rotation", "Döndürme", "Dönüşüm", -3600.0, 3600.0, 1.0, "°"),
    PropertySpec("opacity", "Opaklık", "Dönüşüm", 0.0, 1.0, 0.01),
    PropertySpec("crop_x", "Kırpma X", "Kırpma", 0.0, 1.0, 0.01),
    PropertySpec("crop_y", "Kırpma Y", "Kırpma", 0.0, 1.0, 0.01),
    PropertySpec("crop_w", "Kırpma Genişlik", "Kırpma", 0.01, 1.0, 0.01),
    PropertySpec("crop_h", "Kırpma Yükseklik", "Kırpma", 0.01, 1.0, 0.01),
    PropertySpec("volume", "Ses Seviyesi", "Ses", -60.0, 24.0, 0.5, "dB"),
    PropertySpec("effect:brightness", "Parlaklık", "Efektler", -1.0, 1.0, 0.01),
    PropertySpec("effect:contrast", "Kontrast", "Efektler", 0.0, 3.0, 0.01),
    PropertySpec("effect:saturation", "Doygunluk", "Efektler", 0.0, 3.0, 0.01),
    PropertySpec("effect:gamma", "Gamma", "Efektler", 0.1, 3.0, 0.01),
]


class KeyframeCurveWidget(QWidget):
    """Tek bir ozelligin keyframe egrisini cizen/duzenleyen QPainter widget'i."""

    changed = Signal()
    selection_changed = Signal(object)  # Keyframe | None

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self._spec: PropertySpec | None = None
        self._duration = 1.0
        self._default = 0.0
        self._keyframes: list[Keyframe] = []
        self._selected_time: float | None = None
        self._dragging = False

    # ---- veri baglama ----
    def bind(self, spec: PropertySpec, keyframes: list[Keyframe], duration: float, default: float) -> None:
        self._spec = spec
        self._keyframes = list(keyframes)
        self._duration = max(duration, 0.1)
        self._default = default
        self._selected_time = None
        self.selection_changed.emit(None)
        self.update()

    def keyframes(self) -> list[Keyframe]:
        return list(self._keyframes)

    def selected_keyframe(self) -> Keyframe | None:
        if self._selected_time is None:
            return None
        return next((k for k in self._keyframes if abs(k.time - self._selected_time) < 1e-3), None)

    # ---- koordinat donusumleri ----
    def _plot_rect(self) -> QRectF:
        m = 10.0
        return QRectF(m, m, max(self.width() - 2 * m, 1.0), max(self.height() - 2 * m, 1.0))

    def _to_px(self, t: float, v: float) -> QPointF:
        if self._spec is None:
            return QPointF(0, 0)
        rect = self._plot_rect()
        x = rect.left() + (t / self._duration) * rect.width()
        vr = max(self._spec.vmax - self._spec.vmin, 1e-6)
        y = rect.bottom() - ((v - self._spec.vmin) / vr) * rect.height()
        return QPointF(x, y)

    def _from_px(self, pos: QPointF) -> tuple[float, float]:
        rect = self._plot_rect()
        t = (pos.x() - rect.left()) / max(rect.width(), 1.0) * self._duration
        vr = (self._spec.vmax - self._spec.vmin) if self._spec else 1.0
        v = self._spec.vmin + (1.0 - (pos.y() - rect.top()) / max(rect.height(), 1.0)) * vr
        t = min(max(t, 0.0), self._duration)
        v = min(max(v, self._spec.vmin), self._spec.vmax) if self._spec else v
        return t, v

    # ---- cizim ----
    def paintEvent(self, event) -> None:  # noqa: N802 (Qt API)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self._plot_rect()
        painter.fillRect(self.rect(), QColor("#171a23"))

        pen = QPen(QColor(GRID))
        pen.setWidth(1)
        painter.setPen(pen)
        for i in range(5):
            y = rect.top() + rect.height() * i / 4
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
        for i in range(6):
            x = rect.left() + rect.width() * i / 5
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))

        if self._spec is None:
            painter.end()
            return

        # egri
        pts = sample_curve(self._keyframes, self._default, self._duration, steps=160)
        curve_pen = QPen(QColor(CURVE))
        curve_pen.setWidth(2)
        painter.setPen(curve_pen)
        prev = None
        for t, v in pts:
            p = self._to_px(t, v)
            if prev is not None:
                painter.drawLine(prev, p)
            prev = p

        # keyframe noktalari
        for kf in self._keyframes:
            p = self._to_px(kf.time, kf.value)
            selected = self._selected_time is not None and abs(kf.time - self._selected_time) < 1e-3
            color = QColor(POINT_SEL if selected else POINT)
            painter.setPen(QPen(QColor(ACCENT), 1.5))
            painter.setBrush(color)
            r = 5.5 if selected else 4.5
            painter.drawEllipse(p, r, r)
        painter.end()

    # ---- fare etkilesimi ----
    def _nearest_keyframe(self, pos: QPointF, tol: float = 10.0) -> Keyframe | None:
        best, best_d = None, tol
        for kf in self._keyframes:
            p = self._to_px(kf.time, kf.value)
            d = ((p.x() - pos.x()) ** 2 + (p.y() - pos.y()) ** 2) ** 0.5
            if d < best_d:
                best, best_d = kf, d
        return best

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self._spec is None:
            return
        if event.button() == Qt.LeftButton:
            hit = self._nearest_keyframe(event.position())
            if hit is not None:
                self._selected_time = hit.time
                self._dragging = True
            else:
                t, v = self._from_px(event.position())
                self._keyframes = add_or_update_keyframe(self._keyframes, t, v)
                self._selected_time = t
                self.changed.emit()
            self.selection_changed.emit(self.selected_keyframe())
            self.update()
        elif event.button() == Qt.RightButton:
            hit = self._nearest_keyframe(event.position())
            if hit is not None:
                self._selected_time = hit.time
                self.selection_changed.emit(hit)
                self.update()
                self._show_context_menu(event.globalPosition().toPoint(), hit)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._dragging and self._selected_time is not None and self._spec is not None:
            kf = self.selected_keyframe()
            if kf is None:
                return
            t, v = self._from_px(event.position())
            self._keyframes = remove_keyframe(self._keyframes, kf.time)
            self._keyframes = add_or_update_keyframe(self._keyframes, t, v, kf.easing, kf.bezier)
            self._selected_time = t
            self.changed.emit()
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._dragging = False

    def _show_context_menu(self, global_pos, kf: Keyframe) -> None:
        menu = QMenu(self)
        for easing in EASINGS:
            action = menu.addAction(EASING_LABELS.get(easing, easing))
            action.setCheckable(True)
            action.setChecked(kf.easing == easing)
            action.triggered.connect(lambda _=False, e=easing: self._set_easing(kf.time, e))
        menu.addSeparator()
        delete_action = menu.addAction("Keyframe'i Sil")
        delete_action.triggered.connect(lambda: self._delete(kf.time))
        menu.exec(global_pos)

    def _set_easing(self, time: float, easing: str) -> None:
        kf = next((k for k in self._keyframes if abs(k.time - time) < 1e-3), None)
        if kf is None:
            return
        bezier = kf.bezier if easing == "bezier" else None
        self._keyframes = remove_keyframe(self._keyframes, time)
        self._keyframes = add_or_update_keyframe(self._keyframes, time, kf.value, easing, bezier)
        self.changed.emit()
        self.selection_changed.emit(self.selected_keyframe())
        self.update()

    def _delete(self, time: float) -> None:
        self._keyframes = remove_keyframe(self._keyframes, time)
        if self._selected_time is not None and abs(self._selected_time - time) < 1e-3:
            self._selected_time = None
        self.changed.emit()
        self.selection_changed.emit(None)
        self.update()

    def delete_selected(self) -> None:
        if self._selected_time is not None:
            self._delete(self._selected_time)

    def clear_all(self) -> None:
        self._keyframes = []
        self._selected_time = None
        self.changed.emit()
        self.selection_changed.emit(None)
        self.update()

    def update_selected_bezier(self, y1: float, y2: float) -> None:
        kf = self.selected_keyframe()
        if kf is None or kf.easing != "bezier":
            return
        self._keyframes = remove_keyframe(self._keyframes, kf.time)
        self._keyframes = add_or_update_keyframe(self._keyframes, kf.time, kf.value, "bezier", (y1, y2))
        self.changed.emit()
        self.update()


class KeyframeEditorDialog(QDialog):
    """Bir klibin tum keyframe parcalarini duzenleyen ana diyalog.

    `ClipAudioDialog` ile ayni desen: `exec()` sonrasi `apply()` cagrilirsa
    degisiklikler `clip.keyframes`e yazilir.
    """

    def __init__(self, clip: Clip, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.clip = clip
        self.setWindowTitle(f"Keyframe Engine — {clip.name}")
        self.setMinimumSize(720, 480)

        # calisma kopyasi: Iptal'de orijinal klip degismez
        self._working: dict[str, list[Keyframe]] = {
            spec.key: list(clip.keyframes.get(spec.key, [])) for spec in PROPERTY_SPECS
        }

        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("Özellik:"))
        self.prop_combo = QComboBox()
        groups_seen: set[str] = set()
        for spec in PROPERTY_SPECS:
            if spec.group not in groups_seen:
                groups_seen.add(spec.group)
            self.prop_combo.addItem(f"{spec.group} — {spec.label}", spec.key)
        self.prop_combo.currentIndexChanged.connect(self._on_property_changed)
        top.addWidget(self.prop_combo, 1)
        layout.addLayout(top)

        self.curve = KeyframeCurveWidget()
        self.curve.changed.connect(self._on_curve_changed)
        self.curve.selection_changed.connect(self._on_selection_changed)
        layout.addWidget(self.curve, 1)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Zaman (sn)"))
        self.time_spin = QDoubleSpinBox()
        self.time_spin.setRange(0.0, 10_000.0)
        self.time_spin.setSingleStep(0.1)
        self.time_spin.setDecimals(2)
        controls.addWidget(self.time_spin)

        controls.addWidget(QLabel("Değer"))
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setDecimals(3)
        controls.addWidget(self.value_spin)

        controls.addWidget(QLabel("Yumuşatma"))
        self.easing_combo = QComboBox()
        for easing in EASINGS:
            self.easing_combo.addItem(EASING_LABELS.get(easing, easing), easing)
        controls.addWidget(self.easing_combo)

        self.bezier_label = QLabel("Bezier y1/y2")
        controls.addWidget(self.bezier_label)
        self.bezier_y1 = QDoubleSpinBox()
        self.bezier_y1.setRange(-1.0, 2.0)
        self.bezier_y1.setSingleStep(0.05)
        self.bezier_y1.setDecimals(2)
        controls.addWidget(self.bezier_y1)
        self.bezier_y2 = QDoubleSpinBox()
        self.bezier_y2.setRange(-1.0, 2.0)
        self.bezier_y2.setSingleStep(0.05)
        self.bezier_y2.setDecimals(2)
        controls.addWidget(self.bezier_y2)
        layout.addLayout(controls)

        self.time_spin.valueChanged.connect(self._on_fields_edited)
        self.value_spin.valueChanged.connect(self._on_fields_edited)
        self.easing_combo.currentIndexChanged.connect(self._on_easing_field_changed)
        self.bezier_y1.valueChanged.connect(self._on_bezier_field_changed)
        self.bezier_y2.valueChanged.connect(self._on_bezier_field_changed)

        buttons_row = QHBoxLayout()
        self.apply_point_btn = QPushButton("Keyframe Ekle/Güncelle")
        self.apply_point_btn.clicked.connect(self._apply_field_point)
        buttons_row.addWidget(self.apply_point_btn)
        self.delete_btn = QPushButton("Seçileni Sil")
        self.delete_btn.clicked.connect(self.curve.delete_selected)
        buttons_row.addWidget(self.delete_btn)
        self.clear_btn = QPushButton("Bu Özelliği Temizle")
        self.clear_btn.clicked.connect(self._clear_current)
        buttons_row.addWidget(self.clear_btn)
        buttons_row.addStretch(1)
        layout.addLayout(buttons_row)

        hint = QLabel(
            "Eğri üzerinde boş bir yere tıklayarak keyframe ekleyin, mevcut bir noktayı "
            "sürükleyerek taşıyın, sağ tıklayarak yumuşatma (easing) türünü seçin."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._updating_fields = False
        self._on_property_changed(0)

    # ---- yardimcilar ----
    def _current_spec(self) -> PropertySpec:
        key = self.prop_combo.currentData()
        return next(s for s in PROPERTY_SPECS if s.key == key)

    def _on_property_changed(self, _index: int) -> None:
        spec = self._current_spec()
        self.value_spin.setRange(spec.vmin, spec.vmax)
        self.value_spin.setSuffix(f" {spec.unit}" if spec.unit else "")
        self.time_spin.setRange(0.0, max(self.clip.duration, 0.1))
        self.curve.bind(spec, self._working[spec.key], self.clip.duration, spec.default_for(self.clip))
        self._on_selection_changed(None)

    def _on_curve_changed(self) -> None:
        spec = self._current_spec()
        self._working[spec.key] = self.curve.keyframes()

    def _on_selection_changed(self, kf: Keyframe | None) -> None:
        self._updating_fields = True
        try:
            if kf is not None:
                self.time_spin.setValue(kf.time)
                self.value_spin.setValue(kf.value)
                idx = self.easing_combo.findData(kf.easing)
                self.easing_combo.setCurrentIndex(max(idx, 0))
                y1, y2 = kf.bezier if kf.bezier else (0.42, 0.58)
                self.bezier_y1.setValue(y1)
                self.bezier_y2.setValue(y2)
            is_bezier = kf is not None and kf.easing == "bezier"
            self.bezier_label.setVisible(is_bezier)
            self.bezier_y1.setVisible(is_bezier)
            self.bezier_y2.setVisible(is_bezier)
            self.delete_btn.setEnabled(kf is not None)
        finally:
            self._updating_fields = False

    def _on_fields_edited(self) -> None:
        pass  # degerler yalnizca "Ekle/Guncelle" ile uygulanir (yanlislikla surukleme/yazma karismasin)

    def _apply_field_point(self) -> None:
        spec = self._current_spec()
        easing = self.easing_combo.currentData()
        bezier = (self.bezier_y1.value(), self.bezier_y2.value()) if easing == "bezier" else None
        kfs = add_or_update_keyframe(
            self.curve.keyframes(), self.time_spin.value(), self.value_spin.value(), easing, bezier
        )
        self.curve.bind(spec, kfs, self.clip.duration, spec.default_for(self.clip))
        self._working[spec.key] = kfs

    def _on_easing_field_changed(self) -> None:
        if self._updating_fields:
            return
        kf = self.curve.selected_keyframe()
        if kf is None:
            return
        easing = self.easing_combo.currentData()
        self.curve._set_easing(kf.time, easing)  # noqa: SLF001 (ayni modul icinde dar kapsam)
        self._on_curve_changed()

    def _on_bezier_field_changed(self) -> None:
        if self._updating_fields:
            return
        self.curve.update_selected_bezier(self.bezier_y1.value(), self.bezier_y2.value())
        self._on_curve_changed()

    def _clear_current(self) -> None:
        if QMessageBox.question(
            self, "Temizle", "Bu özelliğin tüm keyframe'lerini silmek istediğinize emin misiniz?",
        ) != QMessageBox.Yes:
            return
        self.curve.clear_all()
        self._on_curve_changed()

    # ---- disa aktarim ----
    def apply(self) -> None:
        """Diyalogdaki tum ozellik egrilerini klibe yazar (yalnizca `Ok` ile kapatildiysa cagirin)."""
        for key, kfs in self._working.items():
            if kfs:
                self.clip.keyframes[key] = kfs
            elif key in self.clip.keyframes:
                del self.clip.keyframes[key]


__all__ = ["KeyframeEditorDialog", "KeyframeCurveWidget", "PropertySpec", "PROPERTY_SPECS"]
