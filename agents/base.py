from __future__ import annotations
import hashlib, json, time
from pathlib import Path
from typing import Any
from .contracts import AgentResult

class BaseAgent:
    name = "base"
    version = "1.0"

    def fingerprint(self, context: dict[str, Any]) -> str:
        payload = json.dumps(self.cache_payload(context), ensure_ascii=False, sort_keys=True, default=str).encode()
        return hashlib.sha256(payload).hexdigest()

    def cache_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        return context

    def run(self, context: dict[str, Any]) -> AgentResult:
        started = time.perf_counter()
        try:
            data = self.analyze(context)
            return AgentResult(self.name, self.version, "ok", float(data.pop("confidence", 1.0)), data,
                               duration_ms=(time.perf_counter()-started)*1000)
        except Exception as exc:
            return AgentResult(self.name, self.version, "error", 0.0, {},
                               duration_ms=(time.perf_counter()-started)*1000, error=str(exc))

    def analyze(self, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
