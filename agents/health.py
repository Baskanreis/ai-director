from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RuntimeHealth:
    provider: str
    status: str
    detail: str
    model: str = ""


def check_provider_health(name: str, spec: dict[str, Any]) -> RuntimeHealth:
    kind = str(spec.get("kind", "heuristic"))
    model = str(spec.get("model", ""))
    if kind == "heuristic":
        return RuntimeHealth(name, "ready", "Built-in fallback", model)
    if kind == "whisper":
        try:
            from app.runtime.paths import whisper_model_dir
            expected = whisper_model_dir() / f"{model or 'base'}.pt"
            if expected.exists():
                return RuntimeHealth(name, "ready", "Whisper modeli hazır", model)
            return RuntimeHealth(name, "missing", f"Model bulunamadı: {expected.name}", model)
        except Exception as exc:
            return RuntimeHealth(name, "error", str(exc), model)
    if kind == "managed_llama":
        try:
            from app.runtime.paths import bundled_dir, model_dir
            exe = bundled_dir("runtime") / "llama" / "llama-server.exe"
            model_path = model_dir() / "llm" / model
            if not exe.exists():
                return RuntimeHealth(name, "missing", "llama-server.exe bulunamadı", model)
            if model and not model_path.exists():
                return RuntimeHealth(name, "missing", f"Model bulunamadı: {model}", model)
            if model and model_path.stat().st_size < 100 * 1024 * 1024:
                return RuntimeHealth(name, "invalid", f"Model dosyası şüpheli/kesik: {model_path.name}", model)
            if exe.stat().st_size < 1024 * 1024:
                return RuntimeHealth(name, "invalid", "llama-server.exe dosyası şüpheli/kesik", model)
            return RuntimeHealth(name, "ready", "Yerel runtime + model hazır", model)
        except Exception as exc:
            return RuntimeHealth(name, "error", str(exc), model)
    if kind in {"openai_compatible", "ollama"}:
        endpoint = str(spec.get("endpoint", ""))
        if endpoint.startswith("http://127.0.0.1") or endpoint.startswith("http://localhost"):
            return RuntimeHealth(name, "configured", "Yerel endpoint yapılandırıldı", model)
        env = str(spec.get("api_key_env", ""))
        if env and not __import__("os").getenv(env):
            return RuntimeHealth(name, "needs_key", f"{env} gerekli", model)
        return RuntimeHealth(name, "configured", "API endpoint yapılandırıldı", model)
    if kind == "command":
        command = spec.get("command") or spec.get("endpoint")
        executable = command[0] if isinstance(command, list) and command else command
        if executable and (Path(str(executable)).exists() or shutil.which(str(executable))):
            return RuntimeHealth(name, "ready", "Yerel command hazır", model)
        return RuntimeHealth(name, "missing", "Yerel command bulunamadı", model)
    return RuntimeHealth(name, "unknown", f"Bilinmeyen provider türü: {kind}", model)
