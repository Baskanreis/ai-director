"""Dolgu kelime (filler word) sözlükleri — v0.8 AI Basic Editor.

Türkçe öncelikli; `app.subtitle.transcribe.SUPPORTED_LANGUAGES` ile aynı dil
kümesini (tr/en/de/fr) kapsar. Saf veri + küçük bir eşleştirici, bağımlılık yok.
"""
from __future__ import annotations

FILLER_WORDS: dict[str, set[str]] = {
    "tr": {
        "şey", "yani", "işte", "hani", "aa", "aaa", "ee", "eee", "ıı", "ııı",
        "mm", "mmm", "aslında", "ya", "falan", "filan", "diyeyim", "nasıl desem",
    },
    "en": {
        "um", "uh", "umm", "uhh", "like", "you know", "i mean", "sort of", "kind of",
        "actually", "basically", "literally", "so yeah",
    },
    "de": {"äh", "ähm", "also", "halt", "sozusagen", "quasi"},
    "fr": {"euh", "ben", "genre", "voilà", "quoi", "en fait"},
}


def filler_words_for(language: str) -> set[str]:
    """`language` ("tr"/"en"/"de"/"fr"/"auto") için dolgu kelime kümesini döndürür.

    Bilinmeyen veya "auto" bir dil için tüm dillerin birleşimi döndürülür (daha
    az isabetli ama hiçbir şeyi kaçırmaz)."""
    if language in FILLER_WORDS:
        return FILLER_WORDS[language]
    union: set[str] = set()
    for words in FILLER_WORDS.values():
        union |= words
    return union


__all__ = ["FILLER_WORDS", "filler_words_for"]
