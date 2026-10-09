"""Context-aware Creative Library selection and non-destructive preview planning."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Iterable
from app.effects.pro_asset_library import CreativeAsset, catalog

@dataclass(frozen=True)
class ClipContext:
    clip_id: str
    duration: float
    scene_type: str = "general"
    energy: float = .5
    speech: bool = False
    music: bool = False
    faces: bool = False
    tags: tuple[str, ...] = ()
    platform: str = "shorts"
    style: str = "viral_fast"

@dataclass(frozen=True)
class PreviewCue:
    asset_id: str
    kind: str
    start: float
    duration: float
    intensity: float
    params: dict[str, Any]

@dataclass(frozen=True)
class PreviewPlan:
    clip_id: str
    cues: tuple[PreviewCue, ...]
    score: float
    reason: str
    metadata: dict[str, Any]
    def to_dict(self): return asdict(self)

_KIND_BONUS={"effect":1.0,"motion":1.0,"text":.8,"transition":.65,"overlay":.5,"sfx":.55,"audio_fx":.35,"filter":.6,"sticker":.45,"template":.4,"music":.3}
_STYLE_TAGS={
    "viral_fast":("viral","shorts","impact","energy","social"),
    "gaming":("gaming","glitch","impact","energy","tech"),
    "cinematic":("cinematic","film","dramatic","soft"),
    "podcast":("podcast","voice","caption","clean"),
    "music_video":("music","beat","rhythm","glow","glitch"),
    "meme":("meme","fun","comic","impact","viral"),
    "documentary":("documentary","story","cinematic","subtle"),
}


def _score(a: CreativeAsset, c: ClipContext) -> float:
    hay=(a.name+' '+' '.join(a.tags)+' '+a.id).lower()
    score=_KIND_BONUS.get(a.kind,.2)
    for tag in c.tags: score += 2.5 if tag.lower() in hay else 0
    for tag in _STYLE_TAGS.get(c.style.lower(),()): score += 1.7 if tag in hay else 0
    if c.speech and any(x in hay for x in ("caption","voice","subtitle","speech")): score += 3.0
    if c.faces and any(x in hay for x in ("portrait","face","speaker","skin")): score += 1.8
    if c.music and any(x in hay for x in ("beat","music","rhythm","audio")): score += 2.0
    if c.energy>.7 and any(x in hay for x in ("impact","energy","fast","glitch","punch")): score += 2.2
    if c.energy<.35 and any(x in hay for x in ("soft","cinematic","clean","subtle")): score += 1.6
    score += min(1.2, max(0.0,c.energy)) if a.kind in {"motion","effect"} else 0
    return score


def rank_for_clip(context: ClipContext, *, kind: str|None=None, limit: int=12) -> list[tuple[CreativeAsset,float]]:
    rows=[(a,_score(a,context)) for a in catalog(kind)]
    rows.sort(key=lambda x:(-x[1],x[0].name))
    return rows[:max(1,limit)]


def build_preview_plan(context: ClipContext, assets: Iterable[CreativeAsset], *, max_cues:int=5) -> PreviewPlan:
    duration=max(.08,float(context.duration)); selected=[]; cursor=0.0
    for a in assets:
        if len(selected)>=max_cues: break
        d=float(a.params.get("duration",a.params.get("length",.45)))
        d=max(.08,min(duration,d)); start=min(cursor,max(0.0,duration-d))
        intensity=min(1.0,max(.2,.55+context.energy*.35))
        selected.append(PreviewCue(a.id,a.kind,round(start,3),round(d,3),round(intensity,3),dict(a.params)))
        cursor=min(duration,cursor+max(.12,d*.7))
    score=sum(_score(a,context) for a in assets)
    reason=f"{context.style} / {context.scene_type} / energy={context.energy:.2f}"
    return PreviewPlan(context.clip_id,tuple(selected),round(score,3),reason,{"non_destructive":True,"engine":"context_rank_v1"})


def generate_variations(context: ClipContext, ranked: list[tuple[CreativeAsset,float]], count:int=3) -> list[PreviewPlan]:
    rows=[a for a,_ in ranked]
    plans=[]
    for i in range(max(1,min(5,count))):
        # Keep variation deterministic: rotate the ranked pool and select diverse kinds.
        pool=rows[i:]+rows[:i]
        chosen=[]; kinds=set()
        for a in pool:
            if a.kind in kinds and len(chosen)<2: continue
            chosen.append(a); kinds.add(a.kind)
            if len(chosen)>=min(4,3+i): break
        plans.append(build_preview_plan(context,chosen,max_cues=5))
    return plans
