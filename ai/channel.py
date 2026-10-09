"""Channel Intelligence / Style DNA engine — v1.7 foundation.

Reference videoların Director çıktılarından ölçülebilir bir edit DNA profili üretir.
Ham videoya bağımlı değildir; v1.6 DirectorPlan ve Transcript gibi mevcut kontratları
kullanır. Böylece ileride YouTube ingestion/vision/LLM katmanları eklenebilir.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import sqrt
from statistics import median
from typing import Iterable

from .director import DirectorPlan
from app.subtitle.models import Transcript


@dataclass(frozen=True)
class ChannelStyleProfile:
    name: str = "Untitled Channel"
    reference_count: int = 0
    avg_hook_score: float = 0.0
    avg_narrative_score: float = 0.0
    avg_cut_ratio: float = 0.0
    avg_pacing_score: float = 0.0
    avg_pattern_breaks_per_minute: float = 0.0
    avg_broll_cues_per_minute: float = 0.0
    avg_beats_per_minute: float = 0.0
    avg_highlight_density_per_minute: float = 0.0
    avg_chapter_count: float = 0.0
    preferred_profiles: tuple[str, ...] = ()
    edit_traits: tuple[str, ...] = ()
    confidence: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass(frozen=True)
class StyleMatch:
    similarity: float
    differences: dict[str, float]
    recommendations: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


def _duration(plan: DirectorPlan, transcript: Transcript | None) -> float:
    if plan.source_duration > 0:
        return plan.source_duration
    if transcript and transcript.segments:
        return max((s.end for s in transcript.segments), default=0.0)
    return 0.0


def _rate(count: int, duration: float) -> float:
    return count / (duration / 60.0) if duration > 0 else 0.0


def _traits(avg: dict[str, float]) -> tuple[str, ...]:
    traits: list[str] = []
    if avg["cut_ratio"] >= 0.22:
        traits.append("aggressive_cuts")
    elif avg["cut_ratio"] <= 0.10:
        traits.append("natural_pacing")
    else:
        traits.append("balanced_pacing")
    if avg["pattern_breaks"] >= 2.5:
        traits.append("frequent_pattern_breaks")
    if avg["broll"] >= 2.0:
        traits.append("broll_heavy")
    if avg["beats"] >= 5.0:
        traits.append("narrative_dense")
    if avg["hook"] >= 75:
        traits.append("strong_hooks")
    if avg["highlight_density"] >= 3.0:
        traits.append("high_emphasis")
    return tuple(traits)


def build_channel_profile(
    references: Iterable[tuple[DirectorPlan, Transcript | None]],
    name: str = "Untitled Channel",
) -> ChannelStyleProfile:
    refs = list(references)
    if not refs:
        return ChannelStyleProfile(name=name)

    rows: list[dict[str, float]] = []
    profiles: list[str] = []
    for plan, transcript in refs:
        duration = _duration(plan, transcript)
        rows.append({
            "hook": plan.hook_score,
            "narrative": plan.narrative_score,
            "cut_ratio": plan.cut_ratio,
            "pacing": plan.pacing_score,
            "pattern_breaks": _rate(sum(e.kind == "pattern_break" for e in plan.events), duration),
            "broll": _rate(sum(e.kind == "broll_cue" for e in plan.events), duration),
            "beats": _rate(sum(e.kind == "beat" for e in plan.events), duration),
            "highlight_density": _rate(len(plan.highlight_words), duration),
            "chapters": float(len(plan.chapters)),
            "cut_density": float((len(plan.events) if duration else 0) / (duration / 60.0)) if duration else 0.0,
            "shot_duration": float(duration / max(1, len(plan.events))) if duration else 0.0,
        })
        profiles.append(plan.profile)

    keys = tuple(rows[0].keys())
    avg = {k: sum(r[k] for r in rows) / len(rows) for k in keys}
    traits = _traits(avg)
    confidence = min(1.0, 0.35 + 0.13 * min(len(rows), 5))
    return ChannelStyleProfile(
        name=name,
        reference_count=len(rows),
        avg_hook_score=round(avg["hook"], 2),
        avg_narrative_score=round(avg["narrative"], 2),
        avg_cut_ratio=round(avg["cut_ratio"], 4),
        avg_pacing_score=round(avg["pacing"], 2),
        avg_pattern_breaks_per_minute=round(avg["pattern_breaks"], 3),
        avg_broll_cues_per_minute=round(avg["broll"], 3),
        avg_beats_per_minute=round(avg["beats"], 3),
        avg_highlight_density_per_minute=round(avg["highlight_density"], 3),
        avg_chapter_count=round(avg["chapters"], 2),
        preferred_profiles=tuple(sorted(set(profiles))),
        edit_traits=traits,
        confidence=round(confidence, 3),
        metadata={"engine_version": "1.8", "source": "director_plans",
                  "avg_cut_density_per_minute": round(avg.get("cut_density", 0.0), 3),
                  "avg_shot_duration": round(avg.get("shot_duration", 0.0), 3)},
    )


def compare_style(target: DirectorPlan, profile: ChannelStyleProfile) -> StyleMatch:
    duration = max(target.source_duration, 0.001)
    actual = {
        "hook": target.hook_score,
        "narrative": target.narrative_score,
        "cut_ratio": target.cut_ratio,
        "pacing": target.pacing_score,
        "pattern_breaks": _rate(sum(e.kind == "pattern_break" for e in target.events), duration),
        "broll": _rate(sum(e.kind == "broll_cue" for e in target.events), duration),
        "beats": _rate(sum(e.kind == "beat" for e in target.events), duration),
        "highlight_density": _rate(len(target.highlight_words), duration),
    }
    reference = {
        "hook": profile.avg_hook_score,
        "narrative": profile.avg_narrative_score,
        "cut_ratio": profile.avg_cut_ratio,
        "pacing": profile.avg_pacing_score,
        "pattern_breaks": profile.avg_pattern_breaks_per_minute,
        "broll": profile.avg_broll_cues_per_minute,
        "beats": profile.avg_beats_per_minute,
        "highlight_density": profile.avg_highlight_density_per_minute,
    }
    scales = {"hook": 100, "narrative": 100, "cut_ratio": .35, "pacing": 100,
              "pattern_breaks": 8, "broll": 8, "beats": 15, "highlight_density": 10}
    diffs = {k: round((actual[k] - reference[k]) / scales[k], 4) for k in actual}
    dist = sqrt(sum(v * v for v in diffs.values()) / len(diffs))
    similarity = max(0.0, min(100.0, 100.0 * (1.0 - min(1.0, dist))))
    recs: list[str] = []
    if actual["cut_ratio"] < reference["cut_ratio"] - .03:
        recs.append("Kesim yoğunluğunu kanal ortalamasına yaklaştır.")
    if actual["cut_ratio"] > reference["cut_ratio"] + .03:
        recs.append("Aşırı kesimi azalt; doğal konuşma bloklarını daha fazla koru.")
    if actual["broll"] < reference["broll"] - .8:
        recs.append("Somut ifadelerde daha fazla B-roll/cutaway kullan.")
    if actual["pattern_breaks"] < reference["pattern_breaks"] - .8:
        recs.append("Uzun konuşma bloklarında daha sık pattern-break planla.")
    if actual["hook"] < reference["hook"] - 8:
        recs.append("İlk 30 saniyede daha güçlü merak/vaat sinyalleri oluştur.")
    return StyleMatch(round(similarity, 2), diffs, tuple(recs))


__all__ = ["ChannelStyleProfile", "StyleMatch", "build_channel_profile", "compare_style"]
