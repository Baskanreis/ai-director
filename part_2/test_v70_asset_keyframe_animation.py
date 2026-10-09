from app.effects.asset_animation import add_asset_keyframe, evaluate_asset_property
from app.effects.pro_asset_library import ASSETS
from app.timeline.model import Clip


def _clip():
    a = ASSETS[0]
    return Clip("media://x", "x", 0, 5, 0, creative_metadata={"asset_stack": [{
        "asset_id": a.id, "intensity": 1.0, "speed": 1.0, "blend": 1.0,
        "duration": .5, "position": 0.0,
    }]})


def test_asset_keyframe_roundtrip_and_interpolation():
    c = _clip(); aid = ASSETS[0].id
    assert add_asset_keyframe(c, aid, "intensity", 0, 1.0).changed
    assert add_asset_keyframe(c, aid, "intensity", 2, 1.5).changed
    item = c.creative_metadata["asset_stack"][0]
    assert evaluate_asset_property(item, "intensity", 0) == 1.0
    assert 1.0 < evaluate_asset_property(item, "intensity", 1) < 1.5


def test_asset_keyframe_clamps_and_rejects_unknown_property():
    c = _clip(); aid = ASSETS[0].id
    add_asset_keyframe(c, aid, "blend", 0, 5)
    item = c.creative_metadata["asset_stack"][0]
    assert evaluate_asset_property(item, "blend", 0) == 1.0
    assert not add_asset_keyframe(c, aid, "unknown", 0, 1).changed
