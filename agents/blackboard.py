"""Shared agent blackboard: lightweight, thread-safe collaboration state.

Agents publish observations/constraints; dependent agents read only the compact
shared state instead of receiving every raw media payload. This keeps prompts small
and prevents contradictory independent decisions.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from threading import RLock
from typing import Any

@dataclass
class Blackboard:
    context: dict[str, Any] = field(default_factory=dict)
    results: dict[str, Any] = field(default_factory=dict)
    constraints: list[dict[str, Any]] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)
    _lock: RLock = field(default_factory=RLock, repr=False)

    def publish(self, agent: str, result: Any) -> None:
        with self._lock:
            self.results[agent] = result
            data = getattr(result, "data", result) or {}
            for key in ("constraints", "warnings", "hard_constraints"):
                values = data.get(key, []) if isinstance(data, dict) else []
                if isinstance(values, list):
                    for value in values:
                        item = {"agent": agent, "type": key, "value": value}
                        if item not in self.constraints:
                            self.constraints.append(item)

    def message(self, sender: str, receiver: str, kind: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self.messages.append({"sender": sender, "receiver": receiver, "kind": kind, "payload": payload})

    def snapshot(self, *, exclude: str | None = None) -> dict[str, Any]:
        with self._lock:
            compact = {}
            for name, result in self.results.items():
                if name == exclude:
                    continue
                data = getattr(result, "data", result) or {}
                compact[name] = _compact(data)
            return {
                "agent_results": compact,
                "constraints": list(self.constraints[-80:]),
                "messages": list(self.messages[-80:]),
            }

def _compact(value: Any, depth: int = 0) -> Any:
    if depth > 3:
        return "<truncated>"
    if isinstance(value, dict):
        return {str(k): _compact(v, depth + 1) for k, v in list(value.items())[:60]}
    if isinstance(value, list):
        return [_compact(v, depth + 1) for v in value[:40]]
    if isinstance(value, tuple):
        return [_compact(v, depth + 1) for v in value[:40]]
    return value
