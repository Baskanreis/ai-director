from app.ai.director import EditProfile, build_director_plan, apply_director_plan
from app.ai.models import AnalysisReport, Suggestion, SuggestionKind
from app.subtitle.models import Segment, Transcript, Word

def _t():
    words=[
        Word("merhaba",0,.3), Word("şey",.3,.6), Word("şey",.6,.9),
        Word("bugün",1,1.4), Word("harika",1.4,1.9),
        Word("bir",3.2,3.4), Word("video",3.4,3.9),
    ]
    return Transcript("tr",[Segment("merhaba şey şey bugün harika",0,1.9,words[:5]),
                            Segment("bir video",3.2,3.9,words[5:])])

def test_director_selects_high_confidence_cuts_and_exports_metrics():
    t=_t()
    report=AnalysisReport("c1","x.mp4",[
        Suggestion(SuggestionKind.FILLER_WORD,.3,.6,"Dolgu"),
        Suggestion(SuggestionKind.REPETITION,.6,.9,"Tekrar"),
        Suggestion(SuggestionKind.LONG_PAUSE,1.9,3.2,"Uzun"),
    ])
    plan=build_director_plan(report,t,EditProfile.HIGH_RETENTION)
    assert plan.cut_seconds > 0
    assert plan.estimated_final_duration < plan.source_duration
    assert 0 <= plan.pacing_score <= 100
    assert plan.highlight_words
    assert plan.to_dict()["profile"] == "high_retention"

def test_director_blocks_long_ambiguous_cut():
    t=_t()
    report=AnalysisReport("c1","x.mp4",[
        Suggestion(SuggestionKind.LONG_PAUSE,.9,8.0,"Uzun")
    ])
    plan=build_director_plan(report,t)
    assert plan.cut_seconds == 0
    assert plan.decisions[0].accepted is False
    assert plan.decisions[0].risk == "high"

def test_apply_director_plan_only_changes_cut_decisions():
    report=AnalysisReport("c1","x.mp4",[
        Suggestion(SuggestionKind.FILLER_WORD,0,1,"f"),
        Suggestion(SuggestionKind.HIGHLIGHT_WORD,1,2,"h",accepted=True,word="harika")
    ])
    plan=build_director_plan(report,None,EditProfile.YOUTUBE_LONGFORM)
    apply_director_plan(report,plan)
    assert report.suggestions[1].accepted is True

def test_director_emits_narrative_events_and_hook_score():
    t = Transcript("tr", [
        Segment("Bugün inanılmaz bir deneme yapıyoruz", 0, 2.0, [Word("Bugün",0,.3), Word("inanılmaz",.3,.8)]),
        Segment("Şimdi sonucu göreceğiz", 2.2, 4.0, [Word("Şimdi",2.2,2.6)]),
        Segment("Telefon ekranını açıyoruz", 7.0, 14.5, [Word("Telefon",7,7.5), Word("ekranını",7.5,8)]),
    ])
    report = AnalysisReport("c1", "x.mp4", [])
    plan = build_director_plan(report, t, EditProfile.HIGH_RETENTION)
    assert plan.hook_score >= 45
    assert plan.narrative_score > 0
    kinds = {e.kind for e in plan.events}
    assert "hook" in kinds
    assert "beat" in kinds
    assert "broll_cue" in kinds


def test_director_cut_budget_blocks_low_priority_overflow():
    t = Transcript("tr", [Segment("x", 0, 10, [Word("x",0,1)])])
    report = AnalysisReport("c1", "x.mp4", [
        Suggestion(SuggestionKind.FILLER_WORD, 1, 3, "a"),
        Suggestion(SuggestionKind.FILLER_WORD, 4, 6, "b"),
        Suggestion(SuggestionKind.FILLER_WORD, 7, 9, "c"),
    ])
    plan = build_director_plan(report, t, EditProfile.YOUTUBE_LONGFORM)
    assert plan.cut_ratio <= .18 + 1e-6
    assert any((not d.accepted and d.risk == "medium") for d in plan.decisions)
