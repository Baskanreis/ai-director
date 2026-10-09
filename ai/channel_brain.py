from __future__ import annotations
"""Channel Brain: low-cost fusion of public DNA, owned analytics and local learning.

This is calibration, not model retraining. It produces compact, confidence-weighted
constraints that the Final Director can consume without loading another model.
"""
from dataclasses import asdict, dataclass, field
from statistics import median
from typing import Any, Iterable

@dataclass(frozen=True)
class ChannelBrainProfile:
    channel_id: str = ""
    channel_name: str = ""
    confidence: float = 0.0
    style_targets: dict[str, float] = field(default_factory=dict)
    packaging_targets: dict[str, float] = field(default_factory=dict)
    performance_targets: dict[str, float] = field(default_factory=dict)
    learned_hints: dict[str, Any] = field(default_factory=dict)
    guardrails: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    def to_dict(self): return asdict(self)


def _num(d: dict, key: str, default=0.0) -> float:
    try: return float(d.get(key, default) or default)
    except Exception: return float(default)


def build_channel_brain(channel_dna: dict | None = None,
                        analytics: Iterable[dict] | None = None,
                        learning_hints: dict | None = None,
                        reference_edit: dict | None = None) -> ChannelBrainProfile:
    dna = channel_dna or {}
    m = dna.get("metrics", {})
    p = dna.get("performance", {})
    rows = list(analytics or [])
    hints = learning_hints or {}
    ref = reference_edit or {}

    # Targets are deliberately soft. They guide the Director rather than forcing copies.
    style = {
        "median_video_seconds": _num(m, "median_video_seconds"),
        "caption_ratio": _num(m, "caption_availability_ratio"),
        "upload_interval_days": _num(m, "upload_interval_days"),
    }
    # Reference-media evidence is the strongest direct style signal.
    agg = ref.get("aggregate", {}) if isinstance(ref, dict) else {}
    if _num(agg, "median_cut_density_per_minute") > 0:
        style["cut_density_per_minute"] = _num(agg, "median_cut_density_per_minute")
    if _num(agg, "median_shot_seconds") > 0:
        style["median_shot_seconds"] = _num(agg, "median_shot_seconds")
    packaging = {
        "question_rate": _num(m, "question_title_ratio"),
        "number_rate": _num(m, "number_title_ratio"),
        "bracket_rate": _num(m, "bracket_title_ratio"),
        "avg_title_chars": _num(m, "avg_title_chars"),
    }

    # Analytics are first-party evidence and therefore receive higher trust than public proxies.
    vals = {}
    for key in ("averageViewPercentage", "avg_view_percentage", "average_view_percentage"):
        xs=[]
        for r in rows:
            try:
                v=float(r.get(key,0) or 0)
                if v>0: xs.append(v)
            except Exception: pass
        if xs: vals["avg_view_percentage"] = median(xs); break
    for key in ("averageViewDuration", "avg_view_duration"):
        xs=[]
        for r in rows:
            try:
                v=float(r.get(key,0) or 0)
                if v>0: xs.append(v)
            except Exception: pass
        if xs: vals["avg_view_duration"] = median(xs); break
    if vals:
        p = dict(p); p.update(vals)

    # Local learning is a calibration layer, never a replacement for direct evidence.
    learned = {k:v for k,v in hints.items() if isinstance(v, dict) and v.get("samples",0)>=2}
    guardrails = [
        "Use channel DNA as a soft prior, not a hard copy of another creator.",
        "Prefer first-party Analytics over public view-count proxies when both exist.",
        "Do not claim a causal edit effect unless owned reference media provides edit evidence.",
        "Keep speech clarity and platform safety constraints above style preferences.",
    ]
    evidence=[]
    n=int(m.get("metadata",{}).get("sample_size",0) or 0)
    if n: evidence.append(f"public_channel_sample:{n}")
    if rows: evidence.append(f"owned_analytics_sample:{len(rows)}")
    if learned: evidence.append(f"learning_signals:{len(learned)}")
    if ref: evidence.append("owned_reference_edit_analysis")
    confidence=min(1.0, .20 + min(n,50)*.012 + (.25 if rows else 0) + (.15 if ref else 0) + min(.20,len(learned)*.01))
    return ChannelBrainProfile(
        channel_id=str(dna.get("channel",{}).get("channel_id", "")),
        channel_name=str(dna.get("channel",{}).get("title", "")),
        confidence=round(confidence,3), style_targets=style, packaging_targets=packaging,
        performance_targets={k:round(float(v),3) for k,v in p.items() if isinstance(v,(int,float))},
        learned_hints=learned, guardrails=tuple(guardrails), evidence=tuple(evidence),
        metadata={"engine_version":"2.52","fusion":"reference+public+first_party+learning","reference_edit":bool(ref)},
    )


def score_plan_against_brain(plan: dict[str, Any], brain: ChannelBrainProfile) -> dict[str, Any]:
    """Cheap deterministic calibration score used before/after final synthesis."""
    checks=[]; score=1.0
    meta=plan.get("metadata",{}) if isinstance(plan,dict) else {}
    density=meta.get("cut_density_per_minute")
    target=brain.style_targets.get("cut_density_per_minute")
    if density is not None and target:
        delta=abs(float(density)-float(target))/max(float(target),1.0)
        penalty=min(.20,delta*.10); score-=penalty
        checks.append({"metric":"cut_density","delta":round(delta,3),"penalty":round(penalty,3)})
    return {"score":round(max(0,score),3),"checks":checks,"confidence":brain.confidence}
