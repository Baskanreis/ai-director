from __future__ import annotations

import pytest

from app.subtitle.ass_format import to_ass
from app.subtitle.editor import SubtitleEditor
from app.subtitle.emoji import annotate_text, annotate_transcript, find_emojis
from app.subtitle.models import Segment, SubtitleError, Transcript, Word
from app.subtitle.style import Animation, Position, SubtitleStyle, get_preset


def _words(*specs) -> list[Word]:
    return [Word(text=t, start=s, end=e) for t, s, e in specs]


# ---- SubtitleStyle / presets ----

def test_get_preset_returns_independent_copy():
    a = get_preset("classic")
    b = get_preset("classic")
    a.font_size = 999
    assert b.font_size != 999


def test_unknown_preset_raises():
    with pytest.raises(KeyError):
        get_preset("does-not-exist")


def test_ass_color_conversion_is_bgr_with_alpha():
    style = SubtitleStyle(text_color="#112233")
    # #RRGGBB -> &HAABBGGRR& : 11/22/33 -> BGR = 33 22 11
    assert style.ass_primary_colour() == "&H00332211&"


def test_position_alignment_mapping():
    assert SubtitleStyle(position=Position.BOTTOM).align() == 2
    assert SubtitleStyle(position=Position.MIDDLE).align() == 5
    assert SubtitleStyle(position=Position.TOP).align() == 8


# ---- to_ass ----

def test_to_ass_contains_script_info_and_styles():
    seg = Segment(text="Merhaba dünya", start=0.0, end=1.0, words=_words(("Merhaba", 0.0, 0.5), ("dünya", 0.5, 1.0)))
    ass = to_ass([seg], get_preset("classic"))
    assert "[Script Info]" in ass
    assert "[V4+ Styles]" in ass
    assert "[Events]" in ass
    assert "Dialogue:" in ass


def test_to_ass_word_highlight_emits_one_event_per_word():
    words = _words(("bir", 0.0, 0.5), ("iki", 0.5, 1.0), ("üç", 1.0, 1.5))
    seg = Segment(text="bir iki üç", start=0.0, end=1.5, words=words)
    style = get_preset("karaoke_highlight")
    assert style.highlight_words is True
    ass = to_ass([seg], style)
    assert ass.count("Dialogue:") == 3


def test_to_ass_without_word_highlight_emits_one_event_per_segment():
    words = _words(("bir", 0.0, 0.5), ("iki", 0.5, 1.0))
    seg = Segment(text="bir iki", start=0.0, end=1.0, words=words)
    style = get_preset("classic")
    assert style.highlight_words is False
    ass = to_ass([seg], style)
    assert ass.count("Dialogue:") == 1


def test_to_ass_always_highlight_colours_pinned_word():
    words = _words(("önemli", 0.0, 0.5), ("kelime", 0.5, 1.0))
    seg = Segment(text="önemli kelime", start=0.0, end=1.0, words=words)
    style = get_preset("classic")  # highlight_words=False -> statik tek satir
    ass = to_ass([seg], style, always_highlight={"önemli"})
    assert style.ass_highlight_colour() in ass


def test_to_ass_escapes_braces_and_backslashes():
    seg = Segment(text="{deneme} \\ test", start=0.0, end=1.0, words=[])
    ass = to_ass([seg], get_preset("classic"))
    assert "\\{deneme\\}" in ass


def test_to_ass_accepts_transcript_directly():
    seg = Segment(text="test", start=0.0, end=1.0, words=[])
    t = Transcript(language="tr", segments=[seg])
    ass = to_ass(t, get_preset("classic"))
    assert "Dialogue:" in ass


def test_animation_pop_adds_transform_tag():
    words = _words(("merhaba", 0.0, 0.6))
    seg = Segment(text="merhaba", start=0.0, end=0.6, words=words)
    style = get_preset("karaoke_highlight")
    assert style.animation == Animation.POP
    ass = to_ass([seg], style)
    assert "\\t(0," in ass


# ---- emoji ----

def test_find_emojis_matches_turkish_keyword():
    assert "🤩" in find_emojis("bugün hava harika görünüyor")


def test_find_emojis_no_match_returns_empty():
    assert find_emojis("masa sandalye kalem defter") == []


def test_annotate_text_appends_emoji():
    out = annotate_text("çok mutluyum")
    assert out.startswith("çok mutluyum")
    assert "😊" in out


def test_annotate_text_respects_max_matches():
    out = annotate_text("mutlu harika süper aşk", max_matches=1)
    assert sum(out.count(e) for e in ("😊", "🤩", "❤️")) == 1


def test_annotate_transcript_preserves_timing():
    words = _words(("mutluyum", 0.0, 1.0))
    seg = Segment(text="mutluyum", start=0.0, end=1.0, words=words)
    t = Transcript(language="tr", segments=[seg])
    t2 = annotate_transcript(t)
    assert t2.segments[0].start == 0.0 and t2.segments[0].end == 1.0
    assert "😊" in t2.segments[0].text
    assert t.segments[0].text == "mutluyum"  # orijinal degismedi


# ---- SubtitleEditor ----

def _sample_transcript() -> Transcript:
    words = _words(("Merhaba", 0.0, 0.5), ("dünya.", 0.5, 1.0))
    seg1 = Segment(text="Merhaba dünya.", start=0.0, end=1.0, words=words)
    seg2 = Segment(text="Nasılsın?", start=1.5, end=2.5, words=_words(("Nasılsın?", 1.5, 2.5)))
    return Transcript(language="tr", segments=[seg1, seg2])


def test_editor_update_text():
    t = _sample_transcript()
    SubtitleEditor(t).update_text(0, "Selam dünya.")
    assert t.segments[0].text == "Selam dünya."


def test_editor_update_text_invalid_index_raises():
    t = _sample_transcript()
    with pytest.raises(SubtitleError):
        SubtitleEditor(t).update_text(5, "x")


def test_editor_update_timing_rescales_words():
    t = _sample_transcript()
    SubtitleEditor(t).update_timing(0, 2.0, 4.0)
    seg = t.segments[0]
    assert seg.start == 2.0 and seg.end == 4.0
    assert seg.words[0].start == pytest.approx(2.0)
    assert seg.words[-1].end == pytest.approx(4.0)


def test_editor_update_timing_rejects_inverted_range():
    t = _sample_transcript()
    with pytest.raises(SubtitleError):
        SubtitleEditor(t).update_timing(0, 5.0, 1.0)


def test_editor_delete_removes_segment():
    t = _sample_transcript()
    SubtitleEditor(t).delete(0)
    assert len(t.segments) == 1
    assert t.segments[0].text == "Nasılsın?"


def test_editor_insert_adds_and_resorts():
    t = _sample_transcript()
    new_seg = Segment(text="Araya girdim", start=1.1, end=1.4)
    SubtitleEditor(t).insert(1, new_seg)
    assert [s.text for s in t.segments] == ["Merhaba dünya.", "Araya girdim", "Nasılsın?"]


def test_editor_merge_combines_two_segments():
    t = _sample_transcript()
    SubtitleEditor(t).merge(0, 1)
    assert len(t.segments) == 1
    assert t.segments[0].text == "Merhaba dünya. Nasılsın?"
    assert t.segments[0].start == 0.0 and t.segments[0].end == 2.5


def test_editor_split_breaks_into_two():
    words = _words(("bir", 0.0, 0.3), ("iki", 0.3, 0.6), ("üç", 0.6, 0.9), ("dört", 0.9, 1.2))
    seg = Segment(text="bir iki üç dört", start=0.0, end=1.2, words=words)
    t = Transcript(language="tr", segments=[seg])
    SubtitleEditor(t).split(0, 2)
    assert len(t.segments) == 2
    assert t.segments[0].text == "bir iki"
    assert t.segments[1].text == "üç dört"
    assert t.segments[0].end == pytest.approx(0.6)
    assert t.segments[1].start == pytest.approx(0.6)


def test_editor_split_without_enough_words_raises():
    seg = Segment(text="tek", start=0.0, end=0.5, words=_words(("tek", 0.0, 0.5)))
    t = Transcript(language="tr", segments=[seg])
    with pytest.raises(SubtitleError):
        SubtitleEditor(t).split(0, 1)


def test_editor_shift_all_moves_every_segment():
    t = _sample_transcript()
    SubtitleEditor(t).shift_all(1.0)
    assert t.segments[0].start == 1.0
    assert t.segments[1].start == 2.5
    assert t.segments[0].words[0].start == pytest.approx(1.0)


def test_editor_shift_all_rejects_negative_result():
    t = _sample_transcript()
    with pytest.raises(SubtitleError):
        SubtitleEditor(t).shift_all(-10.0)


def test_editor_shift_from_only_moves_tail():
    t = _sample_transcript()
    SubtitleEditor(t).shift_from(1, 0.5)
    assert t.segments[0].start == 0.0  # etkilenmedi
    assert t.segments[1].start == 2.0
