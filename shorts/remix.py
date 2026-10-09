"""Multi-segment Shorts Remix planner.

Lets the editor combine separately selected moments from a long video into one
coherent short without pretending that arbitrary clips are already continuous.
The planner adds micro-context, hook-first ordering, and pacing metadata; the
actual render remains non-destructive and is handled by the export pipeline.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

from .models import ShortsCandidate


@dataclass(frozen=True)
class RemixSegment:
    candidate_id: str
    source_start: float
    source_end: float
    role: str
    order: int

    @property
    def duration(self) -> float:
        return max(0.0, self.source_end - self.source_start)


@dataclass(frozen=True)
class RemixPlan:
    name: str
    target: str
    segments: tuple[RemixSegment, ...]
    total_duration: float
    score: float
    strategy: str
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "target": self.target,
            "segments": [s.__dict__ | {"duration": round(s.duration, 3)} for s in self.segments],
            "total_duration": round(self.total_duration, 3),
            "score": round(self.score, 2),
            "strategy": self.strategy,
            "notes": list(self.notes),
        }


def build_remix(candidates: Sequence[ShortsCandidate], target: str = "youtube_shorts", max_duration: float = 58.0) -> RemixPlan:
    """Build a hook -> proof/build -> payoff remix from 2+ selected candidates.

    Candidate order is editorial, not chronological: the strongest hook comes
    first, then distinct supporting moments, then the strongest payoff.
    """
    unique = []
    seen = set()
    for c in candidates:
        if c.id in seen or c.duration <= 0:
            continue
        seen.add(c.id)
        unique.append(c)
    if len(unique) < 2:
        raise ValueError("Remix için en az iki farklı Short adayı seçilmelidir.")

    unique.sort(key=lambda c: c.score, reverse=True)
    hook = unique[0]
    payoff = max(unique[1:], key=lambda c: (c.payoff_score, c.score))
    middle = [c for c in unique[1:] if c.id != payoff.id]
    ordered = [hook] + middle + [payoff]

    rows = []
    roles = ["hook"] + ["build"] * len(middle) + ["payoff"]
    total = 0.0
    for i, (c, role) in enumerate(zip(ordered, roles), 1):
        remaining = max_duration - total
        if remaining <= 0.0:
            break
        # Keep enough context for each clip while respecting the final cap.
        duration = min(c.duration, remaining)
        end = c.source_start + duration
        rows.append(RemixSegment(c.id, round(c.source_start, 3), round(end, 3), role, i))
        total += duration

    avg = sum(c.score for c in ordered[:len(rows)]) / max(1, len(rows))
    diversity_bonus = min(12.0, max(0, len(rows) - 2) * 4.0)
    score = min(100.0, avg + diversity_bonus)
    notes = (
        "Seçilen ayrı bölümler tek Short içinde hook → build → payoff akışında birleştirildi.",
        "Kaynak zamanları korunur; kurgu non-destructive kalır.",
        "Toplam süre platform sınırına göre otomatik kısaltılabilir.",
    )
    return RemixPlan(
        name=f"Remix • {hook.id} + {payoff.id}",
        target=target,
        segments=tuple(rows),
        total_duration=round(total, 3),
        score=round(score, 2),
        strategy="hook_first_payoff_last",
        notes=notes,
    )
