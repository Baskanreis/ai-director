"""AI Subtitle: Whisper tabanlı otomatik altyazı motoru (v0.8 Subtitle Engine).

Alt modüller:
- `models`    : Word / Segment / Transcript veri modeli (Qt'den ve Whisper'dan bağımsız)
- `formats`   : SRT/VTT üretimi + kelime zaman damgalarından cümle/satır segmentasyonu
- `transcribe`: `openai-whisper` ile transkripsiyon (opsiyonel bağımlılık; kurulu
                değilse açık bir `SubtitleError` fırlatır)
- `embed`     : altyazıyı dosyaya (SRT/VTT) yazma, videoya gömülü altyazı (soft-sub,
                mov_text) veya "yakma" (burn-in) olarak ekleme

Türkçe öncelikli tasarlanmıştır (`transcribe.DEFAULT_LANGUAGE = "tr"`); İngilizce,
Almanca ve Fransızca da `transcribe.SUPPORTED_LANGUAGES` üzerinden desteklenir.
"""
from .editor import SubtitleEditor
from .models import Segment, Transcript, Word
from .style import Animation, Position, SubtitleStyle, get_preset

__all__ = [
    "Word",
    "Segment",
    "Transcript",
    "SubtitleEditor",
    "SubtitleStyle",
    "Position",
    "Animation",
    "get_preset",
]
