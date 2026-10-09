"""AI-driven Marketplace Pack Director.

Selects a coherent asset pack from scene/context signals before selecting
individual assets. The result is deterministic, non-destructive and uses the
same bundled catalog that ships inside the single Windows Setup.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import re
from typing import Iterable

from app.ai.creative_studio_ai import ClipContext
from app.effects.marketplace import AssetPack, builtin_packs
from app.effects.pro_asset_library import CreativeAsset

@dataclass(frozen=True)
class PackRecommendation:
    pack_id: str
    pack_name: str
    score: float
    reasons: tuple[str, ...] = ()
    matched_tags: tuple[str, ...] = ()

    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class PackCreativeSelection:
    primary: PackRecommendation
    secondary: PackRecommendation | None = None
    mix: float = 0.0

    def to_dict(self): return asdict(self)

# High-signal aliases keep Turkish prompts and scene metadata useful without a
# second model. Exact asset selection remains metadata-first and lightweight.
ALIASES = {
    "oyun":"gaming", "gaming":"gaming", "fps":"gaming", "game":"gaming",
    "seyahat":"travel", "gezi":"travel", "vlog":"travel", "broll":"broll",
    "eğitim":"education", "egitim":"education", "tutorial":"tutorial", "ders":"education",
    "podcast":"podcast", "konuşma":"talking_head", "konusma":"talking_head",
    "güzellik":"beauty", "guzellik":"beauty", "moda":"fashion", "fashion":"fashion",
    "sinematik":"cinematic", "film":"cinematic", "belgesel":"documentary",
    "meme":"meme", "komedi":"comedy", "reaction":"reaction",
    "altyazı":"subtitle", "altyazi":"subtitle", "caption":"caption", "karaoke":"karaoke",
    "lut":"lut", "filtre":"filter", "renk":"color",
    "ses":"audio", "sfx":"sfx", "whoosh":"whoosh", "impact":"impact",
    "viral":"viral", "shorts":"shorts", "reels":"social", "sosyal":"social",
    "neon":"neon", "glitch":"glitch", "rgb":"rgb", "tech":"tech",
}

PROFILE_TAGS = {
    "viral_fast": {"viral","shorts","hook","impact","energy","social"},
    "cinematic": {"cinematic","film","story","documentary"},
    "podcast": {"podcast","talking_head","voice","dialogue"},
    "gaming": {"gaming","glitch","rgb","neon","tech"},
    "travel": {"travel","broll","cinematic","vlog"},
    "beauty": {"beauty","fashion","portrait","skin","editorial"},
    "education": {"education","tutorial","explainer","caption"},
    "meme": {"meme","reaction","comedy","social","fun"},
}


def _tokens(value: object) -> set[str]:
    return {x for x in re.findall(r"[\wğüşöçıİĞÜŞÖÇ-]+", str(value or "").lower()) if len(x) > 1}


def _expand(values: Iterable[object]) -> set[str]:
    out=set()
    for value in values:
        for token in _tokens(value):
            out.add(token)
            if token in ALIASES: out.add(ALIASES[token])
    return out


def _context_tags(context: ClipContext) -> set[str]:
    tags=_expand((context.scene_type, context.style, *context.tags))
    if context.speech: tags |= {"voice","dialogue","talking_head"}
    if context.faces: tags |= {"portrait","people"}
    if context.music: tags |= {"music","beat"}
    if context.energy >= .80: tags |= {"energy","impact","viral","hook"}
    elif context.energy <= .30: tags |= {"clean","soft","minimal","cinematic"}
    tags |= PROFILE_TAGS.get(context.style, set())
    if context.platform in {"shorts","reels","tiktok"}: tags |= {"shorts","social","viral"}
    return tags


def recommend_packs(context: ClipContext, limit: int = 5) -> list[PackRecommendation]:
    wanted=_context_tags(context)
    rows=[]
    for pack in builtin_packs():
        pack_tags=set(pack.tags) | set(pack.categories)
        matched=sorted(wanted & pack_tags)
        score=float(len(matched)*5)
        # Stronger semantic signals for the most useful pack dimensions.
        if context.speech and "audio_fx" in pack.categories: score += 2.0
        if context.faces and ("beauty" in pack.tags or "portrait" in pack.tags): score += 2.0
        if context.energy >= .8 and pack.id in {"pack.viral-shorts","pack.gaming"}: score += 2.5
        if context.scene_type.lower() in {"broll","b-roll"} and pack.id == "pack.travel-broll": score += 4.0
        if not matched: score += .15
        reasons=[]
        if matched: reasons.append("tag-fit:" + ",".join(matched[:6]))
        if context.speech and "audio_fx" in pack.categories: reasons.append("speech-audio")
        if context.faces and ("beauty" in pack.tags or "portrait" in pack.tags): reasons.append("face-style")
        if context.energy >= .8 and pack.id in {"pack.viral-shorts","pack.gaming"}: reasons.append("high-energy")
        rows.append(PackRecommendation(pack.id,pack.name,round(score,3),tuple(reasons),tuple(matched)))
    rows.sort(key=lambda r:(-r.score,r.pack_name.lower()))
    return rows[:max(1,int(limit))]


def select_pack(context: ClipContext) -> PackCreativeSelection:
    rows=recommend_packs(context,5)
    primary=rows[0]
    secondary=rows[1] if len(rows)>1 and rows[1].score >= max(1.0, primary.score*.72) else None
    mix=round(min(.35,max(.0,(secondary.score/primary.score*.30) if secondary and primary.score else 0.0)),3)
    return PackCreativeSelection(primary,secondary,mix)


def pack_assets(pack: AssetPack, limit: int = 24) -> list[CreativeAsset]:
    return pack.assets(limit=limit)


def select_assets_from_pack(context: ClipContext, kind: str | None = None, limit: int = 12) -> tuple[PackCreativeSelection,list[CreativeAsset]]:
    selection=select_pack(context)
    pack=next((p for p in builtin_packs() if p.id==selection.primary.pack_id), None)
    if not pack: return selection, []
    assets=pack.assets(limit=10000)
    if kind: assets=[a for a in assets if a.kind==kind]
    wanted=_context_tags(context)
    scored=[]
    for asset in assets:
        tags=set(asset.tags) | _tokens(asset.name) | _tokens(asset.id)
        overlap=len(wanted & tags)
        score=overlap*3 + (2 if asset.kind in pack.categories else 0)
        scored.append((score,asset))
    scored.sort(key=lambda x:(-x[0],x[1].kind,x[1].name.lower()))
    return selection,[a for _,a in scored[:max(1,int(limit))]]

__all__=["PackRecommendation","PackCreativeSelection","recommend_packs","select_pack","pack_assets","select_assets_from_pack"]
