"""Managed local llama.cpp OpenAI-compatible provider.

The Windows installer places llama-server and the bundled Qwen model below the
application directory. The provider starts the server lazily, so startup stays
fast and the model process only exists while an AI run needs it.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .providers import ProviderError, _parse_json_object


class ManagedLlamaProvider:
    def __init__(self, spec):
        self.name = spec.name
        self.model = spec.model or "Qwen3-1.7B-Q4_K_M.gguf"
        self.options = spec.options
        self.port = int(self.options.get("port", 18080))
        self.host = str(self.options.get("host", "127.0.0.1"))
        self._process: subprocess.Popen | None = None

    @property
    def endpoint(self) -> str:
        return f"http://{self.host}:{self.port}/v1"

    def _paths(self, model_override: str | None = None) -> tuple[Path, Path]:
        from app.runtime.paths import bundled_dir, model_dir
        binary = self.options.get("binary")
        if binary:
            exe = Path(binary)
        else:
            exe = bundled_dir("runtime") / "llama" / "llama-server.exe"
        model_name = self.options.get("model_path") or model_override or self.model
        model = Path(model_name)
        if not model.is_absolute():
            model = model_dir() / "llm" / model
        return exe, model

    def _healthy(self) -> bool:
        try:
            req = urllib.request.Request(self.endpoint + "/models", method="GET")
            with urllib.request.urlopen(req, timeout=1.5) as r:
                return r.status == 200
        except Exception:
            return False

    def _ensure_server(self, model_override: str | None = None) -> None:
        if self._healthy():
            return
        exe, model = self._paths(model_override)
        if not exe.is_file():
            raise ProviderError(f"Yerel LLM runtime bulunamadı: {exe}")
        if not model.is_file():
            raise ProviderError(f"Yerel LLM modeli bulunamadı: {model}")
        if self._process and self._process.poll() is None:
            raise ProviderError("Yerel LLM sunucusu başlatıldı ancak hazır olmadı")
        args = [str(exe), "-m", str(model), "--host", self.host,
                "--port", str(self.port), "--ctx-size", str(self.options.get("ctx_size", 32768)),
                "-ngl", str(self.options.get("gpu_layers", 99)),
                "--jinja"]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self._process = subprocess.Popen(args, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL,
                                         creationflags=creationflags)
        deadline = time.time() + float(self.options.get("startup_timeout_s", 30))
        while time.time() < deadline:
            if self._healthy():
                return
            if self._process.poll() is not None:
                raise ProviderError("Yerel LLM sunucusu başlatılamadı")
            time.sleep(0.25)
        raise ProviderError("Yerel LLM sunucusu zaman aşımına uğradı")

    def generate(self, *, agent: str, system: str, prompt: str,
                 context: dict[str, Any]) -> dict[str, Any]:
        model_override = context.get("_agent_model") or None
        self._ensure_server(model_override)
        payload = {
            "model": context.get("_agent_model") or self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.options.get("temperature", 0.2),
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            self.endpoint + "/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=float(self.options.get("timeout_s", 120))) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            content = raw["choices"][0]["message"]["content"]
        except Exception as exc:
            raise ProviderError(f"Managed llama.cpp hatası: {exc}") from exc
        data = _parse_json_object(content)
        data.setdefault("confidence", 0.82)
        return data
