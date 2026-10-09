from app.effects.marketplace import (
    builtin_packs, get_pack, marketplace_search, catalog_health, manifest
)


def test_marketplace_has_builtin_packs_and_single_setup_contract():
    packs = builtin_packs()
    assert len(packs) >= 10
    health = catalog_health()
    assert health["assets"] == 50000
    assert health["single_setup"] is True
    assert health["external_runtime_required"] is False


def test_pack_resolution_and_aliases():
    subtitle = get_pack("subtitle-style")
    broll = get_pack("b-roll")
    lut = get_pack("lut")
    assert subtitle and "text" in subtitle.categories
    assert broll and "template" in broll.categories
    assert lut and "filter" in lut.categories
    assert subtitle.count() > 0
    assert broll.count() > 0
    assert lut.count() > 0


def test_marketplace_search_and_manifest():
    rows = marketplace_search("gaming glitch")
    assert rows
    assert rows[0].id == "pack.gaming"
    data = manifest(rows[0])
    assert data["schema"] == "ai-director-pack/v1"
    assert data["asset_count"] > 0
