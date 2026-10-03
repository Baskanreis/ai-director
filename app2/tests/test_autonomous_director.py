from app.ai.autonomous_director import Platform, build_autonomous_plan
from app.ai.models import AnalysisReport, Suggestion, SuggestionKind
from app.subtitle.models import Segment, Transcript, Word


def _sample():
    words = [
        Word("Bugün", 0, .3), Word("inanılmaz", .3, .8), Word("bir", .8, 1.0),
        Word("video", 1.0, 1.5), Word("yapıyoruz", 1.5, 2.2),
        Word("şey", 3.0, 3.4), Word("şey", 3.4, 3.8),
    ]
    return Transcript("tr", [
        Segment("Bugün inanılmaz bir video yapıyoruz", 0, 2.2, words[:5]),
        Segment("şey şey", 3.0, 3.8, words[5:]),
    ])


def test_autonomous_plan_is_reviewable_and_serializable():
    transcript = _sample()
    report = AnalysisReport("c1", "video.mp4", [
        Suggestion(SuggestionKind.FILLER_WORD, 3.0, 3.4, "Dolgu"),
        Suggestion(SuggestionKind.REPETITION, 3.4, 3.8, "Tekrar"),
    ])
    plan = build_autonomous_plan(report, transcript, Platform.YOUTUBE)
    assert plan.platform == "youtube"
    assert plan.aspect_ratio == "16:9"
    assert plan.director.source_duration > 0
    assert isinstance(plan.to_json(), str)
    assert plan.quality_gates


def test_short_platform_selects_vertical_profile():
    plan = build_autonomous_plan(AnalysisReport("c1", "x.mp4", []), _sample(), Platform.TIKTOK)
    assert plan.aspect_ratio == "9:16"
    assert plan.metadata["version"] == "2.18"
