from app.subtitle.typography import list_typography, get_typography, search_typography
from app.subtitle.style import Animation
from app.subtitle.ass_format import to_ass
from app.subtitle.models import Segment, Word


def test_typography_catalog_and_search():
    assert len(list_typography()) >= 8
    assert get_typography("viral_bold").animation == Animation.POP
    assert search_typography("gaming neon")


def test_new_ass_animations_render():
    words = [Word("AI", 0, .25), Word("Director", .25, .8)]
    seg = Segment("AI Director", 0, .8, words)
    for key in ("kinetic_bounce", "glitch_caption", "neon_pulse", "typewriter", "highlight_sweep"):
        ass = to_ass([seg], get_typography(key), {"AI"})
        assert "Dialogue:" in ass
        assert "Style:" in ass
