"""AI Basic Editor veri modeli — v0.8 AI Basic Editor.

Analiz aşaması (`analyzer.py`) bir dizi `Suggestion` üretir; kullanıcı her birini
kabul/ret edebilir (`accepted`); kabul edilenler `apply.py` ile timeline'a uygulanır.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SuggestionKind(str, Enum):
    SILENCE = "silence"              # sessizlikleri kes
    LONG_PAUSE = "long_pause"        # uzun duraklamaları kes
    REPETITION = "repetition"        # tekrarları azalt
    FILLER_WORD = "filler_word"      # dolgu kelimeleri çıkar (gereksiz bölüm)
    SCENE_CHANGE = "scene_change"    # bilgi amaçlı: sahne değişimi tespit edildi
    ADD_SUBTITLE = "add_subtitle"    # altyazı ekle
    HIGHLIGHT_WORD = "highlight_word"  # önemli kelimeyi vurgula


# Hangi öneri türleri, kabul edildiğinde timeline'dan bir zaman aralığını KESER.
CUT_KINDS: frozenset[SuggestionKind] = frozenset(
    {SuggestionKind.SILENCE, SuggestionKind.LONG_PAUSE, SuggestionKind.REPETITION, SuggestionKind.FILLER_WORD}
)


@dataclass
class Suggestion:
    """Tek bir AI önerisi. `start`/`end`, klibin KAYNAK medya zamanına (saniye) göredir
    (timeline zamanı değil) — `apply.py`, klibin `source_in`/`start` farkıyla çevirir."""

    kind: SuggestionKind
    start: float
    end: float
    label: str          # kısa, kullanıcıya gösterilecek başlık (ör. "Sessizlik (2.3 sn)")
    detail: str = ""     # ek açıklama (ör. tespit edilen kelime/metin)
    accepted: bool = True  # varsayılan: kabul edilmiş (kullanıcı reddedebilir)
    word: str | None = None  # HIGHLIGHT_WORD için: vurgulanacak kelime

    @property
    def duration(self) -> float:
        return max(self.end - self.start, 0.0)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind.value, "start": self.start, "end": self.end,
            "label": self.label, "detail": self.detail, "accepted": self.accepted, "word": self.word,
        }


@dataclass
class AnalysisReport:
    """Bir klip için üretilen tüm önerilerin toplamı."""

    clip_id: str
    media_path: str
    suggestions: list[Suggestion] = field(default_factory=list)

    def by_kind(self, kind: SuggestionKind) -> list[Suggestion]:
        return [s for s in self.suggestions if s.kind == kind]

    def accepted(self) -> list[Suggestion]:
        return [s for s in self.suggestions if s.accepted]

    def total_cut_seconds(self) -> float:
        return sum(s.duration for s in self.accepted() if s.kind in CUT_KINDS)


__all__ = ["SuggestionKind", "CUT_KINDS", "Suggestion", "AnalysisReport"]
