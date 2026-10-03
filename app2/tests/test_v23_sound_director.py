from app.ai.director import DirectorEvent, DirectorPlan, EditEventKind, EditProfile
from app.ai.effects_director import build_sound_design_plan, music_asset_path


def _plan():
    return DirectorPlan(
        profile=EditProfile.HIGH_RETENTION.value, source_duration=120, estimated_final_duration=110,
        cut_seconds=10, cut_ratio=.08, pacing_score=90,
        events=[
            DirectorEvent(EditEventKind.HOOK.value, 2, 4, 90, "hook"),
            DirectorEvent(EditEventKind.PATTERN_BREAK.value, 30, 36, 75, "break"),
            DirectorEvent(EditEventKind.BROLL_CUE.value, 50, 52, 80, "broll"),
            DirectorEvent(EditEventKind.BEAT.value, 70, 71, 78, "beat"),
        ],
    )


def test_sound_design_selects_music_and_sfx():
    p = build_sound_design_plan(_plan())
    assert p.music_asset == "music_hype"
    assert len(p.sound_decisions) >= 4
    assert any(x.asset_id == "sfx_hit" for x in p.sound_decisions)
    assert p.metadata["automatic_ducking"] is True


def test_sound_design_deduplicates_same_asset_at_same_moment():
    p = _plan()
    p.events.append(DirectorEvent(EditEventKind.HOOK.value, 2, 4, 90, "hook2"))
    out = build_sound_design_plan(p)
    hits = [x for x in out.sound_decisions if x.asset_id == "sfx_hit" and round(x.start,1)==2.0]
    assert len(hits) == 1


def test_music_path_resolves():
    p = build_sound_design_plan(_plan())
    path = music_asset_path(p)
    assert path and path.endswith("music_hype.wav")
