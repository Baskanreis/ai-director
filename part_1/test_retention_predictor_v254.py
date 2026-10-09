from app.ai.retention_predictor import predict_retention


def test_predictor_is_conservative_without_analytics():
    r = predict_retention({"source_duration": 180, "events": []})
    assert 0 <= r.score <= 100
    assert r.confidence < .5
    assert "weak_or_missing_hook" in r.warnings


def test_owned_analytics_increases_evidence_not_certainty():
    plan={"source_duration":120,"events":[{"kind":"hook","start":0,"end":3}],"metadata":{"cut_density_per_minute":24}}
    r=predict_retention(plan, channel_brain={"confidence":.8,"style_targets":{"cut_density_per_minute":25}}, analytics=[{"avg_view_percentage":62}]*5)
    assert "owned_analytics_baseline" in r.evidence
    assert r.confidence > .5
    assert r.risk in {"low","medium","high"}


def test_hotspot_is_actionable():
    r=predict_retention({"source_duration":200,"events":[]})
    assert r.hotspots
    assert r.hotspots[0]["start"] == 0.0
