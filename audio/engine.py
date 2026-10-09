"""Klip/iz ses filtre parçalarının üretimi (v0.7 Audio Engine).

`app.export.command_builder`, her ses klibini `atrim`/`asetpts`/`aformat`
zincirine bağladıktan sonra bu modülün ürettiği ek filtreleri (kazanç, fade,
mute) o zincire ekler; her iz kendi içinde birleştirildikten (concat) sonra
da iz seviyesindeki filtreleri (kazanç, mute, normalizasyon) ve gerekiyorsa
ducking (sidechain compress) zincirini uygular.

Tüm fonksiyonlar saf Python'dur: ffmpeg çalıştırmazlar, yalnızca filtre
sözdizimi (string) üretirler — bu yüzden ffmpeg kurulu olmayan bir ortamda
bile test edilebilirler. Yalnızca `generate_waveform_peaks` gerçekten ffmpeg
çalıştırır (ve o da bulunamazsa `None` döner).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.effects.video_effects import piecewise_expr
from app.timeline.model import Clip, Track

EPS = 1e-3

# ---- ducking (sidechain compress) varsayılan parametreleri ------------------
# Sesli (voice) izler konuşurken müzik izinin otomatik kısılması için.
DUCK_THRESHOLD = 0.06   # doğrusal genlik eşiği (~ -24 dB); üzeri "konuşma var" sayılır
DUCK_RATIO = 8.0        # eşik üstünde ne kadar bastırılacağı
DUCK_ATTACK_MS = 5      # kısılmaya başlama süresi
DUCK_RELEASE_MS = 300   # eski seviyeye dönme süresi

# ---- normalizasyon (EBU R128 loudnorm) --------------------------------------
LOUDNORM_TARGET_I = -16.0   # entegre loudness hedefi (LUFS) — konuşma/podcast icin tipik
LOUDNORM_TARGET_TP = -1.5   # true-peak tavanı (dBTP)
LOUDNORM_TARGET_LRA = 11.0  # loudness range

# ---- ses enhancement varsayilanlari (v1.1 Audio Engine) ---------------------
VOICE_ENHANCE_HIGHPASS_HZ = 80.0
VOICE_ENHANCE_PRESENCE_HZ = 3000.0
VOICE_ENHANCE_PRESENCE_GAIN_DB = 4.0
VOICE_ENHANCE_PRESENCE_WIDTH = 1.5


def _fmt(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".") or "0"


def _audio_fx_fragments(obj) -> list[str]:
    """`Clip` ve `Track` icin ortak ek ses efektleri (v1.1 Audio Engine).

    Sira: gurultu azaltma -> EQ -> ses netlestirme (voice enhance) ->
    kompresor -> limiter. `obj`, `eq_bands`/`compressor`/`limiter`/`denoise`/
    `voice_enhance` alanlarina sahip olmalidir (Clip ve Track ikisi de sahip).
    """
    parts: list[str] = []

    if getattr(obj, "denoise", False):
        amount = max(0.01, min(97.0, float(getattr(obj, "denoise_amount", 12.0))))
        parts.append(f"afftdn=nr={_fmt(amount)}:nf=-25")

    for freq, gain in getattr(obj, "eq_bands", []) or []:
        if abs(gain) <= EPS:
            continue
        parts.append(f"equalizer=f={_fmt(freq)}:width_type=o:width=1:g={_fmt(gain)}")

    if getattr(obj, "voice_enhance", False):
        parts.append(f"highpass=f={_fmt(VOICE_ENHANCE_HIGHPASS_HZ)}")
        parts.append(
            f"equalizer=f={_fmt(VOICE_ENHANCE_PRESENCE_HZ)}:width_type=o:"
            f"width={_fmt(VOICE_ENHANCE_PRESENCE_WIDTH)}:g={_fmt(VOICE_ENHANCE_PRESENCE_GAIN_DB)}"
        )

    if getattr(obj, "compressor", False):
        threshold = max(0.001, min(1.0, float(getattr(obj, "comp_threshold", 0.1))))
        ratio = max(1.0, min(20.0, float(getattr(obj, "comp_ratio", 4.0))))
        attack = max(0.01, float(getattr(obj, "comp_attack_ms", 20.0)))
        release = max(0.01, float(getattr(obj, "comp_release_ms", 250.0)))
        makeup_db = float(getattr(obj, "comp_makeup_db", 0.0))
        makeup_linear = max(1.0, 10 ** (makeup_db / 20.0))
        parts.append(
            f"acompressor=threshold={_fmt(threshold)}:ratio={_fmt(ratio)}:"
            f"attack={_fmt(attack)}:release={_fmt(release)}:makeup={_fmt(makeup_linear)}"
        )

    if getattr(obj, "limiter", False):
        level = max(0.0625, min(1.0, float(getattr(obj, "limiter_level", 0.95))))
        parts.append(f"alimiter=limit={_fmt(level)}:attack=5:release=50")

    return parts


def clip_filter_fragment(clip: Clip) -> str | None:
    """Bir klip için ek ses filtreleri (mute/kazanç/fade). Yoksa `None`.

    `command_builder`, bunu `atrim=...,asetpts=...,aformat=...` zincirinin
    sonuna virgülle ekler; bu yüzden zaman referansları (fade `st=`) klibin
    kendi süresine (0..duration) görecelidir — `asetpts=PTS-STARTPTS` zaten
    uygulandığı için klip 0'dan başlar.
    """
    parts: list[str] = []
    if clip.muted:
        parts.append("volume=0")
        return ",".join(parts)  # sessizse diger efektlerin anlami yok

    volume_kfs = clip.keyframes.get("volume")
    if volume_kfs:
        # v1.4 Keyframe Engine: zamanla degisen kazanc (dB -> dogrusal carpan,
        # `pow(10, dB/20)`); `eval=frame` her karede yeniden hesaplanmasini saglar.
        db_expr = piecewise_expr(volume_kfs, "t", clip.gain_db)
        parts.append(f"volume=volume='pow(10,({db_expr})/20)':eval=frame")
    elif abs(clip.gain_db) > EPS:
        parts.append(f"volume={_fmt(clip.gain_db)}dB")

    parts.extend(_audio_fx_fragments(clip))

    dur = max(clip.duration, 0.0)
    if clip.fade_in > EPS and dur > EPS:
        d = min(clip.fade_in, dur)
        parts.append(f"afade=t=in:st=0:d={_fmt(d)}")
    if clip.fade_out > EPS and dur > EPS:
        d = min(clip.fade_out, dur)
        st = max(dur - d, 0.0)
        parts.append(f"afade=t=out:st={_fmt(st)}:d={_fmt(d)}")

    return ",".join(parts) if parts else None


def track_filter_fragment(track: Track) -> str | None:
    """Bir sesin izi (Track) için ek filtreler (mute/kazanç/normalizasyon)."""
    parts: list[str] = []
    if track.muted:
        parts.append("volume=0")
        return ",".join(parts)  # sessizse normalize etmenin anlamı yok
    if abs(track.gain_db) > EPS:
        parts.append(f"volume={_fmt(track.gain_db)}dB")
    parts.extend(_audio_fx_fragments(track))
    if track.normalize:
        parts.append(
            f"loudnorm=I={_fmt(LOUDNORM_TARGET_I)}:TP={_fmt(LOUDNORM_TARGET_TP)}:"
            f"LRA={_fmt(LOUDNORM_TARGET_LRA)}"
        )
    return ",".join(parts) if parts else None


def duck_filter_fragment(music_label: str, sidechain_label: str, out_label: str) -> str:
    """Müzik izini `sidechain_label` sinyaline göre kısan sidechaincompress filtresi.

    `music_label` ve `sidechain_label` köşeli parantezli ffmpeg pad etiketleridir
    (ör. `"[track0]"`, `"[duckref]"`); `out_label` parantezsiz çıktı adıdır.
    """
    return (
        f"{music_label}{sidechain_label}sidechaincompress=threshold={DUCK_THRESHOLD}:"
        f"ratio={DUCK_RATIO}:attack={DUCK_ATTACK_MS}:release={DUCK_RELEASE_MS}"
        f"[{out_label}]"
    )


# ---- waveform (dalga formu) üretimi -----------------------------------------

_WAVEFORM_CACHE_DIR = Path(tempfile.gettempdir()) / "ai_director_waveforms"


def _waveform_cache_path(path: Path, peaks_per_second: int) -> Path:
    _WAVEFORM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    stat = path.stat()
    key = f"{path.resolve()}|{stat.st_size}|{stat.st_mtime}|{peaks_per_second}"
    digest = hashlib.sha1(key.encode("utf-8", errors="ignore")).hexdigest()
    return _WAVEFORM_CACHE_DIR / f"{digest}.json"


def generate_waveform_peaks(
    path: str | Path, peaks_per_second: int = 25, max_peaks: int = 4000
) -> list[float] | None:
    """`path`teki sesin (video ya da ses dosyası) 0..1 aralığında peak listesini üretir.

    Her eleman, ilgili küçük zaman diliminde (yaklaşık `1/peaks_per_second`
    saniye) örneklerin mutlak tepe genliğidir (0 = sessizlik, 1 = tam ölçek).
    Sonuç diske önbelleklenir (aynı dosya için tekrar hesaplanmaz). ffmpeg
    veya numpy yoksa, ya da dosyada ses akışı yoksa `None` döner — çağıran
    taraf (timeline çizimi) bu durumda düz bir çizgi göstermelidir.
    """
    p = Path(path)
    if not p.is_file():
        return None
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    try:
        cache = _waveform_cache_path(p, peaks_per_second)
    except OSError:
        cache = None
    if cache is not None and cache.is_file():
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (OSError, ValueError):
            pass

    try:
        import numpy as np
    except ImportError:
        return None

    sample_rate = 4000  # kaba cozunurluk yeterli; hiz icin dusuk tutulur
    cmd = [
        ffmpeg, "-v", "error", "-i", str(p),
        "-ac", "1", "-ar", str(sample_rate), "-f", "s16le", "-",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0 or not proc.stdout:
        return None

    samples = np.frombuffer(proc.stdout, dtype="<i2").astype("float32") / 32768.0
    if samples.size == 0:
        return None

    chunk = max(int(sample_rate / max(peaks_per_second, 1)), 1)
    n_chunks = max(int(samples.size / chunk), 1)
    n_chunks = min(n_chunks, max_peaks)
    trimmed = samples[: n_chunks * chunk]
    if trimmed.size == 0:
        peaks = [float(np.abs(samples).max())]
    else:
        peaks = np.abs(trimmed).reshape(n_chunks, chunk).max(axis=1)
        peaks = [float(min(v, 1.0)) for v in peaks]

    if cache is not None:
        try:
            cache.write_text(json.dumps(peaks), encoding="utf-8")
        except OSError:
            pass
    return peaks
