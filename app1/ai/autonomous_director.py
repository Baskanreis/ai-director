"""Autonomous Professional Director — v2.18.

A deterministic, headless orchestration layer for long-form automatic editing.
It sits above the existing analyzer/director systems and adds:
- platform-aware pacing profiles;
- conservative semantic cut gates;
- quality/retention safety checks;
- machine-readable edit decisions suitable for UI review or later timeline apply;
- a single entry point for a 1-hour (or longer) source video workflow.

The module intentionally does not render media or depend on Qt. Heavy work stays
in the existing background pipeline/export layers so the UI can remain responsive.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
from typing import Any

from app.ai.director import EditProfile, DirectorPlan, build_director_plan
from app.ai.models import AnalysisReport
from app.subtitle.models import Transcript


class Platform(str, Enum):
    YOUTUBE = "youtube"
    YOUTUBE_SHORTS = "youtube_shorts"
    TIKTOK = "tiktok"
    INSTAGRAM_REEL = "instagram_reel"
    UNIVERSAL = "universal"


@dataclass(frozen=True)
class PlatformSpec:
    platform: Platform
    director_profile: EditProfile
    aspect_ratio: str
    max_duration_seconds: float | None
    target_cut_ratio: float
    min_safe_cut_gap: float = 0.08


PLATFORM_SPECS: dict[Platform, PlatformSpec] = {
    Platform.YOUTUBE: PlatformSpec(Platform.YOUTUBE, EditProfile.YOUTUBE_LONGFORM, "16:9", None, .12),
    Platform.YOUTUBE_SHORTS: PlatformSpec(Platform.YOUTUBE_SHORTS, EditProfile.SHORTS, "9:16", 60.0, .22),
    Platform.TIKTOK: PlatformSpec(Platform.TIKTOK, EditProfile.TIKTOK, "9:16", 180.0, .25),
    Platform.INSTAGRAM_REEL: PlatformSpec(Platform.INSTAGRAM_REEL, EditProfile.INSTAGRAM_REEL, "9:16", 180.0, .20),
    Platform.UNIVERSAL: PlatformSpec(Platform.UNIVERSAL, EditProfile.YOUTUBE_LONGFORM, "auto", None, .14),
}


@dataclass
class QualityGate:
    name: str
    passed: bool
    severity: str = "info"
    detail: str = ""


@dataclass
class AutonomousEditPlan:
    source_duration: float
    platform: str
    aspect_ratio: str
    director: DirectorPlan
    quality_gates: list[QualityGate] = field(default_factory=list)
    final_duration_target: float | None = None
    render_recommendations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ready_for_review(self) -> bool:
        return all(g.passed or g.severity != "block" for g in self.quality_gates)

    @property
    def auto_apply_safe(self) -> bool:
        return self.ready_for_review and all(d.risk == "low" for d in self.director.accepted_decisions())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def _quality_gates(plan: DirectorPlan, spec: PlatformSpec) -> list[QualityGate]:
    gates: list[QualityGate] = []
    gates.append(QualityGate(
        "cut-ratio",
        plan.cut_ratio <= min(.40, spec.target_cut_ratio + .12),
        "block",
        f"Kesim oranı %{plan.cut_ratio * 100:.1f}; aşırı agresif kurgu sınırı korunuyor.",
    ))
    gates.append(QualityGate(
        "narrative",
        plan.narrative_score >= 25.0 or plan.source_duration < 30.0,
        "warning",
        f"Anlatı skoru {plan.narrative_score:.1f}.",
    ))
    gates.append(QualityGate(
        "hook",
        plan.hook_score >= 35.0 or plan.source_duration < 30.0,
        "warning",
        f"İlk bölüm hook skoru {plan.hook_score:.1f}.",
    ))
    accepted = plan.accepted_decisions()
    risky = sum(d.risk != "low" for d in accepted)
    gates.append(QualityGate(
        "decision-risk",
        risky == 0,
        "block",
        f"{risky} adet düşük güvenli/riskli otomatik karar kabul edilmiş durumda.",
    ))
    if spec.max_duration_seconds is not None:
        gates.append(QualityGate(
            "platform-duration",
            plan.estimated_final_duration <= spec.max_duration_seconds,
            "warning",
            f"Tahmini çıktı {plan.estimated_final_duration:.1f}s; platform sınırı {spec.max_duration_seconds:.1f}s.",
        ))
    return gates


def build_autonomous_plan(
    report: AnalysisReport,
    transcript: Transcript | None = None,
    platform: Platform = Platform.YOUTUBE,
    bpm: float | None = None,
    beat_times: list[float] | None = None,
) -> AutonomousEditPlan:
    """Build a complete reviewable automatic edit plan without touching the timeline."""
    spec = PLATFORM_SPECS[platform]
    director = build_director_plan(
        report,
        transcript,
        profile=spec.director_profile,
        bpm=bpm,
        beat_times=beat_times,
    )
    gates = _quality_gates(director, spec)
    recommendations = [
        "proxy_media_for_long_sources",
        "background_analysis",
        "render_from_cached_analysis",
        "review_blocked_decisions_before_apply",
    ]
    if director.events:
        recommendations.append("use_contextual_broll_and_pattern_breaks")
    if director.highlight_words:
        recommendations.append("apply_animated_caption_highlights")
    if platform != Platform.YOUTUBE:
        recommendations.append("smart_reframe_to_9x16")
    return AutonomousEditPlan(
        source_duration=director.source_duration,
        platform=platform.value,
        aspect_ratio=spec.aspect_ratio,
        director=director,
        quality_gates=gates,
        final_duration_target=spec.max_duration_seconds,
        render_recommendations=recommendations,
        metadata={
            "version": "2.18",
            "architecture": "analysis -> semantic director -> quality gates -> review/apply -> cached render",
            "non_destructive": True,
            "ui_safe": True,
        },
    )


__all__ = [
    "Platform", "PlatformSpec", "PLATFORM_SPECS", "QualityGate",
    "AutonomousEditPlan", "build_autonomous_plan",
]
