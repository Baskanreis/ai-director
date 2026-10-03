"""Anahtar kelimeye dayalı otomatik emoji ekleme (v0.7 Subtitle Engine — Emoji support).

Saf Python, harici bağımlılık yok. Metin zaten UTF-8 olarak işlendiğinden
(`formats.py`, `ass_format.py` hep `encoding="utf-8"` kullanır) emoji karakterleri
sorunsuz saklanır/yazılır; burada eklenen şey yalnızca **hangi kelimenin hangi
emojiyi tetikleyeceğine** dair basit, belirleyici bir sözlük + eşleştiricidir.

Not: Yakılan (burn-in) altyazılarda emoji'nin *renkli* görünmesi, kullanılan
fontun renkli emoji glifleri içermesine bağlıdır (ör. "Noto Color Emoji");
bkz. `style.SubtitleStyle.emoji_font`. Bu modül emoji seçimini/yerleştirmesini
yönetir, glif render kalitesini değil.
"""
from __future__ import annotations

import re

from .models import Segment, Transcript

# Türkçe öncelikli, İngilizce de desteklenir. Anahtarlar küçük harf + Türkçe'ye
# duyarlı şekilde karşılaştırılır (bkz. `_normalize`). Her anahtara TEK bir emoji
# atanır; bir segmentte birden fazla anahtar eşleşirse en fazla `max_per_segment`
# tanesi (ilk eşleşen sırayla) eklenir.
EMOJI_KEYWORDS: dict[str, str] = {
    # duygular
    "mutlu": "😊", "sevin": "😄", "gül": "😂", "harika": "🤩", "süper": "🤩",
    "üzgün": "😢", "üzül": "😢", "ağla": "😭", "kork": "😨", "şaşır": "😮",
    "kız": "😠", "sinir": "😠", "aşk": "❤️", "sev": "❤️",
    "happy": "😊", "sad": "😢", "love": "❤️", "amazing": "🤩", "wow": "😮",
    "angry": "😠", "laugh": "😂", "cry": "😭", "scared": "😨",
    # eylem/sembol
    "para": "💰", "ödeme": "💰", "money": "💰", "ateş": "🔥", "fire": "🔥",
    "yıldız": "⭐", "star": "⭐", "tebrik": "🎉", "kutla": "🎉", "parti": "🎉",
    "uyarı": "⚠️", "dikkat": "⚠️", "warning": "⚠️", "tamam": "✅", "doğru": "✅",
    "yanlış": "❌", "hayır": "❌", "soru": "❓", "zaman": "⏰", "saat": "⏰",
    "hız": "⚡", "fast": "⚡", "fikir": "💡", "idea": "💡", "müzik": "🎵",
    "music": "🎵", "video": "🎬", "kamera": "📷", "telefon": "📱",
    "bilgisayar": "💻", "kalp": "❤️", "göz": "👀", "el": "👋", "selam": "👋",
    "merhaba": "👋", "teşekkür": "🙏", "lütfen": "🙏",
}

_TR_MAP = str.maketrans("İIŞşĞğÜüÖöÇç", "iisşgğuüoöçc")  # kaba, aksansız normalize


def _normalize(word: str) -> str:
    return word.translate(_TR_MAP).lower().strip(".,!?…\"'()[]{}:;")


def find_emojis(text: str, max_matches: int = 2) -> list[str]:
    """Metindeki kelimeleri `EMOJI_KEYWORDS`'e göre tarar, bulunan emojileri (sırayla,
    tekrarsız, en fazla `max_matches` adet) döndürür. Eşleşme yoksa boş liste döner.
    """
    found: list[str] = []
    seen_emoji: set[str] = set()
    for raw in re.split(r"\s+", text):
        word = _normalize(raw)
        if not word:
            continue
        for key, emoji in EMOJI_KEYWORDS.items():
            if key in word and emoji not in seen_emoji:
                found.append(emoji)
                seen_emoji.add(emoji)
                break
        if len(found) >= max_matches:
            break
    return found


def annotate_text(text: str, max_matches: int = 2) -> str:
    """Metnin sonuna, içeriğiyle eşleşen emojileri (varsa) ekler."""
    emojis = find_emojis(text, max_matches=max_matches)
    if not emojis:
        return text
    return f"{text.rstrip()} {' '.join(emojis)}"


def annotate_transcript(transcript: Transcript, max_matches: int = 2) -> Transcript:
    """`transcript`'in HER segmentine, metnine uygun emoji eklenmiş yeni bir kopyasını döndürür.

    Orijinal `transcript` değiştirilmez (saf fonksiyon); kelime zamanlamaları etkilenmez,
    yalnızca `Segment.text` güncellenir (emoji kelime bazlı zamanlamaya dahil edilmez).
    """
    new_segments: list[Segment] = []
    for seg in transcript.segments:
        new_segments.append(
            Segment(text=annotate_text(seg.text, max_matches=max_matches), start=seg.start, end=seg.end, words=seg.words)
        )
    return Transcript(language=transcript.language, segments=new_segments, source_media_id=transcript.source_media_id)


__all__ = ["EMOJI_KEYWORDS", "find_emojis", "annotate_text", "annotate_transcript"]
