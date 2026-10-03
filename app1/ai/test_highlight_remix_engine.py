from app.ai.highlight_remix_engine import Highlight, build_remix_variants

def test_two_non_adjacent_highlights_become_one_short():
    p = build_remix_variants([
        Highlight("a", 100, 115, 95, hook=True),
        Highlight("b", 800, 810, 92, payoff=True),
    ], 1200)
    v = p.variants[0]
    assert len(v.clips) == 2
    assert v.clips[0].role == "hook"
    assert v.clips[-1].role == "payoff"
    assert v.target_duration == 25

def test_platform_variants_are_vertical():
    p = build_remix_variants([Highlight("a",0,20,90,hook=True), Highlight("b",30,50,80,payoff=True)],100)
    assert {v.aspect_ratio for v in p.variants} == {"9:16"}
