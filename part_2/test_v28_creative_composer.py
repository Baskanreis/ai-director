from app.ai.creative_composer import compose_creative_edit
from app.ai.director import DirectorPlan, DirectorEvent, EditEventKind

def test_composer_builds_beat_aware_plan():
    p=DirectorPlan(profile="shorts", source_duration=10, estimated_final_duration=3, cut_seconds=3, cut_ratio=.3, pacing_score=80, events=[
        DirectorEvent(kind=EditEventKind.HOOK.value,start=0.47,end=1.4,score=92,reason="hook"),
        DirectorEvent(kind=EditEventKind.PATTERN_BREAK.value,start=2.1,end=2.7,score=84,reason="break"),
    ])
    c=compose_creative_edit(p,bpm=120,speech_segments=[(0.2,1.0)])
    assert c.cues
    assert c.duck_segments
    assert c.metadata["beat_quantized"] is True
    assert c.quality["cue_count"] == len(c.cues)

def test_composer_is_deterministic():
    p=DirectorPlan(profile="shorts", source_duration=10, estimated_final_duration=3, cut_seconds=3, cut_ratio=.3, pacing_score=80, events=[DirectorEvent(kind=EditEventKind.HOOK.value,start=1,end=2,score=90,reason="hook")])
    a=compose_creative_edit(p).to_dict(); b=compose_creative_edit(p).to_dict()
    assert a==b
