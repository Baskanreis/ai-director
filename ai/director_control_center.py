"""AI Director Control Center v2.76.

Non-destructive orchestration for specialist passes. The controller ranks
suggestions, applies only approved/high-confidence changes, and can request a
bounded revision for failed QC domains.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, replace
from typing import Any, Callable

DOMAINS = ("story", "rhythm", "visual", "audio", "subtitle")

@dataclass(frozen=True)
class PassResult:
    domain: str
    status: str
    score: float
    confidence: float
    suggestions: tuple[dict[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()

@dataclass(frozen=True)
class Suggestion:
    id: str
    domain: str
    action: str
    confidence: float
    predicted_gain: float
    reason: str
    status: str = "pending"

@dataclass(frozen=True)
class ControlPolicy:
    auto_apply_confidence: float = .92
    min_suggestion_confidence: float = .55
    min_predicted_gain: float = .02
    max_revisions_per_domain: int = 1

class DirectorControlCenter:
    def __init__(self, policy: ControlPolicy | None = None):
        self.policy = policy or ControlPolicy()
        self._history: list[dict[str, Any]] = []
        self._preferences: dict[str, dict[str, float]] = {}
        self._revision_count: dict[str, int] = {}

    def rank(self, suggestions: list[Suggestion]) -> list[Suggestion]:
        def pref(s: Suggestion) -> float:
            p = self._preferences.get(s.domain, {})
            return p.get(s.action, 0.0)
        return sorted(suggestions, key=lambda s: (s.confidence + s.predicted_gain + pref(s)*.05), reverse=True)

    def propose(self, results: list[PassResult]) -> list[Suggestion]:
        out=[]
        for result in results:
            if result.status != "ok":
                continue
            for i, raw in enumerate(result.suggestions):
                s=Suggestion(
                    id=str(raw.get("id", f"{result.domain}-{i}")),
                    domain=result.domain,
                    action=str(raw.get("action", "review")),
                    confidence=float(raw.get("confidence", result.confidence)),
                    predicted_gain=float(raw.get("predicted_gain", 0.0)),
                    reason=str(raw.get("reason", "")),
                )
                if s.confidence >= self.policy.min_suggestion_confidence and s.predicted_gain >= self.policy.min_predicted_gain:
                    out.append(s)
        return self.rank(out)

    def decide(self, suggestions: list[Suggestion], mode: str = "review") -> list[Suggestion]:
        ranked=self.rank(suggestions)
        if mode == "auto_high_confidence":
            return [replace(s, status="accepted") for s in ranked if s.confidence >= self.policy.auto_apply_confidence]
        if mode == "accept_all":
            return [replace(s, status="accepted") for s in ranked]
        if mode == "reject_all":
            return [replace(s, status="rejected") for s in ranked]
        return ranked

    def record(self, suggestion: Suggestion) -> None:
        self._history.append({"suggestion": asdict(suggestion), "preferences": {k: dict(v) for k,v in self._preferences.items()}})
        bucket=self._preferences.setdefault(suggestion.domain,{})
        bucket[suggestion.action]=bucket.get(suggestion.action,0.0) + (1.0 if suggestion.status=="accepted" else -1.0)

    def request_revision(self, domain: str, score: float, threshold: float=.75) -> bool:
        if domain not in DOMAINS or score >= threshold:
            return False
        count=self._revision_count.get(domain,0)
        if count >= self.policy.max_revisions_per_domain:
            return False
        self._revision_count[domain]=count+1
        return True

    def snapshot(self) -> dict[str, Any]:
        return {"history": list(self._history), "preferences": {k:dict(v) for k,v in self._preferences.items()}, "revisions": dict(self._revision_count)}

    def restore(self, snapshot: dict[str, Any]) -> None:
        self._history=list(snapshot.get("history",[]))
        self._preferences={k:dict(v) for k,v in snapshot.get("preferences",{}).items()}
        self._revision_count=dict(snapshot.get("revisions",{}))
