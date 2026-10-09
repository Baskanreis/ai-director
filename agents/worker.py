from __future__ import annotations
from PySide6.QtCore import QThread, Signal
from .orchestrator import MultiAgentOrchestrator

class MultiAgentWorker(QThread):
    finished_ok=Signal(object)
    failed=Signal(str)
    def __init__(self, context:dict, parent=None):
        super().__init__(parent); self.context=context
    def run(self):
        try:
            self.finished_ok.emit(MultiAgentOrchestrator().run(self.context))
        except Exception as exc:
            self.failed.emit(f"Multi-Agent analiz başarısız: {exc}")
