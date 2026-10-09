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
from app.effects.animation_library import AnimationPreset, list_animations
from app.effects.effect_library import ALL_EFFECTS
from app.effects.pro_asset_library import CreativeAsset, catalog
from .director import DirectorEvent, DirectorPlan, EditEventKind, EditProfile
from .edit_styles import get_recipe

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


def _pick_music(profile: EditProfile, assets: list[AudioAsset], style_tags: tuple[str, ...] = ()) -> AudioAsset | None:
    names = {
        EditProfile.HIGH_RETENTION: ("hype", "upbeat"),
        EditProfile.SHORTS: ("hype", "upbeat"),
        EditProfile.TIKTOK: ("hype", "upbeat"),
        EditProfile.INSTAGRAM_REEL: ("upbeat", "travel"),
        EditProfile.YOUTUBE_LONGFORM: ("chill", "corporate"),
    }
    wanted = tuple(style_tags) + names.get(profile, ("upbeat",))
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


def build_sound_design_plan(plan: DirectorPlan, assets: list[AudioAsset] | None = None) -> SoundDesignPlan:
    """Director olaylarından güvenli bir ilk sound-design pass üretir."""
    assets = list(assets) if assets is not None else list_assets()
    recipe = get_recipe(plan.metadata.get("edit_style", "minimal"))
    music = _pick_music(EditProfile(plan.profile), assets, recipe.tags)
    out = SoundDesignPlan(profile=plan.profile, music_asset=music.id if music else None)
    out.music_gain_db = -20.0 if plan.profile in (EditProfile.SHORTS.value, EditProfile.TIKTOK.value, EditProfile.HIGH_RETENTION.value) else -18.0
    if recipe.style.value in {"podcast", "talking_head", "minimal", "news"}:
        out.music_gain_db -= 2.0

    for event in plan.events:
        if event.end <= event.start:
            continue
        if event.kind == EditEventKind.HOOK.value:
            a = _pick_sfx(("hit", "pop"), assets, "sfx_hit")
            if a:
                out.sound_decisions.append(SoundDecision(a.id, a.category, event.start, min(.45, max(.12, event.end-event.start)), -9.0,
                    "Hook başlangıcını sesle işaretle.", min(0.98, event.score/100+.12), True))
            out.visual_decisions.append(VisualDecision("shorts_energy" if plan.profile != EditProfile.YOUTUBE_LONGFORM.value else "punch",
                event.start, min(event.end, event.start+.8), .65, "Hook için kısa görsel vurgu.", min(.95,event.score/100+.1)))
        elif event.kind == EditEventKind.PATTERN_BREAK.value:
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


@dataclass(frozen=True)
class CreativeDecision:
    kind: str
    asset_id: str
    start: float
    end: float
    intensity: float
    reason: str
    confidence: float
    parameters: dict = field(default_factory=dict)

@dataclass
class CreativePassPlan:
    profile: str
    music_asset: str | None = None
    music_gain_db: float = -20.0
    decisions: list[CreativeDecision] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def _pick_asset(kind: str, tags: tuple[str, ...], fallback: str | None = None) -> CreativeAsset | None:
    pool = catalog(kind)
    wanted = set(t.lower() for t in tags)
    ranked = []
    for a in pool:
        score = sum(2 if t in a.name.lower() else 1 for t in wanted if t in a.tags or t in a.name.lower())
        if score:
            ranked.append((score, a))
    if ranked:
        return sorted(ranked, key=lambda x: (-x[0], x[1].name))[0][1]
    if fallback:
        return next((a for a in pool if a.id == fallback), None)
    return pool[0] if pool else None

def build_creative_pass_plan(plan: DirectorPlan, assets: list[AudioAsset] | None = None) -> CreativePassPlan:
    """Director olaylarını gerçek creative-library kararlarına dönüştürür.

    Bu pass deterministiktir: lisanslı/yerel assetleri uydurmaz ve kararları
    timeline'a doğrudan basmak yerine non-destructive bir plan üretir.
    """
    assets = list(assets) if assets is not None else list_assets()
    sound = build_sound_design_plan(plan, assets)
    out = CreativePassPlan(plan.profile, sound.music_asset, sound.music_gain_db)
    profile = EditProfile(plan.profile)
    recipe = get_recipe(plan.metadata.get("edit_style", "minimal"))
    effect_fallback = {
        EditProfile.SHORTS: "effect.shorts_energy",
        EditProfile.TIKTOK: "effect.viral_pop",
        EditProfile.INSTAGRAM_REEL: "effect.vivid",
        EditProfile.HIGH_RETENTION: "effect.shorts_energy",
        EditProfile.YOUTUBE_LONGFORM: "effect.cinematic",
    }[profile]

    for event in plan.events:
        dur = max(0.05, event.end - event.start)
        if event.kind == EditEventKind.HOOK.value:
            eff = _pick_asset("effect", ("shorts", "viral", "energy"), effect_fallback)
            motion = _pick_asset("motion", ("hook", "impact", "shorts"), "motion.punch_fast")
            text = _pick_asset("text", ("hook", "shorts", "social"), "text.bold_hook")
            for kind, asset, reason in (("effect",eff,"Hook için enerjik grade"),("motion",motion,"Hook punch-in"),("text",text,"Hook başlığı")):
                if asset:
                    density = {"effect": recipe.transition_density, "motion": recipe.zoom_density, "text": recipe.caption_density}.get(kind, 1.0)
                    out.decisions.append(CreativeDecision(kind, asset.id, event.start, min(event.end, event.start+0.9), min(1.0, .8 * density), reason, min(.99,event.score/100+.12), asset.params))
        elif event.kind == EditEventKind.PATTERN_BREAK.value:
            tr = _pick_asset("transition", ("motion", "energy", "shorts"), "transition.whip_left")
            motion = _pick_asset("motion", ("impact", "beat", "shorts"), "motion.shake_medium")
            if tr:
                out.decisions.append(CreativeDecision("transition", tr.id, event.start, min(event.end,event.start+.35), min(1.0, .6 * recipe.transition_density), "Pattern-break geçişi", .84, tr.params))
            if motion:
                out.decisions.append(CreativeDecision("motion", motion.id, event.start, min(event.end,event.start+.25), min(1.0, .45 * recipe.zoom_density), "Pattern-break hareketi", .78, motion.params))
        elif event.kind == EditEventKind.BROLL_CUE.value:
            motion = _pick_asset("motion", ("broll", "cinematic", "photo"), "motion.parallax")
            overlay = _pick_asset("motion", ("travel", "aesthetic", "dream"), "overlay.light_leak")
            if motion:
                out.decisions.append(CreativeDecision("motion", motion.id, event.start, min(event.end,event.start+3.0), min(1.0, .4 * recipe.broll_density), "B-roll hareketi", .76, motion.params))
            if overlay and event.score >= 75:
                out.decisions.append(CreativeDecision("overlay", overlay.id, event.start, min(event.end,event.start+.8), min(1.0, .22 * recipe.broll_density), "B-roll atmosferi", .68, overlay.params))
        elif event.kind == EditEventKind.BEAT.value and event.score >= 70:
            tr = _pick_asset("transition", ("beat", "impact"), "transition.flash_white")
            if tr:
                out.decisions.append(CreativeDecision("transition", tr.id, event.start, min(event.end,event.start+.16), min(1.0, .5 * recipe.transition_density), "Beat sync vurgu", .74, tr.params))
        elif event.kind == EditEventKind.EMPHASIZE.value:
            text = _pick_asset("text", ("caption", "viral", "word"), "text.bold_hook")
            if text:
                out.decisions.append(CreativeDecision("text", text.id, event.start, min(event.end,event.start+.5), min(1.0, .7 * recipe.caption_density), "Vurgulu kelime animasyonu", .82, text.params))

    for cue in sound.sound_decisions:
        out.decisions.append(CreativeDecision("sfx", cue.asset_id, cue.start, cue.start+cue.duration, .5, cue.reason, cue.confidence, {"gain_db": cue.gain_db, "duck_music": cue.duck_music}))

    # Aynı anda aşırı efekt yığılmasını engelle. SFX + tek görsel + tek text/motion önceliklidir.
    chosen=[]
    for d in sorted(out.decisions, key=lambda x:(x.start, -x.confidence)):
        overlap=sum(1 for x in chosen if x.kind == d.kind and abs(x.start-d.start) < .12)
        if overlap >= 2 and d.kind not in {"sfx","text"}:
            continue
        chosen.append(d)
    out.decisions=chosen
    out.metadata={
        "engine_version":"2.24",
        "non_destructive":True,
        "automatic_music_ducking":True,
        "decision_policy":"event-driven creative direction",
        "asset_count":len(catalog()),
        "effect_count":len(ALL_EFFECTS),
        "animation_count":len(list_animations()),
        "edit_style": recipe.style.value,
        "style_recipe": {"cut_density": recipe.cut_density, "broll_density": recipe.broll_density, "zoom_density": recipe.zoom_density, "caption_density": recipe.caption_density, "transition_density": recipe.transition_density, "sfx_density": recipe.sfx_density, "speed_ramping": recipe.speed_ramping, "beat_sync": recipe.beat_sync, "face_tracking": recipe.face_tracking, "auto_reframe": recipe.auto_reframe, "cinematic_grade": recipe.cinematic_grade},
    }
    return out

__all__ = ["SoundDecision", "VisualDecision", "SoundDesignPlan", "CreativeDecision", "CreativePassPlan", "build_sound_design_plan", "build_creative_pass_plan", "music_asset_path"]
