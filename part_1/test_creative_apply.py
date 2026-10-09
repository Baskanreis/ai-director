from app.ai.creative_apply import apply_creative_pass
from app.ai.effects_director import CreativePassPlan, CreativeDecision
from app.timeline.model import Timeline, Clip


def test_creative_pass_applies_effect_motion_transition():
    tl = Timeline()
    track = tl.first_track("video")
    clip = Clip("m1", "clip", 0, 10, 0)
    track.clips.append(clip)
    plan = CreativePassPlan("shorts", decisions=[
        CreativeDecision("effect", "effect.viral_pop", 0, 1, .8, "hook", .9),
        CreativeDecision("motion", "motion.punch_fast", 0, .5, .8, "hook", .9),
        CreativeDecision("transition", "transition.flash", 0, .2, .6, "cut", .8),
    ])
    r = apply_creative_pass(tl, plan)
    assert r.applied == 3
    assert clip.transition_in is not None
    assert clip.keyframes["scale"]
    assert clip.keyframes["effect:contrast"]


def test_creative_text_cues_roundtrip():
    tl = Timeline()
    clip = Clip("m1", "clip", 0, 5, 0)
    tl.first_track("video").clips.append(clip)
    plan = CreativePassPlan("shorts", decisions=[CreativeDecision("text", "text.bold_hook", 0, 1, .8, "hook", .9)])
    r = apply_creative_pass(tl, plan)
    assert r.text_cues == 1
    data = tl.to_dict()
    restored = Timeline.from_dict(data)
    assert restored.first_track("video").clips[0].creative_text_cues[0]["asset_id"] == "text.bold_hook"
