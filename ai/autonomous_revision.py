"""Autonomous edit revision loop.

Low-cost controller around the existing renderer/QC/Channel Brain. It does not
load another model. A single optional Final Director provider can be asked for a
revision policy; otherwise deterministic repair policies are generated from QC.

The controller evaluates v1, proposes targeted v2/v3 changes, scores candidates,
and keeps the best non-regressive version. Rendering is supplied by the caller so
this module can use the existing real-media preview/final renderer without making
a second rendering implementation.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from copy import deepcopy
from typing import Any, Callable, Iterable

@dataclass(frozen=True)
class RevisionPolicy:
    max_rounds: int = 3
    min_improvement: float = 0.5
    preserve_speech: bool = True
    avoid_new_heavy_effects: bool = True
    cpu_budget: str = "low"

@dataclass
class RevisionCandidate:
    version: str
    plan: dict[str, Any]
    report: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    changes: list[str] = field(default_factory=list)
    accepted: bool = False

@dataclass
class RevisionResult:
    best: RevisionCandidate
    candidates: list[RevisionCandidate]
    stopped_reason: str


def _clamp(v: float, lo=0.0, hi=100.0) -> float:
    return max(lo, min(hi, float(v)))


def diagnose(report: dict[str, Any]) -> list[str]:
    """Convert generic visual/audio/QC reports into actionable issue IDs."""
    issues: list[str] = []
    for c in report.get("checks", []) if isinstance(report, dict) else []:
        if not isinstance(c, dict):
            continue
        status = str(c.get("status", ""))
        name = str(c.get("name", ""))
        if status in {"fail", "warning"}:
            if name in {"black_frames", "freeze", "decode"}:
                issues.append("visual_integrity")
            elif name in {"blur"}:
                issues.append("soft_visuals")
            elif name in {"audio_clipping"}:
                issues.append("audio_peak")
            elif name in {"visual_duration"}:
                issues.append("duration_drift")
            else:
                issues.append(name or "quality_warning")
    return list(dict.fromkeys(issues))


def _repair_plan(plan: dict[str, Any], issues: Iterable[str], policy: RevisionPolicy) -> tuple[dict[str, Any], list[str]]:
    out = deepcopy(plan)
    changes: list[str] = []
    timeline = out.get("timeline")
    if not isinstance(timeline, list):
        timeline = []
        out["timeline"] = timeline

    issue_set = set(issues)
    if "audio_peak" in issue_set:
        render = dict(out.get("render") or {})
        render["audio_peak_guard"] = True
        render["target_true_peak_db"] = -1.0
        out["render"] = render
        changes.append("audio_peak_guard")

    if "freeze" in issue_set:
        # Remove duplicate adjacent cues that can create an accidental frozen-looking stack.
        cleaned=[]
        last=None
        for cue in timeline:
            key=(cue.get("start"), cue.get("end"), cue.get("kind")) if isinstance(cue,dict) else None
            if key == last:
                continue
            cleaned.append(cue); last=key
        out["timeline"] = cleaned
        changes.append("deduplicate_timeline_cues")

    if "soft_visuals" in issue_set:
        render = dict(out.get("render") or {})
        render["sharpen_guard"] = True
        render["sharpen_amount"] = 0.15
        out["render"] = render
        changes.append("light_sharpen_guard")

    if "visual_integrity" in issue_set:
        # Disable only optional heavy creative layers; never remove speech/captions by default.
        for cue in timeline:
            if not isinstance(cue, dict):
                continue
            if cue.get("optional", False) and cue.get("heavy", False):
                cue["enabled"] = False
        changes.append("disable_optional_heavy_layers")

    if "duration_drift" in issue_set:
        render = dict(out.get("render") or {})
        render["duration_guard"] = True
        out["render"] = render
        changes.append("duration_guard")

    # Safety invariant: autonomous repair cannot add new heavy effects.
    if policy.avoid_new_heavy_effects:
        out.setdefault("metadata", {})["autonomous_no_new_heavy_effects"] = True
    return out, changes


def score_report(report: dict[str, Any], *, brain_score: float = 1.0, retention_score: float | None = None) -> float:
    base = float(report.get("score", 0.0) or 0.0)
    passed = bool(report.get("passed", base >= 90))
    integrity_penalty = 25.0 if not passed else 0.0
    retention_bonus = 0.0 if retention_score is None else (_clamp(retention_score, 0, 100.0) - 70.0) * 0.05
    return _clamp(base - integrity_penalty + _clamp(brain_score,0,1)*5.0 + retention_bonus)


def run_revision_loop(
    initial_plan: dict[str, Any],
    evaluate: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    policy: RevisionPolicy | None = None,
    brain_score: Callable[[dict[str, Any]], float] | None = None,
    retention_score: Callable[[dict[str, Any]], float] | None = None,
) -> RevisionResult:
    """Evaluate and iteratively repair an edit plan.

    ``evaluate`` should render/preview/QC using the application's existing pipeline.
    It may be cheap (structural QC) or real-media (preview render + visual/audio QC).
    """
    policy = policy or RevisionPolicy()
    report = evaluate(deepcopy(initial_plan))
    base_score = score_report(report, brain_score=brain_score(initial_plan) if brain_score else 1.0, retention_score=retention_score(initial_plan) if retention_score else None)
    best = RevisionCandidate("v1", deepcopy(initial_plan), report, base_score, [], True)
    candidates=[best]
    current=best
    for round_no in range(2, max(1, policy.max_rounds)+1):
        issues=diagnose(current.report)
        if not issues:
            return RevisionResult(current, candidates, "no_actionable_qc_issues")
        plan, changes=_repair_plan(current.plan, issues, policy)
        if not changes:
            return RevisionResult(current, candidates, "no_safe_repair")
        rep=evaluate(plan)
        sc=score_report(rep, brain_score=brain_score(plan) if brain_score else 1.0, retention_score=retention_score(plan) if retention_score else None)
        cand=RevisionCandidate(f"v{round_no}", plan, rep, sc, changes, False)
        candidates.append(cand)
        if sc >= current.score + policy.min_improvement:
            cand.accepted=True
            current=cand
        else:
            # Never regress. Keep the last accepted candidate and stop early.
            return RevisionResult(current, candidates, "no_meaningful_improvement")
    return RevisionResult(current, candidates, "max_rounds_reached")

__all__=["RevisionPolicy","RevisionCandidate","RevisionResult","diagnose","score_report","run_revision_loop"]
