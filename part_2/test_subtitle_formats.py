from __future__ import annotations

import pytest

from app.subtitle.formats import segment_words_into_lines, to_srt, to_vtt
from app.subtitle.models import Segment, Word


def _words(*specs) -> list[Word]:
    """specs: (text, start, end) uclulerinden Word listesi uretir."""
    return [Word(text=t, start=s, end=e) for t, s, e in specs]


# ---- segment_words_into_lines ----

def test_segment_words_empty_returns_empty():
    assert segment_words_into_lines([]) == []


def test_segment_words_splits_on_sentence_end():
    words = _words(("Merhaba", 0.0, 0.5), ("dünya.", 0.5, 1.0), ("Nasılsın?", 1.0, 1.5))
    segs = segment_words_into_lines(words)
    assert len(segs) == 2
    assert segs[0].text == "Merhaba dünya."
    assert segs[0].start == 0.0 and segs[0].end == pytest.approx(1.0)
    assert segs[1].text == "Nasılsın?"


def test_segment_words_splits_on_max_duration():
    words = _words(("bir", 0.0, 1.0), ("iki", 1.0, 3.0), ("üç", 3.0, 7.5))
    segs = segment_words_into_lines(words, max_duration=6.0, max_chars=1000, max_words=1000)
    # bir+iki -> 0..3 (3s, altinda), uc eklenince 0..7.5 (7.5s > 6.0) -> flush once uc'ten once kapanmali
    assert len(segs) == 2
    assert segs[0].text == "bir iki"
    assert segs[1].text == "üç"


def test_segment_words_splits_on_max_chars():
    words = _words(("kelime1", 0.0, 0.4), ("kelime2", 0.4, 0.8), ("kelime3", 0.8, 1.2))
    segs = segment_words_into_lines(words, max_chars=15, max_duration=1000, max_words=1000)
    assert len(segs) >= 2
    assert all(len(s.text) <= 20 for s in segs)  # bolunmus, cok uzun degil


def test_segment_words_splits_on_max_words():
    words = _words(*[(f"k{i}", i * 0.1, i * 0.1 + 0.1) for i in range(5)])
    segs = segment_words_into_lines(words, max_words=2, max_chars=1000, max_duration=1000)
    assert len(segs) == 3  # 2+2+1
    assert segs[0].text == "k0 k1"
    assert segs[-1].text == "k4"


def test_segment_words_preserves_word_list_on_segment():
    words = _words(("Merhaba", 0.0, 0.5), ("dünya.", 0.5, 1.0))
    segs = segment_words_into_lines(words)
    assert len(segs[0].words) == 2
    assert segs[0].words[0].text == "Merhaba"


# ---- to_srt ----

def test_to_srt_empty():
    assert to_srt([]) == ""


def test_to_srt_basic_format():
    segs = [Segment("Merhaba dünya", 0.0, 1.5), Segment("Nasılsın?", 1.5, 3.0)]
    srt = to_srt(segs)
    lines = srt.strip("\n").split("\n")
    assert lines[0] == "1"
    assert lines[1] == "00:00:00,000 --> 00:00:01,500"
    assert lines[2] == "Merhaba dünya"
    assert lines[3] == ""
    assert lines[4] == "2"
    assert lines[5] == "00:00:01,500 --> 00:00:03,000"
    assert lines[6] == "Nasılsın?"


def test_to_srt_timestamp_with_hours():
    segs = [Segment("test", 3661.25, 3662.0)]  # 1h 1m 1.25s
    srt = to_srt(segs)
    assert "01:01:01,250 -->" in srt


# ---- to_vtt ----

def test_to_vtt_starts_with_webvtt_header():
    segs = [Segment("Merhaba", 0.0, 1.0)]
    vtt = to_vtt(segs)
    assert vtt.startswith("WEBVTT\n\n")
    assert "00:00:00.000 --> 00:00:01.000" in vtt
    assert "Merhaba" in vtt


def test_to_vtt_empty_segments_still_has_header():
    assert to_vtt([]).strip() == "WEBVTT"
