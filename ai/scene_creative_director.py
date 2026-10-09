"""Scene-aware creative director.

Builds a deterministic, non-destructive creative stack for every analyzed scene.
It deliberately produces plan data first; timeline mutation/rendering is a
separate step so the director can be previewed, revised and cached safely.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable

from app.ai.creative_studio_ai import ClipContext, PreviewCue, rank_for_clip
from app.effects.pro_asset_library import CreativeAsset
from app.ai.asset_marketplace_director import select_pack
from app.effects.marketplace import builtin_packs

@dataclass(frozen=True)
class SceneCreativeItem:
    scene_id: str
    clip_id: str
    asset_id: str
    kind: str
    start: float
    duration: float
    intensity: float
    score: float
    reason: str

@dataclass(frozen=True)
class SceneCreativeStack:
    scene_id: str
    clip_id: str
    start: float
    end: float
    items: tuple[SceneCreativeItem, ...]
    style: str
    variant: int = 0
    primary_pack_id: str = ""
    primary_pack_name: str = ""
    secondary_pack_id: str = ""
    pack_mix: float = 0.0

    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class SceneCreativePlan:
    stacks: tuple[SceneCreativeStack, ...]
    version: str = "scene_creative_v1"

    def to_dict(self): return asdict(self)
    @property
    def item_count(self): return sum(len(s.items) for s in self.stacks)


def _pick_diverse(ranked: list[tuple[CreativeAsset, float]], max_items: int) -> list[tuple[CreativeAsset,float]]:
    chosen=[]; kinds=set()
    # Prefer visual + text/audio combinations, but never duplicate a kind until needed.
    for asset, score in ranked:
        if asset.kind in kinds and len(chosen) < max(2, max_items-1):
            continue
        chosen.append((asset, score)); kinds.add(asset.kind)
        if len(chosen) >= max_items: break
    return chosen


def build_scene_creative_plan(contexts: Iterable[ClipContext], *, items_per_scene: int = 4,
                              variant: int = 0) -> SceneCreativePlan:
    stacks=[]
    for index, context in enumerate(contexts):
        scene_id=f"scene-{index+1:04d}"
        ranked=rank_for_clip(context, limit=24)
        pack_selection=select_pack(context)
        # Pack-first selection: prefer assets from the selected marketplace pack,
        # then fall back to the global semantic ranker for missing categories.
        pack=next((p for p in builtin_packs() if p.id==pack_selection.primary.pack_id), None)
        if pack:
            pack_assets=pack.assets(limit=10000)
            pack_ids={a.id for a in pack_assets}
            ranked=[(a,score + (8.0 if a.id in pack_ids else 0.0)) for a,score in ranked]
            ranked.sort(key=lambda x:(-x[1],x[0].kind,x[0].name.lower()))
        # Rotate the ranked list for alternate creative passes without randomness.
        if ranked and variant:
            shift=(variant + index) % len(ranked)
            ranked=ranked[shift:]+ranked[:shift]
        chosen=_pick_diverse(ranked, max(1,min(8,items_per_scene)))
        cursor=0.0
        items=[]
        for asset, score in chosen:
            duration=float(asset.params.get("duration", asset.params.get("length", .45)))
            duration=max(.08,min(float(context.duration),duration))
            start=min(cursor,max(0.0,float(context.duration)-duration))
            intensity=max(.2,min(1.0,.55+context.energy*.35))
            items.append(SceneCreativeItem(scene_id,context.clip_id,asset.id,asset.kind,round(start,3),round(duration,3),round(intensity,3),round(score,3),f"{context.style}/{context.scene_type}"))
            cursor=min(float(context.duration),cursor+max(.12,duration*.72))
        stacks.append(SceneCreativeStack(
            scene_id,context.clip_id,0.0,float(context.duration),tuple(items),context.style,variant,
            pack_selection.primary.pack_id,pack_selection.primary.pack_name,
            pack_selection.secondary.pack_id if pack_selection.secondary else "",pack_selection.mix
        ))
    return SceneCreativePlan(tuple(stacks))


def flatten_plan(plan: SceneCreativePlan) -> list[dict]:
    """Convert the scene plan into the existing Creative Stack apply schema."""
    rows=[]
    for stack in plan.stacks:
        for item in stack.items:
            rows.append({"asset_id":item.asset_id,"clip_id":item.clip_id,"start":item.start,
                         "duration":item.duration,"intensity":item.intensity,"scene_id":item.scene_id,
                         "reason":item.reason})
    return rows
