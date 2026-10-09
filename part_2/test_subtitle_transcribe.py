"""app.subtitle.transcribe testleri.

Gercek Whisper modeli agir (indirme + GPU/CPU suresi) oldugundan, burada
`sys.modules['whisper']` sahte (fake) bir modulle degistirilerek yalnizca
AI Director tarafindaki entegrasyon (hata yonetimi, sonuc donusumu, progress
callback'leri) test edilir.
"""
from __future__ import annotations

import sys
import types

import pytest

from app.subtitle.models import SubtitleError


@pytest.fixture(autouse=True)
def _clear_model_cache():
    import app.subtitle.transcribe as ts
    ts._model_cache.clear()
    yield
    ts._model_cache.clear()


def _install_fake_whisper(monkeypatch, result: dict, transcribe_kwargs_capture: dict | None = None):
    fake = types.ModuleType("whisper")

    class _FakeModel:
        def transcribe(self, path, **kwargs):
            if transcribe_kwargs_capture is not None:
                transcribe_kwargs_capture["path"] = path
                transcribe_kwargs_capture.update(kwargs)
            return result

    def load_model(size, device=None):
        return _FakeModel()

    fake.load_model = load_model
    monkeypatch.setitem(sys.modules, "whisper", fake)
    return fake


def test_transcribe_raises_subtitle_error_when_whisper_missing(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "whisper", None)  # import whisper -> ImportError benzeri
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **kw):
        if name == "whisper":
            raise ImportError("no whisper")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    from app.subtitle.transcribe import transcribe

    media = tmp_path / "a.wav"
    media.write_bytes(b"\x00")
    with pytest.raises(SubtitleError, match="Whisper"):
        transcribe(media)


def test_transcribe_missing_file_raises():
    from app.subtitle.transcribe import transcribe

    with pytest.raises(SubtitleError, match="bulunamadı"):
        transcribe("/tmp/definitely-not-here-xyz.wav")


def test_transcribe_unsupported_language_raises(tmp_path):
    from app.subtitle.transcribe import transcribe

    media = tmp_path / "a.wav"
    media.write_bytes(b"\x00")
    with pytest.raises(SubtitleError, match="Desteklenmeyen dil"):
        transcribe(media, language="xx")


def test_transcribe_unknown_model_size_raises(tmp_path):
    from app.subtitle.transcribe import transcribe

    media = tmp_path / "a.wav"
    media.write_bytes(b"\x00")
    with pytest.raises(SubtitleError, match="model boyutu"):
        transcribe(media, model_size="huge")


def test_transcribe_with_word_timestamps_resegments(monkeypatch, tmp_path):
    result = {
        "language": "tr",
        "segments": [
            {
                "start": 0.0, "end": 2.0, "text": " Merhaba dünya.",
                "words": [
                    {"word": " Merhaba", "start": 0.0, "end": 0.8, "probability": 0.95},
                    {"word": " dünya.", "start": 0.8, "end": 2.0, "probability": 0.9},
                ],
            }
        ],
    }
    _install_fake_whisper(monkeypatch, result)

    from app.subtitle.transcribe import transcribe

    media = tmp_path / "a.wav"
    media.write_bytes(b"\x00")
    transcript = transcribe(media, language="tr")

    assert transcript.language == "tr"
    assert len(transcript.segments) == 1
    assert transcript.segments[0].text == "Merhaba dünya."
    words = transcript.all_words()
    assert [w.text for w in words] == ["Merhaba", "dünya."]
    assert words[0].prob == pytest.approx(0.95)


def test_transcribe_without_word_timestamps_uses_fallback_segments(monkeypatch, tmp_path):
    result = {
        "language": "en",
        "segments": [
            {"start": 0.0, "end": 1.5, "text": "Hello there", "words": []},
            {"start": 1.5, "end": 3.0, "text": "General Kenobi", "words": []},
        ],
    }
    _install_fake_whisper(monkeypatch, result)

    from app.subtitle.transcribe import transcribe

    media = tmp_path / "a.wav"
    media.write_bytes(b"\x00")
    transcript = transcribe(media, language="en")

    assert [s.text for s in transcript.segments] == ["Hello there", "General Kenobi"]


def test_transcribe_passes_language_and_word_timestamps_flag(monkeypatch, tmp_path):
    captured: dict = {}
    result = {"language": "de", "segments": []}
    _install_fake_whisper(monkeypatch, result, transcribe_kwargs_capture=captured)

    from app.subtitle.transcribe import transcribe

    media = tmp_path / "a.wav"
    media.write_bytes(b"\x00")
    transcribe(media, language="de")

    assert captured["language"] == "de"
    assert captured["word_timestamps"] is True


def test_transcribe_auto_language_passes_none(monkeypatch, tmp_path):
    captured: dict = {}
    result = {"language": "fr", "segments": []}
    _install_fake_whisper(monkeypatch, result, transcribe_kwargs_capture=captured)

    from app.subtitle.transcribe import transcribe

    media = tmp_path / "a.wav"
    media.write_bytes(b"\x00")
    transcribe(media, language="auto")

    assert captured["language"] is None


def test_transcribe_reports_progress(monkeypatch, tmp_path):
    result = {"language": "tr", "segments": []}
    _install_fake_whisper(monkeypatch, result)

    from app.subtitle.transcribe import transcribe

    media = tmp_path / "a.wav"
    media.write_bytes(b"\x00")
    events: list[tuple[float, str]] = []
    transcribe(media, on_progress=lambda frac, msg: events.append((frac, msg)))

    assert events[0][0] == 0.0
    assert events[-1] == (1.0, "Tamamlandı")
    assert all(0.0 <= f <= 1.0 for f, _ in events)


def test_transcribe_wraps_model_transcribe_exception(monkeypatch, tmp_path):
    fake = types.ModuleType("whisper")

    class _FailingModel:
        def transcribe(self, path, **kwargs):
            raise RuntimeError("boom")

    fake.load_model = lambda size, device=None: _FailingModel()
    monkeypatch.setitem(sys.modules, "whisper", fake)

    from app.subtitle.transcribe import transcribe

    media = tmp_path / "a.wav"
    media.write_bytes(b"\x00")
    with pytest.raises(SubtitleError, match="başarısız"):
        transcribe(media)
