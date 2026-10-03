"""Sahne değişimi (scene cut) tespiti — v1.0 Scene Detection.

Ayrı bir OpenCV/PySceneDetect bağımlılığı eklemez: projenin geri kalanıyla aynı
yaklaşımı izler (bkz. `app/video/media_info.py`, `app/export/ffmpeg_export.py`) —
yalnızca sistemde zaten ZORUNLU olan `ffmpeg`'i bir alt süreç olarak çalıştırır.

ffmpeg'in `select` filtresindeki `scene` değişkeni, ardışık iki kare arasındaki
göreli görsel farkı 0..1 aralığında verir (kesmeler/sert geçişlerde yüksek,
sabit kameralı sahnelerde ~0'a yakın). `gt(scene, threshold)` koşulunu geçen
her kare, `showinfo` filtresiyle zaman damgası olarak loglanır; hiçbir video/ses
çıktısı üretilmez (`-f null -`), yani bu işlem gerçek zamanlıdan çok daha hızlı
çalışır ve diske yazmaz.

Bulunan zaman damgaları saf Python ile (`split_at_scenes`) bir timeline klibini
bölmek için kullanılabilir; bu kısım ffmpeg gerektirmediği için bağımsız test
edilebilir.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from app.timeline.model import Timeline

DEFAULT_THRESHOLD = 0.4
MIN_THRESHOLD = 0.05
MAX_THRESHOLD = 0.95

# ffmpeg `showinfo` her eşleşen kare için stderr'e örn. "... pts_time:12.345 ..." yazar.
_PTS_RE = re.compile(r"pts_time:\s*([0-9]+\.?[0-9]*)")


class SceneDetectionError(RuntimeError):
    """Sahne tespiti çalıştırılamadı."""


def ffmpeg_available(ffmpeg_exe: str | None = None) -> bool:
    """ffmpeg sistemde kurulu mu (veya verilen yol geçerli mi)?"""
    return bool(ffmpeg_exe or shutil.which("ffmpeg"))


def detect_scene_changes(
    path: str | Path,
    threshold: float = DEFAULT_THRESHOLD,
    ffmpeg_exe: str | None = None,
    timeout: float | None = None,
) -> list[float]:
    """`path`teki videonun sahne değiştiği zaman damgalarını (saniye) döndürür.

    `threshold` (0..1) ne kadar düşükse o kadar çok (ve o kadar küçük görsel
    değişiklikleri de içeren) kesim bulunur; varsayılan `0.4` sert kesmeler için
    makul bir denge noktasıdır. Video/ses akışı üretilmez, yalnızca ffmpeg'in
    analiz loglarından zaman damgaları okunur.

    ffmpeg kurulu değilse veya dosya işlenemezse `SceneDetectionError` fırlatır.
    Sahne bulunamazsa (ör. tek çekimlik statik bir video) boş liste döner —
    bu bir hata değildir.
    """
    p = Path(path)
    if not p.is_file():
        raise SceneDetectionError(f"Dosya bulunamadı: {p}")
    if not (MIN_THRESHOLD <= threshold <= MAX_THRESHOLD):
        raise SceneDetectionError(
            f"threshold {MIN_THRESHOLD} ile {MAX_THRESHOLD} arasında olmalı (verilen: {threshold})"
        )
    exe = ffmpeg_exe or shutil.which("ffmpeg")
    if not exe:
        raise SceneDetectionError("ffmpeg bulunamadı; sahne tespiti için ffmpeg gereklidir")

    cmd = [
        exe, "-hide_banner", "-nostats", "-loglevel", "info",
        "-i", str(p),
        "-filter:v", f"select='gt(scene,{threshold})',showinfo",
        "-an", "-f", "null", "-",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise SceneDetectionError("Sahne tespiti zaman aşımına uğradı") from exc
    except (OSError, subprocess.SubprocessError) as exc:
        raise SceneDetectionError(f"ffmpeg çalıştırılamadı: {exc}") from exc

    # showinfo çıktısı "info" seviyesinde ve ffmpeg'de stderr'e yazılır; bazı
    # derlemelerde/ortamlarda stdout'a da sızabildiği görüldüğünden ikisi de taranır.
    text = (proc.stderr or "") + "\n" + (proc.stdout or "")
    if proc.returncode != 0 and not _PTS_RE.search(text):
        raise SceneDetectionError(f"ffmpeg başarısız oldu:\n{(proc.stderr or '')[-2000:]}")

    times = sorted({round(float(m.group(1)), 3) for m in _PTS_RE.finditer(text)})
    return times


def split_at_scenes(timeline: Timeline, clip_id: str, scene_times: list[float]) -> int:
    """Bir klibi, kendi kaynak medyası için hesaplanmış sahne zaman damgalarında böler.

    `scene_times`, klibin bağlı olduğu medyanın TAMAMI için `detect_scene_changes`
    ile (kaynak zamanına göre, 0'dan itibaren) hesaplanmış zaman damgalarıdır.
    Bunlardan yalnızca klibin şu an kullandığı `[source_in, source_out)` aralığına
    denk gelenler, klibin timeline üzerindeki karşılık gelen mutlak konumuna
    (`clip.start + (t - source_in)`) çevrilip sırayla bölünür. Bağlı klipler
    (ör. aynı medyanın video + ses parçası) `Timeline.split` tarafından otomatik
    olarak birlikte bölünür; timeline'daki İLİŞKİSİZ diğer klipler etkilenmez.

    Döndürülen değer, başarıyla uygulanan bölme sayısıdır (0 = uygun kesim yok).
    """
    found = timeline.find(clip_id)
    if not found:
        return 0
    track, clip = found
    source_in, source_out = clip.source_in, clip.source_out
    # Kenara çok yakın kesimler (pratikte kırpılamayacak kadar kısa bir parça
    # doğuracak kesimler) atlanır; Timeline.split zaten MIN_CLIP kontrolü yapar,
    # burada yalnızca gereksiz deneme sayısını azaltmak için bir marj kullanılır.
    margin = 0.05
    positions = sorted(
        clip.start + (t - source_in)
        for t in scene_times
        if source_in + margin < t < source_out - margin
    )
    count = 0
    current_id = clip_id
    for at in positions:
        cur = next((c for c in track.clips if c.id == current_id), None)
        if cur is None or not (cur.start < at < cur.end):
            # Onceki bolmeler sonrasi id degismis olabilir: ayni izde 'at'i
            # kapsayan parcayi konumuna gore yeniden bul.
            cur = next((c for c in track.clips if c.start < at < c.end), None)
        if cur is None:
            continue
        if timeline.split(at, clip_id=cur.id):
            count += 1
            current_id = cur.id  # bolmeden sonra sol parca ayni id'yi korur
    return count
