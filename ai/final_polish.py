"""Final Polish + Human Control layer.

The AI never mutates the user's timeline directly. It creates deterministic,
non-destructive suggestions. Each suggestion can be accepted, rejected, or
edited by the user. Accepted/rejected decisions update only the current
project's preference profile and never train or persist globally.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class HumanControlPolicy:
    min_confidence: float = 0.65
    min_improvement: float = 0.25
    max_suggestions: int = 24
    learn_from_decisions: bool = True
    protect_locked_items: bool = True


@dataclass
class PreferenceProfile:
    accepted: dict[str, int] = field(default_factory=dict)
    rejected: dict[str, int] = field(default_factory=dict)

    def weight(self, key: str) -> float:
        a = self.accepted.get(key, 0)
        r = self.rejected.get(key, 0)
        total = a + r
        return 0.0 if total == 0 else round((a - r) / total, 3)

    def learn(self, key: str, accepted: bool) -> None:
        bucket = self.accepted if accepted else self.rejected
        bucket[key] = bucket.get(key, 0) + 1


@dataclass
class PolishSuggestion:
    id: str
    kind: str
    target_id: str
    title: str
    reason: str
    confidence: float
    before: dict[str, Any]
    after: dict[str, Any]
    score_before: float
    score_after: float
    status: str = "pending"
    locked: bool = False

    @property
    def improvement(self) -> float:
        return round(self.score_after - self.score_before, 4)


@dataclass
class PolishSnapshot:
    plan: dict[str, Any]
    label: str


class FinalPolishSession:
    """Suggestion manager with isolated snapshots and project-local learning."""

    def __init__(self, plan: dict[str, Any], *, policy: HumanControlPolicy | None = None,
                 preferences: PreferenceProfile | None = None) -> None:
        self.policy = policy or HumanControlPolicy()
        self.plan = deepcopy(plan)
        self.preferences = preferences or PreferenceProfile()
        self.suggestions: list[PolishSuggestion] = []
        self._history: list[PolishSnapshot] = [PolishSnapshot(deepcopy(self.plan), "initial")]

    def propose(
        self,
        *,
        kind: str,
        target_id: str,
        title: str,
        reason: str,
        before: dict[str, Any],
        after: dict[str, Any],
        score_before: float,
        score_after: float,
        confidence: float,
        locked: bool = False,
    ) -> PolishSuggestion | None:
        if len(self.suggestions) >= self.policy.max_suggestions:
            return None
        if confidence < self.policy.min_confidence:
            return None
        if self.policy.protect_locked_items and locked:
            return None
        if score_after - score_before < self.policy.min_improvement:
            return None
        sid = f"polish-{len(self.suggestions) + 1:03d}"
        suggestion = PolishSuggestion(
            id=sid, kind=kind, target_id=target_id, title=title, reason=reason,
            confidence=round(float(confidence), 3), before=deepcopy(before),
            after=deepcopy(after), score_before=float(score_before),
            score_after=float(score_after), locked=locked,
        )
        self.suggestions.append(suggestion)
        return suggestion

    def decide(self, suggestion_id: str, decision: str,
               *, edit: dict[str, Any] | None = None) -> PolishSuggestion:
        suggestion = self._get(suggestion_id)
        decision = decision.lower().strip()
        if decision not in {"accept", "reject", "modify"}:
            raise ValueError("decision must be accept, reject, or modify")
        if suggestion.status != "pending":
            raise ValueError("suggestion is already decided")
        if suggestion.locked and decision != "reject":
            raise ValueError("locked suggestions cannot be applied")

        if decision == "accept":
            self._apply(suggestion.after, suggestion.target_id)
        elif decision == "modify":
            if not edit:
                raise ValueError("modify requires an edit payload")
            self._apply(edit, suggestion.target_id)
        suggestion.status = decision

        if self.policy.learn_from_decisions:
            key = f"{suggestion.kind}:{suggestion.title}"
            self.preferences.learn(key, decision != "reject")
        self._history.append(PolishSnapshot(deepcopy(self.plan), f"{decision}:{suggestion.id}"))
        return suggestion

    def undo_last_decision(self) -> bool:
        if len(self._history) <= 1:
            return False
        self._history.pop()
        self.plan = deepcopy(self._history[-1].plan)
        return True

    def export_state(self) -> dict[str, Any]:
        return {
            "plan": deepcopy(self.plan),
            "suggestions": [asdict(s) for s in self.suggestions],
            "preferences": asdict(self.preferences),
            "history_depth": len(self._history),
        }

    def _get(self, suggestion_id: str) -> PolishSuggestion:
        for suggestion in self.suggestions:
            if suggestion.id == suggestion_id:
                return suggestion
        raise KeyError(suggestion_id)

    def _apply(self, payload: dict[str, Any], target_id: str) -> None:
        timeline = self.plan.setdefault("timeline", [])
        for item in timeline:
            if str(item.get("id", item.get("asset_id", ""))) == str(target_id) or str(item.get("clip_id", "")) == str(target_id):
                item.update(deepcopy(payload))
                return
        # Allow plan-level decisions (e.g. global subtitle/audio policy).
        self.plan.setdefault("polish", {}).setdefault("targets", {})[target_id] = deepcopy(payload)


def build_final_polish_session(plan: dict[str, Any], *, policy: HumanControlPolicy | None = None) -> FinalPolishSession:
    return FinalPolishSession(plan, policy=policy)


__all__ = [
    "HumanControlPolicy", "PreferenceProfile", "PolishSuggestion",
    "PolishSnapshot", "FinalPolishSession", "build_final_polish_session",
]
