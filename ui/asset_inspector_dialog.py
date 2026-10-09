from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout,
)
from app.effects.asset_inspector import AssetInspectorController


class AssetInspectorDialog(QDialog):
    """Live editor for a selected creative asset stack entry.

    The dialog only mutates the Timeline while the caller's transaction is active;
    the Studio wraps accepted changes in one undo snapshot.
    """
    def __init__(self, timeline, clip_id: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Creative Asset Inspector")
        self.setMinimumWidth(460)
        self.controller = AssetInspectorController(timeline)
        self.clip_id = clip_id
        self._items = []
        self._original = None

        root = QVBoxLayout(self)
        root.addWidget(QLabel("Timeline asset katmanını canlı düzenle"))
        self.asset_combo = QComboBox()
        self.asset_combo.currentIndexChanged.connect(self._load_item)
        root.addWidget(self.asset_combo)

        form = QFormLayout()
        self.intensity = self._spin(0, 2, 0.01, 1.0)
        self.speed = self._spin(.05, 8, .05, 1.0)
        self.blend = self._spin(0, 1, .01, 1.0)
        self.duration = self._spin(.04, 60, .01, .5)
        self.position = self._spin(0, 3600, .01, 0)
        self.variation = self._spin(0, 9999, 1, 0)
        for label, widget in (("Intensity", self.intensity), ("Speed", self.speed),
                              ("Blend", self.blend), ("Duration (s)", self.duration),
                              ("Position (s)", self.position), ("Variation", self.variation)):
            form.addRow(label, widget)
        root.addLayout(form)

        row = QHBoxLayout()
        self.similar_btn = QPushButton("Şuna Benzer")
        self.similar_btn.clicked.connect(self._show_similar)
        self.replace_btn = QPushButton("Seçileni Değiştir")
        self.replace_btn.clicked.connect(self._replace)
        row.addWidget(self.similar_btn); row.addWidget(self.replace_btn)
        root.addLayout(row)
        self.similar_list = QListWidget()
        root.addWidget(self.similar_list)
        self.similar_list.itemDoubleClicked.connect(self._replace)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self._load_clip()

    @staticmethod
    def _spin(lo, hi, step, value):
        w = QDoubleSpinBox(); w.setRange(lo, hi); w.setSingleStep(step); w.setValue(value); return w

    def _load_clip(self):
        self.asset_combo.clear()
        found = self.controller.timeline.find(self.clip_id)
        if not found: return
        stack = found[1].creative_metadata.get("asset_stack", [])
        self._items = [(i, x) for i, x in enumerate(stack) if x.get("asset_id")]
        for _, item in self._items:
            self.asset_combo.addItem(f"{item.get('asset_name', item['asset_id'])} • {item.get('asset_kind','asset')}", item.get('asset_id'))
        self._load_item(0)

    def _load_item(self, index):
        if index < 0 or index >= len(self._items): return
        asset_id = self.asset_combo.itemData(index); stack_index = self._items[index][0]
        snap = self.controller.snapshot(self.clip_id, asset_id, stack_index)
        if not snap: return
        self._original = snap
        self.intensity.setValue(float(snap.get("intensity", 1.0)))
        self.speed.setValue(float(snap.get("speed", 1.0)))
        self.blend.setValue(float(snap.get("blend", 1.0)))
        self.duration.setValue(float(snap.get("duration", .5)))
        self.position.setValue(float(snap.get("position", 0.0)))
        self.variation.setValue(float(snap.get("asset_variant", 0)))
        self.similar_list.clear()

    def _apply_live(self):
        idx = self.asset_combo.currentIndex()
        if idx < 0: return
        aid = self.asset_combo.itemData(idx); stack_index = self._items[idx][0]
        self.controller.update(self.clip_id, aid, stack_index,
            intensity=self.intensity.value(), speed=self.speed.value(), blend=self.blend.value(),
            duration=self.duration.value(), position=self.position.value(), variation=int(self.variation.value()))

    def _show_similar(self):
        self._apply_live()
        idx = self.asset_combo.currentIndex()
        if idx < 0: return
        aid = self.asset_combo.itemData(idx)
        self.similar_list.clear()
        for asset, score in self.controller.similar(aid, 20):
            item = __import__('PySide6.QtWidgets', fromlist=['QListWidgetItem']).QListWidgetItem(f"{asset.name}  •  {score:.3f}")
            item.setData(Qt.UserRole, asset.id)
            self.similar_list.addItem(item)

    def _replace(self, item=None):
        if item is None: item = self.similar_list.currentItem()
        if item is None: return
        idx = self.asset_combo.currentIndex()
        if idx < 0: return
        aid = self.asset_combo.itemData(idx); stack_index = self._items[idx][0]
        self.controller.replace(self.clip_id, aid, item.data(Qt.UserRole), stack_index)
        self._load_clip()

    def accept(self):
        self._apply_live()
        super().accept()
