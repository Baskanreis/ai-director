from app.effects.pro_asset_library import ASSETS, library_stats, search_library, featured

def test_library_has_exactly_one_thousand_assets():
    assert len(ASSETS) == 50000
    assert sum(library_stats().values()) == 50000
    assert len({a.id for a in ASSETS}) == 50000

def test_thousand_library_covers_creator_workflows():
    stats = library_stats()
    for kind in ("effect", "transition", "motion", "text", "overlay", "sticker", "sfx", "audio_fx", "filter", "template", "music"):
        assert stats[kind] > 0
    assert search_library("cinematic", limit=20)
    assert search_library("gaming glitch", limit=20)
    assert search_library("podcast caption", limit=20)
    assert search_library("music beat", kind="music", limit=20)
    assert len(featured(50)) == 50
