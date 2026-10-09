"""Autonomous Edit Pass controller.

Unifies scene creative planning, Marketplace Pack Director, deterministic QC and
existing Autonomous Revision into one low-cost controller. No second AI model is
loaded: the controller only orchestrates already available metadata/analysis
layers and an optional caller-provided real preview/render evaluator.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Iterable

from app.ai.autonomous_revision import RevisionPolicy, RevisionResult, run_revision_loop
from app.ai.creative_studio_ai import ClipContext
from app.ai.scene_creative_director import SceneCreativePlan, build_scene_creative_plan


@dataclass(frozen=True)
class AutonomousEditPolicy:
    max_revision_rounds: int = 3
    min_improvement: float = 0.5
    items_per_scene: int = 4
    preview_first: bool = True
    allow_secondary_pack_mix: bool = True
    max_pack_mix: float = 0.35
    cpu_budget: str = "low"


@dataclass(frozen=True)
class SceneDecision:
    scene_id: str
    clip_id: str
    pack_id: str
    pack_name: str
    secondary_pack_id: str = ""
    pack_mix: float = 0.0
    item_count: int = 0
    intensity: float = 0.0
    reason: str = ""


@dataclass
class AutonomousEditResult:
    plan: dict[str, Any]
    scene_plan: SceneCreativePlan
    scene_decisions: list[SceneDecision]
    revision: RevisionResult | None = None
    status: str = "planned"
    qc_score: float = 0.0
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan": self.plan,
            "scene_plan": self.scene_plan.to_dict(),
            "scene_decisions": [asdict(x) for x in self.scene_decisions],
            "revision": None if self.revision is None else {
                "best": asdict(self.revision.best),
                "candidates": [asdict(x) for x in self.revision.candidates],
                "stopped_reason": self.revision.stopped_reason,
            },
            "status": self.status,
            "qc_score": self.qc_score,
            "history": self.history,
        }


def _scene_decisions(scene_plan: SceneCreativePlan) -> list[SceneDecision]:
    out: list[SceneDecision] = []
    for stack in scene_plan.stacks:
        intensity = max((item.intensity for item in stack.items), default=0.0)
        out.append(SceneDecision(
            scene_id=stack.scene_id,
            clip_id=stack.clip_id,
            pack_id=stack.primary_pack_id,
            pack_name=stack.primary_pack_name,
            secondary_pack_id=stack.secondary_pack_id,
            pack_mix=stack.pack_mix,
            item_count=len(stack.items),
            intensity=round(intensity, 3),
            reason=f"{stack.style} scene; pack-first creative stack",
        ))
    return out


def build_autonomous_plan(
    contexts: Iterable[ClipContext],
    *,
    policy: AutonomousEditPolicy | None = None,
) -> tuple[dict[str, Any], SceneCreativePlan, list[SceneDecision]]:
    """Create a deterministic scene-by-scene autonomous edit plan."""
    policy = policy or AutonomousEditPolicy()
    context_list = list(contexts)
    scene_plan = build_scene_creative_plan(
        context_list,
        items_per_scene=policy.items_per_scene,
        variant=0,
    )
    decisions = _scene_decisions(scene_plan)
    if not policy.allow_secondary_pack_mix:
        decisions = [SceneDecision(
            d.scene_id, d.clip_id, d.pack_id, d.pack_name,
            "", 0.0, d.item_count, d.intensity, d.reason
        ) for d in decisions]

    timeline = []
    for stack in scene_plan.stacks:
        for item in stack.items:
            timeline.append({
                "scene_id": item.scene_id,
                "clip_id": item.clip_id,
                "asset_id": item.asset_id,
                "kind": item.kind,
                "start": item.start,
                "duration": item.duration,
                "intensity": item.intensity,
                "optional": True,
                "heavy": item.kind in {"motion", "effect", "transition"} and item.intensity >= 0.85,
                "enabled": True,
                "reason": item.reason,
            })

    plan = {
        "version": "autonomous_edit_v1",
        "timeline": timeline,
        "scenes": [asdict(d) for d in decisions],
        "metadata": {
            "single_model_policy": True,
            "marketplace_pack_first": True,
            "cpu_budget": policy.cpu_budget,
            "max_pack_mix": policy.max_pack_mix,
        },
    }
    return plan, scene_plan, decisions


def run_autonomous_edit_pass(
    contexts: Iterable[ClipContext],
    *,
    evaluate: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    policy: AutonomousEditPolicy | None = None,
    brain_score: Callable[[dict[str, Any]], float] | None = None,
    retention_score: Callable[[dict[str, Any]], float] | None = None,
) -> AutonomousEditResult:
    """Build, optionally preview/QC, and safely revise one autonomous edit pass.

    ``evaluate`` is deliberately injected. The normal application can point it
    at its existing preview renderer + visual/audio/export QC, while tests can
    use a cheap structural evaluator. If no evaluator is supplied, planning ends
    without pretending a real render/QC occurred.
    """
    policy = policy or AutonomousEditPolicy()
    plan, scene_plan, decisions = build_autonomous_plan(contexts, policy=policy)
    result = AutonomousEditResult(plan, scene_plan, decisions)

    if evaluate is None:
        result.status = "planned_no_render"
        result.qc_score = 0.0
        return result

    revision = run_revision_loop(
        deepcopy(plan),
        evaluate,
        policy=RevisionPolicy(
            max_rounds=policy.max_revision_rounds,
            min_improvement=policy.min_improvement,
            preserve_speech=True,
            avoid_new_heavy_effects=True,
            cpu_budget=policy.cpu_budget,
        ),
        brain_score=brain_score,
        retention_score=retention_score,
    )
    result.revision = revision
    result.plan = revision.best.plan
    result.status = "qc_pass" if bool(revision.best.report.get("passed", False)) else "revised"
    result.qc_score = float(revision.best.report.get("score", revision.best.score) or 0.0)
    result.history = [
        {"version": c.version, "score": c.score, "accepted": c.accepted, "changes": list(c.changes)}
        for c in revision.candidates
    ]
    return result


__all__ = [
    "AutonomousEditPolicy", "SceneDecision", "AutonomousEditResult",
    "build_autonomous_plan", "run_autonomous_edit_pass",
]
