"""Creative Library Studio orchestration helpers.

Keeps UI state separate from timeline mutation so the same logic powers GUI and
AI agents. Original/licensed metadata only; no proprietary media is bundled.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
from app.effects.pro_asset_library import CreativeAsset, catalog, search
from app.ai.creative_studio_ai import ClipContext, PreviewPlan, rank_for_clip, build_preview_plan, generate_variations

@dataclass(frozen=True)
class PreviewSpec:
    asset_id: str
    kind: str
    duration: float
    params: dict[str, Any]
    mode: str = "metadata"

@dataclass(frozen=True)
class ApplyItem:
    asset_id: str
    clip_id: str
    start: float
    duration: float
    intensity: float = 1.0

@dataclass
class ApplyStack:
    items: list[ApplyItem]
    blend: str = "stack"
    label: str = "Creative Library Stack"

    def to_dict(self):
        return asdict(self)

def preview_spec(asset: CreativeAsset) -> PreviewSpec:
    duration = float(asset.params.get("duration", asset.params.get("length", 0.8)))
    return PreviewSpec(asset.id, asset.kind, max(.08, min(8.0, duration)), dict(asset.params))

def recommend(query: str, *, kind: str | None = None, limit: int = 3,
              preferred_tags: tuple[str, ...] = ()) -> list[CreativeAsset]:
    """Return diverse top recommendations rather than three near-duplicates."""
    candidates = search(query, kind, limit=100)
    if not candidates:
        candidates = catalog(kind)[:100]
    scored = []
    q = {x.lower() for x in query.replace(',', ' ').split() if x.strip()}
    pref = {x.lower() for x in preferred_tags}
    for a in candidates:
        hay = (a.name + ' ' + a.id + ' ' + ' '.join(a.tags)).lower()
        score = sum(4 if x in a.name.lower() else 2 for x in q if x in hay)
        score += sum(3 for x in pref if x in hay)
        scored.append((score, a))
    scored.sort(key=lambda x: (-x[0], x[1].name))
    chosen=[]; seen_kinds=set()
    for _, a in scored:
        if len(chosen) >= limit: break
        if a.kind not in seen_kinds or len(scored) <= limit:
            chosen.append(a); seen_kinds.add(a.kind)
    return chosen

__all__=["PreviewSpec","ApplyItem","ApplyStack","preview_spec","recommend","ClipContext","PreviewPlan","rank_for_clip","build_preview_plan","generate_variations"]
