from app.ai.director import DirectorPlan, DirectorEvent, EditEventKind
from app.ai.effects_director import build_creative_pass_plan


def _plan(style):
    return DirectorPlan(profile="shorts", source_duration=30, estimated_final_duration=28, cut_seconds=2, cut_ratio=.06,
        pacing_score=90, events=[DirectorEvent(EditEventKind.HOOK.value, 1, 2, 90, "hook")], metadata={"edit_style": style})


def test_style_changes_creative_intensity_metadata():
    meme = build_creative_pass_plan(_plan("meme"), assets=[])
    podcast = build_creative_pass_plan(_plan("podcast"), assets=[])
    assert meme.metadata["edit_style"] == "meme"
    assert podcast.metadata["edit_style"] == "podcast"
    assert meme.metadata["style_recipe"]["caption_density"] > podcast.metadata["style_recipe"]["caption_density"]
