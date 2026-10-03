from app.ai.models import AnalysisReport
from app.ai.autonomous_director import Platform
from app.ai.professional_director import build_professional_edit_plan
from app.subtitle.models import Transcript, Segment


def test_v219_full_plan_is_serializable_and_contextual():
    transcript = Transcript("tr", [
        Segment(start=0.0, end=2.0, text="Neden bunu yaptık? Çünkü sonuç gerçekten şaşırtıcı."),
        Segment(start=3.0, end=7.5, text="Şimdi ürünün nasıl çalıştığını gösterelim."),
    ])
    report = AnalysisReport("clip", "demo.mp4", [])
    plan = build_professional_edit_plan(report, transcript, Platform.YOUTUBE)
    data = plan.to_dict()
    assert data["metadata"]["version"] == "2.19"
    assert data["workflow"]
    assert len(plan.captions) == 2
    assert plan.motion
    assert plan.sound is not None
