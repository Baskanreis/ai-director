"""Feature-aware render-time prediction with conservative fallbacks."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from statistics import median
from typing import Any

@dataclass(frozen=True)
class RenderFeatures:
    source_duration_s: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    codec: str = ""
    effect_intensity: float = 0.0
    proxy: bool = False

    @property
    def work_units(self) -> float:
        duration = max(1.0, float(self.source_duration_s or 1.0))
        pixels = max(1.0, (self.width * self.height) / (1280 * 720)) if self.width and self.height else 1.0
        fps = max(0.5, float(self.fps or 30.0) / 30.0)
        codec_factor = {"h264": 1.0, "hevc": 1.18, "h265": 1.18, "av1": 1.30, "prores": 1.35}.get(self.codec.lower(), 1.05 if self.codec else 1.0)
        effects = 1.0 + min(2.0, max(0.0, float(self.effect_intensity))) * 0.35
        proxy_factor = 0.45 if self.proxy else 1.0
        return duration * pixels * fps * codec_factor * effects * proxy_factor

@dataclass(frozen=True)
class Prediction:
    eta_s: float | None
    confidence: float
    sample_count: int
    work_units: float

class PredictiveRenderModel:
    """Robust median-rate model; never overrides hard resource gates."""
    def __init__(self, max_history: int = 500):
        self.max_history = max(20, int(max_history))
        self.samples: list[tuple[float, float, bool]] = []  # work_units, seconds, success

    @staticmethod
    def features_from(job: Any) -> RenderFeatures:
        f = getattr(job, "render_features", None)
        if isinstance(f, RenderFeatures):
            return f
        if isinstance(f, dict):
            try: return RenderFeatures(**{k:v for k,v in f.items() if k in RenderFeatures.__dataclass_fields__})
            except TypeError: pass
        return RenderFeatures(
            source_duration_s=float(getattr(job, "duration_s", 0) or getattr(job, "source_duration_s", 0) or 0),
            width=int(getattr(job, "width", 0) or 0), height=int(getattr(job, "height", 0) or 0),
            fps=float(getattr(job, "fps", 0) or 0), codec=str(getattr(job, "codec", "") or ""),
            effect_intensity=float(getattr(job, "effect_intensity", 0) or 0), proxy=bool(getattr(job, "proxy", False)),
        )

    def record(self, features: RenderFeatures, duration_s: float, success: bool = True) -> None:
        self.samples.append((features.work_units, max(0.001, float(duration_s)), bool(success)))
        self.samples = self.samples[-self.max_history:]

    def predict(self, features: RenderFeatures) -> Prediction:
        units = features.work_units
        good = [(seconds / max(0.001, u)) for u, seconds, ok in self.samples if ok and u > 0]
        if not good:
            return Prediction(None, 0.0, 0, units)
        rates = good[-50:]
        rate = float(median(rates))
        n = len(rates)
        confidence = min(1.0, n / 12.0)
        return Prediction(max(0.001, rate * units), confidence, n, units)

    def to_dict(self):
        return {"version": 1, "samples": [{"work_units":u,"duration_s":d,"success":ok} for u,d,ok in self.samples]}

    @classmethod
    def from_dict(cls, data):
        x=cls()
        for s in (data or {}).get("samples", []):
            try: x.samples.append((float(s["work_units"]), float(s["duration_s"]), bool(s.get("success", True))))
            except (KeyError,TypeError,ValueError): continue
        return x
