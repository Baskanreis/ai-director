from app.effects.pro_asset_library import catalog, library_stats
from app.ai.semantic_asset_matcher import SemanticContext, match_assets
from app.ai.regional_revision import RegionalRevisionPolicy, generate_regional_candidates
from app.ai.retention_hotspots import RetentionHotspot
from app.ai.combination_engine import CombinationContext

def test_creative_library_is_20k():
    assert len(catalog()) == 50000
    assert sum(library_stats().values()) == 50000

def test_semantic_match_uses_context():
    ctx=SemanticContext(transcript="Bu telefon ile video çekiyorum", objects=("telefon",), emotion="heyecan", scene_type="product", faces=True)
    rows=match_assets(ctx, kind="effect", limit=5)
    assert len(rows)==5
    assert all(r.asset.kind == "effect" for r in rows)

def test_regional_revision_receives_semantic_matches():
    plan={"timeline":[],"metadata":{"speech":True,"music":True,"faces":True,"hotspot_transcript":"telefonu şimdi göstereceğim","objects":["telefon"],"emotion":"heyecan"}}
    hs=RetentionHotspot(2,6,"visual_variety_risk","high",.9)
    rows=generate_regional_candidates(plan,hs,RegionalRevisionPolicy(max_candidates=3,combination_budget=10000),CombinationContext(scene_type="product",style="viral_fast",speech=True,music=True,faces=True,seed=4))
    assert len(rows)==3
    assert all(c.report.get("semantic_matches") for c in rows)
