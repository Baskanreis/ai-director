"""Sürüm Geçmişi (Versioning) diyaloğu.

Undo/redo (Ctrl+Z/Ctrl+Y) ile karıştırılmamalı: bu diyalog, kullanıcının
ELLE oluşturduğu, uygulama kapatılıp açılsa bile KALICI kalan isimli kontrol
noktalarını (örn. "AI düzenlemeden önce", "ilk taslak") listeler, yeni sürüm
oluşturur ve seçilen bir sürümü geri yükler.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.project.project import Project
from app.project.versioning import VersionEntry, VersionManager, VersioningError


class VersionDialog(QDialog):
    """Geri döndürülen değer `self.restored_project` — kullanıcı bir sürümü geri
    yüklediyse dolu (`Project`), aksi halde `None`. Çağıran taraf (MainWindow),
    bunu mevcut projenin yerine koymaktan sorumludur.
    """

    def __init__(self, manager: VersionManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.restored_project: Project | None = None

        self.setWindowTitle("Sürüm Geçmişi")
        self.setMinimumSize(520, 420)

        layout = QVBoxLayout(self)

        hint = QLabel(
            "Sürümler, projenin diskte kalıcı olarak saklanan isimli kontrol noktalarıdır\n"
            "(Geri Al/Ctrl+Z'den farklı olarak uygulama kapatılsa da kaybolmaz). Bir sürümü\n"
            "geri yüklemeden önce, kaybolmaması için MEVCUT durum da otomatik olarak yeni\n"
            "bir sürüm olarak kaydedilir."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        create_row = QHBoxLayout()
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("Sürüm adı (ör. 'AI düzenlemeden önce')…")
        create_row.addWidget(self.label_edit, 1)
        self.create_btn = QPushButton("+ Sürüm Oluştur")
        self.create_btn.clicked.connect(self._create_version)
        create_row.addWidget(self.create_btn)
        layout.addLayout(create_row)

        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._update_buttons)
        self.list_widget.itemDoubleClicked.connect(lambda _: self._restore_selected())
        layout.addWidget(self.list_widget, 1)

        btn_row = QHBoxLayout()
        self.restore_btn = QPushButton("Bu Sürümü Geri Yükle")
        self.restore_btn.clicked.connect(self._restore_selected)
        self.delete_btn = QPushButton("Sil")
        self.delete_btn.clicked.connect(self._delete_selected)
        btn_row.addWidget(self.restore_btn)
        btn_row.addWidget(self.delete_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Close).clicked.connect(self.reject)
        layout.addWidget(buttons)

        self._reload()

    # ---------------- iç yardımcılar ----------------
    def _reload(self) -> None:
        self.list_widget.clear()
        for entry in self.manager.list():
            label = entry.label + ("  (otomatik)" if entry.auto else "")
            text = f"{label}\n{entry.created.replace('T', '  ')}"
            if entry.note:
                text += f"\n{entry.note}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, entry.id)
            self.list_widget.addItem(item)
        self._update_buttons()

    def _update_buttons(self) -> None:
        has_sel = self.list_widget.currentItem() is not None
        self.restore_btn.setEnabled(has_sel)
        self.delete_btn.setEnabled(has_sel)

    def _selected_id(self) -> str | None:
        item = self.list_widget.currentItem()
        return item.data(Qt.UserRole) if item else None

    # ---------------- eylemler ----------------
    def _create_version(self) -> None:
        label = self.label_edit.text().strip()
        if not label:
            label, ok = QInputDialog.getText(self, "Sürüm Oluştur", "Sürüm adı:")
            if not ok or not label.strip():
                return
        try:
            self.manager.create(label)
        except VersioningError as exc:
            QMessageBox.critical(self, "Sürüm oluşturulamadı", str(exc))
            return
        self.label_edit.clear()
        self._reload()

    def _restore_selected(self) -> None:
        vid = self._selected_id()
        if vid is None:
            return
        choice = QMessageBox.question(
            self,
            "Sürümü geri yükle",
            "Seçili sürüm geri yüklenecek. Mevcut çalışma, kaybolmaması için önce\n"
            "otomatik bir sürüm olarak kaydedilecek. Devam edilsin mi?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if choice != QMessageBox.Yes:
            return
        try:
            self.manager.create("Geri yüklemeden önce", auto=True)
            restored = self.manager.restore(vid)
        except VersioningError as exc:
            QMessageBox.critical(self, "Geri yüklenemedi", str(exc))
            return
        self.restored_project = restored
        self.accept()

    def _delete_selected(self) -> None:
        vid = self._selected_id()
        if vid is None:
            return
        if QMessageBox.question(
            self, "Sürümü sil", "Bu sürüm kalıcı olarak silinecek. Emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        self.manager.delete(vid)
        self._reload()
