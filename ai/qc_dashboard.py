"""Preview/QC Dashboard and targeted AI revision loop for AI Director v2.77.

Qt-free state model: a future UI can bind to this without changing the edit core.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from copy import deepcopy
from typing import Any, Callable

DOMAINS = ("story", "rhythm", "visual", "audio", "subtitle")

@dataclass(frozen=True)
class DomainDelta:
    domain: str
    before: float
    after: float
    delta: float
    status: str

@dataclass(frozen=True)
class PreviewFrame:
    time: float
    label: str
    domain: str

@dataclass(frozen=True)
class RevisionEvent:
    round_no: int
    domain: str
    reason: str
    before: float
    after: float
    accepted: bool

@dataclass(frozen=True)
class DashboardState:
    final_score: float
    status: str
    failed_domains: tuple[str, ...]
    deltas: tuple[DomainDelta, ...]
    preview_frames: tuple[PreviewFrame, ...]
    revisions: tuple[RevisionEvent, ...]

    def to_dict(self):
        return asdict(self)


def build_dashboard(before: dict[str, Any], after: dict[str, Any], *, preview_frames: list[dict[str, Any]] | None = None, revisions: list[RevisionEvent] | None = None) -> DashboardState:
    deltas = []
    for domain in DOMAINS:
        b = float((before.get(domain) or {}).get("score", 0.0))
        a = float((after.get(domain) or {}).get("score", 0.0))
        status = "improved" if a > b else ("unchanged" if a == b else "regressed")
        deltas.append(DomainDelta(domain, b, a, a - b, status))
    score = float(after.get("score", 0.0))
    failed = tuple(after.get("failed_domains", ()))
    frames = tuple(PreviewFrame(float(x.get("time", 0.0)), str(x.get("label", "")), str(x.get("domain", "global"))) for x in (preview_frames or []))
    return DashboardState(score, str(after.get("status", "unknown")), failed, tuple(deltas), frames, tuple(revisions or ()))


def run_targeted_revision_loop(
    plan: dict[str, Any],
    qc: Callable[[dict[str, Any]], dict[str, Any]],
    repair: Callable[[dict[str, Any], str], tuple[dict[str, Any], str]],
    *,
    threshold: float = .75,
    max_rounds: int = 5,
    min_improvement: float = .01,
) -> tuple[dict[str, Any], dict[str, Any], list[RevisionEvent]]:
    """Re-run only failed domains; never accepts a lower-scoring revision."""
    current = deepcopy(plan)
    report = qc(deepcopy(current))
    events: list[RevisionEvent] = []
    seen: set[str] = set()
    for round_no in range(1, max_rounds + 1):
        domains = report.get("domains", {}) if isinstance(report, dict) else {}
        failed = [d for d in DOMAINS if float((domains.get(d) or {}).get("score", 0.0)) < threshold]
        if not failed:
            break
        domain = next((d for d in failed if d not in seen), None)
        if domain is None:
            break
        before_score = float((domains.get(domain) or {}).get("score", 0.0))
        candidate, reason = repair(deepcopy(current), domain)
        candidate_report = qc(deepcopy(candidate))
        after_score = float((candidate_report.get("domains", {}).get(domain) or {}).get("score", 0.0))
        accepted = after_score >= before_score + min_improvement
        events.append(RevisionEvent(round_no, domain, reason, before_score, after_score, accepted))
        seen.add(domain)
        if accepted:
            current, report = candidate, candidate_report
        else:
            # A failed attempt is isolated; move to another domain without compounding damage.
            report = dict(report)
    return current, report, events
