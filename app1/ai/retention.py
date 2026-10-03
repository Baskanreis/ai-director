"""Retention-aware QA and autonomous edit passes — v2.0.

Bu katman gerçek izleyici retention datası yoksa bunu iddia etmez. Transcript,
Director events ve kanal DNA'sından *heuristic retention risk* çıkarır; gerçek
YouTube Analytics verisi geldiğinde aynı kontrata yeni sinyaller eklenebilir.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from statistics import mean

from .director import DirectorPlan, DirectorDecision, EditEventKind, adapt_plan_to_channel


class RetentionRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class RetentionSignal:
    kind: str
    start: float
    end: float
    score: float
    risk: RetentionRisk
    reason: str


@dataclass(frozen=True)
class RetentionQAReport:
    score: float
    risk: RetentionRisk
    signals: tuple[RetentionSignal, ...] = ()
    strengths: tuple[str, ...] = ()
    actions: tuple[str, ...] = ()
    pass_number: int = 1

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AutonomousEditPass:
    plan: DirectorPlan
    qa: RetentionQAReport
    applied: bool = False
    pass_number: int = 1
    history: tuple[RetentionQAReport, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return asdict(self)


def _risk(score: float) -> RetentionRisk:
    if score >= 70:
        return RetentionRisk.HIGH
    if score >= 40:
        return RetentionRisk.MEDIUM
    return RetentionRisk.LOW


def evaluate_retention(plan: DirectorPlan, pass_number: int = 1) -> RetentionQAReport:
    """Planın yapısal retention riskini ölçer; izlenme tahmini değildir."""
    signals: list[RetentionSignal] = []
    actions: list[str] = []
    strengths: list[str] = []
    duration = plan.source_duration

    if duration <= 0:
        return RetentionQAReport(100.0, RetentionRisk.LOW, pass_number=pass_number)

    hook_penalty = max(0.0, 65.0 - plan.hook_score)
    if hook_penalty:
        signals.append(RetentionSignal("weak_hook", 0, min(30.0, duration), hook_penalty,
                                       _risk(hook_penalty), "İlk bölümde hook sinyali zayıf."))
        actions.append("strengthen_hook")
    else:
        strengths.append("strong_hook")

    events = plan.events
    breaks = sum(e.kind == EditEventKind.PATTERN_BREAK.value for e in events)
    broll = sum(e.kind == EditEventKind.BROLL_CUE.value for e in events)
    beats = sum(e.kind == EditEventKind.BEAT.value for e in events)
    per_min = max(duration / 60.0, 1e-6)
    break_rate = breaks / per_min
    broll_rate = broll / per_min

    if duration > 180 and break_rate < 0.5:
        penalty = min(35.0, 25.0 + (0.5 - break_rate) * 20.0)
        signals.append(RetentionSignal("low_pattern_break_density", 0, duration, penalty,
                                       _risk(penalty), "Uzun içerikte pattern-break yoğunluğu düşük."))
        actions.append("add_pattern_breaks")
    else:
        strengths.append("adequate_pattern_breaks")

    if duration > 120 and broll_rate < 0.6:
        penalty = min(25.0, 18.0 + (0.6 - broll_rate) * 12.0)
        signals.append(RetentionSignal("low_broll_density", 0, duration, penalty,
                                       _risk(penalty), "Uzun içerikte B-roll/cutaway sinyali düşük."))
        actions.append("add_broll_cues")

    if duration > 120 and beats < max(2, int(duration / 180)):
        penalty = 15.0
        signals.append(RetentionSignal("low_narrative_beats", 0, duration, penalty,
                                       RetentionRisk.LOW, "Anlatı geçişleri seyrek."))
        actions.append("increase_narrative_beats")

    pacing_penalty = max(0.0, 65.0 - plan.pacing_score) * 0.6
    if pacing_penalty:
        signals.append(RetentionSignal("pacing_risk", 0, duration, pacing_penalty,
                                       _risk(pacing_penalty), "Pacing skoru hedef aralıktan uzak."))
        actions.append("rebalance_pacing")
    else:
        strengths.append("balanced_pacing")

    total_penalty = min(100.0, sum(s.score for s in signals))
    score = max(0.0, 100.0 - total_penalty)
    # Aynı aksiyonun tekrarını temizle, sıralamayı koru.
    actions = list(dict.fromkeys(actions))
    return RetentionQAReport(round(score, 2), _risk(total_penalty), tuple(signals),
                             tuple(dict.fromkeys(strengths)), tuple(actions), pass_number)


def _refine_plan(plan: DirectorPlan, qa: RetentionQAReport) -> DirectorPlan:
    """Güvenli ikinci pass: mevcut kesimleri bozmaz, yalnızca metadata ve event önerileri ekler."""
    metadata = dict(plan.metadata)
    metadata["retention_qa"] = qa.to_dict()
    metadata["autonomous_actions"] = list(qa.actions)
    events = list(plan.events)

    if "add_pattern_breaks" in qa.actions:
        # Director event'i olarak cue üretir; timeline'a hayali bir kesim uygulamaz.
        if not any(e.kind == EditEventKind.PATTERN_BREAK.value and e.payload.get("source") == "retention_qa" for e in events):
            events.append(__import__("app.ai.director", fromlist=["DirectorEvent"]).DirectorEvent(
                EditEventKind.PATTERN_BREAK.value, 0.0, plan.source_duration, 60.0,
                "Retention QA: uzun bölüm boyunca ek pattern-break/cutaway planlanmalı.",
                {"source": "retention_qa", "action": "add_pattern_breaks"}))
    if "add_broll_cues" in qa.actions:
        if not any(e.kind == EditEventKind.BROLL_CUE.value and e.payload.get("source") == "retention_qa" for e in events):
            events.append(__import__("app.ai.director", fromlist=["DirectorEvent"]).DirectorEvent(
                EditEventKind.BROLL_CUE.value, 0.0, plan.source_duration, 55.0,
                "Retention QA: B-roll/cutaway coverage artırılmalı.",
                {"source": "retention_qa", "action": "add_broll_cues"}))
    return replace(plan, events=events, metadata=metadata)


def run_autonomous_edit_pass(plan: DirectorPlan, channel_profile=None, max_passes: int = 2) -> AutonomousEditPass:
    """Director planını QA edip en fazla iki güvenli pass çalıştırır."""
    current = adapt_plan_to_channel(plan, channel_profile) if channel_profile is not None else plan
    history: list[RetentionQAReport] = []
    best = current
    for n in range(1, max(1, max_passes) + 1):
        qa = evaluate_retention(best, n)
        history.append(qa)
        refined = _refine_plan(best, qa)
        if qa.score >= 80 or n == max_passes:
            best = refined
            break
        best = refined
    final_qa = history[-1]
    metadata = dict(best.metadata)
    metadata["autonomous_edit"] = {"passes": len(history), "qa_score": final_qa.score,
                                    "risk": final_qa.risk.value}
    best = replace(best, metadata=metadata)
    return AutonomousEditPass(best, final_qa, applied=False, pass_number=len(history), history=tuple(history))


__all__ = ["RetentionRisk", "RetentionSignal", "RetentionQAReport", "AutonomousEditPass",
           "evaluate_retention", "run_autonomous_edit_pass"]
