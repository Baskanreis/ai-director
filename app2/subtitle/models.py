"""Altyazı veri modeli (Qt'den ve Whisper'dan bağımsız, saf Python).

- `Word`      : tek bir kelime + zaman damgası (kelime bazlı zamanlama, v0.8)
- `Segment`   : ekranda aynı anda gösterilecek bir altyazı satırı/bloğu (bir veya
                daha fazla `Word` içerebilir)
- `Transcript`: bir medyanın tüm transkripsiyonu (dil + segment listesi)
"""
from __future__ import annotations

from dataclasses import dataclass, field


class SubtitleError(RuntimeError):
    """Altyazı üretimi/işlenmesi başarısız oldu."""


@dataclass
class Word:
    text: str
    start: float
    end: float
    prob: float = 1.0  # Whisper'ın kelime güven skoru (0..1); yoksa 1.0

    @property
    def duration(self) -> float:
        return max(self.end - self.start, 0.0)

    def to_dict(self) -> dict:
        return {"text": self.text, "start": self.start, "end": self.end, "prob": self.prob}

    @classmethod
    def from_dict(cls, d: dict) -> "Word":
        return cls(
            text=str(d["text"]),
            start=float(d["start"]),
            end=float(d["end"]),
            prob=float(d.get("prob", 1.0)),
        )


@dataclass
class Segment:
    text: str
    start: float
    end: float
    words: list[Word] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return max(self.end - self.start, 0.0)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "words": [w.to_dict() for w in self.words],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Segment":
        return cls(
            text=str(d["text"]),
            start=float(d["start"]),
            end=float(d["end"]),
            words=[Word.from_dict(w) for w in d.get("words", [])],
        )


@dataclass
class Transcript:
    language: str
    segments: list[Segment] = field(default_factory=list)
    source_media_id: str | None = None

    @property
    def duration(self) -> float:
        return max((s.end for s in self.segments), default=0.0)

    def all_words(self) -> list[Word]:
        return [w for s in self.segments for w in s.words]

    def shifted(self, offset: float) -> "Transcript":
        """Tüm zaman damgalarını `offset` saniye kaydırılmış yeni bir transcript döndürür.

        Bir klip timeline'da `start` konumundaysa, timeline zamanına göre altyazı
        üretmek için `transcript.shifted(clip.start - clip.source_in)` kullanılır.
        """
        new_segments = []
        for s in self.segments:
            new_words = [Word(w.text, w.start + offset, w.end + offset, w.prob) for w in s.words]
            new_segments.append(Segment(s.text, s.start + offset, s.end + offset, new_words))
        return Transcript(self.language, new_segments, self.source_media_id)

    def to_dict(self) -> dict:
        return {
            "language": self.language,
            "source_media_id": self.source_media_id,
            "segments": [s.to_dict() for s in self.segments],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Transcript":
        return cls(
            language=str(d.get("language", "")),
            segments=[Segment.from_dict(s) for s in d.get("segments", [])],
            source_media_id=d.get("source_media_id"),
        )
