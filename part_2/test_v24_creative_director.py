from app.ai.director import DirectorEvent, DirectorPlan, EditEventKind, EditProfile
from app.ai.effects_director import build_creative_pass_plan


def _plan():
    return DirectorPlan(
        profile=EditProfile.SHORTS.value, source_duration=90, estimated_final_duration=75,
        cut_seconds=15, cut_ratio=.16, pacing_score=92,
        events=[
            DirectorEvent(EditEventKind.HOOK.value, 2, 4, 92, "hook"),
            DirectorEvent(EditEventKind.PATTERN_BREAK.value, 22, 25, 80, "break"),
            DirectorEvent(EditEventKind.BROLL_CUE.value, 40, 44, 86, "broll"),
            DirectorEvent(EditEventKind.BEAT.value, 60, 61, 82, "beat"),
        ],
    )


def test_creative_pass_maps_events_to_library_assets():
    p = build_creative_pass_plan(_plan())
    assert p.music_asset == "music_hype"
    assert len(p.decisions) >= 8
    assert any(d.kind == "text" and "bold_hook" in d.asset_id for d in p.decisions)
    assert any(d.kind == "transition" for d in p.decisions)
    assert p.metadata["non_destructive"] is True


def test_creative_pass_reports_library_sizes():
    p = build_creative_pass_plan(_plan())
    assert p.metadata["effect_count"] >= 20
    assert p.metadata["animation_count"] >= 20
    assert p.metadata["asset_count"] >= 50
