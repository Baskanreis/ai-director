"""Çökme Sonrası Kurtarma (Crash Recovery) diyaloğu.

Uygulama bir önceki çalıştırmada TEMİZ kapatılmadıysa (çökme, güç kesintisi,
görev yöneticisinden sonlandırma vb.) başlangıçta gösterilir; bulunan her
kurtarılabilir oturum için "Kurtar" veya "Yoksay" seçeneği sunar.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.project.autosave import SessionRecord


class RecoveryDialog(QDialog):
    """Kullanıcının seçimi `self.to_recover` (kurtarılacak `SessionRecord` listesi)
    ve `self.to_discard` (kalıcı olarak silinecek session_id listesi) içinde döner.
    """

    def __init__(self, sessions: list[SessionRecord], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.sessions = sessions
        self.to_recover: list[SessionRecord] = []
        self.to_discard: list[str] = []

        self.setWindowTitle("Kurtarılabilir Oturum Bulundu")
        self.setMinimumSize(480, 320)

        layout = QVBoxLayout(self)
        title = QLabel("AI Director önceki çalıştırmada düzgün kapatılmamış.")
        title.setStyleSheet("font-weight: 600;")
        layout.addWidget(title)

        hint = QLabel(
            "Aşağıdaki proje(ler) için otomatik kaydedilmiş, henüz kaybolmamış bir\n"
            "çalışma bulundu. Kurtarmak istediklerinizi işaretleyip seçin."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        for rec in sessions:
            where = rec.project_path or "(hiç kaydedilmemiş proje)"
            item = QListWidgetItem(f"{rec.project_name}\n{where}\nson güncelleme: {rec.updated.replace('T', ' ')}")
            item.setSelected(True)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget, 1)

        btn_row = QHBoxLayout()
        recover_btn = QPushButton("Seçilenleri Kurtar")
        recover_btn.clicked.connect(self._recover)
        discard_btn = QPushButton("Hepsini Yoksay")
        discard_btn.clicked.connect(self._discard_all)
        btn_row.addWidget(recover_btn)
        btn_row.addWidget(discard_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _recover(self) -> None:
        selected_rows = {self.list_widget.row(i) for i in self.list_widget.selectedItems()}
        self.to_recover = [rec for i, rec in enumerate(self.sessions) if i in selected_rows]
        self.to_discard = [rec.session_id for i, rec in enumerate(self.sessions) if i not in selected_rows]
        self.accept()

    def _discard_all(self) -> None:
        self.to_recover = []
        self.to_discard = [rec.session_id for rec in self.sessions]
        self.accept()
