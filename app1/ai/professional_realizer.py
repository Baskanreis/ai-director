"""Professional timeline realization: cuts + motion + sound + delivery metadata (v2.21)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable

from app.ai.timeline_realizer import realize_professional_timeline, RealizationReport
from app.ai.professional_director import ProfessionalEditPlan
from app.effects.asset_library import list_assets
from app.motion.director_motion import apply_motion_plan
from app.ai.beat_sync import MotionCue
from app.timeline.model import Clip, Timeline

@dataclass(frozen=True)
class AppliedLayerReport:
    motion_cues: int = 0
    sfx_clips: int = 0
    music_clips: int = 0
    caption_cues: int = 0
    transition_cues: int = 0
    broll_cues: int = 0
    warnings: tuple[str, ...] = ()
    def to_dict(self):
        return {
            "motion_cues": self.motion_cues, "sfx_clips": self.sfx_clips,
            "music_clips": self.music_clips, "caption_cues": self.caption_cues,
            "transition_cues": self.transition_cues, "broll_cues": self.broll_cues,
            "warnings": list(self.warnings),
        }


def _motion_cues(plan: ProfessionalEditPlan) -> list[MotionCue]:
    mapped = {"hook_punch": "punch", "broll_reframe": "push_in", "micro_push": "micro_push", "push_in": "push_in", "pull_out": "pull_out"}
    return [MotionCue(start=m.start, end=m.end, preset=mapped.get(m.preset, "micro_push"), intensity=m.intensity, reason=m.reason)
            for m in plan.motion if m.end > m.start]


def _find_clip(timeline: Timeline, start: float, end: float):
    video = timeline.first_track("video")
    for c in video.clips:
        if c.start < end and c.end > start:
            return c
    return None


def apply_professional_layers(timeline: Timeline, plan: ProfessionalEditPlan, *, add_music: bool = True, add_sfx: bool = True) -> AppliedLayerReport:
    warnings: list[str] = []
    video = timeline.first_track("video")
    applied_motion = apply_motion_plan(video.clips, _motion_cues(plan), max_cues_per_clip=6)

    # Sound assets are local starter assets; publication rights remain the user's responsibility.
    assets = {a.id: a for a in list_assets()}
    sfx_track = timeline.add_audio_track("SFX", role="")
    music_track = timeline.add_audio_track("Music", role="music")
    music_track.duck = True
    sfx_count = 0
    if add_sfx:
        for d in plan.sound.sound_decisions:
            asset = assets.get(d.asset_id)
            if not asset or d.duration <= 0:
                continue
            # Director times are source/timeline times after realization; constrain to actual edit duration.
            if d.start >= timeline.duration:
                continue
            start = max(0.0, d.start)
            end = min(timeline.duration, start + d.duration)
            if end <= start:
                continue
            # Track model forbids overlaps; use a deterministic skip instead of fabricating a mixer layer.
            if sfx_track.overlaps(start, end):
                continue
            clip = Clip(media_id=asset.path, name=asset.name, source_in=0.0, source_out=end-start,
                        start=start, gain_db=d.gain_db, fade_in=min(.03, end-start/2), fade_out=min(.06, end-start/2))
            sfx_track.add(clip); sfx_count += 1

    music_count = 0
    if add_music and plan.sound.music_asset and plan.sound.music_asset in assets and timeline.duration > 0:
        asset = assets[plan.sound.music_asset]
        # One loopable starter asset can cover the full edit via renderer loop support/metadata.
        music_track.clips.clear()
        music_track.add(Clip(media_id=asset.path, name=asset.name, source_in=0.0, source_out=timeline.duration,
                             start=0.0, gain_db=plan.sound.music_gain_db))
        music_track.clips[0].keyframes["volume"] = []
        music_count = 1

    # Preserve higher-level decisions for renderers that support captions/B-roll/transitions.
    broll = [e for e in plan.director.events if e.kind == "broll_cue" and e.end > e.start]
    timeline.ai_director.update({
        "version": "2.21",
        "layers_applied": True,
        "motion_applied": [a.__dict__ for a in applied_motion],
        "captions": [c.__dict__ for c in plan.captions],
        "broll_cues": [e.__dict__ for e in broll],
        "transition_policy": "short_crossfade_only_when_renderer supports overlap; otherwise hard cut",
        "sound_policy": "local starter assets only; verify license before publication",
    })
    return AppliedLayerReport(len(applied_motion), sfx_count, music_count, len(plan.captions),
                              max(0, len(video.clips)-1), len(broll), tuple(warnings))


def realize_full_professional_timeline(plan: ProfessionalEditPlan, media_id: str, media_name: str = "Source", fps: float = 30.0):
    timeline, report = realize_professional_timeline(plan, media_id, media_name, fps)
    layers = apply_professional_layers(timeline, plan)
    return timeline, report, layers

__all__ = ["AppliedLayerReport", "apply_professional_layers", "realize_full_professional_timeline"]
