"""Professional, parameterized creative toolkit.

This is an original, FFmpeg-friendly toolkit inspired by common NLE workflows.
It deliberately does not bundle proprietary CapCut/Premiere assets, presets or
fonts. Users can add licensed packs through the same schema.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Literal

Kind = Literal["effect", "transition", "motion", "text", "sfx", "music", "audio_fx"]

@dataclass(frozen=True)
class CreativeAsset:
    id: str
    name: str
    kind: Kind
    tags: tuple[str, ...]
    params: dict
    license: str = "AI Director Original / user-importable"

ASSETS = [
    CreativeAsset("effect.cinematic", "Cinematic Grade", "effect", ("cinematic","film","story"), {"preset":"cinematic"}),
    CreativeAsset("effect.vivid", "Vivid Social", "effect", ("social","bright","vivid"), {"preset":"social_vivid"}),
    CreativeAsset("effect.noir", "Noir", "effect", ("dark","dramatic","noir"), {"preset":"noir"}),
    CreativeAsset("effect.skin_soft", "Skin Soft", "effect", ("portrait","skin","talking_head"), {"preset":"skin_soft"}),
    CreativeAsset("effect.shorts_energy", "Shorts Energy", "effect", ("shorts","viral","energy"), {"preset":"shorts_energy"}),
    CreativeAsset("transition.crossfade", "Cross Dissolve", "transition", ("clean","cinematic","soft"), {"kind":"crossfade","duration":0.35}),
    CreativeAsset("transition.fade_black", "Fade Through Black", "transition", ("cinematic","dramatic"), {"kind":"fade_black","duration":0.25}),
    CreativeAsset("transition.flash", "Flash Cut", "transition", ("energy","beat","shorts"), {"kind":"flash","duration":0.10}),
    CreativeAsset("transition.zoom", "Zoom Cut", "transition", ("social","energy","punch"), {"kind":"zoom","duration":0.18}),
    CreativeAsset("motion.punch_in", "Punch In", "motion", ("emphasis","speaker","hook"), {"scale_from":1.0,"scale_to":1.055,"duration":0.45}),
    CreativeAsset("motion.punch_out", "Punch Out", "motion", ("reveal","emphasis"), {"scale_from":1.055,"scale_to":1.0,"duration":0.45}),
    CreativeAsset("motion.ken_burns", "Ken Burns", "motion", ("photo","story","cinematic"), {"scale_from":1.0,"scale_to":1.035,"duration":3.0}),
    CreativeAsset("motion.shake_light", "Micro Shake", "motion", ("impact","music","shorts"), {"amplitude":2.0,"duration":0.16}),
    CreativeAsset("text.clean_caption", "Clean Captions", "text", ("caption","subtitle","clean"), {"font_family":"system","weight":700,"size":46,"animation":"word_pop"}),
    CreativeAsset("text.bold_hook", "Bold Hook", "text", ("hook","shorts","social"), {"font_family":"system","weight":900,"size":58,"animation":"word_pop"}),
    CreativeAsset("text.kinetic", "Kinetic Type", "text", ("music","lyrics","energetic"), {"font_family":"system","weight":800,"size":52,"animation":"kinetic"}),
    CreativeAsset("text.minimal_title", "Minimal Title", "text", ("title","cinematic","documentary"), {"font_family":"system","weight":600,"size":54,"animation":"fade_up"}),
    CreativeAsset("audio_fx.voice_clean", "Voice Clean", "audio_fx", ("voice","podcast","dialogue"), {"denoise":10,"compressor":True,"limiter":True,"voice_enhance":True}),
    CreativeAsset("audio_fx.duck_music", "Auto Duck Music", "audio_fx", ("dialogue","music","mix"), {"duck_db":-10,"attack":0.08,"release":0.35}),
    CreativeAsset("audio_fx.punch_sfx", "Impact Accent", "sfx", ("impact","hit","shorts"), {"generator":"impact"}),
    CreativeAsset("audio_fx.whoosh", "Whoosh Accent", "sfx", ("transition","motion","swipe"), {"generator":"whoosh"}),
    CreativeAsset("audio_fx.rise", "Riser Accent", "sfx", ("build","hook","transition"), {"generator":"riser"}),
]


def catalog(kind: str | None = None) -> list[CreativeAsset]:
    return [a for a in ASSETS if kind is None or a.kind == kind]


def search(query: str, kind: str | None = None, limit: int = 20) -> list[CreativeAsset]:
    tokens = {x.strip().lower() for x in query.replace(",", " ").split() if x.strip()}
    scored = []
    for asset in catalog(kind):
        hay = {asset.id.lower(), asset.name.lower(), *asset.tags}
        score = sum(2 if t in asset.name.lower() else 1 for t in tokens if any(t in h for h in hay))
        if score:
            scored.append((score, asset))
    return [a for _, a in sorted(scored, key=lambda x: (-x[0], x[1].name))[:limit]]


def manifest() -> list[dict]:
    return [asdict(a) for a in ASSETS]
