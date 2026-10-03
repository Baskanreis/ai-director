"""Transkripsiyon sonrası altyazı düzenleme (v0.7 Subtitle Engine — Subtitle editing).

Whisper her zaman mükemmel değildir: yazım hataları, yanlış bölünmüş satırlar,
hatalı zamanlama olabilir. Bu modül, bir `Transcript` üzerinde satır bazlı
düzenlemeleri (metin değiştirme, zamanlama değiştirme, bölme, birleştirme,
ekleme, silme, tüm zamanlamayı kaydırma) güvenli şekilde uygulayan, saf Python
(Qt/ffmpeg gerektirmeyen, bağımsız test edilebilir) bir yardımcı sınıftır.

`SubtitleDialog` (UI), kullanıcının düzenleme tablosundaki her değişikliği bu
sınıf üzerinden `self.transcript`'e uygular.
"""
from __future__ import annotations

from dataclasses import replace

from .models import Segment, SubtitleError, Transcript, Word


class SubtitleEditor:
    """Bir `Transcript` üzerinde satır (segment) bazlı düzenleme işlemleri.

    Tüm metotlar `self.transcript`'i yerinde değiştirir (segment listesi mutasyona
    uğrar) ve zincirlenebilmesi için `self`'i döndürür. Sıra her zaman başlangıç
    zamanına göre korunur.
    """

    def __init__(self, transcript: Transcript) -> None:
        self.transcript = transcript

    # ---------------- iç yardımcılar ----------------
    def _segments(self) -> list[Segment]:
        return self.transcript.segments

    def _check_index(self, index: int) -> None:
        if not (0 <= index < len(self._segments())):
            raise SubtitleError(f"Geçersiz satır indeksi: {index} (toplam {len(self._segments())} satır)")

    def _resort(self) -> None:
        self.transcript.segments.sort(key=lambda s: s.start)

    # ---------------- metin / zamanlama düzenleme ----------------
    def update_text(self, index: int, new_text: str) -> "SubtitleEditor":
        """Bir satırın metnini değiştirir (zamanlama/kelimeler etkilenmez)."""
        self._check_index(index)
        seg = self._segments()[index]
        self._segments()[index] = replace(seg, text=new_text.strip())
        return self

    def update_timing(self, index: int, start: float, end: float) -> "SubtitleEditor":
        """Bir satırın başlangıç/bitiş zamanını değiştirir.

        `end`, `start`'tan büyük olmalıdır. Kelime zamanlamaları satırın yeni
        aralığına orantılı olarak yeniden ölçeklenir (varsa), böylece tutarlı kalır.
        """
        self._check_index(index)
        if end <= start:
            raise SubtitleError(f"Bitiş zamanı başlangıçtan büyük olmalı (start={start}, end={end})")
        seg = self._segments()[index]
        old_dur = max(seg.end - seg.start, 1e-6)
        new_words: list[Word] = []
        for w in seg.words:
            rel_start = (w.start - seg.start) / old_dur
            rel_end = (w.end - seg.start) / old_dur
            new_words.append(
                Word(
                    text=w.text,
                    start=start + rel_start * (end - start),
                    end=start + rel_end * (end - start),
                    prob=w.prob,
                )
            )
        self._segments()[index] = replace(seg, start=start, end=end, words=new_words)
        # İndeksi koru: UI tablo satırı, timing değişikliğinden hemen sonra aynı
        # segmenti göstermeye devam etmelidir. Yeniden sıralama, toplu düzenleme
        # akışında çağıran katmanın açıkça istediği bir işlem olmalıdır.
        return self

    def delete(self, index: int) -> "SubtitleEditor":
        self._check_index(index)
        del self._segments()[index]
        return self

    def insert(self, index: int, segment: Segment) -> "SubtitleEditor":
        """`index` konumuna yeni bir satır ekler (ör. kaçırılmış bir cümle için)."""
        if not (0 <= index <= len(self._segments())):
            raise SubtitleError(f"Geçersiz ekleme indeksi: {index}")
        self._segments().insert(index, segment)
        self._resort()
        return self

    def merge(self, index_a: int, index_b: int) -> "SubtitleEditor":
        """İki (genelde ardışık) satırı tek satırda birleştirir; metinler boşlukla birleşir,
        zaman aralığı ikisini de kapsayacak şekilde genişler, kelime listeleri birleşir."""
        self._check_index(index_a)
        self._check_index(index_b)
        if index_a == index_b:
            raise SubtitleError("Aynı satır kendisiyle birleştirilemez")
        segs = self._segments()
        a, b = (segs[index_a], segs[index_b]) if index_a < index_b else (segs[index_b], segs[index_a])
        lo, hi = min(index_a, index_b), max(index_a, index_b)
        merged = Segment(
            text=f"{a.text.strip()} {b.text.strip()}".strip(),
            start=min(a.start, b.start),
            end=max(a.end, b.end),
            words=sorted([*a.words, *b.words], key=lambda w: w.start),
        )
        del segs[hi]
        del segs[lo]
        segs.insert(lo, merged)
        self._resort()
        return self

    def split(self, index: int, at_word_index: int) -> "SubtitleEditor":
        """Bir satırı, kelime listesindeki `at_word_index`'ten itibaren ikiye böler
        (`at_word_index`'teki kelime ikinci satırda başlar). Kelime zamanlaması yoksa
        (ör. Whisper kelime zamanlaması kapalıysa) `SubtitleError` fırlatır."""
        self._check_index(index)
        seg = self._segments()[index]
        if not seg.words or not (0 < at_word_index < len(seg.words)):
            raise SubtitleError(
                "Bölme için satırda en az 2 kelimelik zaman damgası gerekir "
                f"(satırda {len(seg.words)} kelime var, bölme noktası {at_word_index})"
            )
        left_words = seg.words[:at_word_index]
        right_words = seg.words[at_word_index:]
        left = Segment(
            text=" ".join(w.text.strip() for w in left_words), start=left_words[0].start,
            end=left_words[-1].end, words=left_words,
        )
        right = Segment(
            text=" ".join(w.text.strip() for w in right_words), start=right_words[0].start,
            end=right_words[-1].end, words=right_words,
        )
        segs = self._segments()
        segs[index] = left
        segs.insert(index + 1, right)
        self._resort()
        return self

    # ---------------- toplu zamanlama ----------------
    def shift_all(self, offset: float) -> "SubtitleEditor":
        """Tüm satırların zamanlamasını `offset` saniye kaydırır (negatif de olabilir;
        sonuç negatif zamana düşerse `SubtitleError` fırlatır)."""
        segs = self._segments()
        if segs and min(s.start for s in segs) + offset < 0:
            raise SubtitleError("Kaydırma, bir satırı negatif zamana taşır")
        self.transcript.segments = [
            Segment(
                text=s.text, start=s.start + offset, end=s.end + offset,
                words=[Word(w.text, w.start + offset, w.end + offset, w.prob) for w in s.words],
            )
            for s in segs
        ]
        return self

    def shift_from(self, index: int, offset: float) -> "SubtitleEditor":
        """`index`'teki satırdan itibaren (dahil) tüm sonraki satırları kaydırır —
        ör. bir satırın süresini uzattıktan sonra geri kalanların kaymasını önlemek için."""
        self._check_index(index)
        segs = self._segments()
        if offset < 0 and segs[index].start + offset < 0:
            raise SubtitleError("Kaydırma, bir satırı negatif zamana taşır")
        for i in range(index, len(segs)):
            s = segs[i]
            segs[i] = Segment(
                text=s.text, start=s.start + offset, end=s.end + offset,
                words=[Word(w.text, w.start + offset, w.end + offset, w.prob) for w in s.words],
            )
        return self


__all__ = ["SubtitleEditor"]
