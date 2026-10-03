"""Whisper (openai-whisper) ile transkripsiyon (v0.8 Subtitle Engine).

`openai-whisper` isteğe bağlı bir bağımlılıktır (bkz. `requirements-optional.txt`);
kurulu değilse `transcribe()` açık bir `SubtitleError` fırlatır — uygulamanın geri
kalanı (timeline, export, audio engine) bundan etkilenmez.

Türkçe öncelikli: `DEFAULT_LANGUAGE = "tr"`. Ayrıca İngilizce/Almanca/Fransızca ve
"otomatik algıla" desteklenir (bkz. `SUPPORTED_LANGUAGES`).
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .formats import segment_words_into_lines
from .models import SubtitleError, Segment, Transcript, Word

ProgressCB = Callable[[float, str], None]  # (0..1, mesaj)

SUPPORTED_LANGUAGES: dict[str, str] = {
    "tr": "Türkçe",
    "en": "English",
    "de": "Deutsch",
    "fr": "Français",
    "auto": "Otomatik Algıla",
}
DEFAULT_LANGUAGE = "tr"

MODEL_SIZES: list[str] = ["tiny", "base", "small", "medium", "large"]
DEFAULT_MODEL_SIZE = "small"

_model_cache: dict[str, Any] = {}


def whisper_available() -> bool:
    try:
        import whisper  # noqa: F401
    except ImportError:
        return False
    return True


def _load_model(model_size: str, device: str | None):
    import whisper

    key = f"{model_size}:{device or 'auto'}"
    if key not in _model_cache:
        _model_cache[key] = (
            whisper.load_model(model_size, device=device) if device else whisper.load_model(model_size)
        )
    return _model_cache[key]


def _result_to_transcript(result: dict, resegment: bool = True) -> Transcript:
    """Whisper'ın ham `transcribe()` sonucunu (dict) `Transcript`'e çevirir.

    Whisper'da her kelime `word["word"]` alanında genelde başında bir boşlukla
    gelir (ör. `" merhaba"`); bu yüzden `.strip()` uygulanır. `word_timestamps`
    kapalıysa (ya da model kelime zamanlaması döndürmezse) segment'ler Whisper'ın
    kendi (genelde daha uzun) segmentasyonuyla kullanılır.
    """
    language = str(result.get("language", "") or "")
    words: list[Word] = []
    fallback_segments: list[Segment] = []

    for seg in result.get("segments", []):
        seg_words = seg.get("words") or []
        if seg_words:
            for w in seg_words:
                text = str(w.get("word", "")).strip()
                if not text:
                    continue
                words.append(
                    Word(
                        text=text,
                        start=float(w["start"]),
                        end=float(w["end"]),
                        prob=float(w.get("probability", 1.0)),
                    )
                )
        else:
            text = str(seg.get("text", "")).strip()
            if text:
                fallback_segments.append(
                    Segment(text=text, start=float(seg["start"]), end=float(seg["end"]))
                )

    if words:
        segments = segment_words_into_lines(words) if resegment else fallback_segments or [
            Segment(text=" ".join(w.text for w in words), start=words[0].start, end=words[-1].end, words=words)
        ]
        return Transcript(language=language, segments=segments)
    return Transcript(language=language, segments=fallback_segments)


def transcribe(
    path: str | Path,
    language: str = DEFAULT_LANGUAGE,
    model_size: str = DEFAULT_MODEL_SIZE,
    device: str | None = None,
    resegment: bool = True,
    on_progress: ProgressCB | None = None,
) -> Transcript:
    """`path`teki medyayı Whisper ile transkribe eder ve bir `Transcript` döndürür.

    `language`, `SUPPORTED_LANGUAGES` içindeki bir anahtar olmalı ("tr" varsayılan);
    `"auto"` Whisper'ın dili kendiliğinden algılamasını sağlar. `model_size`,
    `MODEL_SIZES` içinden biri olmalı — büyük modeller daha doğru ama daha yavaştır.
    Whisper kurulu değilse (bkz. `whisper_available`) `SubtitleError` fırlatılır.
    """
    p = Path(path)
    if not p.is_file():
        raise SubtitleError(f"Dosya bulunamadı: {p}")
    if language not in SUPPORTED_LANGUAGES:
        raise SubtitleError(
            f"Desteklenmeyen dil: {language!r}. Desteklenenler: {', '.join(SUPPORTED_LANGUAGES)}"
        )
    if model_size not in MODEL_SIZES:
        raise SubtitleError(f"Bilinmeyen model boyutu: {model_size!r}. Seçenekler: {', '.join(MODEL_SIZES)}")

    def report(frac: float, msg: str) -> None:
        if on_progress:
            on_progress(min(max(frac, 0.0), 1.0), msg)

    try:
        import whisper  # noqa: F401
    except ImportError as exc:
        raise SubtitleError(
            "Whisper (openai-whisper) kurulu değil. Kurmak için:\n"
            "  pip install openai-whisper\n"
            "(bkz. requirements-optional.txt). Ayrıca sisteminizde ffmpeg kurulu olmalı."
        ) from exc

    report(0.0, f"Model yükleniyor ({model_size})…")
    try:
        model = _load_model(model_size, device)
    except Exception as exc:  # model indirilemedi / yuklenemedi
        raise SubtitleError(f"Whisper modeli yüklenemedi ({model_size}): {exc}") from exc

    report(0.1, "Transkripsiyon başlıyor…")
    whisper_language = None if language == "auto" else language
    try:
        result = model.transcribe(str(p), language=whisper_language, word_timestamps=True, verbose=False)
    except Exception as exc:  # whisper/ffmpeg calisma zamani hatasi
        raise SubtitleError(f"Transkripsiyon başarısız: {exc}") from exc

    report(0.9, "Sonuçlar işleniyor…")
    transcript = _result_to_transcript(result, resegment=resegment)
    report(1.0, "Tamamlandı")
    return transcript
