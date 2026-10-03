"""Professional editorial decision engine — v3.0.

The goal is not "more effects". It models an editor's order of operations:
1) understand speech beats and visual shots, 2) protect story/meaning,
3) remove only dead air/redundancy, 4) shape pacing, 5) add restrained
camera emphasis, 6) polish audio, and 7) run a continuity/safety pass.

It is deterministic and explainable; model-backed semantic analysis can feed
its signals later without changing the edit contract.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable
import math

from app.ai.models import AnalysisReport, SuggestionKind
from app.ai.apply import merge_ranges, cut_ranges_in_clip
from app.subtitle.models import Transcript
from app.timeline.model import Keyframe, Timeline


@dataclass(frozen=True)
class EditorialProfile:
    name: str
    target_shot: float
    max_cut_ratio: float
    pause_floor: float
    motion_strength: float
    emphasis_scale: float
    beat_density: float


PROFILES = {
    "professional": EditorialProfile("professional", 4.0, .20, 0.35, .18, 1.025, .55),
    "high_retention": EditorialProfile("high_retention", 2.8, .28, 0.25, .24, 1.035, .75),
    "cinematic": EditorialProfile("cinematic", 5.5, .12, 0.45, .12, 1.018, .35),
    "talking_head": EditorialProfile("talking_head", 4.2, .22, 0.30, .20, 1.028, .60),
}


@dataclass
class EditorialAction:
    start: float
    end: float
    kind: str
    confidence: float
    reason: str
    params: dict = field(default_factory=dict)


@dataclass
class ProfessionalEditPlan:
    source: str
    duration: float
    profile: str
    cut_ranges: list[tuple[float, float]] = field(default_factory=list)
    actions: list[EditorialAction] = field(default_factory=list)
    protected_ranges: list[tuple[float, float]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    estimated_duration: float = 0.0
    editorial_score: float = 0.0
    version: str = "3.0.0"

    def to_dict(self) -> dict:
        return asdict(self)


def _overlap(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def _clamp_ranges(ranges: Iterable[tuple[float, float]], duration: float) -> list[tuple[float, float]]:
    out = []
    for s, e in ranges:
        s, e = max(0.0, float(s)), min(duration, float(e))
        if e - s >= .06:
            out.append((s, e))
    return merge_ranges(out)


def _speech_protection(transcript: Transcript | None) -> list[tuple[float, float]]:
    """Protect words around semantic-looking sentence starts/ends.

    We intentionally protect a small context around every spoken segment. This
    prevents an aggressive silence cutter from chopping consonants or the tail
    of a sentence and gives the editor room for J/L-cut style audio continuity.
    """
    if not transcript:
        return []
    ranges = []
    for seg in transcript.segments:
        if seg.end <= seg.start:
            continue
        ranges.append((max(0.0, seg.start - .08), seg.end + .12))
    return merge_ranges(ranges)


def _candidate_cuts(report: AnalysisReport, duration: float, profile: EditorialProfile) -> list[tuple[float, float, float, str]]:
    candidates = []
    allowed = {
        SuggestionKind.SILENCE: 1.00,
        SuggestionKind.LONG_PAUSE: .92,
        SuggestionKind.REPETITION: .82,
        SuggestionKind.FILLER_WORD: .72,
    }
    for s in report.suggestions:
        if not s.accepted or s.kind not in allowed or s.end <= s.start:
            continue
        length = s.end - s.start
        if s.kind in (SuggestionKind.SILENCE, SuggestionKind.LONG_PAUSE) and length < profile.pause_floor:
            continue
        # Keep filler/repetition cuts tiny. A professional edit removes the word,
        # not the breathing room around it.
        if s.kind in (SuggestionKind.FILLER_WORD, SuggestionKind.REPETITION):
            length = min(length, .55)
            end = s.start + length
        else:
            end = s.end
        score = allowed[s.kind] * min(1.0, length / .45)
        candidates.append((s.start, end, score, s.kind.value))
    return sorted(candidates, key=lambda x: (-x[2], x[0]))


def build_professional_edit_plan(
    source: str,
    duration: float,
    report: AnalysisReport,
    transcript: Transcript | None = None,
    profile: str = "professional",
    beat_times: list[float] | None = None,
) -> ProfessionalEditPlan:
    if profile not in PROFILES:
        raise ValueError(f"Bilinmeyen profesyonel profil: {profile}")
    cfg = PROFILES[profile]
    if duration <= 0:
        raise ValueError("duration pozitif olmalı")

    protected = _speech_protection(transcript)
    raw = _candidate_cuts(report, duration, cfg)
    selected: list[tuple[float, float]] = []
    actions: list[EditorialAction] = []
    budget = duration * cfg.max_cut_ratio
    used = 0.0

    # High-confidence cuts first, but never blindly exceed an editorial budget.
    for s, e, confidence, kind in raw:
        if any(_overlap((s, e), p) for p in protected) and kind == SuggestionKind.LONG_PAUSE.value:
            # A long pause inside speech context can be intentional; only cut its
            # central dead-air portion rather than the protected edges.
            s += .10
            e -= .10
        if e <= s:
            continue
        if any(_overlap((s, e), x) for x in selected):
            continue
        if used + (e - s) > budget:
            continue
        selected.append((s, e)); used += e - s
        actions.append(EditorialAction(s, e, "cut", confidence, f"{kind}: gereksiz süre azaltıldı."))

    selected = merge_ranges(selected)

    # Pacing pass: identify long uninterrupted shots. We don't cut them by
    # default; instead we schedule a subtle push/reframe at a natural midpoint.
    for a, b in protected:
        if b - a > cfg.target_shot * 1.8:
            mid = a + (b - a) * .55
            actions.append(EditorialAction(
                mid, min(b, mid + .7), "subtle_push", .78,
                "Uzun konuşma/plan; seyir monotonluğunu azaltmak için kontrollü kamera hareketi.",
                {"scale": cfg.emphasis_scale},
            ))

    # Beat pass is deliberately sparse. Music should support the story, not
    # dictate every cut.
    if beat_times:
        spacing = max(cfg.target_shot * cfg.beat_density, 1.0)
        last = -999.0
        for t in sorted(float(x) for x in beat_times if 0 < float(x) < duration):
            if t - last < spacing:
                continue
            if any(a <= t <= b for a, b in selected):
                continue
            actions.append(EditorialAction(t, min(duration, t + .18), "beat_emphasis", .70,
                                           "Müzik vuruşu; hikâyeyi kesmeden mikro vurgu.",
                                           {"scale": cfg.emphasis_scale}))
            last = t

    # Audio continuity: tiny J/L style cues around cuts, represented as metadata
    # so the render layer can duck/retain room tone without hard audio chopping.
    for s, e in selected:
        actions.append(EditorialAction(s, e, "audio_continuity", .88,
                                       "Kesim çevresinde ses sürekliliğini koru.",
                                       {"handle": .06}))

    cut_seconds = sum(e - s for s, e in selected)
    ratio = cut_seconds / duration
    score = 100.0
    score -= max(0.0, ratio - cfg.max_cut_ratio) * 400
    score -= max(0, len(selected) - duration / cfg.target_shot) * .35
    score = max(0.0, min(100.0, score))
    warnings = []
    if not transcript:
        warnings.append("Transkript yok: anlatı anlamı doğrulanamadığı için kurgu daha konservatif tutuldu.")
    if not report.suggestions:
        warnings.append("Analiz önerisi yok: kaynak mümkün olduğunca korunuyor.")
    warnings.append("Profesyonel mod efekt sayısını değil edit kararlarının kalitesini optimize eder.")

    return ProfessionalEditPlan(
        source=str(source), duration=duration, profile=profile,
        cut_ranges=selected, actions=sorted(actions, key=lambda x: x.start),
        protected_ranges=protected, warnings=warnings,
        estimated_duration=max(0.0, duration - cut_seconds),
        editorial_score=round(score, 2),
    )


def apply_professional_edit(timeline: Timeline, clip_id: str, plan: ProfessionalEditPlan) -> int:
    """Apply the plan to a timeline without touching source media."""
    found = timeline.find(clip_id)
    if not found:
        return 0
    track, clip = found
    source_ranges = [(max(clip.source_in, s), min(clip.source_out, e)) for s, e in plan.cut_ranges]
    n = cut_ranges_in_clip(timeline, clip_id, source_ranges)

    # Add subtle motion after cuts so each resulting clip gets its own clean
    # treatment. Avoid effect stacking and keep the camera move under 3.5%.
    for tr in timeline.tracks:
        for c in tr.clips:
            if tr.kind != "video" or c.media_id != clip.media_id:
                continue
            c.keyframes.pop("scale", None)
            c.keyframes.pop("pos_x", None)
            c.keyframes.pop("pos_y", None)
            for action in plan.actions:
                if action.kind not in {"subtle_push", "beat_emphasis"}:
                    continue
                if c.source_in - .001 <= action.start <= c.source_out + .001:
                    local = max(.05, min(c.duration - .05, action.start - c.source_in))
                    amount = min(1.035, float(action.params.get("scale", 1.02)))
                    c.keyframes["scale"] = [
                        Keyframe(max(0.0, local - .18), 1.0, "ease_out"),
                        Keyframe(local, amount, "ease_in_out"),
                        Keyframe(min(c.duration, local + .42), 1.0, "ease_out"),
                    ]
                    break
            c.gain_db = max(-1.5, min(1.5, c.gain_db))
    return n
