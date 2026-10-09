"""Automatic timeline composition from existing clips.

Builds a deterministic, reversible edit plan that combines scene-aware creative
stacks, beat timing, transitions, caption cues and music-ducking metadata.
No media is rendered here; applying the plan only changes timeline metadata,
keyframes and transitions through the existing Creative Apply engine.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Iterable

from app.audio.beat_sync import BeatGrid, quantize_time
from app.ai.creative_apply import apply_creative_stack, ApplyReport
from app.ai.creative_studio_ai import ClipContext
from app.ai.scene_creative_director import SceneCreativePlan, build_scene_creative_plan, flatten_plan
from app.effects.pro_asset_library import catalog
from app.timeline.model import Timeline, Transition

@dataclass(frozen=True)
class TimelineScene:
    scene_id: str
    clip_id: str
    start: float
    end: float
    style: str
    variant: int
    beat_times: tuple[float, ...] = ()
    transition: str | None = None

@dataclass(frozen=True)
class AutoTimelinePlan:
    scenes: tuple[TimelineScene, ...]
    creative: SceneCreativePlan
    bpm: float | None = None
    beat_offset: float = 0.0
    version: str = "auto_timeline_v1"
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)

    @property
    def duration(self) -> float:
        return max((s.end for s in self.scenes), default=0.0)


def _transition_for(style: str, index: int, bpm: float | None) -> str:
    style = style.lower()
    if "music" in style:
        return "strobe" if bpm and index % 4 == 0 else "rgb_split"
    if "gaming" in style or "meme" in style:
        return "digital_wipe" if index % 2 else "rgb_split"
    if "cinematic" in style or "documentary" in style:
        return "light_leak" if index % 2 else "crossfade"
    if "podcast" in style or "minimal" in style:
        return "crossfade"
    return "slide_right" if index % 2 else "push_left"


def _context_from_clip(clip, *, style: str, platform: str) -> ClipContext:
    name = clip.name.lower()
    tags = []
    if any(x in name for x in ("game", "gaming", "valorant", "minecraft", "fortnite")):
        tags.append("gaming")
    if any(x in name for x in ("podcast", "talk", "speech", "interview")):
        tags.append("podcast")
    if any(x in name for x in ("music", "song", "beat")):
        tags.append("music")
    # Existing linked audio is a useful, conservative signal; we never claim
    # speech unless a voice/caption analyzer supplied it.
    speech = bool(clip.creative_metadata.get("speech", False))
    music = bool(clip.creative_metadata.get("music", False))
    faces = bool(clip.creative_metadata.get("faces", False))
    energy = float(clip.creative_metadata.get("energy", .55))
    scene_type = str(clip.creative_metadata.get("scene_type", "general"))
    return ClipContext(clip.id, clip.duration, scene_type=scene_type, energy=max(0,min(1,energy)),
                       speech=speech, music=music, faces=faces, tags=tuple(tags),
                       platform=platform, style=style)


def build_auto_timeline_plan(
    timeline: Timeline,
    *,
    style: str = "viral_fast",
    platform: str = "shorts",
    bpm: float | None = None,
    beat_offset: float = 0.0,
    variant: int = 0,
    items_per_scene: int = 4,
) -> AutoTimelinePlan:
    video = timeline.first_track("video")
    clips = video.sorted_clips()
    contexts = [_context_from_clip(c, style=style, platform=platform) for c in clips]
    creative = build_scene_creative_plan(contexts, items_per_scene=items_per_scene, variant=variant)
    grid = BeatGrid(float(bpm), float(beat_offset)) if bpm and bpm > 0 else None
    scenes=[]
    for i, clip in enumerate(clips):
        beats = tuple(grid.beats(clip.end) if grid else ())
        # Store absolute beat times only inside this scene's range.
        beats = tuple(round(t,4) for t in beats if clip.start <= t < clip.end)
        transition = _transition_for(style, i, bpm) if i > 0 else None
        scenes.append(TimelineScene(
            scene_id=f"scene-{i+1:04d}", clip_id=clip.id, start=clip.start, end=clip.end,
            style=style, variant=variant, beat_times=beats, transition=transition,
        ))
    return AutoTimelinePlan(tuple(scenes), creative, bpm, beat_offset, metadata={
        "platform": platform, "style": style, "scene_count": len(scenes),
        "creative_item_count": creative.item_count, "non_destructive": True,
    })


def apply_auto_timeline_plan(timeline: Timeline, plan: AutoTimelinePlan) -> ApplyReport:
    """Apply an automatic plan without rendering or changing source media."""
    rows = flatten_plan(plan.creative)
    report = apply_creative_stack(timeline, rows)
    scene_by_clip = {s.clip_id: s for s in plan.scenes}
    for track in timeline.tracks:
        if track.kind != "video":
            continue
        for clip in track.clips:
            scene = scene_by_clip.get(clip.id)
            if not scene:
                continue
            clip.creative_metadata.update({
                "auto_timeline_version": plan.version,
                "scene_id": scene.scene_id,
                "style": scene.style,
                "variant": scene.variant,
                "beat_times": list(scene.beat_times),
            })
            if scene.transition:
                # Transition duration comes from the selected library asset when available.
                asset = next((a for a in catalog("transition") if a.params.get("kind") == scene.transition), None)
                duration = float(asset.params.get("duration", .22)) if asset else .22
                clip.transition_in = Transition(kind=scene.transition, duration=max(.05, min(.8, duration)))
    return report

__all__ = ["TimelineScene", "AutoTimelinePlan", "build_auto_timeline_plan", "apply_auto_timeline_plan"]
