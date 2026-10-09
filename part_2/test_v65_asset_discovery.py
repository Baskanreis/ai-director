from app.effects.pro_asset_library import ASSETS
from app.effects.asset_discovery import DiscoveryFilters, category_counts, similar_assets, visual_query


def test_category_counts_cover_full_catalog():
    assert sum(category_counts().values()) == 50000
    assert len(category_counts()) >= 8


def test_structured_filters_and_visual_query():
    rows = visual_query("gaming glitch", DiscoveryFilters(kind="effect", safe_only=True), 12)
    assert rows
    assert all(a.kind == "effect" for a in rows)
    assert all(a.params.get("safe_to_auto_apply") for a in rows)


def test_similar_asset_discovery():
    seed = ASSETS[0]
    rows = similar_assets(seed, 10)
    assert rows
    assert all(a.id != seed.id and 0 <= score <= 1 for a, score in rows)
