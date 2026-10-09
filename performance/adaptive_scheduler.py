"""Adaptive render scheduling based on resource headroom and job type."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Any
from .render_scheduler import RenderAdmission, ResourceSnapshot, SchedulerPolicy
from .render_intelligence import RenderIntelligence

@dataclass(frozen=True)
class AdaptivePolicy:
    base: SchedulerPolicy = field(default_factory=SchedulerPolicy)
    max_vram_percent: float = 90.0
    long_priority: int = 20
    short_priority: int = 30
    thumbnail_priority: int = 50
    preview_priority: int = 60

class AdaptiveRenderScheduler(RenderAdmission):
    def __init__(self, policy: AdaptivePolicy | None = None, sample: Callable[[], ResourceSnapshot] | None = None, intelligence: RenderIntelligence | None = None):
        self.adaptive_policy = policy or AdaptivePolicy()
        self.intelligence = intelligence or RenderIntelligence()
        super().__init__(self.adaptive_policy.base, sample)
    @staticmethod
    def _kind(job: Any) -> str:
        return str(getattr(job, "kind", job if isinstance(job, str) else "long")).lower()
    def priority(self, job: Any) -> int:
        return {"long": self.adaptive_policy.long_priority, "short": self.adaptive_policy.short_priority,
                "thumbnail": self.adaptive_policy.thumbnail_priority, "preview": self.adaptive_policy.preview_priority}.get(self._kind(job), 25)
    def estimate(self, job: Any):
        features = getattr(job, "render_features", None)
        if features is not None:
            try:
                prediction = self.intelligence.predictive.predict(self.intelligence.predictive.features_from(job))
                if prediction.eta_s is not None:
                    base = self.intelligence.estimate(self._kind(job))
                    return type(base)(base.kind, prediction.eta_s, prediction.confidence, base.recommended_parallel, prediction.sample_count)
            except (AttributeError, TypeError, ValueError):
                pass
        return self.intelligence.estimate(self._kind(job))
    def score(self, job: Any, snapshot: ResourceSnapshot | None = None) -> float:
        s=snapshot or self.snapshot(); headroom=100.0
        if s.cpu is not None: headroom=min(headroom,100.0-s.cpu)
        if s.gpu is not None: headroom=min(headroom,100.0-s.gpu)
        if s.vram is not None: headroom=min(headroom,100.0-s.vram)
        estimate=self.estimate(job)
        eta_bonus=0.0 if estimate.eta_s is None else min(20.0, 20.0/(1.0+estimate.eta_s/60.0))
        return self.priority(job)+max(0.0,headroom)+eta_bonus
    def recommended_parallel(self, job: Any, hard_cap: int | None = None) -> int:
        cap = hard_cap if hard_cap is not None else self.adaptive_policy.base.max_parallel
        return self.intelligence.recommended_parallel(self._kind(job), cap)

    def acquire_for(self, job: Any, cancel=None, timeout=None) -> bool:
        return self.acquire(cancel=cancel, timeout=timeout)
