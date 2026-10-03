from pathlib import Path

from app.render.karaoke import events_to_segments, write_karaoke_ass
from app.render.controller import RenderController, RenderJob
from app.render.unified_pipeline import RenderOptions
from app.subtitle.style import get_preset


def test_word_level_events_become_karaoke_segment(tmp_path):
    events = [{
        "segment_id": "s1", "start": 0, "end": 1.2, "text": "Merhaba dünya",
        "words": [
            {"text": "Merhaba", "start": 0, "end": .5},
            {"text": "dünya", "start": .5, "end": 1.2},
        ],
    }]
    segments = events_to_segments(events)
    assert len(segments) == 1
    assert [w.text for w in segments[0].words] == ["Merhaba", "dünya"]

    ass = write_karaoke_ass(events, tmp_path / "k.ass", get_preset("karaoke_highlight"))
    text = ass.read_text(encoding="utf-8")
    assert "Merhaba" in text and "dünya" in text
    assert "&H0000D4FF&" in text or "\u0026H00" in text


def test_controller_preview_keeps_pipeline(tmp_path):
    assert RenderController().preview_job is not None


def test_render_profile_is_safe():
    profile = RenderController().render_profile()
    assert profile["hardware_accel"] in profile["available"]
    assert profile["preview_supported"] is True
