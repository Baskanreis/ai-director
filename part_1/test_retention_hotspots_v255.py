from app.ai.retention_hotspots import RetentionHotspot, normalize_hotspots, targeted_revision_request

def test_hotspots_merge_and_clamp():
    hs = normalize_hotspots([
        {"start": 0, "end": 10, "reason": "hook_risk", "confidence": .4},
        {"start": 9.9, "end": 20, "reason": "hook_risk", "severity": "high"},
        {"start": 50, "end": 70, "reason": "pacing_risk"},
    ], duration=60)
    assert len(hs) == 2
    assert hs[0].start == 0 and hs[0].end == 20 and hs[0].severity == "high"
    assert hs[1].end == 60

def test_targeted_revision_is_scoped_and_non_destructive():
    req = targeted_revision_request(RetentionHotspot(10, 20, "visual_variety_risk", "high", .8))
    assert req["scope"] == {"start": 10, "end": 20}
    assert req["non_destructive"] is True
    assert "add_broll_or_reframe" in req["actions"]
