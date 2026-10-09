from app.ai.beat_animation_director import BeatAnimationPolicy, plan_asset_animation, apply_asset_animation
from app.ai.beat_sync import BeatCue
from app.effects.pro_asset_library import ASSETS
from app.timeline.model import Clip


def _clip():
    a = ASSETS[0]
    return Clip("media://x", "x", 0, 5, 0, creative_metadata={"asset_stack": [{
        "asset_id": a.id, "intensity": 1.0, "speed": 1.0, "blend": 1.0,
        "duration": .5, "position": 0.0,
    }]})


def test_director_is_sparse_and_bounded():
    beats = [BeatCue(0,0,.9), BeatCue(.05,1,1), BeatCue(.5,2,.8), BeatCue(1,3,1)]
    cues = plan_asset_animation(beats, policy=BeatAnimationPolicy(cooldown=.2, minimum_beat_distance=.2, intensity_ceiling=1.2))
    assert len(cues) == 3
    assert all(c.peak <= 1.2 for c in cues)


def test_manual_keyframe_is_protected():
    c = _clip(); aid = ASSETS[0].id
    c.creative_metadata["asset_stack"][0]["keyframes"] = {"intensity": [{"time": .5, "value": 1.4}]}
    out = apply_asset_animation(c, aid, [BeatCue(.5, 0, 1.0)])
    assert out == []
