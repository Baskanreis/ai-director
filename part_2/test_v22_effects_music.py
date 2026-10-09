from pathlib import Path
from app.effects.asset_library import list_assets
from app.effects.effect_library import ALL_EFFECTS
from app.brain.effects_preset import preset_names
from app.timeline.model import Timeline


def test_bundled_audio_library_has_sfx_and_music():
    assets = list_assets()
    assert len(assets) >= 15
    assert any(a.category == 'SFX' and Path(a.path).is_file() for a in assets)
    assert any(a.category == 'Music' and Path(a.path).is_file() for a in assets)


def test_effect_library_is_large_and_exposes_presets():
    assert len(ALL_EFFECTS) >= 20
    assert 'shorts_energy' in preset_names()
    assert 'cinematic' in preset_names()


def test_audio_only_media_can_be_added_to_timeline():
    tl = Timeline()
    clip = tl.add_audio_media('music1', 'Music', 8.0)
    assert clip in tl.first_track('audio').clips
    assert tl.duration == 8.0


def test_expanded_creative_library_and_animations():
    from app.effects.pro_asset_library import catalog
    from app.effects.animation_library import list_animations
    assert len(catalog()) >= 50
    assert len(list_animations()) >= 20
    assert any(a.id == "effect.cyberpunk" for a in catalog("effect"))
    assert any(a.id == "text.glitch" for a in catalog("text"))
    assert any(a.id == "transition.whip_left" for a in catalog("transition"))


def test_expanded_original_audio_pack():
    assets = list_assets()
    assert len(assets) >= 45
    assert any(a.id == "music_future" and a.bpm == 128 for a in assets)
    assert any(a.id == "sfx_laser" for a in assets)
