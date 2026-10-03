from app.ai.smart_reframe import SubjectBox, plan_smart_reframe
from app.shorts.caption_animation import CaptionAnimationCue, build_caption_animation
from app.export.platform_variants import get_platform_variant

class C:
    start=0; end=1; emphasis=("harika",); position="lower_safe"

def test_reframe_tracks_subject():
    p=plan_smart_reframe([SubjectBox(0,5,.75,.4,.15,.3,1)],0,5)
    assert p.aspect_ratio=="9:16"
    assert p.keyframes[0].center_x > .5

def test_caption_animation_has_pop_for_emphasis():
    p=build_caption_animation([C()])
    assert p[0].animation=="pop"

def test_platform_matrix():
    p=get_platform_variant("tiktok")
    assert (p.width,p.height)==(1080,1920)
