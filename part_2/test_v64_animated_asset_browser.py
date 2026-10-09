from app.effects.pro_asset_library import ASSETS, search_library


def test_full_catalog_is_available():
    assert len(ASSETS) == 50000


def test_search_aliases_make_discovery_easier():
    assert search_library("gamer", limit=10)
    assert search_library("captions", limit=10)
    assert search_library("broll", limit=10)
    assert search_library("lut", limit=10)

