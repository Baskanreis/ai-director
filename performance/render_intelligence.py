"""Historical render intelligence: ETA and conservative parallelism recommendations."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from collections import defaultdict
from statistics import median
from time import time
import json
from pathlib import Path
from typing import Any
from .predictive_render import PredictiveRenderModel, RenderFeatures

@dataclass(frozen=True)
class RenderObservation:
    kind: str
    duration_s: float
    cpu: float | None = None
    gpu: float | None = None
    vram: float | None = None
    success: bool = True
    timestamp: float = 0.0
    features: dict[str, Any] | None = None

@dataclass(frozen=True)
class RenderEstimate:
    kind: str
    eta_s: float | None
    confidence: float
    recommended_parallel: int
    sample_count: int

class RenderIntelligence:
    """Small dependency-free history model. It is advisory, never a hard gate."""
    def __init__(self, max_history: int = 500):
        self.max_history = max(10, int(max_history))
        self.observations: list[RenderObservation] = []
        self.predictive = PredictiveRenderModel(self.max_history)

    @staticmethod
    def _kind(job_or_kind: Any) -> str:
        return str(getattr(job_or_kind, "kind", job_or_kind)).lower()

    def record(self, kind: Any, duration_s: float, *, cpu=None, gpu=None, vram=None, success=True, features=None) -> RenderObservation:
        obs = RenderObservation(self._kind(kind), max(0.001, float(duration_s)), cpu, gpu, vram, bool(success), time(), features)
        if features:
            try:
                self.predictive.record(RenderFeatures(**features) if isinstance(features, dict) else features, obs.duration_s, obs.success)
            except (TypeError, ValueError):
                pass
        self.observations.append(obs)
        self.observations = self.observations[-self.max_history:]
        return obs

    def _samples(self, kind: Any) -> list[RenderObservation]:
        k = self._kind(kind)
        return [x for x in self.observations if x.kind == k and x.success]

    def estimate(self, kind: Any) -> RenderEstimate:
        k = self._kind(kind); samples = self._samples(k)
        if not samples:
            return RenderEstimate(k, None, 0.0, 1, 0)
        values = [x.duration_s for x in samples[-25:]]
        eta = float(median(values))
        confidence = min(1.0, len(samples) / 10.0)
        # More history allows a modest increase, but never exceeds observed safe parallelism.
        load = [x.gpu for x in samples[-10:] if x.gpu is not None]
        vram = [x.vram for x in samples[-10:] if x.vram is not None]
        recommended = 1
        if confidence >= 0.7 and (not load or median(load) < 55) and (not vram or median(vram) < 60):
            recommended = 2
        if confidence >= 1.0 and (not load or median(load) < 40) and (not vram or median(vram) < 50):
            recommended = 3
        return RenderEstimate(k, eta, confidence, recommended, len(samples))

    def eta_for(self, kind: Any) -> float | None:
        return self.estimate(kind).eta_s

    def recommended_parallel(self, kind: Any, hard_cap: int = 3) -> int:
        return min(max(1, int(hard_cap)), self.estimate(kind).recommended_parallel)

    def to_dict(self) -> dict[str, Any]:
        return {"version": 1, "observations": [asdict(x) for x in self.observations]}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "RenderIntelligence":
        obj = cls()
        for d in (data or {}).get("observations", []):
            try: obj.observations.append(RenderObservation(**d))
            except TypeError: continue
        obj.observations = obj.observations[-obj.max_history:]
        obj.predictive = PredictiveRenderModel(obj.max_history)
        for o in obj.observations:
            if o.features:
                try: obj.predictive.record(RenderFeatures(**o.features), o.duration_s, o.success)
                except (TypeError, ValueError): pass
        return obj

    def save(self, path: str | Path) -> None:
        p = Path(path); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(self.to_dict()), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "RenderIntelligence":
        p = Path(path)
        if not p.exists(): return cls()
        try: return cls.from_dict(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError): return cls()
