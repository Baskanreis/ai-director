"""Non-destructive timeline creative-asset inspector.

Edits asset-stack recipes instead of materializing media.  The controller is Qt-free
so it can be tested independently and used by the UI/automation layers.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass

from app.effects.pro_asset_library import ASSETS, CreativeAsset
from app.effects.asset_discovery import visual_similar_assets
from app.timeline.model import Timeline

EDITABLE = ("intensity", "speed", "blend", "duration", "position", "variation")

@dataclass(frozen=True)
class InspectorResult:
    changed: bool
    reason: str
    clip_id: str | None = None
    asset_id: str | None = None


def _find_stack_item(clip, asset_id: str, index: int = 0):
    stack = clip.creative_metadata.get("asset_stack", [])
    matches = [(i, x) for i, x in enumerate(stack) if x.get("asset_id") == asset_id]
    if not matches:
        return None
    i, item = matches[min(max(0, index), len(matches) - 1)]
    return i, item


class AssetInspectorController:
    def __init__(self, timeline: Timeline):
        self.timeline = timeline

    def _clip(self, clip_id: str):
        found = self.timeline.find(clip_id)
        return found[1] if found else None

    def snapshot(self, clip_id: str, asset_id: str, index: int = 0) -> dict | None:
        clip = self._clip(clip_id)
        if not clip:
            return None
        found = _find_stack_item(clip, asset_id, index)
        return deepcopy(found[1]) if found else None

    def update(self, clip_id: str, asset_id: str, index: int = 0, **values) -> InspectorResult:
        clip = self._clip(clip_id)
        if not clip:
            return InspectorResult(False, "target_clip_not_found", clip_id, asset_id)
        found = _find_stack_item(clip, asset_id, index)
        if not found:
            return InspectorResult(False, "asset_stack_item_not_found", clip_id, asset_id)
        _, item = found
        before = deepcopy(item)
        for key in EDITABLE:
            if key not in values:
                continue
            value = values[key]
            if key == "variation":
                value = int(value)
                item["asset_variant"] = value
                item["variation_seed"] = f"{asset_id}:{value}"
                item["variation_strength"] = 1.0 + ((value % 5) - 2) * 0.08
            elif key == "position":
                value = max(0.0, float(value))
                item["position"] = value
            elif key == "duration":
                item["duration"] = max(0.04, min(float(value), 60.0))
            elif key == "speed":
                item["speed"] = max(0.05, min(float(value), 8.0))
            elif key == "blend":
                item["blend"] = max(0.0, min(float(value), 1.0))
            elif key == "intensity":
                item["intensity"] = max(0.0, min(float(value), 2.0))
        return InspectorResult(item != before, "update_asset_recipe", clip_id, asset_id)

    def replace(self, clip_id: str, asset_id: str, replacement_id: str, index: int = 0) -> InspectorResult:
        clip = self._clip(clip_id)
        if not clip:
            return InspectorResult(False, "target_clip_not_found", clip_id, asset_id)
        found = _find_stack_item(clip, asset_id, index)
        replacement = next((a for a in ASSETS if a.id == replacement_id), None)
        if not found or replacement is None:
            return InspectorResult(False, "replacement_not_found", clip_id, asset_id)
        _, item = found
        old = deepcopy(item)
        preserved = {k: item[k] for k in ("intensity", "speed", "blend", "duration", "position", "asset_variant") if k in item}
        item.clear()
        item.update({
            "asset_id": replacement.id,
            "asset_name": replacement.name,
            "asset_kind": replacement.kind,
            "asset_recipe": deepcopy(replacement.params),
            "asset_tags": list(replacement.tags),
            "asset_license": replacement.license,
            "asset_action": "replace",
            **preserved,
        })
        return InspectorResult(item != old, "replace_asset", clip_id, replacement.id)

    def add_keyframe(self, clip_id: str, asset_id: str, prop: str, time: float, value: float,
                     *, easing: str = "linear", bezier=None, index: int = 0):
        from app.effects.asset_animation import add_asset_keyframe
        clip = self._clip(clip_id)
        if clip is None:
            return None
        return add_asset_keyframe(clip, asset_id, prop, time, value, easing=easing, bezier=bezier, index=index)

    def evaluate_at(self, clip_id: str, asset_id: str, time: float, *, index: int = 0):
        from app.effects.asset_animation import evaluate_asset_stack_item
        clip = self._clip(clip_id)
        if clip is None:
            return None
        found = _find_stack_item(clip, asset_id, index)
        return evaluate_asset_stack_item(found[1], time) if found else None

    def similar(self, asset_id: str, limit: int = 20):
        return visual_similar_assets(asset_id, limit=limit)

    def set_transition_duration(self, clip_id: str, duration: float) -> InspectorResult:
        found = self.timeline.find(clip_id)
        if not found:
            return InspectorResult(False, "target_clip_not_found", clip_id)
        _, clip = found
        if clip.transition_in is None:
            return InspectorResult(False, "no_transition", clip_id)
        old = clip.transition_in.duration
        clip.transition_in.duration = max(0.0, min(float(duration), 10.0))
        return InspectorResult(abs(old - clip.transition_in.duration) > 1e-9, "update_transition", clip_id)
