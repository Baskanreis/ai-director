from app.ai.asset_marketplace_director import recommend_packs, select_pack, select_assets_from_pack
from app.ai.creative_studio_ai import ClipContext


def test_pack_director_prefers_gaming_for_high_energy_gaming_scene():
    ctx=ClipContext("clip-1",10.0,"gaming",.92,False,True,False,("glitch","fps"),"shorts","gaming")
    rows=recommend_packs(ctx)
    assert rows and rows[0].pack_id == "pack.gaming"
    selection=select_pack(ctx)
    assert selection.primary.pack_id == "pack.gaming"
    assert selection.primary.score > 0


def test_pack_director_builds_coherent_asset_selection():
    ctx=ClipContext("clip-2",8.0,"broll",.62,False,True,False,("travel","cinematic"),"shorts","travel")
    selection, assets=select_assets_from_pack(ctx, limit=8)
    assert selection.primary.pack_id == "pack.travel-broll"
    assert assets
    assert all(a.id for a in assets)
