from app.ai.content_understanding import ContentUnderstanding, SegmentSignal
from app.ai.multimodal_analyzer import AudioSignal, MultimodalAnalysis, VisualSignal, enrich_content_understanding
from app.ai.edit_decision_graph import build_edit_decision_graph
from app.ai.editorial_style_engine import build_editorial_style_plan
from app.ai.quality_gate import optimize_edit_graph, validate_edit_graph


def test_multimodal_fusion_raises_visual_action():
    u=ContentUnderstanding(segments=[SegmentSignal(0,2,"şimdi hareket ediyor")])
    mm=MultimodalAnalysis(2,30,[VisualSignal(0,2,motion=.9,scene_change=.8,visual_density=.7)], [AudioSignal(0,1,beat=1)], beats=[.5])
    enrich_content_understanding(u,mm)
    assert u.action >= .5
    assert u.signals["beat_count"] == 1.0


def test_decision_graph_gets_visual_actions_and_optimizer():
    u=ContentUnderstanding(segments=[SegmentSignal(0,1,"şimdi",importance=.7,action=.8)])
    mm=MultimodalAnalysis(1,30,[VisualSignal(0,1,motion=.9,scene_change=.9)])
    style=build_editorial_style_plan("gaming action")
    g=build_edit_decision_graph(u,style,mm)
    assert any(a.kind=="visual_scene_cut" for a in g.actions)
    g2=optimize_edit_graph(g)
    assert g2.metadata["optimized"] is True
    assert validate_edit_graph(g2,1).passed
