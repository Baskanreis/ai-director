"""Fast discovery helpers for the 50K asset catalog.

No second model is required. Similarity is a deterministic hybrid of semantic tags,
asset kind, style/mood/intent and normalized recipe parameters. It is designed for
instant UI search and lazy preview generation.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
from typing import Iterable
from app.effects.pro_asset_library import ASSETS, CreativeAsset, search_library, categories

CATEGORY_META = {
    "effect": ("FX", "Görsel efektler", "spark"),
    "transition": ("TR", "Geçişler", "transition"),
    "motion": ("MO", "Motion graphics", "motion"),
    "sticker": ("ST", "Sticker ve emoji", "sticker"),
    "sfx": ("SFX", "Sound effects", "sound"),
    "audio_fx": ("AF", "Audio FX", "audio"),
    "subtitle": ("CC", "Altyazı stilleri", "subtitle"),
    "text": ("TX", "Text ve typography", "text"),
    "filter": ("LT", "LUT / filtre", "color"),
    "overlay": ("OV", "Overlay", "overlay"),
    "b_roll": ("BR", "B-roll", "broll"),
    "template": ("TP", "Template", "template"),
    "music": ("MU", "Music", "music"),
}

@dataclass(frozen=True)
class DiscoveryFilters:
    kind: str | None = None
    tags: tuple[str, ...] = ()
    intent: str | None = None
    mood: str | None = None
    style: str | None = None
    license: str | None = None
    min_energy: float | None = None
    max_energy: float | None = None
    safe_only: bool = False
    favorites_only: bool = False


def category_meta(kind: str) -> tuple[str, str, str]:
    return CATEGORY_META.get(kind, (kind[:3].upper(), kind.title(), kind))


def _num(params: dict, key: str):
    value = params.get(key)
    try: return float(value)
    except (TypeError, ValueError): return None


def filter_assets(filters: DiscoveryFilters, favorites: set[str] | None = None) -> list[CreativeAsset]:
    favorites = favorites or set()
    wanted = {x.lower() for x in filters.tags}
    rows = []
    for a in ASSETS:
        p = a.params
        tags = {x.lower() for x in a.tags}
        if filters.kind and a.kind != filters.kind: continue
        if wanted and not wanted.issubset(tags): continue
        if filters.intent and str(p.get("intent", "")).lower() != filters.intent.lower(): continue
        if filters.mood and str(p.get("mood", "")).lower() != filters.mood.lower(): continue
        if filters.style and filters.style.lower() not in tags and str(p.get("style", "")).lower() != filters.style.lower(): continue
        if filters.license and a.license.lower() != filters.license.lower(): continue
        energy = _num(p, "energy")
        if filters.min_energy is not None and energy is not None and energy < filters.min_energy: continue
        if filters.max_energy is not None and energy is not None and energy > filters.max_energy: continue
        if filters.safe_only and not p.get("safe_to_auto_apply", False): continue
        if filters.favorites_only and a.id not in favorites: continue
        rows.append(a)
    return rows


def _feature_set(a: CreativeAsset) -> set[str]:
    p = a.params
    values = set(a.tags)
    values.add(a.kind)
    for key in ("intent", "mood", "style", "generator", "filter_family", "template_recipe", "music_recipe", "audio_chain"):
        value = p.get(key)
        if value is not None: values.add(str(value).lower())
    return {x.lower() for x in values}


def similar_assets(asset: CreativeAsset | str, limit: int = 20) -> list[tuple[CreativeAsset, float]]:
    if isinstance(asset, str):
        asset = next((a for a in ASSETS if a.id == asset), None)
    if asset is None: return []
    base = _feature_set(asset)
    base_energy = _num(asset.params, "energy")
    rows = []
    for other in ASSETS:
        if other.id == asset.id: continue
        other_set = _feature_set(other)
        union = len(base | other_set) or 1
        overlap = len(base & other_set) / union
        score = overlap * 0.78
        if other.kind == asset.kind: score += 0.14
        e = _num(other.params, "energy")
        if base_energy is not None and e is not None:
            score += max(0.0, 1.0 - abs(base_energy - e)) * 0.08
        rows.append((other, round(score, 5)))
    rows.sort(key=lambda x: (-x[1], x[0].name.lower()))
    return rows[:max(0, int(limit))]


def visual_query(query: str, filters: DiscoveryFilters | None = None, limit: int = 50) -> list[CreativeAsset]:
    """Natural-language discovery combining semantic search and structured filters."""
    filters = filters or DiscoveryFilters()
    candidates = search_library(query, kind=filters.kind, tags=filters.tags, limit=max(500, limit * 8))
    allowed = {a.id for a in filter_assets(filters)}
    if allowed: candidates = [a for a in candidates if a.id in allowed]
    elif any((filters.intent, filters.mood, filters.style, filters.license, filters.min_energy is not None, filters.max_energy is not None, filters.safe_only, filters.favorites_only)):
        candidates = []
    return candidates[:max(0, int(limit))]


def category_counts() -> dict[str, int]:
    return {k: sum(1 for a in ASSETS if a.kind == k) for k in categories()}


def visual_similar_assets(asset: CreativeAsset | str, limit: int = 20,
                           blend_metadata: float = 0.30) -> list[tuple[CreativeAsset, float]]:
    """Rank assets by preview/visual character, optionally blended with metadata similarity."""
    from app.effects.visual_similarity import cosine, visual_signature
    if isinstance(asset, str):
        asset = next((a for a in ASSETS if a.id == asset), None)
    if asset is None:
        return []
    target = visual_signature(asset)
    meta = {a.id: score for a, score in similar_assets(asset, max(100, limit * 4))}
    rows = []
    for other in ASSETS:
        if other.id == asset.id:
            continue
        visual_score = cosine(target, visual_signature(other))
        metadata_score = meta.get(other.id, 0.0)
        score = visual_score * (1.0 - blend_metadata) + metadata_score * blend_metadata
        rows.append((other, round(score, 5)))
    rows.sort(key=lambda x: (-x[1], x[0].name.lower()))
    return rows[:max(0, int(limit))]
