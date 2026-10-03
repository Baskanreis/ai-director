"""AI Basic Editor testleri (v0.8).

`detect_silence_regions` ve sahne tespiti gerçek ffmpeg çalıştırır (bulunamazsa
atlanır/sessizce boş döner); geri kalan her şey (uzun duraklama, tekrar, dolgu
kelime, önemli kelime önerisi, kesim uygulama) saf Python olduğundan ffmpeg'e
ihtiyaç duymadan test edilir.
"""
from __future__ import annotations

import shutil
import subprocess

import pytest

from app.ai.analyzer import (
    AnalysisError,
    build_report,
    detect_filler_words,
    detect_long_pauses,
    detect_repetitions,
    detect_silence_regions,
    suggest_highlight_words,
)
from app.ai.apply import apply_accepted_cuts, cut_ranges_in_clip, merge_ranges
from app.ai.models import Suggestion, SuggestionKind
from app.subtitle.models import Segment, Transcript, Word
from app.timeline.model import Timeline

HAS_FFMPEG = shutil.which("ffmpeg") is not None


def _words(*specs) -> list[Word]:
    return [Word(text=t, start=s, end=e) for t, s, e in specs]


# ---- detect_long_pauses ----

def test_detect_long_pauses_finds_gap_above_threshold():
    words = _words(("bir", 0.0, 0.5), ("iki", 3.0, 3.5))
    t = Transcript(language="tr", segments=[Segment("bir iki", 0.0, 3.5, words)])
    out = detect_long_pauses(t, min_pause=1.0)
    assert len(out) == 1
    assert out[0].kind == SuggestionKind.LONG_PAUSE
    assert out[0].start == pytest.approx(0.5)
    assert out[0].end == pytest.approx(3.0)


def test_detect_long_pauses_ignores_short_gaps():
    words = _words(("bir", 0.0, 0.5), ("iki", 0.8, 1.2))
    t = Transcript(language="tr", segments=[Segment("bir iki", 0.0, 1.2, words)])
    assert detect_long_pauses(t, min_pause=1.0) == []


# ---- detect_repetitions ----

def test_detect_repetitions_single_word_stutter():
    words = _words(("şey", 0.0, 0.3), ("şey", 0.3, 0.6), ("tamam", 0.6, 1.0))
    t = Transcript(language="tr", segments=[Segment("şey şey tamam", 0.0, 1.0, words)])
    out = detect_repetitions(t)
    assert len(out) == 1
    assert out[0].kind == SuggestionKind.REPETITION
    assert out[0].start == pytest.approx(0.3)
    assert out[0].end == pytest.approx(0.6)


def test_detect_repetitions_phrase_repeat():
    words = _words(
        ("ben", 0.0, 0.2), ("de", 0.2, 0.4), ("ben", 0.5, 0.7), ("de", 0.7, 0.9), ("geldim", 0.9, 1.2)
    )
    t = Transcript(language="tr", segments=[Segment("ben de ben de geldim", 0.0, 1.2, words)])
    out = detect_repetitions(t)
    assert any(s.kind == SuggestionKind.REPETITION for s in out)


def test_detect_repetitions_no_false_positive_on_distinct_words():
    words = _words(("bir", 0.0, 0.3), ("iki", 0.3, 0.6), ("üç", 0.6, 0.9))
    t = Transcript(language="tr", segments=[Segment("bir iki üç", 0.0, 0.9, words)])
    assert detect_repetitions(t) == []


def test_detect_repetitions_respects_window():
    words = _words(("şey", 0.0, 0.3), ("şey", 10.0, 10.3))  # 9.7sn ara: tekrar sayilmaz
    t = Transcript(language="tr", segments=[Segment("şey ... şey", 0.0, 10.3, words)])
    assert detect_repetitions(t, window=2.0) == []


# ---- detect_filler_words ----

def test_detect_filler_words_merges_consecutive():
    words = _words(("şey", 0.0, 0.3), ("yani", 0.3, 0.6), ("tamam", 0.6, 1.0))
    t = Transcript(language="tr", segments=[Segment("şey yani tamam", 0.0, 1.0, words)])
    out = detect_filler_words(t, language="tr")
    assert len(out) == 1
    assert out[0].kind == SuggestionKind.FILLER_WORD
    assert out[0].start == pytest.approx(0.0)
    assert out[0].end == pytest.approx(0.6)


def test_detect_filler_words_none_found():
    words = _words(("merhaba", 0.0, 0.5), ("dünya", 0.5, 1.0))
    t = Transcript(language="tr", segments=[Segment("merhaba dünya", 0.0, 1.0, words)])
    assert detect_filler_words(t, language="tr") == []


# ---- suggest_highlight_words ----

def test_suggest_highlight_words_picks_longest_content_word():
    words = _words(("bu", 0.0, 0.2), ("harikaymış", 0.2, 1.0), ("ve", 1.0, 1.1))
    t = Transcript(language="tr", segments=[Segment("bu harikaymış ve", 0.0, 1.1, words)])
    out = suggest_highlight_words(t, language="tr")
    assert len(out) == 1
    assert out[0].word == "harikaymış"


def test_suggest_highlight_words_respects_max_words():
    segs = []
    for i in range(5):
        w = Word(f"kelimecik{i}", float(i), float(i) + 0.5)
        segs.append(Segment(w.text, w.start, w.end, [w]))
    t = Transcript(language="tr", segments=segs)
    out = suggest_highlight_words(t, max_words=2)
    assert len(out) == 2


# ---- merge_ranges / cut_ranges_in_clip / apply_accepted_cuts ----

def test_merge_ranges_combines_overlapping():
    assert merge_ranges([(0.0, 2.0), (1.5, 3.0), (5.0, 6.0)]) == [(0.0, 3.0), (5.0, 6.0)]


def test_merge_ranges_empty():
    assert merge_ranges([]) == []


def _timeline_with_clip(duration=20.0):
    tl = Timeline()
    clips = tl.add_media("m1", "test", duration=duration, has_audio=False)
    return tl, clips[0]


def test_cut_ranges_in_clip_removes_and_shifts():
    tl, clip = _timeline_with_clip(20.0)
    n = cut_ranges_in_clip(tl, clip.id, [(5.0, 8.0)])
    assert n == 1
    assert tl.duration == pytest.approx(17.0)


def test_cut_ranges_in_clip_handles_multiple_ranges_in_order():
    tl, clip = _timeline_with_clip(20.0)
    n = cut_ranges_in_clip(tl, clip.id, [(10.0, 12.0), (2.0, 3.0)])
    assert n == 2
    assert tl.duration == pytest.approx(17.0)


def test_cut_ranges_in_clip_clips_to_source_bounds():
    tl, clip = _timeline_with_clip(10.0)
    n = cut_ranges_in_clip(tl, clip.id, [(-5.0, 2.0), (9.0, 50.0)])
    assert n == 2
    assert tl.duration == pytest.approx(7.0)


def test_apply_accepted_cuts_skips_rejected_suggestions():
    tl, clip = _timeline_with_clip(20.0)
    suggestions = [
        Suggestion(SuggestionKind.SILENCE, 5.0, 8.0, "Sessizlik", accepted=False),
        Suggestion(SuggestionKind.LONG_PAUSE, 10.0, 11.0, "Duraklama", accepted=True),
    ]
    n = apply_accepted_cuts(tl, clip.id, suggestions)
    assert n == 1
    assert tl.duration == pytest.approx(19.0)


def test_apply_accepted_cuts_ignores_non_cut_kinds():
    tl, clip = _timeline_with_clip(10.0)
    suggestions = [Suggestion(SuggestionKind.HIGHLIGHT_WORD, 1.0, 1.5, "Önemli kelime")]
    n = apply_accepted_cuts(tl, clip.id, suggestions)
    assert n == 0
    assert tl.duration == pytest.approx(10.0)


# ---- build_report ----

def test_build_report_without_transcript_suggests_add_subtitle(tmp_path):
    fake_media = tmp_path / "does_not_matter.mp4"
    fake_media.write_bytes(b"")  # icerik onemli degil, build_report ffmpeg'i best-effort calistirir
    report = build_report("clip1", fake_media, transcript=None, include_silence=False, include_scenes=False)
    kinds = [s.kind for s in report.suggestions]
    assert SuggestionKind.ADD_SUBTITLE in kinds


def test_build_report_with_transcript_runs_text_analyses(tmp_path):
    words = _words(("şey", 0.0, 0.3), ("şey", 0.3, 0.6), ("harikaymış", 3.0, 4.0))
    t = Transcript(language="tr", segments=[Segment("şey şey harikaymış", 0.0, 4.0, words)])
    fake_media = tmp_path / "video.mp4"
    fake_media.write_bytes(b"")
    report = build_report("clip1", fake_media, transcript=t, include_silence=False, include_scenes=False)
    kinds = {s.kind for s in report.suggestions}
    assert SuggestionKind.FILLER_WORD in kinds or SuggestionKind.REPETITION in kinds
    assert SuggestionKind.LONG_PAUSE in kinds
    assert SuggestionKind.HIGHLIGHT_WORD in kinds


def test_build_report_missing_media_raises_for_silence_but_not_for_report(tmp_path):
    missing = tmp_path / "missing.mp4"
    # include_silence=True ama dosya yok -> detect_silence_regions AnalysisError firlatir,
    # build_report bunu yutar (sessizce atlar), rapor yine de donmeli.
    report = build_report("clip1", missing, transcript=None, include_silence=True, include_scenes=False)
    assert report.clip_id == "clip1"


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg kurulu değil")
def test_detect_silence_regions_finds_real_silence(tmp_path):
    media = tmp_path / "silence_test.wav"
    # 1sn ton + 2sn sessizlik + 1sn ton
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono:d=2",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
        "-filter_complex", "[0:a][1:a][2:a]concat=n=3:v=0:a=1[a]",
        "-map", "[a]", str(media),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    regions = detect_silence_regions(media, noise_db=-30.0, min_duration=0.5)
    assert len(regions) == 1
    assert regions[0].start == pytest.approx(1.0, abs=0.2)
    assert regions[0].end == pytest.approx(3.0, abs=0.2)


def test_detect_silence_regions_missing_file_raises():
    with pytest.raises(AnalysisError):
        detect_silence_regions("/does/not/exist.mp4")
