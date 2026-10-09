from app.ai.auto_timeline_director import build_auto_timeline_plan, apply_auto_timeline_plan
from app.timeline.model import Timeline


def _timeline():
    t=Timeline()
    t.add_media("m1","gaming_clip_1.mp4",4.0,False)
    t.add_media("m2","gaming_clip_2.mp4",5.0,False)
    return t


def test_auto_timeline_builds_scene_and_beats():
    t=_timeline()
    p=build_auto_timeline_plan(t,style="gaming",platform="shorts",bpm=120)
    assert len(p.scenes)==2
    assert p.scenes[0].clip_id != p.scenes[1].clip_id
    assert p.metadata["creative_item_count"] > 0
    assert p.scenes[1].transition in {"rgb_split","digital_wipe"}
    assert p.scenes[0].beat_times


def test_auto_timeline_apply_is_non_destructive_and_persistable():
    t=_timeline()
    before=[c.source_in for c in t.all_clips()]
    p=build_auto_timeline_plan(t,style="cinematic",bpm=100)
    report=apply_auto_timeline_plan(t,p)
    assert report.applied > 0
    assert before == [c.source_in for c in t.all_clips()]
    assert all(c.creative_metadata.get("scene_id") for c in t.first_track("video").clips)
    assert t.first_track("video").clips[1].transition_in is not None
    payload=t.to_dict()
    restored=Timeline.from_dict(payload)
    assert restored.first_track("video").clips[0].creative_metadata["style"]=="cinematic"


def test_auto_timeline_is_deterministic():
    a=build_auto_timeline_plan(_timeline(),style="meme",variant=1)
    b=build_auto_timeline_plan(_timeline(),style="meme",variant=1)
    assert [(s.start,s.end,s.transition) for s in a.scenes] == [(s.start,s.end,s.transition) for s in b.scenes]
    assert [[i.asset_id for i in s.items] for s in a.creative.stacks] == [[i.asset_id for i in s.items] for s in b.creative.stacks]
