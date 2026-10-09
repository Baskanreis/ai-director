from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .base import BaseAgent
from .contracts import AgentResult
from .providers import ProviderError, ProviderRegistry


@dataclass
class AgentPolicy:
    provider: str
    fallback: list[str]
    retries: int = 1
    retry_delay_s: float = 0.25
    model: str = ""


class ProviderBackedAgent:
    """Decorates an existing agent with a selectable model/provider policy."""

    def __init__(self, agent: BaseAgent, registry: ProviderRegistry,
                 policy: AgentPolicy):
        self.agent = agent
        self.registry = registry
        self.policy = policy

    @property
    def name(self): return self.agent.name

    @property
    def version(self): return self.agent.version

    def fingerprint(self, context: dict[str, Any]) -> str:
        payload = dict(context)
        payload["_provider"] = self.policy.provider
        payload["_fallback"] = self.policy.fallback
        payload["_model_policy"] = {"retries": self.policy.retries, "model": self.policy.model}
        return self.agent.fingerprint(payload)

    def run(self, context: dict[str, Any]) -> AgentResult:
        providers = [self.policy.provider, *self.policy.fallback]
        errors: list[str] = []
        for provider_name in providers:
            for attempt in range(max(0, self.policy.retries) + 1):
                started = time.perf_counter()
                try:
                    provider = self.registry.resolve(provider_name)
                    system = (
                        "You are a specialist AI video-editing agent. "
                        "Return ONLY a JSON object. Keep decisions deterministic and "
                        "machine-readable. Never invent unavailable media facts."
                    )
                    provider_context = dict(context)
                    if self.policy.model:
                        provider_context["_agent_model"] = self.policy.model
                    prompt = self._prompt(provider_context)
                    data = provider.generate(
                        agent=self.name, system=system, prompt=prompt, context=provider_context
                    )
                    # The builtin provider intentionally returns a marker; in that
                    # case preserve the mature local implementation as the fallback.
                    if data.get("fallback") is True:
                        result = self.agent.run(context)
                        result.version = f"{result.version}+fallback"
                        result.warnings.extend(errors)
                        result.warnings.append(f"Provider fallback kullanıldı: {provider_name}")
                        return result
                    confidence = float(data.pop("confidence", 0.8))
                    data["provider"] = provider_name
                    data["model"] = self.policy.model or getattr(provider, "model", "")
                    return AgentResult(
                        self.name, f"{self.version}+provider", "ok",
                        confidence, data,
                        warnings=errors,
                        duration_ms=(time.perf_counter() - started) * 1000,
                    )
                except Exception as exc:
                    errors.append(f"{provider_name} attempt {attempt+1}: {exc}")
                    if attempt < self.policy.retries:
                        time.sleep(self.policy.retry_delay_s * (attempt + 1))
                    continue
        # Last-resort local implementation means one broken model never kills the run.
        result = self.agent.run(context)
        result.warnings.extend(errors)
        result.warnings.append("Tüm model provider'ları başarısız; built-in fallback kullanıldı.")
        result.version = f"{result.version}+fallback"
        return result

    def _prompt(self, context: dict[str, Any]) -> str:
        compact = dict(context)
        # Avoid sending huge media payloads to every LLM. Providers that need the file
        # path can read it locally; text models get the analysis context.
        for key in ("raw_frames", "audio_bytes", "video_bytes"):
            compact.pop(key, None)
        return (
            f"Agent: {self.name}\n"
            "Produce the agent's structured output for this editing context.\n"
            f"Context JSON:\n{_safe_json(compact)}"
        )


def _safe_json(value: Any) -> str:
    import json
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
