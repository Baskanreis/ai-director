from __future__ import annotations

import base64
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol


class ProviderError(RuntimeError):
    """Raised when a model/provider cannot complete an agent request."""


class AgentProvider(Protocol):
    name: str
    model: str

    def generate(self, *, agent: str, system: str, prompt: str,
                 context: dict[str, Any]) -> dict[str, Any]:
        ...


@dataclass
class ProviderSpec:
    name: str
    kind: str
    model: str = ""
    endpoint: str = ""
    api_key_env: str = ""
    timeout_s: float = 90.0
    options: dict[str, Any] = field(default_factory=dict)


class ProviderRegistry:
    """Runtime provider registry.

    Provider selection is independent per agent. All network/model integrations are
    optional; when unavailable, the orchestrator can fall back to another provider.
    """

    def __init__(self, specs: dict[str, ProviderSpec] | None = None):
        self.specs = specs or {}
        self._providers: dict[str, AgentProvider] = {}

    def register(self, name: str, provider: AgentProvider) -> None:
        self._providers[name] = provider

    def resolve(self, name: str) -> AgentProvider:
        if name in self._providers:
            return self._providers[name]
        spec = self.specs.get(name)
        if not spec:
            raise ProviderError(f"Provider tanımlı değil: {name}")
        provider = self._build(spec)
        self._providers[name] = provider
        return provider

    def _build(self, spec: ProviderSpec) -> AgentProvider:
        if spec.kind in {"openai_compatible", "ollama"}:
            return OpenAICompatibleProvider(spec)
        if spec.kind == "whisper":
            return WhisperProvider(spec)
        if spec.kind == "command":
            return CommandProvider(spec)
        if spec.kind == "managed_llama":
            from .managed_llm import ManagedLlamaProvider
            return ManagedLlamaProvider(spec)
        if spec.kind == "heuristic":
            return HeuristicProvider(spec)
        raise ProviderError(f"Bilinmeyen provider türü: {spec.kind}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProviderRegistry":
        specs = {}
        for name, raw in data.items():
            if not isinstance(raw, dict):
                continue
            specs[name] = ProviderSpec(
                name=name,
                kind=str(raw.get("kind", "heuristic")),
                model=str(raw.get("model", "")),
                endpoint=str(raw.get("endpoint", "")),
                api_key_env=str(raw.get("api_key_env", "")),
                timeout_s=float(raw.get("timeout_s", 90)),
                options=dict(raw.get("options", {})),
            )
        return cls(specs)


class OpenAICompatibleProvider:
    """Works with OpenAI-compatible APIs, including local servers such as Ollama.

    No SDK is required. The provider sends JSON and expects a JSON object in the
    model response. A model may return a fenced JSON block; it is also accepted.
    """

    def __init__(self, spec: ProviderSpec):
        self.name, self.model = spec.name, spec.model
        self.endpoint = spec.endpoint.rstrip("/") or "http://127.0.0.1:11434/v1"
        self.timeout_s = spec.timeout_s
        self.api_key = os.getenv(spec.api_key_env, "") if spec.api_key_env else ""
        self.options = spec.options

    def generate(self, *, agent: str, system: str, prompt: str,
                 context: dict[str, Any]) -> dict[str, Any]:
        if not self.model:
            raise ProviderError(f"{self.name}: model belirtilmemiş")
        url = self.endpoint
        if not url.endswith("/chat/completions"):
            url += "/chat/completions"
        user_content: Any = prompt
        vision_images = context.get("_vision_images") or []
        if vision_images:
            user_content = [{"type": "text", "text": prompt}]
            for image_url in vision_images:
                user_content.append({"type": "image_url", "image_url": {"url": image_url, "detail": "low"}})
        payload = {
            "model": context.get("_agent_model") or self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            "temperature": self.options.get("temperature", 0.2),
            "response_format": {"type": "json_object"},
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(
            url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise ProviderError(f"{self.name} bağlantı/yanıt hatası: {exc}") from exc

        try:
            content = raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"{self.name}: geçersiz chat completion yanıtı") from exc
        return _parse_json_object(content)


class WhisperProvider:
    """Real local OpenAI Whisper adapter.

    It consumes context['audio_path'] or context['media_path']. openai-whisper is
    optional; if absent this provider fails cleanly and fallback can continue.
    """

    def __init__(self, spec: ProviderSpec):
        self.name, self.model = spec.name, spec.model or "base"
        self.options = spec.options

    def generate(self, *, agent: str, system: str, prompt: str,
                 context: dict[str, Any]) -> dict[str, Any]:
        try:
            import whisper
        except ImportError as exc:
            raise ProviderError("openai-whisper kurulu değil") from exc
        path = context.get("audio_path") or context.get("media_path") or context.get("video_path")
        if not path:
            raise ProviderError("Whisper için audio_path/media_path/video_path gerekli")
        device = self.options.get("device")
        if device == "auto":
            device = None
        download_root = self.options.get("download_root")
        if not download_root:
            try:
                from app.runtime.paths import whisper_model_dir
                download_root = str(whisper_model_dir())
            except Exception:
                download_root = None
        kwargs = {"device": device} if device else {}
        if download_root:
            kwargs["download_root"] = download_root
        model_name = context.get("_agent_model") or self.model
        model = whisper.load_model(model_name, **kwargs)
        kwargs = {"language": context.get("language") or None}
        result = model.transcribe(str(path), word_timestamps=True, **kwargs)
        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": float(seg.get("start", 0)),
                "end": float(seg.get("end", 0)),
                "text": seg.get("text", "").strip(),
                "words": seg.get("words", []),
            })
        return {
            "segments": segments,
            "text": result.get("text", "").strip(),
            "language": result.get("language") or context.get("language"),
            "confidence": 0.9,
        }


class CommandProvider:
    """Adapter for arbitrary local GPU/model runners.

    command receives one JSON object on stdin and must print one JSON object on stdout.
    This is intentionally generic so users can connect Transformers, vLLM, llama.cpp,
    custom CUDA inference, or a studio-specific executable without changing agents.
    """

    def __init__(self, spec: ProviderSpec):
        self.name, self.model = spec.name, spec.model
        self.command = spec.options.get("command") or spec.endpoint
        self.timeout_s = spec.timeout_s

    def generate(self, *, agent: str, system: str, prompt: str,
                 context: dict[str, Any]) -> dict[str, Any]:
        if not self.command:
            raise ProviderError(f"{self.name}: command belirtilmemiş")
        request = {"agent": agent, "model": context.get("_agent_model") or self.model, "system": system,
                   "prompt": prompt, "context": context}
        try:
            proc = subprocess.run(
                self.command if isinstance(self.command, list) else str(self.command),
                input=json.dumps(request, ensure_ascii=False),
                text=True, capture_output=True, timeout=self.timeout_s,
                shell=isinstance(self.command, str),
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProviderError(f"{self.name}: local command hatası: {exc}") from exc
        if proc.returncode != 0:
            raise ProviderError(f"{self.name}: exit={proc.returncode}: {proc.stderr[-500:]}")
        return _parse_json_object(proc.stdout)


class HeuristicProvider:
    """Deterministic built-in fallback; never requires a model or network."""

    def __init__(self, spec: ProviderSpec):
        self.name, self.model = spec.name, spec.model or "builtin"

    def generate(self, *, agent: str, system: str, prompt: str,
                 context: dict[str, Any]) -> dict[str, Any]:
        return {"fallback": True, "provider": self.name, "confidence": 0.5}


def _parse_json_object(content: str) -> dict[str, Any]:
    text = str(content).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0].strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                obj = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                raise ProviderError("Model JSON üretemedi") from exc
        else:
            raise ProviderError("Model JSON üretemedi") from exc
    if not isinstance(obj, dict):
        raise ProviderError("Provider yanıtı JSON object olmalı")
    return obj
