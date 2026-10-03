"""Professional AI Director — v2.19.

A single orchestration contract for autonomous long-form editing.  It combines
semantic edit decisions with contextual sound/visual direction and a platform
plan while remaining metadata-first and non-destructive.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.ai.autonomous_director import AutonomousEditPlan, Platform, build_autonomous_plan
from app.ai.director import DirectorPlan
from app.ai.effects_director import SoundDesignPlan, build_sound_design_plan
from app.ai.creative_intelligence import CreativeDirection, build_creative_direction
from app.ai.content_understanding import ContentUnderstanding, understand_content
from app.ai.edit_decision_graph import EditDecisionGraph, build_edit_decision_graph
from app.ai.quality_gate import QualityReport, validate_edit_graph, optimize_edit_graph
from app.ai.editorial_style_engine import EditorialStylePlan, build_editorial_style_plan
from app.ai.models import AnalysisReport
from app.ai.multimodal_analyzer import MultimodalAnalysis, analyze_media, enrich_content_understanding
from app.subtitle.models import Transcript


@dataclass(frozen=True)
class CaptionDecision:
    start: float
    end: float
    text: str
    style: str
    emphasis: tuple[str, ...] = ()
    confidence: float = 0.0


@dataclass(frozen=True)
class MotionDecision:
    start: float
    end: float
    preset: str
    intensity: float
    reason: str
    confidence: float


@dataclass
class ProfessionalEditPlan:
    autonomous: AutonomousEditPlan
    sound: SoundDesignPlan
    creative: CreativeDirection
    captions: list[CaptionDecision] = field(default_factory=list)
    motion: list[MotionDecision] = field(default_factory=list)
    workflow: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    editorial_style: EditorialStylePlan | None = None
    understanding: ContentUnderstanding | None = None
    decision_graph: EditDecisionGraph | None = None
    quality_report: QualityReport | None = None
    multimodal: MultimodalAnalysis | None = None

    @property
    def director(self) -> DirectorPlan:
        return self.autonomous.director

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def _caption_plan(transcript: Transcript | None, director: DirectorPlan, style: EditorialStylePlan | None = None) -> list[CaptionDecision]:
    if not transcript:
        return []
    highlights = set(director.highlight_words)
    style_name = (style.recipe.caption_style if style else None) or ("dynamic_short" if director.profile in {"shorts", "tiktok", "instagram_reel"} else "clean_pro")
    out: list[CaptionDecision] = []
    for seg in transcript.segments:
        text = (seg.text or "").strip()
        if not text or seg.end <= seg.start:
            continue
        words = tuple(w for w in text.split() if w.strip(".,!?;:").lower() in highlights)
        out.append(CaptionDecision(seg.start, seg.end, text, style_name, words,
                                   min(0.99, 0.70 + 0.02 * len(words))))
    return out


def _motion_plan(director: DirectorPlan, style: EditorialStylePlan | None = None) -> list[MotionDecision]:
    out: list[MotionDecision] = []
    recipe = style.recipe if style else None
    for event in director.events:
        if event.end <= event.start:
            continue
        if event.kind == "hook":
            out.append(MotionDecision(event.start, min(event.end, event.start + .9), "hook_punch", (recipe.zoom_strength if recipe else .55),
                                      "İlk güçlü vaat/merak anında kısa dikkat vurgusu.", event.score / 100.0))
        elif event.kind == "pattern_break":
            out.append(MotionDecision(event.start, min(event.end, event.start + .7), "micro_push", (recipe.zoom_strength if recipe else .35),
                                      "Uzun konuşma bloğunu küçük kadraj hareketiyle kır.", .82))
        elif event.kind == "broll_cue" and event.score >= 70:
            out.append(MotionDecision(event.start, min(event.end, event.start + .5), "broll_reframe", (max(.10, recipe.zoom_strength * .75) if recipe else .25),
                                      "Somut konu için B-roll alanı aç.", event.score / 100.0))
    return out


def build_professional_edit_plan(
    report: AnalysisReport,
    transcript: Transcript | None = None,
    platform: Platform = Platform.YOUTUBE,
    bpm: float | None = None,
    beat_times: list[float] | None = None,
    content_text: str | None = None,
    content_title: str | None = None,
    content_tags: tuple[str, ...] = (),
    requested_style: str | None = None,
    media_path: str | None = None,
    multimodal: MultimodalAnalysis | None = None,
) -> ProfessionalEditPlan:
    """Build the full non-destructive professional editing plan."""
    autonomous = build_autonomous_plan(report, transcript, platform, bpm, beat_times)
    style = build_editorial_style_plan(content_text, content_title, content_tags, requested_style)
    creative = build_creative_direction(transcript, report)
    understanding = understand_content(transcript, report, content_title or content_text)
    mm = multimodal
    if mm is None and media_path:
        mm = analyze_media(media_path)
    if mm is not None:
        understanding = enrich_content_understanding(understanding, mm)
    decision_graph = build_edit_decision_graph(understanding, style, multimodal=mm)
    decision_graph = optimize_edit_graph(decision_graph)
    quality_report = validate_edit_graph(decision_graph, autonomous.director.source_duration)
    sound = build_sound_design_plan(autonomous.director, style=style)
    captions = _caption_plan(transcript, autonomous.director, style)
    motion = _motion_plan(autonomous.director, style)
    workflow = [
        "proxy_and_cache_source",
        "analyze_speech_scenes_audio",
        "build_semantic_edit_decisions",
        "run_quality_gates",
        "plan_contextual_sound_and_motion",
        "generate_platform_captions",
        "review_non_destructive_timeline",
        "render_from_cached_analysis",
    ]
    return ProfessionalEditPlan(
        autonomous=autonomous,
        sound=sound,
        creative=creative,
        captions=captions,
        motion=motion,
        workflow=workflow,
        metadata={
            "version": "2.19",
            "mode": "professional_ai_director",
            "long_form_ready": True,
            "non_destructive": True,
            "metadata_first": True,
            "content_aware_editing": True,
            "creative_genre": creative.primary.genre.value,
            "editorial_style": style.to_dict(),
            "style_adaptation": "content_aware",
            "content_understanding_version": "2.28",
            "decision_graph_version": "2.28",
            "quality_score": quality_report.score,
            "effect_actions": len(decision_graph.actions),
            "multimodal_enabled": mm is not None,
            "multimodal_version": "2.29" if mm is not None else None,
        },
        editorial_style=style,
        understanding=understanding,
        decision_graph=decision_graph,
        quality_report=quality_report,
        multimodal=mm,
    )


__all__ = ["CaptionDecision", "MotionDecision", "ProfessionalEditPlan", "build_professional_edit_plan"]


def realize_timeline(plan: ProfessionalEditPlan, media_id: str, media_name: str = "Source", fps: float = 30.0):
    """Professional planını gerçek, non-destructive Timeline nesnesine uygular."""
    from app.ai.timeline_realizer import realize_professional_timeline
    return realize_professional_timeline(plan, media_id, media_name, fps)
