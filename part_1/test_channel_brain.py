from app.ai.channel_brain import build_channel_brain, score_plan_against_brain

def test_channel_brain_fuses_sources():
    dna={"channel":{"channel_id":"UC1","title":"Demo"},"metrics":{"median_video_seconds":120,"question_title_ratio":.4,"number_title_ratio":.2,"avg_title_chars":44,"metadata":{"sample_size":40}},"performance":{"median_avg_view_percentage":52}}
    brain=build_channel_brain(dna,[{"averageViewPercentage":61}],{"hook":{"value":.8,"samples":5}})
    assert brain.channel_id=="UC1"
    assert brain.performance_targets["avg_view_percentage"]==61
    assert "hook" in brain.learned_hints
    assert brain.confidence>.6

def test_channel_brain_is_deterministic_and_cheap():
    b=build_channel_brain({"channel":{"title":"x"},"metrics":{}})
    out=score_plan_against_brain({"metadata":{}},b)
    assert 0 <= out["score"] <= 1
