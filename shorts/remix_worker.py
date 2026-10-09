"""Qt worker for non-blocking Shorts Remix renders."""
from __future__ import annotations
from PySide6.QtCore import QThread, Signal
from .remix_render import render_remix, RemixRenderCancelled


class RemixRenderWorker(QThread):
    progress_changed = Signal(float, str)
    finished_ok = Signal(str)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, source, plan, output, caption_cues=None, caption_style="bold_hook", parent=None):
        super().__init__(parent)
        self.source = source
        self.plan = plan
        self.output = output
        self.caption_cues = caption_cues or []
        self.caption_style = caption_style
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            result = render_remix(
                self.source,
                self.plan,
                self.output,
                on_progress=lambda f, m: self.progress_changed.emit(float(f), m),
                is_cancelled=lambda: self._cancel,
                caption_cues=self.caption_cues,
                caption_style=self.caption_style,
                dynamic_captions=bool(self.caption_cues),
                smart_reframe=True,
            )
            if self._cancel:
                self.cancelled.emit()
            else:
                self.finished_ok.emit(str(result))
        except RemixRenderCancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.failed.emit(str(exc))
