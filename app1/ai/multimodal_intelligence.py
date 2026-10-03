"""Optional model-backed multimodal intelligence with deterministic caching.

The core editor never requires a heavyweight ML package. Adapters may provide
objects, scene labels, emotions, shot types and VLM descriptions; results are
cached by media fingerprint + model/config so repeated analysis is cheap.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Protocol
import hashlib, json, time

@dataclass(frozen=True)
class ModelObservation:
    start: float
    end: float
    objects: tuple[str, ...] = ()
    scene: str = ""
    emotions: tuple[str, ...] = ()
    shot_type: str = ""
    action: str = ""
    description: str = ""
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

class MultimodalModelAdapter(Protocol):
    model_id: str
    def analyze(self, media_path: str | Path, sample_times: list[float]) -> list[ModelObservation]: ...

class NullModelAdapter:
    model_id = "none"
    def analyze(self, media_path, sample_times):
        return []

class JsonModelAdapter:
    """Offline adapter useful for local model runners and deterministic tests."""
    def __init__(self, json_path: str | Path, model_id: str = "json"):
        self.path = Path(json_path); self.model_id = model_id
    def analyze(self, media_path, sample_times):
        if not self.path.exists(): return []
        try: data=json.loads(self.path.read_text(encoding="utf-8"))
        except Exception: return []
        rows=data.get("observations", data if isinstance(data,list) else [])
        out=[]
        for row in rows:
            out.append(ModelObservation(
                float(row.get("start",0)), float(row.get("end",row.get("start",0)+1)),
                tuple(row.get("objects",()) or ()), str(row.get("scene", "")),
                tuple(row.get("emotions",()) or ()), str(row.get("shot_type", "")),
                str(row.get("action", "")), str(row.get("description", "")),
                float(row.get("confidence",0)), dict(row.get("metadata",{}) or {})))
        return out

class AnalysisCache:
    def __init__(self, root: str | Path = ".ai_cache/multimodal"):
        self.root=Path(root); self.root.mkdir(parents=True, exist_ok=True)
    def key(self, media_path, model_id, config=None):
        p=Path(media_path); st=p.stat() if p.exists() else None
        raw=f"{p.resolve()}|{st.st_size if st else 0}|{st.st_mtime_ns if st else 0}|{model_id}|{json.dumps(config or {},sort_keys=True)}"
        return hashlib.sha256(raw.encode()).hexdigest()
    def load(self, media_path, model_id, config=None):
        f=self.root/(self.key(media_path,model_id,config)+".json")
        if not f.exists(): return None
        try:
            data=json.loads(f.read_text(encoding="utf-8"));
            return [ModelObservation(
                float(x.get("start",0)), float(x.get("end",0)), tuple(x.get("objects",()) or ()),
                str(x.get("scene", "")), tuple(x.get("emotions",()) or ()), str(x.get("shot_type", "")),
                str(x.get("action", "")), str(x.get("description", "")), float(x.get("confidence",0)),
                dict(x.get("metadata",{}) or {})) for x in data["observations"]]
        except Exception: return None
    def save(self, media_path, model_id, observations, config=None):
        f=self.root/(self.key(media_path,model_id,config)+".json")
        f.write_text(json.dumps({"version":1,"created":time.time(),"model_id":model_id,"observations":[asdict(x) for x in observations]}, ensure_ascii=False),encoding="utf-8")

@dataclass
class IntelligenceResult:
    observations: list[ModelObservation] = field(default_factory=list)
    model_id: str = "none"
    cache_hit: bool = False

class CachedMultimodalIntelligence:
    def __init__(self, adapter: MultimodalModelAdapter | None = None, cache: AnalysisCache | None = None):
        self.adapter=adapter or NullModelAdapter(); self.cache=cache or AnalysisCache()
        try:
            from .model_runtime import RuntimeRegistry
            self.runtime=RuntimeRegistry()
        except Exception:
            self.runtime=None
    def analyze(self, media_path, sample_times, config=None):
        cached=self.cache.load(media_path,self.adapter.model_id,config)
        if cached is not None: return IntelligenceResult(cached,self.adapter.model_id,True)
        observations=self.adapter.analyze(media_path,sample_times)
        self.cache.save(media_path,self.adapter.model_id,observations,config)
        return IntelligenceResult(observations,self.adapter.model_id,False)

__all__=["ModelObservation","MultimodalModelAdapter","NullModelAdapter","JsonModelAdapter","AnalysisCache","IntelligenceResult","CachedMultimodalIntelligence"]
