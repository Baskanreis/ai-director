"""Production model registry and policy-aware selection for AI Director v2.32."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Iterable

@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    task: str
    backend: str = "onnx"
    quality: float = .5
    speed: float = .5
    memory_mb: int = 0
    required: bool = False
    tags: tuple[str, ...] = ()

@dataclass(frozen=True)
class ModelSelection:
    task: str
    model_id: str
    score: float
    reason: str

class ModelRegistry:
    """Registers optional models and selects by task, hardware and quality budget."""
    def __init__(self, specs: Iterable[ModelSpec] = ()):
        self._specs: dict[str, ModelSpec] = {s.model_id:s for s in specs}
    def register(self, spec: ModelSpec) -> None:
        self._specs[spec.model_id] = spec
    def list(self, task: str | None = None) -> list[ModelSpec]:
        return [s for s in self._specs.values() if task is None or s.task == task]
    def select(self, task: str, *, quality_bias: float=.65, speed_bias: float=.35,
               available_backends: set[str] | None=None, max_memory_mb: int | None=None) -> ModelSelection | None:
        candidates=[]
        for s in self.list(task):
            if available_backends is not None and s.backend not in available_backends: continue
            if max_memory_mb is not None and s.memory_mb > max_memory_mb: continue
            score=quality_bias*s.quality + speed_bias*s.speed
            candidates.append((score,s))
        if not candidates: return None
        score,s=max(candidates,key=lambda x:(x[0],x[1].quality,x[1].speed))
        return ModelSelection(task,s.model_id,round(score,4),f"quality={s.quality:.2f},speed={s.speed:.2f},backend={s.backend}")
    def summary(self) -> list[dict[str,Any]]:
        return [{"id":s.model_id,"task":s.task,"backend":s.backend,"quality":s.quality,"speed":s.speed,"memory_mb":s.memory_mb,"tags":list(s.tags)} for s in self._specs.values()]

def default_model_registry() -> ModelRegistry:
    r=ModelRegistry()
    r.register(ModelSpec("scene-fast","scene",quality=.72,speed=.92,tags=("fast","general")))
    r.register(ModelSpec("scene-accurate","scene",quality=.94,speed=.55,memory_mb=1200,tags=("accurate",)))
    r.register(ModelSpec("objects-fast","objects",quality=.76,speed=.88,tags=("fast",)))
    r.register(ModelSpec("objects-accurate","objects",quality=.93,speed=.52,memory_mb=1800,tags=("accurate",)))
    r.register(ModelSpec("faces-reaction","emotion",quality=.86,speed=.64,memory_mb=900,tags=("face","reaction")))
    r.register(ModelSpec("shot-classifier","shot",quality=.88,speed=.82,memory_mb=500,tags=("shot",)))
    r.register(ModelSpec("action-fast","action",quality=.78,speed=.70,memory_mb=1200,tags=("action",)))
    r.register(ModelSpec("vlm-editorial","vlm",quality=.96,speed=.34,memory_mb=5000,tags=("semantic","editorial")))
    return r

__all__=["ModelSpec","ModelSelection","ModelRegistry","default_model_registry"]
