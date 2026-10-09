from __future__ import annotations
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QPlainTextEdit,QMessageBox,QLineEdit,QFormLayout
from app.youtube.health import check_youtube_health
from app.youtube.client import YouTubeDataClient
from app.youtube.config import load_runtime_config, save_runtime_config

class YouTubeConnectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("YouTube Connection Center"); self.resize(760,650)
        root=QVBoxLayout(self)
        self.summary=QLabel(); self.summary.setWordWrap(True); root.addWidget(self.summary)
        form=QFormLayout()
        self.api_key=QLineEdit(); self.api_key.setEchoMode(QLineEdit.Password); self.api_key.setPlaceholderText("YouTube Data API v3 key")
        self.oauth=QPlainTextEdit(); self.oauth.setPlaceholderText('{"installed": {"client_id": "...", "client_secret": "...", "auth_uri": "...", "token_uri": "..."}}')
        form.addRow("Data API key", self.api_key); form.addRow("Google OAuth client JSON", self.oauth); root.addLayout(form)
        row=QHBoxLayout(); self.save_btn=QPushButton("Yapılandırmayı Kaydet"); self.refresh_btn=QPushButton("Durumu Yenile"); self.test_btn=QPushButton("Data API Testi")
        self.save_btn.clicked.connect(self.save); self.refresh_btn.clicked.connect(self.refresh); self.test_btn.clicked.connect(self.test_api)
        row.addWidget(self.save_btn); row.addWidget(self.refresh_btn); row.addWidget(self.test_btn); root.addLayout(row)
        self.output=QPlainTextEdit(); self.output.setReadOnly(True); root.addWidget(self.output,1)
        key, oauth = load_runtime_config(); self.api_key.setText(key); self.oauth.setPlainText(oauth); self.refresh()
    def refresh(self):
        h=check_youtube_health(); self.test_btn.setEnabled(h.data_api_configured and h.critical_modules_ok)
        states=[("Data API",h.data_api_configured),("Google OAuth",h.oauth_configured and h.google_packages_available),("OAuth oturumu",h.oauth_token_present),("Kritik modüller",h.critical_modules_ok)]
        self.summary.setText("YouTube Connection Center\n"+"\n".join(f"{'✓' if ok else '✗'} {name}" for name,ok in states)); self.output.setPlainText("\n".join(h.messages))
    def save(self):
        try:
            save_runtime_config(self.api_key.text(), self.oauth.toPlainText())
            self.refresh(); QMessageBox.information(self,"YouTube","Yapılandırma kullanıcı profilinize kaydedildi. Setup'ı yeniden oluşturmaya gerek yok.")
        except Exception as exc: QMessageBox.critical(self,"YouTube yapılandırması",f"Kaydedilemedi:\n{exc}")
    def test_api(self):
        try:
            key_client=YouTubeDataClient()
            if not key_client.api_key: raise RuntimeError("YouTube Data API anahtarı yapılandırılmamış.")
            self.output.appendPlainText("\nData API anahtarı bulundu. Gerçek kanal testi Channel ID ile yapılabilir.")
        except Exception as exc: QMessageBox.critical(self,"YouTube Data API",str(exc))
