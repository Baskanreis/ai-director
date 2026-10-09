"""Shared typography catalog for AI Director's short-form caption engine."""
from __future__ import annotations
from dataclasses import dataclass
from .style import Animation, SubtitleStyle, get_preset, PRESETS

@dataclass(frozen=True)
class TypographyPreset:
    id: str
    name: str
    style_key: str
    tags: tuple[str, ...]
    description: str

TYPOGRAPHY_PRESETS = [
    TypographyPreset("viral_bold", "Viral Bold", "bold_hook", ("hook","viral","shorts"), "Büyük, yüksek kontrastlı hook/caption."),
    TypographyPreset("kinetic_bounce", "Kinetic Bounce", "kinetic_bounce", ("viral","fun","word"), "Kelime vurgulu bounce animasyonu."),
    TypographyPreset("glitch", "Glitch", "glitch_caption", ("gaming","tech","impact"), "Kısa glitch hareketi ve vurgu."),
    TypographyPreset("neon", "Neon Pulse", "neon_pulse", ("music","gaming","night"), "Neon renk ve pulse hareketi."),
    TypographyPreset("typewriter", "Typewriter", "typewriter", ("story","documentary","minimal"), "Sade anlatım için daktilo görünümü."),
    TypographyPreset("marker", "Highlight Sweep", "highlight_sweep", ("education","explainer","caption"), "Önemli kelimelerde marker/sweep hissi."),
    TypographyPreset("clean", "Clean Modern", "modern_bold", ("podcast","clean","creator"), "Okunabilir günlük creator altyazısı."),
    TypographyPreset("minimal", "Minimal", "classic", ("minimal","cinematic"), "Düşük dikkat dağıtımıyla sade altyazı."),
]

def list_typography() -> list[TypographyPreset]:
    return list(TYPOGRAPHY_PRESETS)

def get_typography(key: str) -> SubtitleStyle:
    item = next((x for x in TYPOGRAPHY_PRESETS if x.id == key or x.style_key == key), None)
    if item is None:
        raise KeyError(f"Bilinmeyen typography preset: {key}")
    return get_preset(item.style_key)

def search_typography(query: str, limit: int = 20) -> list[TypographyPreset]:
    tokens = [x.lower() for x in query.replace(",", " ").split() if x.strip()]
    ranked=[]
    for item in TYPOGRAPHY_PRESETS:
        hay=" ".join((item.id,item.name,item.description,*item.tags)).lower()
        score=sum(2 if t in item.name.lower() else 1 for t in tokens if t in hay)
        if score: ranked.append((score,item))
    return [x for _,x in sorted(ranked,key=lambda p:(-p[0],p[1].name))[:limit]]
