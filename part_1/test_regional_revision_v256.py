from app.ai.retention_hotspots import RetentionHotspot
from app.ai.regional_revision import RegionalRevisionPolicy, generate_regional_candidates, revise_hotspot


def test_candidates_are_scoped_and_non_destructive():
    plan = {"timeline": [{"start": 0, "end": 20, "kind": "video"}], "metadata": {}}
    hs = RetentionHotspot(5, 10, "visual_variety_risk", "high", .9)
    original = repr(plan)
    out = generate_regional_candidates(plan, hs)
    assert out
    assert repr(plan) == original
    assert all(c.plan["metadata"]["regional_revision"]["scope"] == {"start": 5, "end": 10} for c in out)


def test_never_accepts_a_regression():
    plan = {"timeline": [], "metadata": {}}
    hs = RetentionHotspot(0, 5, "hook_risk", "high", .9)
    scores = iter([80, 79, 78, 79])
    result = revise_hotspot(plan, hs, lambda p: {"score": next(scores)}, policy=RegionalRevisionPolicy(max_candidates=3))
    assert result.best.name == "base"
    assert result.stopped_reason == "no_meaningful_regional_improvement"


def test_accepts_only_meaningful_regional_gain():
    plan = {"timeline": [], "metadata": {}}
    hs = RetentionHotspot(0, 5, "hook_risk", "high", .9)
    calls = [80, 83, 82, 81]
    result = revise_hotspot(plan, hs, lambda p: {"score": calls.pop(0)}, policy=RegionalRevisionPolicy(max_candidates=3, min_improvement=0.5))
    assert result.best.name == "r1"
    assert result.best.accepted is True
