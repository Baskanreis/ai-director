"""Timeline-friendly retention hotspot normalization and targeted revision requests."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Iterable

@dataclass(frozen=True)
class RetentionHotspot:
    start: float
    end: float
    reason: str
    severity: str = "medium"
    confidence: float = 0.0
    source: str = "retention_predictor"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _severity(value: Any) -> str:
    if isinstance(value, str) and value in {"low", "medium", "high"}:
        return value
    try:
        n = float(value)
        return "high" if n >= 70 else "medium" if n >= 40 else "low"
    except Exception:
        return "medium"


def normalize_hotspots(items: Iterable[dict[str, Any]] | None, duration: float = 0.0) -> tuple[RetentionHotspot, ...]:
    out: list[RetentionHotspot] = []
    for item in items or ():
        if not isinstance(item, dict):
            continue
        try:
            start = max(0.0, float(item.get("start", 0.0)))
            end = max(start, float(item.get("end", start)))
        except Exception:
            continue
        if duration > 0:
            start, end = min(start, duration), min(end, duration)
        if end <= start:
            continue
        out.append(RetentionHotspot(start, end, str(item.get("reason", "retention_risk")),
                                   _severity(item.get("severity", item.get("score", "medium"))),
                                   max(0.0, min(1.0, float(item.get("confidence", 0.0) or 0.0))),
                                   str(item.get("source", "retention_predictor"))))
    # Merge overlapping/adjacent hotspots with the same reason; keep UI uncluttered.
    out.sort(key=lambda h: (h.start, h.end, h.reason))
    merged: list[RetentionHotspot] = []
    for h in out:
        if merged and h.reason == merged[-1].reason and h.start <= merged[-1].end + 0.25:
            p = merged[-1]
            merged[-1] = RetentionHotspot(p.start, max(p.end, h.end), p.reason,
                                          "high" if "high" in (p.severity, h.severity) else "medium" if "medium" in (p.severity, h.severity) else "low",
                                          max(p.confidence, h.confidence), p.source)
        else:
            merged.append(h)
    return tuple(merged)


def targeted_revision_request(hotspot: RetentionHotspot) -> dict[str, Any]:
    """A deterministic request consumed by the revision/director layer; no model call."""
    actions = {
        "hook_risk": ("strengthen_hook", "visual_pattern_break"),
        "visual_variety_risk": ("add_broll_or_reframe", "pattern_break"),
        "low_pattern_break_density": ("add_pattern_break", "rebalance_pacing"),
        "low_broll_density": ("add_broll_or_reframe",),
        "pacing_risk": ("rebalance_pacing",),
    }.get(hotspot.reason, ("inspect_pacing",))
    return {"scope": {"start": hotspot.start, "end": hotspot.end},
            "reason": hotspot.reason, "severity": hotspot.severity,
            "confidence": hotspot.confidence, "actions": list(actions),
            "non_destructive": True}


__all__ = ["RetentionHotspot", "normalize_hotspots", "targeted_revision_request"]
