from app.ai.professional_realizer import realize_full_professional_timeline
from app.ai.professional_director import ProfessionalEditPlan
from app.ai.autonomous_director import build_autonomous_plan, Platform
from app.ai.effects_director import build_sound_design_plan
from app.ai.models import AnalysisReport, Suggestion, SuggestionKind
from app.subtitle.models import Segment, Transcript

def _report():
    return AnalysisReport("c1", "demo.mp4", [
        Suggestion(SuggestionKind.FILLER_WORD, 5.0, 6.0, "pause")
    ])

def test_full_realization_applies_layers():
    tr = Transcript("tr", [Segment("Bugün bunu yapıyoruz", 0, 10, [])])
    ap = build_autonomous_plan(_report(), tr, Platform.YOUTUBE)
    plan = ProfessionalEditPlan(ap, build_sound_design_plan(ap.director), motion=[], captions=[])
    timeline, report, layers = realize_full_professional_timeline(plan, "media-1", "Demo")
    assert timeline.duration > 0
    assert report.video_clips >= 1
    assert layers.music_clips in (0, 1)
    assert timeline.ai_director["layers_applied"] is True
