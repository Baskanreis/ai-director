"""CPU-light retention risk predictor.

This is deliberately a *risk model*, not a claim of viewer behavior.  It uses
observable edit structure plus first-party channel baselines when available.
It never loads an LLM and exposes confidence/evidence so the Director can
separate learned evidence from heuristics.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from statistics import median
from typing import Any

@dataclass(frozen=True)
class RetentionPrediction:
    score: float
    confidence: float
    risk: str
    evidence: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    hotspots: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clamp(x: float, lo=0.0, hi=100.0) -> float:
    return max(lo, min(hi, float(x)))


def _events(plan: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    out=[]
    for e in plan.get("events", []) if isinstance(plan, dict) else []:
        if isinstance(e, dict) and e.get("kind") == kind:
            out.append(e)
    return out


def predict_retention(plan: dict[str, Any], *, channel_brain: dict[str, Any] | None = None,
                      analytics: list[dict[str, Any]] | None = None) -> RetentionPrediction:
    """Return a conservative, explainable retention-risk estimate.

    A score is *edit-watchability*, not predicted percentage watched. If owned
    analytics exist, only their channel-level baselines calibrate the target;
    they do not magically prove causality for an edit choice.
    """
    duration=float(plan.get("source_duration", plan.get("duration", 0)) or 0)
    if duration <= 0:
        return RetentionPrediction(0.0, 0.05, "unknown", (), ("duration_missing",), ())

    score=70.0; warnings=[]; evidence=["structural_heuristic"]
    events=plan.get("events", []) if isinstance(plan,dict) else []
    breaks=len(_events(plan,"pattern_break")); broll=len(_events(plan,"broll_cue")); hooks=len(_events(plan,"hook"))
    per_min=max(duration/60.0,1e-6)
    break_rate=breaks/per_min; broll_rate=broll/per_min
    if hooks: score += 8
    else: score -= 10; warnings.append("weak_or_missing_hook")
    if duration>90 and break_rate < .5: score -= 8; warnings.append("low_pattern_break_density")
    elif break_rate > 8: score -= 5; warnings.append("high_pattern_break_density")
    if duration>120 and broll_rate < .5: score -= 6; warnings.append("low_broll_density")

    metadata=plan.get("metadata",{}) if isinstance(plan,dict) else {}
    target=(((channel_brain or {}).get("style_targets") or {}).get("cut_density_per_minute"))
    observed=metadata.get("cut_density_per_minute")
    if target and observed:
        delta=abs(float(observed)-float(target))/max(float(target),1.0)
        score -= min(12.0, delta*8.0)
        evidence.append("channel_brain_cut_density")

    rows=analytics or []
    avp=[]
    for r in rows:
        if not isinstance(r,dict): continue
        for k in ("averageViewPercentage","avg_view_percentage","average_view_percentage"):
            try:
                v=float(r.get(k,0) or 0)
                if v>0: avp.append(v); break
            except Exception: pass
    confidence=.20
    if target or observed: confidence += .15
    if avp:
        baseline=median(avp)
        evidence.append("owned_analytics_baseline")
        confidence += min(.45, .15 + len(avp)*.01)
        # Calibrate the *target* conservatively; never claim causal lift.
        if baseline >= 55: score += 5
        elif baseline < 35: score -= 5
    if (channel_brain or {}).get("confidence"):
        confidence += min(.15, float(channel_brain["confidence"])*.15)
    score=_clamp(score)
    risk="high" if score < 50 else "medium" if score < 70 else "low"
    hotspot=[]
    if hooks==0: hotspot.append({"start":0.0,"end":min(30.0,duration),"reason":"hook_risk"})
    if duration>120 and broll_rate<.5: hotspot.append({"start":duration*.35,"end":duration*.65,"reason":"visual_variety_risk"})
    return RetentionPrediction(round(score,2), round(min(1.0,confidence),3), risk,
                                tuple(dict.fromkeys(evidence)), tuple(dict.fromkeys(warnings)), tuple(hotspot))

__all__=["RetentionPrediction","predict_retention"]
