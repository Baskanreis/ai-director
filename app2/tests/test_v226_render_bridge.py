from app.ai.smart_reframe import ReframeKeyframe, ReframePlan
from app.render.director_pipeline import apply_reframe_plan, apply_caption_motion_metadata
from app.timeline.model import Clip


def test_reframe_becomes_crop_keyframes():
    clip = Clip("m", "clip", 0, 10, 0)
    plan = ReframePlan("9:16", (
        ReframeKeyframe(0, .8, .5, .3164, 1.0),
        ReframeKeyframe(10, .2, .5, .3164, 1.0),
    ), "speaker_priority")
    result = apply_reframe_plan(clip, plan)
    assert "crop_x" in clip.keyframes
    assert len(clip.keyframes["crop_x"]) == 2
    assert result.kind == "reframe"


def test_caption_events_are_non_destructive():
    clip = Clip("m", "clip", 0, 5, 0)
    result = apply_caption_motion_metadata(clip, [
        {"start": 0.1, "end": .5, "text": "Merhaba", "animation": "pop"},
        {"start": .5, "end": .8, "text": "dünya", "animation": "fade"},
    ])
    assert len(clip.caption_events) == 2
    assert clip.source_in == 0 and clip.source_out == 5
    assert result.kind == "captions"
