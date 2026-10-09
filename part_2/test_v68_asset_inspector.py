from app.effects.asset_inspector import AssetInspectorController
from app.effects.pro_asset_library import ASSETS
from app.timeline.model import Timeline, Track, Clip


def _fixture():
    tl = Timeline()
    tr = tl.tracks[0]
    asset = ASSETS[0]
    clip = Clip("media://x", "x", 0, 5, 0, creative_metadata={"asset_stack": [{
        "asset_id": asset.id, "asset_name": asset.name, "asset_kind": asset.kind,
        "intensity": 1.0, "speed": 1.0, "blend": 1.0, "duration": .5,
        "position": 0.0, "asset_variant": 0,
    }]})
    tr.clips.append(clip)
    return tl, clip, asset


def test_update_asset_recipe_is_non_destructive():
    tl, clip, asset = _fixture()
    ctl = AssetInspectorController(tl)
    r = ctl.update(clip.id, asset.id, intensity=1.4, speed=1.8, blend=.6, duration=1.2, position=.25, variation=3)
    item = clip.creative_metadata["asset_stack"][0]
    assert r.changed
    assert item["intensity"] == 1.4
    assert item["speed"] == 1.8
    assert item["blend"] == .6
    assert item["duration"] == 1.2
    assert item["position"] == .25
    assert item["asset_variant"] == 3
    assert clip.media_id == "media://x"


def test_similar_returns_visual_candidates():
    tl, clip, asset = _fixture()
    rows = AssetInspectorController(tl).similar(asset.id, 8)
    assert len(rows) == 8
    assert all(x[0].id != asset.id for x in rows)


def test_replace_preserves_editor_controls():
    tl, clip, asset = _fixture()
    other = ASSETS[1]
    ctl = AssetInspectorController(tl)
    ctl.update(clip.id, asset.id, intensity=1.3, speed=1.5, blend=.7)
    r = ctl.replace(clip.id, asset.id, other.id)
    item = clip.creative_metadata["asset_stack"][0]
    assert r.changed and item["asset_id"] == other.id
    assert item["intensity"] == 1.3
    assert item["speed"] == 1.5
    assert item["blend"] == .7


def test_invalid_clip_does_not_mutate():
    tl, _, asset = _fixture()
    r = AssetInspectorController(tl).update("missing", asset.id, intensity=2)
    assert not r.changed
