from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QLineEdit, QSpinBox,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QLabel, QMessageBox,
    QGroupBox, QFormLayout, QHeaderView,
)

from app.agents.provider_config import DEFAULT_PROVIDER_CONFIG, load_provider_config, save_provider_config


AGENTS = [
    ("vision", "Vision Agent"), ("speech", "Speech Agent"),
    ("caption", "Caption Agent"), ("rhythm", "Rhythm Agent"),
    ("creative", "Creative Agent"), ("platform", "Platform Agent"),
    ("quality", "Quality Agent"), ("scene", "Scene Agent"),
    ("copy", "Copy Agent"),
]


class ProviderStudioDialog(QDialog):
    """GUI for independent agent/provider/model policies."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Provider Studio")
        self.resize(900, 640)
        self.config = copy.deepcopy(load_provider_config())
        self.providers = self.config.setdefault("providers", {})
        self.agents = self.config.setdefault("agents", {})

        root = QVBoxLayout(self)
        title = QLabel("Agent → Provider → Model")
        title.setStyleSheet("font-size:18px;font-weight:700;")
        root.addWidget(title)
        root.addWidget(QLabel("Her agent bağımsız model kullanır. Hata olursa retry → fallback → built-in çalışır."))

        self.enabled = QCheckBox("Gerçek provider katmanını etkinleştir")
        self.enabled.setChecked(bool(self.config.get("enable_real_providers", True)))
        root.addWidget(self.enabled)

        self.table = QTableWidget(len(AGENTS), 5)
        self.table.setHorizontalHeaderLabels(["Agent", "Provider", "Model", "Retry", "Fallback"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setMinimumHeight(360)
        root.addWidget(self.table)

        names = list(self.providers)
        for r, (key, label) in enumerate(AGENTS):
            self.table.setItem(r, 0, QTableWidgetItem(label))
            combo = QComboBox(); combo.addItems(names)
            raw = self.agents.get(key, {})
            combo.setCurrentText(str(raw.get("provider", names[0] if names else "builtin")))
            self.table.setCellWidget(r, 1, combo)
            model = QLineEdit()
            model.setText(str(self.providers.get(combo.currentText(), {}).get("model", "")))
            model.setPlaceholderText("Provider model")
            self.table.setCellWidget(r, 2, model)
            retry = QSpinBox(); retry.setRange(0, 5); retry.setValue(int(raw.get("retries", 1)))
            self.table.setCellWidget(r, 3, retry)
            fallback = QLineEdit(); fallback.setText(", ".join(raw.get("fallback", ["builtin"])))
            fallback.setPlaceholderText("builtin, local_llm")
            self.table.setCellWidget(r, 4, fallback)
            combo.currentTextChanged.connect(lambda name, rr=r: self._provider_changed(rr, name))

        box = QGroupBox("Bulut API anahtarları")
        form = QFormLayout(box)
        self.openai_key = QLineEdit()
        self.openai_key.setEchoMode(QLineEdit.Password)
        self.openai_key.setPlaceholderText("İsteğe bağlı — OPENAI_API_KEY")
        form.addRow("OpenAI API key", self.openai_key)
        root.addWidget(box)

        note = QLabel("Whisper ve yerel Qwen runtime Setup tarafından kurulup Program Files\\AI Director altında tutulur. Bulut provider'lar isteğe bağlıdır.")
        note.setWordWrap(True); note.setObjectName("Muted")
        root.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _provider_changed(self, row, name):
        model = self.table.cellWidget(row, 2)
        if isinstance(model, QLineEdit):
            model.setText(str(self.providers.get(name, {}).get("model", "")))

    def _save(self):
        self.config["enable_real_providers"] = self.enabled.isChecked()
        for r, (key, _label) in enumerate(AGENTS):
            provider = self.table.cellWidget(r, 1).currentText()
            model = self.table.cellWidget(r, 2).text().strip()
            retries = self.table.cellWidget(r, 3).value()
            fallback_text = self.table.cellWidget(r, 4).text().strip()
            fallback = [x.strip() for x in fallback_text.split(",") if x.strip()] or ["builtin"]
            self.agents[key] = {
                **self.agents.get(key, {}), "provider": provider, "model": model,
                "fallback": fallback, "retries": retries,
            }
        try:
            save_provider_config(self.config)
            self.accept()
        except OSError as exc:
            QMessageBox.critical(self, "Kaydedilemedi", str(exc))
