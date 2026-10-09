from app.ai.retention_hotspots import RetentionHotspot
from app.ai.regional_revision import RegionalRevisionPolicy, generate_regional_candidates
from app.ai.combination_engine import CombinationContext

def test_regional_revision_uses_asset_combination_engine():
    plan={"timeline":[],"metadata":{"speech":True,"music":True,"faces":True}}
    hs=RetentionHotspot(10,18,"visual_variety_risk","high",.9)
    rows=generate_regional_candidates(plan, hs, RegionalRevisionPolicy(max_candidates=3, combination_count=3, combination_budget=10000),
                                      CombinationContext(style="viral_fast", speech=True, music=True, faces=True, seed=11))
    assert len(rows) == 3
    assert all(c.report.get("asset_combination") for c in rows)
    assert all(c.report.get("combination_score") is not None for c in rows)
    assert all(c.plan["metadata"]["regional_asset_stacks"] for c in rows)

def test_regional_asset_search_is_deterministic():
    plan={"timeline":[],"metadata":{}}
    hs=RetentionHotspot(1,4,"hook_risk","high",.8)
    pol=RegionalRevisionPolicy(max_candidates=2, combination_count=2, combination_budget=10000)
    ctx=CombinationContext(style="cinematic", seed=99)
    a=generate_regional_candidates(plan,hs,pol,ctx)
    b=generate_regional_candidates(plan,hs,pol,ctx)
    assert [x.report["asset_combination"] for x in a] == [x.report["asset_combination"] for x in b]
