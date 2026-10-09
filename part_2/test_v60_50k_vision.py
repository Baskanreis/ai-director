from app.effects.pro_asset_library import catalog, library_stats, search_library

def test_library_is_exactly_50k():
    assert len(catalog()) == 50000
    assert sum(library_stats().values()) == 50000
    assert len(library_stats()) == 11

def test_50k_has_rich_recipe_metadata():
    rows = search_library("gaming hook viral", kind="effect", limit=5)
    assert rows
    assert all("semantic_tags" in x.params and x.params.get("safe_to_auto_apply") for x in rows)

def test_scene_enricher_imports():
    from app.ai.scene_context_enricher import enrich_scene_context
    assert callable(enrich_scene_context)
