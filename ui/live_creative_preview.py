from __future__ import annotations

import json
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget
from app.ui.creative_preview import render_asset_preview


class LiveCreativePreview(QWidget):
    """Lightweight animated procedural preview with play/scrub controls."""
    position_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.asset = None
        self.position = 0.35
        self.playing = False
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self._tick)
        self.image = QLabel()
        self.image.setMinimumSize(300, 170)
        self.image.setAlignment(Qt.AlignCenter)
        self.image.setStyleSheet("background:#17171c;border:1px solid #34343c;border-radius:8px;")
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedWidth(42)
        self.play_btn.clicked.connect(self.toggle)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setValue(350)
        self.slider.valueChanged.connect(self._slider)
        row = QHBoxLayout(); row.setContentsMargins(0, 4, 0, 0)
        row.addWidget(self.play_btn); row.addWidget(self.slider, 1)
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.image); lay.addLayout(row)

    def set_asset(self, asset) -> None:
        self.asset = asset
        self.position = 0.35
        self.slider.blockSignals(True); self.slider.setValue(350); self.slider.blockSignals(False)
        self._render()

    def _render(self):
        if self.asset is None:
            self.image.clear(); return
        key = json.dumps(self.asset.params, sort_keys=True, ensure_ascii=False)
        pm = render_asset_preview(self.asset, (max(300, self.image.width()), max(170, self.image.height()),), self.position)
        self.image.setPixmap(pm)

    def _slider(self, value: int):
        self.position = value / 1000.0
        self._render()
        self.position_changed.emit(self.position)

    def _tick(self):
        self.position += 0.025
        if self.position >= 1.0:
            self.position = 0.0
        self.slider.blockSignals(True); self.slider.setValue(int(self.position * 1000)); self.slider.blockSignals(False)
        self._render()
        self.position_changed.emit(self.position)

    def toggle(self):
        self.playing = not self.playing
        self.play_btn.setText("⏸" if self.playing else "▶")
        if self.playing: self.timer.start()
        else: self.timer.stop()

    def stop(self):
        self.playing = False; self.timer.stop(); self.play_btn.setText("▶")
