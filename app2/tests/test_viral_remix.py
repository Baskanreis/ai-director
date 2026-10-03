from app.ai.viral_remix import HighlightSelection, build_remix_plan, realize_remix


def test_two_liked_moments_are_harmonized():
    picks = [
        HighlightSelection(120.0, 135.0, preference=1.0, text="güçlü ilk an"),
        HighlightSelection(820.0, 830.0, preference=0.95, text="sonunda sonuç ortaya çıktı"),
    ]
    plan = build_remix_plan(picks, target="youtube_shorts", target_duration=30)
    assert len(plan.segments) == 2
    assert plan.segments[0].source_start == 120.0
    assert plan.segments[1].source_start == 820.0
    assert plan.segments[0].role == "hook"
    assert plan.segments[1].role == "payoff"
    assert plan.target_duration == 25.0


def test_remix_realizes_without_modifying_source_ranges():
    picks = [HighlightSelection(10, 25), HighlightSelection(100, 110)]
    plan = build_remix_plan(picks, target_duration=30)
    tl = realize_remix(plan, "video-1")
    clips = tl.first_track("video").clips
    assert [(c.source_in, c.source_out) for c in clips] == [(10, 25), (100, 110)]
    assert clips[1].start == 15.0
    assert tl.ai_director["version"] == "2.22"
