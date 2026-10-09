"""Asset Browser -> Timeline bridge.

Keeps Asset Browser actions as first-class, non-destructive timeline commands.
Procedural assets are stored as ``asset://...`` references plus creative metadata;
renderers can resolve those references later without copying 50K media files.
"""
from __future__ import annotations
from dataclasses import dataclass
from copy import deepcopy
from app.effects.pro_asset_library import ASSETS, CreativeAsset
from app.timeline.model import Timeline, Clip, Transition, new_id, MIN_CLIP
from app.pro.editor_engine import ProfessionalEditEngine, EditResult


@dataclass(frozen=True)
class AssetAction:
    action: str
    asset_id: str
    target_clip_id: str | None = None
    target_track_id: str | None = None
    at: float | None = None
    variant: int = 0


def resolve_asset(asset: CreativeAsset | str) -> CreativeAsset | None:
    if isinstance(asset, CreativeAsset):
        return asset
    return next((a for a in ASSETS if a.id == asset), None)


def _asset_meta(asset: CreativeAsset, action: str, variant: int = 0) -> dict:
    return {
        "asset_id": asset.id,
        "asset_name": asset.name,
        "asset_kind": asset.kind,
        "asset_action": action,
        "asset_variant": int(variant),
        "asset_recipe": deepcopy(asset.params),
        "asset_tags": list(asset.tags),
        "asset_license": asset.license,
    }


class AssetTimelineBridge:
    """Applies browser actions to a Timeline without making destructive edits."""
    def __init__(self, timeline: Timeline):
        self.timeline = timeline
        self.engine = ProfessionalEditEngine(timeline)

    def apply(self, action: AssetAction) -> EditResult:
        asset = resolve_asset(action.asset_id)
        if not asset:
            return EditResult(False, "asset_not_found")
        if action.action == "apply":
            return self._apply_to_clip(asset, action)
        if action.action == "insert":
            return self._insert_asset(asset, action)
        if action.action == "variation":
            return self._apply_variation(asset, action)
        return EditResult(False, "unsupported_asset_action")

    def _apply_to_clip(self, asset: CreativeAsset, action: AssetAction) -> EditResult:
        if not action.target_clip_id:
            return EditResult(False, "missing_target_clip")
        found = self.timeline.find(action.target_clip_id)
        if not found:
            return EditResult(False, "target_clip_not_found")
        track, clip = found
        meta = _asset_meta(asset, "apply", action.variant)
        if asset.kind in {"effect", "filter", "overlay"}:
            stack = list(clip.creative_metadata.get("asset_stack", []))
            stack.append(meta)
            clip.creative_metadata["asset_stack"] = stack
            return EditResult(True, "apply_asset", (clip.id,))
        if asset.kind in {"motion", "transition"}:
            stack = list(clip.creative_metadata.get("asset_stack", []))
            stack.append(meta)
            clip.creative_metadata["asset_stack"] = stack
            if asset.kind == "transition":
                recipe = asset.params
                clip.transition_in = Transition(
                    kind=str(recipe.get("kind", recipe.get("animation", asset.id))),
                    duration=max(0.0, float(recipe.get("duration", 0.25))),
                )
            return EditResult(True, "apply_asset", (clip.id,))
        if asset.kind in {"text", "subtitle"}:
            cue = {"asset_ref": f"asset://{asset.id}", **meta}
            clip.creative_text_cues.append(cue)
            return EditResult(True, "apply_text_asset", (clip.id,))
        if asset.kind in {"audio_fx", "sfx", "music"}:
            # Audio assets are intentionally represented as a non-destructive cue on
            # the selected clip; the audio resolver can materialize/generated-render it.
            cues = list(clip.creative_metadata.get("audio_asset_cues", []))
            cues.append({"asset_ref": f"asset://{asset.id}", **meta})
            clip.creative_metadata["audio_asset_cues"] = cues
            return EditResult(True, "apply_audio_asset", (clip.id,))
        return EditResult(False, "asset_kind_not_applicable")

    def _insert_asset(self, asset: CreativeAsset, action: AssetAction) -> EditResult:
        if action.at is None:
            return EditResult(False, "missing_insert_time")
        track_id = action.target_track_id
        if not track_id:
            track_id = "A1" if asset.kind in {"audio_fx", "sfx", "music"} else "V1"
        try:
            track = self.timeline.track(track_id)
        except Exception:
            return EditResult(False, "target_track_not_found")
        duration = float(asset.params.get("duration", 0.5))
        duration = max(MIN_CLIP, min(duration, 30.0))
        clip = Clip(
            media_id=f"asset://{asset.id}",
            name=asset.name,
            source_in=0.0,
            source_out=duration,
            start=max(0.0, float(action.at)),
            creative_metadata={"asset_ref": f"asset://{asset.id}", **_asset_meta(asset, "insert", action.variant)},
        )
        result = self.engine.insert(clip, track.id, clip.start, ripple=False)
        return EditResult(result.changed, "insert_asset", result.affected_ids)

    def _apply_variation(self, asset: CreativeAsset, action: AssetAction) -> EditResult:
        # Variation is intentionally recipe-level, not a new file. The renderer can
        # use the deterministic seed to alter intensity while the project stays tiny.
        if not action.target_clip_id:
            return EditResult(False, "missing_target_clip")
        found = self.timeline.find(action.target_clip_id)
        if not found:
            return EditResult(False, "target_clip_not_found")
        _, clip = found
        variant = int(action.variant)
        meta = _asset_meta(asset, "variation", variant)
        meta["variation_seed"] = f"{asset.id}:{variant}"
        meta["variation_strength"] = 1.0 + ((variant % 5) - 2) * 0.08
        stack = list(clip.creative_metadata.get("asset_stack", []))
        stack.append(meta)
        clip.creative_metadata["asset_stack"] = stack
        return EditResult(True, "asset_variation", (clip.id,))
