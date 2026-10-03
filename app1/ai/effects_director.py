"""AI Effects & Sound Director — v2.3.

Director events -> deterministic music/SFX/visual effect decisions.  This layer
is intentionally metadata-first: it can plan a sound design pass without
pretending that a particular copyrighted song is available.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from app.effects.asset_library import AudioAsset, list_assets
from .director import DirectorEvent, DirectorPlan, EditEventKind, EditProfile
from .editorial_style_engine import EditorialStylePlan

@dataclass(frozen=True)
class SoundDecision:
    asset_id: str
    category: str
    start: float
    duration: float
    gain_db: float
    reason: str
    confidence: float
    duck_music: bool = False

@dataclass(frozen=True)
class VisualDecision:
    preset: str
    start: float
    end: float
    intensity: float
    reason: str
    confidence: float

@dataclass
class SoundDesignPlan:
    profile: str
    music_asset: str | None = None
    music_gain_db: float = -18.0
    sound_decisions: list[SoundDecision] = field(default_factory=list)
    visual_decisions: list[VisualDecision] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def _pick_music(profile: EditProfile, assets: list[AudioAsset]) -> AudioAsset | None:
    names = {
        EditProfile.HIGH_RETENTION: ("hype", "upbeat"),
        EditProfile.SHORTS: ("hype", "upbeat"),
        EditProfile.TIKTOK: ("hype", "upbeat"),
        EditProfile.INSTAGRAM_REEL: ("upbeat", "travel"),
        EditProfile.YOUTUBE_LONGFORM: ("chill", "corporate"),
    }
    wanted = names.get(profile, ("upbeat",))
    music = [a for a in assets if a.category == "Music"]
    for tag in wanted:
        for a in music:
            if tag in a.tags:
                return a
    return music[0] if music else None


def _pick_sfx(tags: Iterable[str], assets: list[AudioAsset], fallback: str = "sfx_whoosh") -> AudioAsset | None:
    tagset = set(tags)
    sfx = [a for a in assets if a.category == "SFX"]
    for a in sfx:
        if tagset.intersection(a.tags) or any(t in a.id for t in tagset):
            return a
    return next((a for a in sfx if a.id == fallback), sfx[0] if sfx else None)


def build_sound_design_plan(plan: DirectorPlan, assets: list[AudioAsset] | None = None, style: EditorialStylePlan | None = None) -> SoundDesignPlan:
    """Director olaylarından güvenli bir ilk sound-design pass üretir."""
    assets = list(assets) if assets is not None else list_assets()
    music = _pick_music(EditProfile(plan.profile), assets)
    recipe = style.recipe if style else None
    out = SoundDesignPlan(profile=plan.profile, music_asset=music.id if music else None)
    out.music_gain_db = -20.0 if plan.profile in (EditProfile.SHORTS.value, EditProfile.TIKTOK.value, EditProfile.HIGH_RETENTION.value) else -18.0

    for event in plan.events:
        if event.end <= event.start:
            continue
        if event.kind == EditEventKind.HOOK.value:
            a = _pick_sfx(("hit", "pop"), assets, "sfx_hit")
            if a and (recipe is None or recipe.sfx_rate > .05):
                out.sound_decisions.append(SoundDecision(a.id, a.category, event.start, min(.45, max(.12, event.end-event.start)), -9.0,
                    "Hook başlangıcını sesle işaretle.", min(0.98, event.score/100+.12), True))
            out.visual_decisions.append(VisualDecision("shorts_energy" if plan.profile != EditProfile.YOUTUBE_LONGFORM.value else "punch",
                event.start, min(event.end, event.start+.8), .65, "Hook için kısa görsel vurgu.", min(.95,event.score/100+.1)))
        elif event.kind == EditEventKind.PATTERN_BREAK.value and (recipe is None or recipe.visual_density >= .35):
            a = _pick_sfx(("whoosh", "swoosh"), assets)
            if a:
                at = event.start + min(.15, max(0.0, event.end-event.start)*.1)
                out.sound_decisions.append(SoundDecision(a.id, a.category, at, .35, -12.0,
                    "Uzun konuşma bloğunda pattern-break.", .82, True))
            out.visual_decisions.append(VisualDecision("punch", event.start, min(event.end, event.start+.6), .45,
                "Pattern-break için kısa görsel vurgu.", .78))
        elif event.kind == EditEventKind.BROLL_CUE.value:
            a = _pick_sfx(("click", "pop"), assets, "sfx_click")
            if a and event.score >= 70:
                out.sound_decisions.append(SoundDecision(a.id, a.category, event.start, .22, -20.0,
                    "B-roll girişini hafifçe işaretle.", .72, True))
        elif event.kind == EditEventKind.BEAT.value and event.score >= 70:
            a = _pick_sfx(("tick",), assets, "sfx_tick")
            if a:
                out.sound_decisions.append(SoundDecision(a.id, a.category, event.start, .18, -22.0,
                    "Narrative beat'i düşük seviyeli SFX ile vurgula.", .70, True))

    # Çakışan aynı-SFX kararlarını sadeleştir.
    seen: set[tuple[str,int]] = set()
    filtered=[]
    for d in sorted(out.sound_decisions, key=lambda x:(x.start,x.asset_id)):
        key=(d.asset_id, round(d.start*10))
        if key not in seen:
            seen.add(key); filtered.append(d)
    out.sound_decisions = filtered
    out.metadata = {
        "engine_version": "2.3",
        "music_is_loopable": bool(music and music.loopable),
        "asset_policy": "Use only assets whose metadata/license permits your intended publication.",
        "automatic_ducking": True,
        "decisions_are_suggestions": True,
    }
    return out


def music_asset_path(sound_plan: SoundDesignPlan, assets: list[AudioAsset] | None = None) -> str | None:
    if not sound_plan.music_asset:
        return None
    assets = list(assets) if assets is not None else list_assets()
    found = next((a for a in assets if a.id == sound_plan.music_asset), None)
    return str(Path(found.path)) if found else None

__all__ = ["SoundDecision", "VisualDecision", "SoundDesignPlan", "build_sound_design_plan", "music_asset_path"]
