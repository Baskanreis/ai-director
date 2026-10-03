from app.ai.content_understanding import understand_content
from app.ai.edit_decision_graph import build_edit_decision_graph
from app.ai.editorial_style_engine import build_editorial_style_plan
from app.ai.quality_gate import validate_edit_graph
from app.subtitle.models import Transcript, Segment

def t(texts):
    return Transcript('tr',[Segment(x,i*3,(i+1)*3) for i,x in enumerate(texts)])

def test_understanding_extracts_horror_and_information_signals():
    u=understand_content(t(['Gece karanlık evde bir ses duyduk.','Sonra kapı açıldı ve sonunda gerçeği gördük.']))
    assert u.suspense > 0
    assert u.payoff_strength > 0
    assert len(u.segments)==2

def test_decision_graph_preserves_meaning_and_adds_style_actions():
    u=understand_content(t(['Bu derste önemli sonucu nasıl bulacağınızı anlatacağım.']))
    style=build_editorial_style_plan('eğitim dersi bilgi anlatımı')
    g=build_edit_decision_graph(u,style)
    assert g.protected_ranges
    assert any(a.kind=='caption_emphasis' for a in g.actions)
    assert validate_edit_graph(g,3).passed
