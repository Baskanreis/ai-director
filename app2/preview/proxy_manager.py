"""Non-blocking preview proxy manager.

Proxy generation is deliberately opportunistic: it runs only while the preview
is paused, so background transcoding never competes with real-time playback.
"""
from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from app.render.proxy_cache import ProxyCache, ProxySpec
from app.ui.background import BackgroundTask, pool


class PreviewProxyManager(QObject):
    ready = Signal(str, str)  # source, proxy path
    failed = Signal(str)

    def __init__(self, root: str | Path | None = None, parent=None):
        super().__init__(parent)
        import tempfile
        self.cache = ProxyCache(root or (Path(tempfile.gettempdir()) / "ai_director_proxies"))
        self._pending: set[str] = set()

    def proxy_for(self, source: str) -> str | None:
        try:
            artifact = self.cache.artifact(source)
            return artifact.path if self.cache.is_valid(artifact) else None
        except (OSError, ValueError):
            return None

    def request(self, source: str, spec: ProxySpec = ProxySpec()) -> None:
        if source in self._pending:
            return
        try:
            artifact = self.cache.artifact(source, spec)
        except OSError:
            return
        if self.cache.is_valid(artifact):
            self.ready.emit(source, artifact.path)
            return
        self._pending.add(source)
        command = self.cache.command(source, spec)
        task = BackgroundTask(lambda cmd=command: __import__("subprocess").run(
            cmd, stdout=__import__("subprocess").DEVNULL,
            stderr=__import__("subprocess").DEVNULL, check=False, timeout=300
        ).returncode)
        task.signals.result.connect(lambda code, src=source, art=artifact: self._done(src, art.path, code))
        task.signals.error.connect(lambda _err, src=source: self._failed(src))
        pool().start(task)

    def _done(self, source: str, path: str, code: int) -> None:
        self._pending.discard(source)
        if code == 0 and Path(path).is_file():
            self.ready.emit(source, path)
        else:
            self.failed.emit(source)

    def _failed(self, source: str) -> None:
        self._pending.discard(source)
        self.failed.emit(source)
