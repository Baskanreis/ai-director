"""Video/konuşma analizi — v0.8 AI Basic Editor.

Spesifikasyondaki beş analiz türünü karşılar:

1. **sessizlik**      -> `detect_silence_regions` (ffmpeg `silencedetect`, ses tabanlı)
2. **uzun duraklamalar** -> `detect_long_pauses` (transkript kelimeleri ARASI boşluk, saf Python)
3. **tekrar**          -> `detect_repetitions` (ardışık/yakın tekrar eden kelime-öbeği, saf Python)
4. **dolgu kelimeleri** -> `detect_filler_words` (bkz. `filler_words.py`, saf Python)
5. **sahne değişimleri** -> `app.scene.detector.detect_scene_changes` (ffmpeg, mevcut v1.0 modülü)

Ayrıca "önemli kelimeleri vurgula" önerisi için `suggest_highlight_words` — bu,
`app.subtitle.ass_format`'taki kelime vurgulama özelliğiyle doğrudan bağlanır.

Yalnızca `detect_silence_regions` ve sahne tespiti gerçekten ffmpeg çalıştırır;
geri kalan her şey saf Pythondur ve zaten elde bir `Transcript` (bkz.
`app.subtitle.transcribe`) olduğunda ffmpeg'siz test edilebilir.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from app.subtitle.models import Transcript, Word

from .filler_words import filler_words_for
from .models import AnalysisReport, Suggestion, SuggestionKind

DEFAULT_LONG_PAUSE_SEC = 1.2
DEFAULT_SILENCE_NOISE_DB = -35.0
DEFAULT_SILENCE_MIN_DUR = 0.6
DEFAULT_REPETITION_WINDOW_SEC = 2.5
DEFAULT_MAX_HIGHLIGHT_WORDS = 8
MIN_HIGHLIGHT_WORD_LEN = 5

_TR_STOPWORDS = {
    "ve", "ile", "bir", "bu", "şu", "o", "da", "de", "ki", "mi", "mı", "mu", "mü",
    "için", "gibi", "ama", "fakat", "ya", "ne", "çok", "daha", "en", "her", "hem",
    "ben", "sen", "biz", "siz", "onlar", "var", "yok", "oldu", "olan", "olarak",
}

_PUNCT_RE = re.compile(r"[.,!?…;:\"'()\[\]{}]")


def _normalize(word: str) -> str:
    return _PUNCT_RE.sub("", word).strip().lower()


# ---------------------------------------------------------------------------
# 2. uzun duraklamalar (saf Python — transkript kelime boşlukları)
# ---------------------------------------------------------------------------

def detect_long_pauses(transcript: Transcript, min_pause: float = DEFAULT_LONG_PAUSE_SEC) -> list[Suggestion]:
    """Ardışık iki kelime arasında `min_pause` saniyeden uzun boşlukları bulur."""
    words = sorted(transcript.all_words(), key=lambda w: w.start)
    out: list[Suggestion] = []
    for a, b in zip(words, words[1:]):
        gap = b.start - a.end
        if gap >= min_pause:
            out.append(
                Suggestion(
                    kind=SuggestionKind.LONG_PAUSE, start=a.end, end=b.start,
                    label=f"Uzun duraklama ({gap:.1f} sn)",
                    detail=f"'{a.text.strip()}' ile '{b.text.strip()}' arasında",
                )
            )
    return out


# ---------------------------------------------------------------------------
# 3. tekrar (saf Python — yakın zamanda tekrar eden kelime/öbek)
# ---------------------------------------------------------------------------

def detect_repetitions(
    transcript: Transcript, window: float = DEFAULT_REPETITION_WINDOW_SEC
) -> list[Suggestion]:
    """Aynı kelimenin (ör. kekeleme: "şey şey", "yani yani") veya kısa bir öbeğin
    `window` saniye içinde tekrarlandığı durumları bulur. Yalnızca TEKRARLANAN
    (ilk geçen hariç) kısmı kesime aday gösterir — ilk söyleyiş korunur."""
    words = sorted(transcript.all_words(), key=lambda w: w.start)
    out: list[Suggestion] = []

    # (a) tek kelime ardışık tekrarı: "bu bu", "çok çok çok"
    i = 0
    while i < len(words) - 1:
        norm = _normalize(words[i].text)
        if not norm:
            i += 1
            continue
        j = i + 1
        while j < len(words) and _normalize(words[j].text) == norm and words[j].start - words[j - 1].end <= window:
            j += 1
        if j - i >= 2:  # en az bir tekrar var
            out.append(
                Suggestion(
                    kind=SuggestionKind.REPETITION, start=words[i + 1].start, end=words[j - 1].end,
                    label=f"Tekrar: \"{words[i].text.strip()}\" ({j - i} kez)",
                    detail="İlk söyleyiş korunur, tekrarlar kesime aday.",
                )
            )
            i = j
        else:
            i += 1

    # (b) kısa öbek tekrarı (2-4 kelimelik): "ben de düşünüyorum ki ... ben de düşünüyorum ki"
    for phrase_len in (2, 3, 4):
        k = 0
        while k + 2 * phrase_len <= len(words):
            a_words = words[k : k + phrase_len]
            b_words = words[k + phrase_len : k + 2 * phrase_len]
            a_norm = tuple(_normalize(w.text) for w in a_words)
            b_norm = tuple(_normalize(w.text) for w in b_words)
            if all(a_norm) and a_norm == b_norm and b_words[0].start - a_words[-1].end <= window:
                out.append(
                    Suggestion(
                        kind=SuggestionKind.REPETITION,
                        start=b_words[0].start, end=b_words[-1].end,
                        label=f"Tekrar öbeği: \"{' '.join(w.text.strip() for w in a_words)}\"",
                        detail="İlk söyleyiş korunur, tekrar eden öbek kesime aday.",
                    )
                )
                k += 2 * phrase_len
            else:
                k += 1
    out.sort(key=lambda s: s.start)
    return out


# ---------------------------------------------------------------------------
# 4. dolgu kelimeleri (saf Python)
# ---------------------------------------------------------------------------

def detect_filler_words(transcript: Transcript, language: str = "tr") -> list[Suggestion]:
    """Dolgu kelimelerini (bkz. `filler_words.py`) bulur; ardışık olanları tek öneride birleştirir."""
    fillers = filler_words_for(language)
    words = sorted(transcript.all_words(), key=lambda w: w.start)
    out: list[Suggestion] = []
    i = 0
    while i < len(words):
        if _normalize(words[i].text) in fillers:
            j = i
            while j + 1 < len(words) and _normalize(words[j + 1].text) in fillers:
                j += 1
            span_words = words[i : j + 1]
            out.append(
                Suggestion(
                    kind=SuggestionKind.FILLER_WORD,
                    start=span_words[0].start, end=span_words[-1].end,
                    label=f"Dolgu kelime: \"{' '.join(w.text.strip() for w in span_words)}\"",
                )
            )
            i = j + 1
        else:
            i += 1
    return out


# ---------------------------------------------------------------------------
# önemli kelimeleri vurgula (saf Python)
# ---------------------------------------------------------------------------

def suggest_highlight_words(
    transcript: Transcript, max_words: int = DEFAULT_MAX_HIGHLIGHT_WORDS, language: str = "tr"
) -> list[Suggestion]:
    """Altyazıda vurgulanmaya değer "önemli" kelimeleri önerir (basit sezgisel:
    uzun, dolgu/stopword olmayan içerik kelimeleri; segment başına en fazla bir tane,
    toplamda en fazla `max_words`)."""
    fillers = filler_words_for(language)
    stop = _TR_STOPWORDS if language == "tr" else set()
    out: list[Suggestion] = []
    for seg in transcript.segments:
        best: Word | None = None
        for w in seg.words:
            norm = _normalize(w.text)
            if len(norm) < MIN_HIGHLIGHT_WORD_LEN or norm in fillers or norm in stop:
                continue
            if best is None or len(norm) > len(_normalize(best.text)):
                best = w
        if best is not None:
            out.append(
                Suggestion(
                    kind=SuggestionKind.HIGHLIGHT_WORD, start=best.start, end=best.end,
                    label=f"Önemli kelime: \"{best.text.strip()}\"", word=_normalize(best.text),
                )
            )
        if len(out) >= max_words:
            break
    return out


# ---------------------------------------------------------------------------
# 1. sessizlik (ffmpeg `silencedetect` — ses tabanlı, transkriptten bağımsız)
# ---------------------------------------------------------------------------

class AnalysisError(RuntimeError):
    """AI analizi çalıştırılamadı (ör. ffmpeg eksik/başarısız)."""


_SILENCE_START_RE = re.compile(r"silence_start:\s*(-?[0-9]+\.?[0-9]*)")
_SILENCE_END_RE = re.compile(r"silence_end:\s*(-?[0-9]+\.?[0-9]*)")


def detect_silence_regions(
    path: str | Path,
    noise_db: float = DEFAULT_SILENCE_NOISE_DB,
    min_duration: float = DEFAULT_SILENCE_MIN_DUR,
    ffmpeg_exe: str | None = None,
    timeout: float | None = None,
) -> list[Suggestion]:
    """`path`teki medyanın sessiz bölgelerini ffmpeg'in `silencedetect` filtresiyle bulur.

    `noise_db`'nin altındaki (yani bu kadar sessiz) ve `min_duration` saniyeden uzun
    bölgeler döndürülür. Video/ses çıktısı üretilmez (`-f null -`), yalnızca analiz
    loglarından zaman damgaları okunur — `app.scene.detector.detect_scene_changes`
    ile aynı yaklaşım. ffmpeg kurulu değilse `AnalysisError` fırlatır.
    """
    p = Path(path)
    if not p.is_file():
        raise AnalysisError(f"Dosya bulunamadı: {p}")
    exe = ffmpeg_exe or shutil.which("ffmpeg")
    if not exe:
        raise AnalysisError("ffmpeg bulunamadı; sessizlik tespiti için ffmpeg gereklidir")

    cmd = [
        exe, "-hide_banner", "-nostats", "-loglevel", "info",
        "-i", str(p),
        "-af", f"silencedetect=noise={noise_db}dB:d={min_duration}",
        "-vn", "-f", "null", "-",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise AnalysisError("Sessizlik tespiti zaman aşımına uğradı") from exc
    except (OSError, subprocess.SubprocessError) as exc:
        raise AnalysisError(f"ffmpeg çalıştırılamadı: {exc}") from exc

    text = (proc.stderr or "") + "\n" + (proc.stdout or "")
    if proc.returncode != 0 and not _SILENCE_START_RE.search(text):
        raise AnalysisError(f"ffmpeg başarısız oldu:\n{(proc.stderr or '')[-2000:]}")

    starts = [float(m.group(1)) for m in _SILENCE_START_RE.finditer(text)]
    ends = [float(m.group(1)) for m in _SILENCE_END_RE.finditer(text)]
    out: list[Suggestion] = []
    for start, end in zip(starts, ends):
        if end > start:
            out.append(
                Suggestion(
                    kind=SuggestionKind.SILENCE, start=start, end=end,
                    label=f"Sessizlik ({end - start:.1f} sn)",
                )
            )
    return out


# ---------------------------------------------------------------------------
# toplayıcı
# ---------------------------------------------------------------------------

def build_report(
    clip_id: str,
    media_path: str | Path,
    transcript: Transcript | None,
    language: str = "tr",
    include_silence: bool = True,
    include_scenes: bool = True,
    long_pause_threshold: float = DEFAULT_LONG_PAUSE_SEC,
    silence_noise_db: float = DEFAULT_SILENCE_NOISE_DB,
    silence_min_duration: float = DEFAULT_SILENCE_MIN_DUR,
    ffmpeg_exe: str | None = None,
) -> AnalysisReport:
    """Tüm analiz türlerini çalıştırıp tek bir `AnalysisReport`te birleştirir.

    `transcript` yoksa (ör. henüz altyazı çıkarılmamışsa) yalnızca ses/sahne
    tabanlı analizler (sessizlik, sahne değişimi) çalışır ve bir "ADD_SUBTITLE"
    önerisi eklenir ("altyazı ekle"); kelime bazlı analizler (tekrar/dolgu/uzun
    duraklama/önemli kelime) atlanır çünkü bunlar transkript gerektirir.
    """
    suggestions: list[Suggestion] = []

    if transcript is not None and transcript.segments:
        suggestions.extend(detect_long_pauses(transcript, min_pause=long_pause_threshold))
        suggestions.extend(detect_repetitions(transcript))
        suggestions.extend(detect_filler_words(transcript, language=language))
        suggestions.extend(suggest_highlight_words(transcript, language=language))
    else:
        suggestions.append(
            Suggestion(
                kind=SuggestionKind.ADD_SUBTITLE, start=0.0, end=0.0,
                label="Altyazı ekle", detail="Bu klip için henüz transkript yok (AI Subtitle ile çıkarılabilir).",
            )
        )

    if include_silence:
        try:
            suggestions.extend(
                detect_silence_regions(
                    media_path, noise_db=silence_noise_db, min_duration=silence_min_duration, ffmpeg_exe=ffmpeg_exe
                )
            )
        except AnalysisError:
            pass  # ffmpeg yoksa/başarısızsa sessizlik analizi sessizce atlanır

    if include_scenes:
        try:
            from app.scene.detector import SceneDetectionError, detect_scene_changes

            for t in detect_scene_changes(media_path, ffmpeg_exe=ffmpeg_exe):
                suggestions.append(
                    Suggestion(
                        kind=SuggestionKind.SCENE_CHANGE, start=t, end=t,
                        label=f"Sahne değişimi ({t:.1f} sn)", accepted=False,  # bilgi amaçlı, varsayılan kapalı
                    )
                )
        except (AnalysisError, ImportError):
            pass
        except Exception:  # scene detector kendi hata sınıfını fırlatabilir
            pass

    suggestions.sort(key=lambda s: s.start)
    return AnalysisReport(clip_id=clip_id, media_path=str(media_path), suggestions=suggestions)


__all__ = [
    "AnalysisError",
    "detect_long_pauses",
    "detect_repetitions",
    "detect_filler_words",
    "suggest_highlight_words",
    "detect_silence_regions",
    "build_report",
]
