from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QLabel, QComboBox, QMessageBox
from PySide6.QtCore import Qt
from app.effects.asset_library import list_assets
from app.effects.effect_library import effect_names
from app.brain.effects_preset import apply_effects_preset
from app.video.media_info import probe_media

class EffectsMusicDialog(QDialog):
    def __init__(self, project, history, refresh_callback, parent=None):
        super().__init__(parent); self.project=project; self.history=history; self.refresh=refresh_callback
        self.setWindowTitle('Efektler & Müzik Kütüphanesi'); self.resize(700,520)
        root=QVBoxLayout(self)
        top=QHBoxLayout(); self.kind=QComboBox(); self.kind.addItems(['Tümü','Müzik','SFX']); self.kind.currentTextChanged.connect(self._reload)
        top.addWidget(QLabel('Kategori')); top.addWidget(self.kind); top.addStretch(); root.addLayout(top)
        self.list=QListWidget(); root.addWidget(self.list)
        row=QHBoxLayout(); self.effect=QComboBox(); self.effect.addItems(effect_names()); row.addWidget(QLabel('Görsel preset')); row.addWidget(self.effect)
        apply=QPushButton('Seçili klibe uygula'); apply.clicked.connect(self._apply_effect); row.addWidget(apply)
        add=QPushButton('Seçili sesi Timeline\'a ekle'); add.clicked.connect(self._add_audio); row.addWidget(add); root.addLayout(row)
        self._reload('Tümü')
    def _reload(self, value):
        self.list.clear(); cat=None if value=='Tümü' else value
        for a in list_assets(cat):
            item=QListWidgetItem(f'{a.name}  ·  {a.category}  ·  {a.license}')
            item.setData(Qt.UserRole,a); self.list.addItem(item)
    def _apply_effect(self):
        cid=self.parent().timeline_view.selected_clip_id() if self.parent() else None
        found=self.project.timeline.find(cid) if cid else None
        if not found: QMessageBox.information(self,'Klip seçilmedi','Önce timeline üzerinde bir video klibi seçin.'); return
        self.history.push(); apply_effects_preset(found[1],self.effect.currentText()); self.project.touch(); self.refresh();
    def _add_audio(self):
        item=self.list.currentItem();
        if not item: return
        a=item.data(Qt.UserRole)
        try: info=probe_media(a.path)
        except Exception as exc: QMessageBox.warning(self,'Ses eklenemedi',str(exc)); return
        media,created=self.project.add_media(info)
        start=self.project.timeline.duration
        self.history.push()
        try: self.project.timeline.add_audio_media(media.id,media.name,media.duration,start=start)
        except Exception as exc: self.history.undo(); QMessageBox.warning(self,'Timeline hatası',str(exc)); return
        self.project.touch(); self.refresh()
