"""Deterministic FFmpeg color-grade primitives."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class ColorGrade:
    exposure: float = 0.0
    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    gamma: float = 1.0
    temperature: float = 0.0
    tint: float = 0.0
    highlights: float = 0.0
    shadows: float = 0.0
    def clamp(self):
        self.contrast=max(0.0,min(4.0,self.contrast)); self.saturation=max(0.0,min(4.0,self.saturation)); self.gamma=max(0.1,min(4.0,self.gamma)); return self
    def to_dict(self): return self.__dict__.copy()
    @classmethod
    def from_dict(cls,d): return cls(**{k:float(d.get(k,getattr(cls,k))) for k in cls.__dataclass_fields__})

def color_grade_fragment(g: ColorGrade) -> str:
    g=ColorGrade(**g.to_dict()).clamp()
    # exposure is expressed as a power-of-two multiplier; temperature/tint are
    # conservative channel offsets to keep the filter portable across FFmpeg builds.
    exposure_mul=2.0**g.exposure
    parts=[f"eq=brightness={g.brightness:.4f}:contrast={g.contrast:.4f}:saturation={g.saturation:.4f}:gamma={g.gamma:.4f}"]
    if abs(g.exposure)>1e-6: parts.append(f"lutrgb=r='clip(val*{exposure_mul:.5f})':g='clip(val*{exposure_mul:.5f})':b='clip(val*{exposure_mul:.5f})'")
    if abs(g.temperature)>1e-6 or abs(g.tint)>1e-6:
        r=1+g.temperature/100.0+g.tint/200.0; b=1-g.temperature/100.0+g.tint/200.0
        parts.append(f"lutrgb=r='clip(val*{r:.5f})':g='clip(val*{1-g.tint/200.0:.5f})':b='clip(val*{b:.5f})'")
    return ",".join(parts)
