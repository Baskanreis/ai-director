from app.ai.channel import build_channel_profile, compare_style
from app.ai.director import DirectorPlan, DirectorEvent, EditEventKind


def plan(cut=.1, hook=70, narrative=60, duration=600, broll=6, breaks=3, beats=12):
    events=[]
    for _ in range(broll): events.append(DirectorEvent(EditEventKind.BROLL_CUE.value,0,1,70,"b"))
    for _ in range(breaks): events.append(DirectorEvent(EditEventKind.PATTERN_BREAK.value,0,1,70,"p"))
    for _ in range(beats): events.append(DirectorEvent(EditEventKind.BEAT.value,0,1,70,"b"))
    return DirectorPlan("youtube_longform",duration,duration*(1-cut),duration*cut,cut,75,events=events,hook_score=hook,narrative_score=narrative,highlight_words=["x"]*6,chapters=[{}]*4)


def test_empty_profile():
    p=build_channel_profile([], "x")
    assert p.reference_count == 0
    assert p.confidence == 0


def test_profile_aggregates_rates():
    p=build_channel_profile([(plan(),None),(plan(.2,80,70),None)], "x")
    assert p.reference_count == 2
    assert .1 < p.avg_cut_ratio < .2
    assert p.avg_broll_cues_per_minute > 0
    assert "strong_hooks" in p.edit_traits


def test_profile_json():
    p=build_channel_profile([(plan(),None)], "x")
    assert '"name": "x"' in p.to_json()


def test_style_similarity_same_plan():
    p=build_channel_profile([(plan(),None)], "x")
    m=compare_style(plan(),p)
    assert m.similarity > 99
    assert not m.recommendations


def test_style_recommends_broll():
    p=build_channel_profile([(plan(broll=12),None)], "x")
    m=compare_style(plan(broll=0),p)
    assert any("B-roll" in x for x in m.recommendations)


def test_director_adapts_to_channel_profile():
    from app.ai.director import adapt_plan_to_channel
    p=build_channel_profile([(plan(cut=.2, hook=85, narrative=80, broll=12),None)], "ref")
    out=adapt_plan_to_channel(plan(cut=.05, hook=60, narrative=50, broll=0), p)
    rec=out.metadata["channel_intelligence"]["recommendations"]
    assert "increase_cut_density" in rec
    assert "strengthen_hook" in rec
    assert "add_broll_cues" in rec
