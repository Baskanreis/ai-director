"""Confidence-aware multimodal fusion and decision reliability."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class SignalConfidence:
    value: float
    sources: tuple[str,...] = ()
    agreement: float = 1.0
    quality: float = 1.0
    reason: str = ""

def fuse_confidences(values: Iterable[tuple[str,float]], *, quality: float=1.0) -> SignalConfidence:
    rows=[(n,max(0.,min(1.,float(v)))) for n,v in values]
    if not rows: return SignalConfidence(0.,(),0.,quality,"no evidence")
    vals=[v for _,v in rows]; mean=sum(vals)/len(vals)
    spread=max(vals)-min(vals) if len(vals)>1 else 0.
    agreement=max(0.,1.-spread)
    value=max(0.,min(1.,mean*(.65+.35*agreement)*max(0.,min(1.,quality))))
    return SignalConfidence(round(value,4),tuple(n for n,_ in rows),round(agreement,4),round(quality,4),f"{len(rows)} evidence sources")

__all__=["SignalConfidence","fuse_confidences"]
