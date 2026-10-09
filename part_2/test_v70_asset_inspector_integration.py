from app.effects.asset_inspector import AssetInspectorController
from app.effects.pro_asset_library import ASSETS
from app.timeline.model import Clip, Timeline


def test_inspector_exposes_asset_keyframe_and_evaluate():
    a = ASSETS[0]
    tl = Timeline(); clip = Clip("media://x", "x", 0, 2, 0, creative_metadata={"asset_stack": [{
        "asset_id": a.id, "intensity": 1.0, "speed": 1.0, "blend": 1.0, "duration": .5, "position": 0.0
    }]})
    tl.tracks[0].clips.append(clip)
    ctl = AssetInspectorController(tl)
    r = ctl.add_keyframe(clip.id, a.id, "intensity", 1.0, 1.6)
    assert r.changed
    snap = ctl.evaluate_at(clip.id, a.id, 1.0)
    assert snap["intensity"] == 1.6
