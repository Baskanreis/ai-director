from app.effects.pro_asset_library import categories, search_library, library_stats
from app.ai.edit_styles import blend_styles
from app.ai.creative_composer import compose_style_mix


def test_library_has_major_nle_categories():
    kinds = set(categories())
    assert {"effect","transition","motion","text","overlay","sticker","template"}.issubset(kinds)


def test_library_expansion_is_large_and_searchable():
    stats = library_stats()
    assert sum(stats.values()) >= 150
    assert search_library("glitch gaming", kind="transition")
    assert search_library("viral", kind="template")


def test_style_composer_blends_styles():
    mix = blend_styles("gaming", "meme", .5)
    assert mix["primary"] == "gaming"
    assert mix["secondary"] == "meme"
    assert mix["cut_density"] > 1.0
    assert "gaming" in mix["tags"] and "meme" in mix["tags"]
    assert compose_style_mix("cinematic", "documentary")["cinematic_grade"] is True
