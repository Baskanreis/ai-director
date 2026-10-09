from app.ai.pro_editor import ShotAnalysis, build_pro_edit_plan

def test_pro_plan_marks_long_shots_for_review():
    p=build_pro_edit_plan('clip.mp4',12,[ShotAnalysis(0,12,visual_quality=60)],'balanced')
    assert any(x.action=='pattern_break' for x in p.beats)
    assert p.duration==12

def test_low_quality_is_flagged_not_deleted():
    p=build_pro_edit_plan('clip.mp4',3,[ShotAnalysis(0,3,visual_quality=10)])
    assert any(x.action=='review_or_trim' for x in p.beats)
    assert p.shots[0].start==0

def test_sparse_beat_accents():
    p=build_pro_edit_plan('clip.mp4',10,[ShotAnalysis(0,10)],beat_times=list(i*.25 for i in range(1,40)))
    assert len([x for x in p.beats if x.action=='beat_accent']) < 20

def test_invalid_style():
    import pytest
    with pytest.raises(ValueError): build_pro_edit_plan('x',1,[],'invalid')
