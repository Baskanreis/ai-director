"""CPU-light, non-destructive regional revision engine.

Generates small edit alternatives only for a retention hotspot. It never loads a
new model and never mutates the original plan. A caller may pass an existing real
media preview evaluator to score each candidate; otherwise candidates remain
structural and ready for the normal renderer.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from copy import deepcopy
from typing import Any, Callable

from .retention_hotspots import RetentionHotspot, targeted_revision_request
from .combination_engine import CombinationContext, generate_combinations
from .semantic_asset_matcher import SemanticContext, match_assets

@dataclass(frozen=True)
class RegionalRevisionPolicy:
    max_candidates: int = 3
    min_improvement: float = 0.5
    max_broll_cues: int = 2
    preserve_speech: bool = True
    cpu_budget: str = "low"
    combination_budget: int = 10_000
    combination_count: int = 3
    semantic_match_count: int = 6

@dataclass
class RegionalCandidate:
    name: str
    plan: dict[str, Any]
    operations: list[dict[str, Any]] = field(default_factory=list)
    report: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    accepted: bool = False

@dataclass
class RegionalRevisionResult:
    best: RegionalCandidate
    candidates: list[RegionalCandidate]
    stopped_reason: str


def _overlap(cue: dict[str, Any], start: float, end: float) -> bool:
    try:
        a = float(cue.get("start", 0.0)); b = float(cue.get("end", a))
        return a < end and b > start
    except Exception:
        return False


def _apply_ops(plan: dict[str, Any], hotspot: RetentionHotspot, ops: list[dict[str, Any]]) -> dict[str, Any]:
    out = deepcopy(plan)
    out.setdefault("metadata", {})["regional_revision"] = {
        "scope": {"start": hotspot.start, "end": hotspot.end},
        "reason": hotspot.reason,
        "operations": deepcopy(ops),
        "non_destructive": True,
    }
    timeline = out.get("timeline")
    if not isinstance(timeline, list):
        timeline = []
        out["timeline"] = timeline

    # Operations are intentionally represented in metadata as well as light cue
    # annotations. The existing renderer can ignore them safely; a regional-aware
    # renderer can consume them without changing the source media.
    for op in ops:
        kind = op.get("kind")
        if kind == "reframe":
            for cue in timeline:
                if isinstance(cue, dict) and _overlap(cue, hotspot.start, hotspot.end):
                    cue.setdefault("creative_metadata", {})["regional_reframe"] = True
                    cue["creative_metadata"]["regional_scale"] = float(op.get("scale", 1.06))
        elif kind == "broll":
            timeline.append({
                "kind": "creative_overlay", "start": hotspot.start,
                "end": hotspot.end, "optional": True, "heavy": False,
                "creative_metadata": {"regional_broll_candidate": True},
            })
        elif kind == "pattern_break":
            timeline.append({
                "kind": "creative_marker", "start": hotspot.start,
                "end": min(hotspot.end, hotspot.start + 0.35), "optional": True,
                "creative_metadata": {"regional_pattern_break": True},
            })
        elif kind == "pacing":
            out["metadata"]["regional_pacing_hint"] = {"start": hotspot.start, "end": hotspot.end, "target": op.get("target", "tighter")}
        elif kind == "asset_stack":
            out.setdefault("metadata", {}).setdefault("regional_asset_stacks", []).append({
                "start": hotspot.start, "end": hotspot.end,
                "assets": deepcopy(op.get("assets", {})),
                "combination_score": op.get("combination_score"),
                "combination_reasons": deepcopy(op.get("combination_reasons", [])),
                "search_budget": op.get("search_budget", 0),
                "non_destructive": True,
            })
    return out


def generate_regional_candidates(plan: dict[str, Any], hotspot: RetentionHotspot,
                                 policy: RegionalRevisionPolicy | None = None,
                                 combination_context: CombinationContext | None = None) -> list[RegionalCandidate]:
    policy = policy or RegionalRevisionPolicy()
    req = targeted_revision_request(hotspot)
    actions = set(req["actions"])
    variants: list[list[dict[str, Any]]] = []
    if "strengthen_hook" in actions or hotspot.reason == "hook_risk":
        variants.append([{"kind": "pattern_break"}, {"kind": "reframe", "scale": 1.08}])
    if "add_broll_or_reframe" in actions:
        variants.append([{"kind": "broll"}])
        variants.append([{"kind": "reframe", "scale": 1.06}])
    if "pattern_break" in actions or "add_pattern_break" in actions:
        variants.append([{"kind": "pattern_break"}, {"kind": "reframe", "scale": 1.05}])
    if "rebalance_pacing" in actions or "inspect_pacing" in actions:
        variants.append([{"kind": "pacing", "target": "tighter"}])
    # Stable unique variants, capped for low CPU usage.
    seen=set(); unique=[]
    for ops in variants:
        key=tuple(sorted((o["kind"], str(o.get("scale", "")), str(o.get("target", ""))) for o in ops))
        if key not in seen:
            seen.add(key); unique.append(ops)
    out=[]
    # Asset-aware regional search: use the existing 10K+ combination engine,
    # but only for this hotspot. This keeps the global library search out of
    # the full-video revision loop. The engine is deterministic and model-free.
    ctx = combination_context or CombinationContext(
        scene_type="general", style="viral_fast", platform="shorts",
        energy=0.72 if hotspot.severity == "high" else 0.58,
        speech=bool(plan.get("metadata", {}).get("speech", False)),
        music=bool(plan.get("metadata", {}).get("music", False)),
        faces=bool(plan.get("metadata", {}).get("faces", False)),
        duration=max(0.1, hotspot.end - hotspot.start),
        seed=int(hotspot.start * 1000) ^ int(hotspot.end * 1000),
        retention_priority=0.9,
    )
    sem = SemanticContext(
        transcript=str(plan.get("metadata", {}).get("hotspot_transcript", plan.get("metadata", {}).get("transcript", ""))),
        objects=tuple(plan.get("metadata", {}).get("objects", ()) or ()),
        emotion=str(plan.get("metadata", {}).get("emotion", "")),
        scene_type=ctx.scene_type, intent=str(plan.get("metadata", {}).get("creative_intent", "")),
        energy=ctx.energy, duration=ctx.duration, faces=ctx.faces,
    )
    semantic = match_assets(sem, limit=policy.semantic_match_count)
    combos = generate_combinations(ctx, count=max(1, min(policy.combination_count, policy.max_candidates)),
                                   candidate_budget=policy.combination_budget)
    limit = max(1, policy.max_candidates)
    for i, ops in enumerate(unique[:limit], 1):
        chosen_combo = combos[i - 1] if i <= len(combos) else None
        if chosen_combo:
            asset_stack = {k: (getattr(chosen_combo, k).id if getattr(chosen_combo, k) else None)
                           for k in ("effect", "motion", "transition", "text", "overlay", "sfx", "audio_fx")}
            ops = list(ops) + [{"kind": "asset_stack", "assets": asset_stack,
                                "semantic_matches": [{"id": m.asset.id, "kind": m.asset.kind, "score": m.score, "reasons": list(m.reasons)} for m in semantic],
                                "combination_score": chosen_combo.score,
                                "combination_reasons": list(chosen_combo.reasons),
                                "search_budget": policy.combination_budget}]
        candidate = RegionalCandidate(f"r{i}", _apply_ops(plan, hotspot, ops), ops)
        candidate.report["asset_combination"] = asset_stack if chosen_combo else None
        candidate.report["semantic_matches"] = [{"id": m.asset.id, "score": m.score, "reasons": list(m.reasons)} for m in semantic]
        candidate.report["combination_score"] = chosen_combo.score if chosen_combo else None
        out.append(candidate)
    return out


def revise_hotspot(plan: dict[str, Any], hotspot: RetentionHotspot,
                   evaluate: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
                   *, policy: RegionalRevisionPolicy | None = None) -> RegionalRevisionResult:
    policy = policy or RegionalRevisionPolicy()
    base_report = evaluate(deepcopy(plan)) if evaluate else {"score": 0.0, "passed": True}
    base_score = float(base_report.get("score", 0.0) or 0.0)
    base = RegionalCandidate("base", deepcopy(plan), [], base_report, base_score, True)
    candidates=[base]
    current=base
    for cand in generate_regional_candidates(plan, hotspot, policy):
        cand.report = evaluate(deepcopy(cand.plan)) if evaluate else {"score": base_score}
        cand.score = float(cand.report.get("score", base_score) or base_score)
        if cand.score >= current.score + policy.min_improvement:
            current.accepted=False
            cand.accepted=True
            current=cand
        candidates.append(cand)
    reason = "regional_improvement" if current.name != "base" else "no_meaningful_regional_improvement"
    return RegionalRevisionResult(current, candidates, reason)

__all__=["RegionalRevisionPolicy","RegionalCandidate","RegionalRevisionResult","generate_regional_candidates","revise_hotspot"]
