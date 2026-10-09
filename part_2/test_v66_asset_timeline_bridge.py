from app.timeline.model import Timeline, Clip
from app.effects.asset_timeline_bridge import AssetTimelineBridge, AssetAction


def _clip(t):
    c = Clip("media://source", "Source", 0, 5, 0)
    t.first_track("video").add(c)
    return c


def test_apply_effect_to_clip_is_non_destructive():
    t = Timeline(); c = _clip(t)
    r = AssetTimelineBridge(t).apply(AssetAction("apply", "effect.cinematic", c.id))
    assert r.changed
    assert c.media_id == "media://source"
    assert c.creative_metadata["asset_stack"][0]["asset_id"] == "effect.cinematic"


def test_apply_transition_updates_transition_and_metadata():
    t = Timeline(); c = _clip(t)
    r = AssetTimelineBridge(t).apply(AssetAction("apply", "transition.flash", c.id))
    assert r.changed and c.transition_in is not None
    assert c.creative_metadata["asset_stack"][-1]["asset_id"] == "transition.flash"


def test_insert_asset_uses_asset_uri_not_extra_media_file():
    t = Timeline()
    r = AssetTimelineBridge(t).apply(AssetAction("insert", "audio_fx.punch_sfx", target_track_id="A1", at=1.0))
    assert r.changed
    clip = t.track("A1").clips[0]
    assert clip.media_id == "asset://audio_fx.punch_sfx"


def test_text_asset_is_a_timeline_cue():
    t = Timeline(); c = _clip(t)
    r = AssetTimelineBridge(t).apply(AssetAction("apply", "text.clean_caption", c.id))
    assert r.changed and c.creative_text_cues
    assert c.creative_text_cues[-1]["asset_ref"].startswith("asset://")


def test_variation_is_deterministic_and_no_file_copy():
    t = Timeline(); c = _clip(t)
    r = AssetTimelineBridge(t).apply(AssetAction("variation", "motion.punch_in", c.id, variant=3))
    item = c.creative_metadata["asset_stack"][-1]
    assert r.changed
    assert item["variation_seed"] == "motion.punch_in:3"
    assert "variation_strength" in item
