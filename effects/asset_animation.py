"""Creative asset keyframe animation engine — v2.70.

Asset-stack recipes remain metadata-only.  Keyframes are stored inside the asset
recipe and evaluated deterministically, so no media is duplicated or rendered
until export.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from app.motion.engine import add_or_update_keyframe, sample
from app.timeline.model import Keyframe

ANIMATABLE_ASSET_PROPS = ("intensity", "speed", "blend", "position", "duration")
LIMITS = {
    "intensity": (0.0, 2.0),
    "speed": (0.05, 8.0),
    "blend": (0.0, 1.0),
    "position": (0.0, 1.0),
    "duration": (0.04, 60.0),
}

@dataclass(frozen=True)
class AssetKeyframeResult:
    changed: bool
    asset_id: str
    property: str
    reason: str


def _clamp(prop: str, value: float) -> float:
    lo, hi = LIMITS[prop]
    return max(lo, min(hi, float(value)))


def _stack_item(clip: Any, asset_id: str, index: int = 0):
    stack = list(clip.creative_metadata.get("asset_stack", []))
    matches = [(i, x) for i, x in enumerate(stack) if x.get("asset_id") == asset_id]
    if not matches:
        return None
    i, item = matches[min(max(index, 0), len(matches) - 1)]
    return i, item


def add_asset_keyframe(clip: Any, asset_id: str, prop: str, time: float, value: float,
                       *, easing: str = "linear", bezier=None, index: int = 0) -> AssetKeyframeResult:
    if prop not in ANIMATABLE_ASSET_PROPS:
        return AssetKeyframeResult(False, asset_id, prop, "unsupported_property")
    found = _stack_item(clip, asset_id, index)
    if not found:
        return AssetKeyframeResult(False, asset_id, prop, "asset_stack_item_not_found")
    _, item = found
    kfs = list(item.get("keyframes", {}).get(prop, []))
    old = deepcopy(kfs)
    kfs = add_or_update_keyframe(kfs, max(0.0, float(time)), _clamp(prop, value), easing, bezier)
    item.setdefault("keyframes", {})[prop] = kfs
    return AssetKeyframeResult(kfs != old, asset_id, prop, "asset_keyframe_added")


def remove_asset_keyframe(clip: Any, asset_id: str, prop: str, time: float, *, index: int = 0) -> AssetKeyframeResult:
    if prop not in ANIMATABLE_ASSET_PROPS:
        return AssetKeyframeResult(False, asset_id, prop, "unsupported_property")
    found = _stack_item(clip, asset_id, index)
    if not found:
        return AssetKeyframeResult(False, asset_id, prop, "asset_stack_item_not_found")
    _, item = found
    kfs = list(item.get("keyframes", {}).get(prop, []))
    new = [k for k in kfs if abs(k.time - float(time)) > 1e-3]
    if new:
        item.setdefault("keyframes", {})[prop] = new
    else:
        item.setdefault("keyframes", {}).pop(prop, None)
    return AssetKeyframeResult(new != kfs, asset_id, prop, "asset_keyframe_removed")


def evaluate_asset_property(item: dict[str, Any], prop: str, time: float) -> float:
    if prop not in ANIMATABLE_ASSET_PROPS:
        raise ValueError(f"Unsupported asset animation property: {prop}")
    default = float(item.get(prop, 1.0 if prop in ("speed", "blend") else 0.0))
    raw = item.get("keyframes", {}).get(prop, [])
    kfs = [k if isinstance(k, Keyframe) else Keyframe.from_dict(k) for k in raw]
    return _clamp(prop, sample(kfs, float(time), default))


def evaluate_asset_stack_item(item: dict[str, Any], time: float) -> dict[str, Any]:
    out = deepcopy(item)
    for prop in ANIMATABLE_ASSET_PROPS:
        if prop in item or prop in item.get("keyframes", {}):
            out[prop] = evaluate_asset_property(item, prop, time)
    return out


def snapshot_asset_animation(item: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(item.get("keyframes", {}))

__all__ = [
    "ANIMATABLE_ASSET_PROPS", "AssetKeyframeResult", "add_asset_keyframe",
    "remove_asset_keyframe", "evaluate_asset_property", "evaluate_asset_stack_item",
    "snapshot_asset_animation",
]
