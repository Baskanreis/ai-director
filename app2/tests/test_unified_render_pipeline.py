from app.render.unified_pipeline import RenderOptions, SFXEvent, write_caption_ass
from app.timeline.model import Clip

def test_caption_metadata_serializes_with_clip():
    clip = Clip("m", "clip", 0, 2, 1, caption_events=[{"start": .1, "end": .5, "text": "Merhaba"}])
    restored = Clip.from_dict(clip.to_dict())
    assert restored.caption_events[0]["text"] == "Merhaba"

def test_caption_ass_contains_timed_animated_dialogue(tmp_path):
    target = write_caption_ass([{"start": .25, "end": 1.5, "text": "Merhaba dünya",
                                 "animation": "pop", "emphasis": ["dünya"]}],
                               tmp_path / "captions.ass", 1080, 1920)
    data = target.read_text(encoding="utf-8-sig")
    assert "Dialogue: 0,0:00:00.25,0:00:01.50" in data
    assert "Merhaba " in data and "dünya" in data
    assert "\\fscx70" in data

def test_render_options_accept_sfx():
    options = RenderOptions(sfx=[SFXEvent("hit.wav", 1, 1.5)])
    assert options.sfx[0].start == 1

def test_render_options_carry_karaoke_style():
    from app.render.unified_pipeline import RenderOptions
    from app.subtitle.style import get_preset
    options = RenderOptions(captions=[], caption_style=get_preset("karaoke_highlight"), always_highlight={"AI"})
    assert options.caption_style.name == "Karaoke Vurgu"
    assert "AI" in options.always_highlight
