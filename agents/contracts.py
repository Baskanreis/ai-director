from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass
class AgentResult:
    agent: str
    version: str
    status: str = "ok"
    confidence: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    cached: bool = False
    duration_ms: float = 0.0
    error: str | None = None

    def to_dict(self):
        return asdict(self)

@dataclass
class CompiledEditPlan:
    version: str
    source_fingerprint: str
    profile: str
    duration: float
    agents: dict[str, AgentResult]
    timeline: list[dict[str, Any]] = field(default_factory=list)
    render: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "version": self.version,
            "source_fingerprint": self.source_fingerprint,
            "profile": self.profile,
            "duration": self.duration,
            "agents": {k: v.to_dict() for k, v in self.agents.items()},
            "timeline": self.timeline,
            "render": self.render,
            "quality": self.quality,
            "metadata": self.metadata,
        }
