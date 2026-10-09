"""AI Director Asset Marketplace / Pack Engine.

The marketplace is intentionally metadata-first: built-in packs reference the
original, renderable CreativeAsset recipes already shipped with AI Director.
Optional user packs can be imported as JSON through the application UI; no
external runtime or separate installer is required.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .pro_asset_library import ASSETS, CreativeAsset, catalog, search_library
from .library_manager import load_pack, save_pack


@dataclass(frozen=True)
class AssetPack:
    id: str
    name: str
    description: str
    categories: tuple[str, ...]
    query: str = ""
    tags: tuple[str, ...] = ()
    asset_ids: tuple[str, ...] = ()
    tier: str = "included"
    version: str = "1.0"

    def assets(self, limit: int | None = None) -> list[CreativeAsset]:
        """Resolve the pack against the current catalog without copying assets."""
        by_id = {a.id: a for a in ASSETS}
        out: list[CreativeAsset] = []
        for aid in self.asset_ids:
            if aid in by_id:
                out.append(by_id[aid])
        if self.query or self.tags:
            candidates = search_library(self.query, tags=self.tags, limit=10000)
            seen = {a.id for a in out}
            for asset in candidates:
                if self.categories and asset.kind not in self.categories:
                    continue
                if asset.id not in seen:
                    out.append(asset)
                    seen.add(asset.id)
        if self.categories:
            out = [a for a in out if a.kind in self.categories]
        return out[:limit] if limit else out

    def count(self) -> int:
        return len(self.assets())


# Curated, original recipes. No third-party/proprietary media is embedded.
BUILTIN_PACKS: tuple[AssetPack, ...] = (
    AssetPack("pack.creator-core", "Creator Core",
              "Günlük YouTube/Shorts kurgu için temel efekt, motion, caption ve audio zincirleri.",
              ("effect","motion","text","audio_fx","sfx","transition"),
              tags=("creator","shorts","social")),
    AssetPack("pack.cinematic-studio", "Cinematic Studio",
              "Film, documentary, travel ve storytelling görünümü için sinematik reçeteler.",
              ("effect","transition","motion","overlay","filter","music"),
              tags=("cinematic","film","story","documentary")),
    AssetPack("pack.viral-shorts", "Viral Shorts",
              "Hızlı hook, impact, caption, sticker ve beat tabanlı kısa video paketi.",
              ("effect","transition","motion","text","sticker","sfx"),
              tags=("viral","shorts","hook","impact","energy")),
    AssetPack("pack.gaming", "Gaming & Glitch",
              "Gaming, RGB, glitch, neon ve yüksek enerjili edit paketi.",
              ("effect","transition","motion","overlay","text","sfx"),
              tags=("gaming","glitch","rgb","neon","tech")),
    AssetPack("pack.podcast", "Podcast & Talking Head",
              "Konuşma videoları, podcast, lower-third ve temiz ses zincirleri.",
              ("text","motion","effect","audio_fx","sfx","template"),
              tags=("podcast","talking_head","voice","dialogue","creator")),
    AssetPack("pack.beauty-fashion", "Beauty & Fashion",
              "Beauty, fashion, portrait, skin ve editorial görünüm paketi.",
              ("effect","filter","motion","text","overlay","template"),
              tags=("beauty","fashion","portrait","skin","editorial")),
    AssetPack("pack.travel-broll", "Travel B-Roll",
              "Seyahat ve B-roll kurguları için shot/motion/transition/template reçeteleri.",
              ("motion","transition","effect","overlay","template","music"),
              tags=("travel","broll","cinematic","vlog","lifestyle")),
    AssetPack("pack.education", "Education & Tutorial",
              "Eğitim, tutorial, explainer, marker/sticker ve subtitle odaklı paket.",
              ("text","sticker","motion","effect","template","audio_fx"),
              tags=("education","tutorial","explainer","caption")),
    AssetPack("pack.meme-social", "Meme & Social",
              "Meme, reaction, comedy ve sosyal medya için hızlı görsel/ses araçları.",
              ("text","sticker","sfx","effect","transition","template"),
              tags=("meme","reaction","comedy","social","fun")),
    AssetPack("pack.subtitle-studio", "Subtitle Studio",
              "Karaoke, word-pop, editorial, clean ve kinetic subtitle stilleri.",
              ("text",),
              tags=("caption","subtitle","karaoke","word","kinetic","lowerthird")),
    AssetPack("pack.lut-filter-lab", "LUT & Filter Lab",
              "LUT/filter benzeri renk reçeteleri; skin-safe ve sinematik varyantlar.",
              ("effect","filter","overlay"),
              tags=("lut","filter","cinematic","color","skin","film")),
    AssetPack("pack.audio-sfx", "Sound FX & Audio",
              "Whoosh, impact, riser, UI, voice enhancement ve music ducking reçeteleri.",
              ("sfx","audio_fx","music"),
              tags=("sfx","whoosh","impact","riser","voice","audio")),
)

# Stable aliases for UI/search. "B-roll", "subtitle style" and "LUT" are pack
# concepts while the underlying recipes remain compatible with the existing
# renderer's effect/motion/text/filter/template kinds.
PACK_ALIASES = {
    "b-roll": "pack.travel-broll",
    "broll": "pack.travel-broll",
    "subtitle": "pack.subtitle-studio",
    "subtitle-style": "pack.subtitle-studio",
    "lut": "pack.lut-filter-lab",
    "filter": "pack.lut-filter-lab",
    "sound-effects": "pack.audio-sfx",
}


def builtin_packs() -> list[AssetPack]:
    return list(BUILTIN_PACKS)


def get_pack(pack_id: str) -> AssetPack | None:
    pid = PACK_ALIASES.get(str(pack_id).strip().lower(), str(pack_id).strip())
    return next((p for p in BUILTIN_PACKS if p.id == pid), None)


def marketplace_search(query: str = "", category: str | None = None,
                       limit: int = 48) -> list[AssetPack]:
    """Rank packs by name, description, category and tag relevance."""
    terms = {t for t in re.split(r"[\s,;]+", query.lower()) if t}
    rows = []
    for pack in BUILTIN_PACKS:
        if category and category not in pack.categories:
            continue
        hay = " ".join((pack.id, pack.name, pack.description, *pack.categories, *pack.tags)).lower()
        score = 1 if not terms else sum((6 if t in pack.name.lower() else 3 if t in pack.tags else 1) for t in terms if t in hay)
        if score:
            rows.append((score, pack))
    rows.sort(key=lambda x: (-x[0], x[1].name.lower()))
    return [p for _, p in rows[:max(0, int(limit))]]


def manifest(pack: AssetPack) -> dict:
    return {
        "schema": "ai-director-pack/v1",
        "id": pack.id,
        "name": pack.name,
        "version": pack.version,
        "description": pack.description,
        "categories": list(pack.categories),
        "query": pack.query,
        "tags": list(pack.tags),
        "tier": pack.tier,
        "asset_count": pack.count(),
    }


def export_pack(path: str | Path, pack_id: str) -> None:
    """Export the resolved original recipes for interoperability."""
    pack = get_pack(pack_id)
    if not pack:
        raise KeyError(pack_id)
    save_pack(path, pack.assets(), name=pack.name, version=pack.version)


def import_pack(path: str | Path) -> list[CreativeAsset]:
    """Validate and load a user pack; actual media paths remain optional."""
    return load_pack(path)


def catalog_health() -> dict[str, object]:
    counts = {k: 0 for k in ("effect","transition","motion","text","sfx","music","audio_fx","overlay","filter","sticker","template")}
    for asset in ASSETS:
        counts[asset.kind] = counts.get(asset.kind, 0) + 1
    return {
        "assets": len(ASSETS),
        "packs": len(BUILTIN_PACKS),
        "categories": counts,
        "single_setup": True,
        "external_runtime_required": False,
    }


__all__ = [
    "AssetPack", "BUILTIN_PACKS", "builtin_packs", "get_pack",
    "marketplace_search", "manifest", "export_pack", "import_pack",
    "catalog_health",
]
