from app.ai.models import AnalysisReport
from app.ai.autonomous_director import Platform
from app.ai.professional_director import build_professional_edit_plan, realize_timeline
from app.ai.models import Suggestion, SuggestionKind
from app.subtitle.models import Transcript, Segment


def test_v220_realizes_safe_cuts_into_linked_timeline():
    transcript = Transcript("tr", [
        Segment("İlk bölüm.", 0.0, 2.0),
        Segment("Sonraki bölüm.", 3.0, 8.0),
    ])
    report = AnalysisReport("clip", "demo.mp4", [
        Suggestion(SuggestionKind.FILLER_WORD, 2.0, 3.0, 0.99, True),
    ])
    plan = build_professional_edit_plan(report, transcript, Platform.YOUTUBE)
    timeline, result = realize_timeline(plan, "media-1", "demo.mp4")
    video = timeline.track("V1")
    audio = timeline.track("A1")
    assert len(video.clips) == 2
    assert len(audio.clips) == 2
    assert video.clips[0].link_id == audio.clips[0].link_id
    assert result.applied_cut_seconds == 1.0
    assert round(timeline.duration, 3) == 7.0
    assert timeline.ai_director["non_destructive"] is True
