from app.ai.reference import analyze_reference
from app.ai.director import DirectorPlan, DirectorEvent, EditEventKind
from app.subtitle.models import Transcript, Segment, Word


def make_plan():
    events = [DirectorEvent(EditEventKind.BROLL_CUE.value, 2, 3, 80, "b") for _ in range(4)]
    events += [DirectorEvent(EditEventKind.PATTERN_BREAK.value, 5, 7, 80, "p")]
    return DirectorPlan("youtube_longform", 120, 110, 10, .083, 80, events=events,
                        hook_score=82, narrative_score=77, highlight_words=["viral"]*6, chapters=[{}]*3)


def test_reference_report():
    r = analyze_reference(make_plan(), source="ref.mp4", scene_times=[10,20,40,80])
    assert r.shot_count == 5
    assert r.cut_density_per_minute == 2.0
    assert "strong_hook" in r.signals


def test_reference_without_transcript():
    r = analyze_reference(make_plan())
    assert r.transcript_word_count == 0
    assert r.words_per_minute == 0
