from app.effects.pro_asset_library import catalog
from app.ai.creative_library_studio import preview_spec, recommend, ApplyStack

def test_creative_studio_catalog_and_preview():
    assert len(catalog()) == 50000
    a=catalog()[0]
    p=preview_spec(a)
    assert p.asset_id == a.id and p.duration > 0

def test_ai_top3_recommendations_are_bounded_and_useful():
    rows=recommend('gaming glitch', limit=3)
    assert 1 <= len(rows) <= 3
    assert any('gaming' in (a.name+' '+' '.join(a.tags)).lower() for a in rows)

def test_stack_contract_serializes():
    s=ApplyStack([])
    assert s.to_dict()['blend'] == 'stack'
