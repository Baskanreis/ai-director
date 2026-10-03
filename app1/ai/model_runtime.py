"""Production-oriented optional inference runtime for AI Director v2.31.

Keeps heavyweight ML dependencies optional. Supports provider discovery for
ONNX Runtime (TensorRT/CUDA/DirectML/CoreML/OpenVINO/CPU), deterministic
batching, model metadata, and graceful fallback to CPU/JSON adapters.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable
import hashlib, json, time

@dataclass(frozen=True)
class RuntimeCapabilities:
    available: bool
    providers: tuple[str, ...] = ()
    selected: str = "none"
    package_version: str = ""
    reason: str = ""

@dataclass(frozen=True)
class RuntimeConfig:
    preferred_providers: tuple[str, ...] = (
        "TensorrtExecutionProvider", "CUDAExecutionProvider",
        "DmlExecutionProvider", "CoreMLExecutionProvider",
        "OpenVINOExecutionProvider", "CPUExecutionProvider",
    )
    batch_size: int = 8
    intra_threads: int = 0
    inter_threads: int = 0
    graph_optimization: str = "all"
    cache_dir: str = ".ai_cache/models"

@dataclass
class InferenceBatchResult:
    outputs: list[Any] = field(default_factory=list)
    provider: str = "none"
    batch_size: int = 0
    elapsed_ms: float = 0.0
    cache_hits: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

class InferenceCache:
    def __init__(self, root: str | Path = ".ai_cache/models"):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True)
    def key(self, model_id: str, payload: Any, config: dict[str, Any] | None = None) -> str:
        raw = json.dumps({"model": model_id, "payload": payload, "config": config or {}}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()
    def load(self, key: str):
        p=self.root/(key+".json")
        if not p.exists(): return None
        try: return json.loads(p.read_text(encoding="utf-8"))
        except Exception: return None
    def save(self, key: str, value: Any):
        (self.root/(key+".json")).write_text(json.dumps(value, ensure_ascii=False, default=str), encoding="utf-8")

class OnnxRuntimeManager:
    """Owns optional ONNX Runtime sessions and provider fallback."""
    def __init__(self, config: RuntimeConfig | None = None):
        self.config = config or RuntimeConfig()
        self.ort = None
        self.capabilities = self._discover()
        self._sessions: dict[str, Any] = {}

    def _discover(self) -> RuntimeCapabilities:
        try:
            import onnxruntime as ort
        except Exception as exc:
            return RuntimeCapabilities(False, reason=f"onnxruntime unavailable: {exc}")
        self.ort = ort
        available = tuple(ort.get_available_providers())
        selected = next((p for p in self.config.preferred_providers if p in available), "none")
        return RuntimeCapabilities(True, available, selected, getattr(ort, "__version__", ""))

    def provider_chain(self) -> list[str]:
        if not self.capabilities.available: return []
        available=set(self.capabilities.providers)
        return [p for p in self.config.preferred_providers if p in available]

    def session(self, model_path: str | Path, model_id: str | None = None):
        if not self.capabilities.available: raise RuntimeError(self.capabilities.reason)
        key=str(Path(model_path).resolve())
        if key in self._sessions: return self._sessions[key]
        opts=self.ort.SessionOptions()
        if self.config.intra_threads: opts.intra_op_num_threads=self.config.intra_threads
        if self.config.inter_threads: opts.inter_op_num_threads=self.config.inter_threads
        try: opts.graph_optimization_level=getattr(self.ort.GraphOptimizationLevel, "ORT_ENABLE_ALL")
        except Exception: pass
        providers=self.provider_chain() or ["CPUExecutionProvider"]
        sess=self.ort.InferenceSession(str(model_path), sess_options=opts, providers=providers)
        self._sessions[key]=sess
        return sess

class BatchedInference:
    """Generic batched execution wrapper for model adapters."""
    def __init__(self, runner: Callable[[list[Any]], list[Any]], batch_size: int = 8):
        self.runner=runner; self.batch_size=max(1,int(batch_size))
    def run(self, items: Iterable[Any]) -> InferenceBatchResult:
        rows=list(items); out=[]; started=time.perf_counter()
        for i in range(0,len(rows),self.batch_size):
            batch=rows[i:i+self.batch_size]
            result=self.runner(batch)
            if result is None: continue
            out.extend(result)
        return InferenceBatchResult(out, batch_size=self.batch_size, elapsed_ms=(time.perf_counter()-started)*1000)

class OnnxModelAdapter:
    """Adapter for ONNX models with an injected preprocessor/postprocessor.

    This deliberately avoids assuming a particular vision architecture. The
    editor can use the same runtime for classifiers, detectors or embeddings.
    """
    def __init__(self, model_path: str | Path, model_id: str | None = None,
                 preprocess: Callable[[Any], Any] | None = None,
                 postprocess: Callable[[Any], Any] | None = None,
                 runtime: OnnxRuntimeManager | None = None,
                 batch_size: int = 8):
        self.model_path=Path(model_path)
        self.model_id=model_id or self.model_path.stem
        self.preprocess=preprocess or (lambda x:x)
        self.postprocess=postprocess or (lambda x:x)
        self.runtime=runtime or OnnxRuntimeManager(RuntimeConfig(batch_size=batch_size))
        self.batch_size=batch_size

    def _run_batch(self, batch):
        import numpy as np
        session=self.runtime.session(self.model_path,self.model_id)
        inp=session.get_inputs()[0]
        arr=np.asarray([self.preprocess(x) for x in batch])
        result=session.run(None,{inp.name:arr})
        return [self.postprocess([r[i] for r in result]) for i in range(len(batch))]

    def infer(self, items: Iterable[Any]) -> InferenceBatchResult:
        return BatchedInference(self._run_batch,self.batch_size).run(items)

class RuntimeRegistry:
    """Selects the strongest installed runtime without making it mandatory."""
    def __init__(self, config: RuntimeConfig | None = None):
        self.config=config or RuntimeConfig()
        self.onnx=OnnxRuntimeManager(self.config)
    def summary(self) -> dict[str,Any]:
        c=self.onnx.capabilities
        return {"onnxruntime":c.available,"providers":list(c.providers),"selected":c.selected,"version":c.package_version,"reason":c.reason}

__all__=["RuntimeCapabilities","RuntimeConfig","InferenceBatchResult","InferenceCache","OnnxRuntimeManager","BatchedInference","OnnxModelAdapter","RuntimeRegistry"]
