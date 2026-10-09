from app.ai.scene_context import build_scene_context, summarize_scene_context
from app.ai.semantic_asset_matcher import match_scene_assets


def test_shared_context_merges_speech_and_events():
    ctx = build_scene_context({
        "plan_events": [{"start":0,"end":3,"kind":"hook"}],
        "speech_segments": [(0.5,2.5)],
        "transcript_segments": [{"start":0.5,"end":2.5,"text":"Bu telefon gerçekten çok iyi!"}],
        "objects_by_scene": {0:["telefon"]},
        "faces_by_scene": {0: True},
    })
    assert len(ctx) == 1
    assert ctx[0]["speech"] is True
    assert "telefon" in ctx[0]["objects"]
    assert ctx[0]["faces"] is True
    assert ctx[0]["energy"] > .6


def test_summary_is_compact():
    scenes=build_scene_context({"duration":10})
    s=summarize_scene_context(scenes)
    assert s["scene_count"] == 1
    assert "scenes" in s


def test_scene_asset_matching_uses_shared_context():
    scenes=build_scene_context({
        "plan_events":[{"start":0,"end":2,"kind":"broll_cue"}],
        "speech_segments":[(0,2)],
        "transcript_segments":[{"start":0,"end":2,"text":"telefon kullanımı"}],
        "objects_by_scene":{0:["telefon"]},
    })
    matches=match_scene_assets(scenes[0], limit=5)
    assert matches
    assert any("semantic-overlap" in r for m in matches for r in m.reasons)
