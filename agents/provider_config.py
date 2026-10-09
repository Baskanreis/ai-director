from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.runtime.paths import provider_config_file, whisper_model_dir

DEFAULT_PROVIDER_CONFIG: dict[str, Any] = {
    "enable_real_providers": True,
    "final_director": {"enabled": True, "provider": "local_llm", "fallback": ["builtin"]},
    "shared_vision": {"enabled": False, "provider": "local_vision", "max_scenes": 12},
    "providers": {
        "local_vision": {
            "kind": "openai_compatible",
            "endpoint": "http://127.0.0.1:11434/v1",
            "model": "llava",
            "timeout_s": 120,
        },
        "whisper_local": {
            "kind": "whisper",
            "model": "base",
            "options": {"device": "auto", "download_root": str(whisper_model_dir())},
        },
        "strong_llm": {
            "kind": "openai_compatible",
            "endpoint": "https://api.openai.com/v1",
            "model": "gpt-5.6-sol",
            "api_key_env": "OPENAI_API_KEY",
            "timeout_s": 90,
        },
        "local_llm": {
            "kind": "managed_llama",
            "model": "Qwen3-1.7B-Q4_K_M.gguf",
            "timeout_s": 120,
            "options": {"port": 18080, "gpu_layers": 99, "ctx_size": 32768},
        },
        "builtin": {"kind": "heuristic", "model": "builtin"},
    },
    "agents": {
        "vision": {"enabled": False, "provider": "local_vision", "fallback": ["builtin"], "retries": 2},
        "speech": {"enabled": True, "provider": "whisper_local", "fallback": ["builtin"], "retries": 1},
        "caption": {"enabled": False, "provider": "strong_llm", "fallback": ["local_llm", "builtin"], "retries": 2},
        "rhythm": {"enabled": False, "provider": "local_llm", "fallback": ["builtin"], "retries": 1},
        "creative": {"enabled": False, "provider": "strong_llm", "fallback": ["local_llm", "builtin"], "retries": 2},
        "platform": {"enabled": False, "provider": "local_llm", "fallback": ["builtin"], "retries": 1},
        "quality": {"enabled": False, "provider": "local_llm", "fallback": ["builtin"], "retries": 1},
        "scene": {"enabled": False, "provider": "local_vision", "fallback": ["builtin"], "retries": 1},
        "copy": {"enabled": False, "provider": "strong_llm", "fallback": ["local_llm", "builtin"], "retries": 2},
    },
}


def load_provider_config(path: str | Path | None = None) -> dict[str, Any]:
    if path is None:
        path = provider_config_file()
    path = Path(path)
    if not path.exists():
        return DEFAULT_PROVIDER_CONFIG
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        merged = json.loads(json.dumps(DEFAULT_PROVIDER_CONFIG))
        merged["providers"].update(data.get("providers", {}))
        merged["agents"].update(data.get("agents", {}))
        merged["final_director"].update(data.get("final_director", {}))
        merged["shared_vision"].update(data.get("shared_vision", {}))
        return merged
    except (OSError, ValueError, TypeError):
        return DEFAULT_PROVIDER_CONFIG


def save_provider_config(data: dict[str, Any], path: str | Path | None = None) -> Path:
    path = Path(path or provider_config_file())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
