"""AI Director -> real non-destructive timeline realization (v2.20).

Turns the reviewed professional edit plan into actual Clip objects.  It never
renders media and never destroys source material; it only constructs a timeline
whose source ranges skip accepted safe cuts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from app.ai.professional_director import ProfessionalEditPlan
from app.timeline.model import Clip, Timeline, Track, Transition, MIN_CLIP


@dataclass(frozen=True)
class RealizationReport:
    source_duration: float
    final_duration: float
    applied_cut_seconds: float
    video_clips: int
    audio_clips: int
    skipped_decisions: int
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "source_duration": self.source_duration,
            "final_duration": self.final_duration,
            "applied_cut_seconds": self.applied_cut_seconds,
            "video_clips": self.video_clips,
            "audio_clips": self.audio_clips,
            "skipped_decisions": self.skipped_decisions,
            "warnings": list(self.warnings),
        }


def _merge_ranges(ranges: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for start, end in sorted(ranges):
        start, end = max(0.0, float(start)), float(end)
        if end <= start + MIN_CLIP:
            continue
        if out and start <= out[-1][1] + 0.01:
            out[-1] = (out[-1][0], max(out[-1][1], end))
        else:
            out.append((start, end))
    return out


def _kept_ranges(duration: float, cuts: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    duration = max(0.0, duration)
    merged = _merge_ranges((max(0.0, s), min(duration, e)) for s, e in cuts)
    kept: list[tuple[float, float]] = []
    cursor = 0.0
    for start, end in merged:
        if start > cursor + MIN_CLIP:
            kept.append((cursor, start))
        cursor = max(cursor, end)
    if duration > cursor + MIN_CLIP:
        kept.append((cursor, duration))
    return kept


def realize_professional_timeline(
    plan: ProfessionalEditPlan,
    media_id: str,
    media_name: str = "Source",
    fps: float = 30.0,
    add_audio: bool = True,
) -> tuple[Timeline, RealizationReport]:
    """Materialize accepted safe cuts as linked video/audio clips.

    The source timebase remains untouched. Timeline time is compacted around
    removed ranges, making the operation equivalent to a ripple edit.
    """
    duration = max(0.0, float(plan.director.source_duration))
    accepted = [d for d in plan.director.accepted_decisions() if d.risk == "low"]
    cuts = _merge_ranges((d.start, d.end) for d in accepted)
    kept = _kept_ranges(duration, cuts)

    timeline = Timeline(fps=fps)
    video = timeline.track("V1")
    audio = timeline.track("A1")
    audio.role = "voice"

    cursor = 0.0
    link_index = 0
    warnings: list[str] = []
    for source_in, source_out in kept:
        dur = source_out - source_in
        if dur < MIN_CLIP:
            continue
        link_id = f"director_link_{link_index:04d}"
        vclip = Clip(media_id=media_id, name=media_name, source_in=source_in,
                     source_out=source_out, start=cursor, link_id=link_id)
        if video.clips:
            vclip.transition_in = Transition(kind="cut", duration=0.0)
        video.add(vclip)
        if add_audio:
            aclip = Clip(media_id=media_id, name=f"{media_name} Audio", source_in=source_in,
                         source_out=source_out, start=cursor, link_id=link_id,
                         denoise=True, voice_enhance=True)
            audio.add(aclip)
        cursor += dur
        link_index += 1

    # The visual/sound/caption plans remain available as metadata on the result
    # object without inventing media assets that were not supplied by the user.
    timeline.ai_director = {
        "version": "2.20",
        "profile": plan.director.profile,
        "motion_decisions": [m.__dict__ for m in plan.motion],
        "caption_decisions": [c.__dict__ for c in plan.captions],
        "sound_plan": plan.sound.to_dict(),
        "non_destructive": True,
        "asset_policy": "Only supplied/licensed assets are materialized.",
    }

    applied = sum(e - s for s, e in cuts)
    skipped = len(plan.director.decisions) - len(accepted)
    if skipped:
        warnings.append(f"{skipped} decision review/safety nedeniyle timeline'a uygulanmadı.")
    report = RealizationReport(
        source_duration=duration,
        final_duration=timeline.duration,
        applied_cut_seconds=applied,
        video_clips=len(video.clips),
        audio_clips=len(audio.clips),
        skipped_decisions=skipped,
        warnings=tuple(warnings),
    )
    return timeline, report


__all__ = ["RealizationReport", "realize_professional_timeline"]
