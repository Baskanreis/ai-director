from app.ai.models import AnalysisReport, Suggestion, SuggestionKind
from app.ai.professional_editor import build_professional_edit_plan, PROFILES
from app.subtitle.models import Transcript, Segment, Word


def _report():
    return AnalysisReport("c1", "x.mp4", [
        Suggestion(SuggestionKind.LONG_PAUSE, 4.0, 5.2, "uzun durak", accepted=True),
        Suggestion(SuggestionKind.FILLER_WORD, 7.0, 7.25, "eee", accepted=True),
        Suggestion(SuggestionKind.REPETITION, 9.0, 9.4, "tekrar", accepted=True),
    ])


def _transcript():
    return Transcript(language="tr", segments=[
        Segment(start=0, end=12, text="Bu bir test videosudur", words=[
            Word(start=0, end=.3, text="Bu"), Word(start=.35, end=.6, text="bir")
        ])
    ])


def test_professional_is_conservative():
    plan = build_professional_edit_plan("x.mp4", 60, _report(), _transcript())
    assert plan.estimated_duration < 60
    assert sum(e-s for s,e in plan.cut_ranges) <= 60 * PROFILES["professional"].max_cut_ratio
    assert any(a.kind == "audio_continuity" for a in plan.actions)


def test_no_transcript_warns_and_still_works():
    plan = build_professional_edit_plan("x.mp4", 60, _report(), None)
    assert plan.cut_ranges
    assert any("Transkript" in w for w in plan.warnings)


def test_effects_are_sparse():
    plan = build_professional_edit_plan("x.mp4", 30, _report(), _transcript(), beat_times=[1,2,2.1,5,9,12])
    beat = [a for a in plan.actions if a.kind == "beat_emphasis"]
    assert len(beat) <= 4
