from app.ai.highlight_remix_engine import Highlight
from app.ai.variant_factory import build_variant_factory
from app.ai.quality_gate import validate_short_edit

def test_variant_factory_creates_alternatives():
    hs=[Highlight("a",0,15,95,hook=True), Highlight("b",60,70,90,payoff=True), Highlight("c",120,128,82)]
    packages=build_variant_factory(hs,180)
    assert len(packages)==3
    assert all(p.remix is not None for p in packages)

def test_quality_gate_blocks_empty():
    r=validate_short_edit(0,0,False,False)
    assert not r.passed
