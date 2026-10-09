"""Kabul edilen önerileri timeline'a uygulama — v0.8 AI Basic Editor.

Yalnızca `models.CUT_KINDS` içindeki öneri türleri (sessizlik, uzun duraklama,
tekrar, dolgu kelime) timeline'dan bir aralığı KESER; `ADD_SUBTITLE` ve
`HIGHLIGHT_WORD` önerileri burada değil, sırasıyla `app.subtitle` araçlarıyla
(transkripsiyon / `always_highlight`) ele alınır (bkz. `ui/ai_editor_dialog.py`).

Kesme stratejisi, projenin kendi `app.scene.detector.split_at_scenes`'iyle aynı
deseni izler: klibin `[source_in, source_out)` aralığına denk gelen zaman
damgaları, klibin TIMELINE konumuna (`clip.start + (t - source_in)`) çevrilip
`Timeline.split()` ile bölünür. Farkı: burada nokta değil ARALIK kesiliyor —
aralığın başında ve sonunda birer `split()`, ardından ortadaki parçanın
`Timeline.remove(ripple=True)` ile silinmesi. `remove(ripple=True)` TÜM izlerdeki
sonraki klipleri kaydırdığından (bkz. `Timeline.remove`), ardışık kesimler
artan başlangıç sırasına göre, kümülatif kayma payı düşülerek uygulanır.
"""
from __future__ import annotations

from app.timeline.model import MIN_CLIP, Timeline

from .models import CUT_KINDS, Suggestion

MIN_CUT = 0.05  # bu kadardan kısa aralıklar (pratikte kesilemeyecek kadar küçük) atlanır
_EDGE_EPS = MIN_CLIP  # bu kadar yakınsa klip kenarına "tam denk" sayılır (ekstra split gerekmez)


def merge_ranges(ranges: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Çakışan/bitişik (start, end) aralıklarını birleştirir (artan `start` sırasına göre)."""
    if not ranges:
        return []
    ordered = sorted(ranges)
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + MIN_CUT:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def cut_ranges_in_clip(timeline: Timeline, clip_id: str, source_ranges: list[tuple[float, float]]) -> int:
    """Bir klibin KAYNAK medya zamanındaki `source_ranges` aralıklarını timeline'dan keser.

    Klibin dışında kalan veya `source_in`/`source_out` sınırlarını aşan kısımlar
    klip sınırına kırpılır. Döndürülen değer, başarıyla kesilen aralık sayısıdır.
    """
    found = timeline.find(clip_id)
    if not found:
        return 0
    track, clip = found
    source_in, source_out = clip.source_in, clip.source_out

    clipped: list[tuple[float, float]] = []
    for s, e in source_ranges:
        s2, e2 = max(s, source_in), min(e, source_out)
        if e2 - s2 >= MIN_CUT:
            clipped.append((s2, e2))
    clipped = merge_ranges(clipped)
    if not clipped:
        return 0

    # orijinal (kesimden önceki) klip konumuna göre mutlak timeline aralıkları
    abs_ranges = sorted((clip.start + (s - source_in), clip.start + (e - source_in)) for s, e in clipped)

    cumulative_shift = 0.0
    count = 0
    for a_orig, b_orig in abs_ranges:
        a, b = a_orig - cumulative_shift, b_orig - cumulative_shift
        if b - a < MIN_CUT:
            continue
        cur = next((c for c in track.clips if c.start - 1e-6 <= a and b <= c.end + 1e-6), None)
        if cur is None:
            continue  # önceki kesimler bu aralığı zaten tükettiyse atla

        # Kesim, klibin tam BAŞINDA değilse önce orada böl; aksi halde (ör. aralık
        # klibin ilk karesinden başlıyorsa) gereksiz/başarısız bir sıfır-uzunluklu
        # split denemesinden kaçınılır — `cur` zaten "a"dan başlıyor demektir.
        target = cur
        if a - cur.start >= _EDGE_EPS:
            if not timeline.split(a, clip_id=cur.id):
                continue
            target = next((c for c in track.clips if abs(c.start - a) < 1e-3 and c.id != cur.id), None)
            if target is None:
                continue

        # Kesim, (yeni) target'ın tam SONUNA denk gelmiyorsa orada da böl; aksi
        # halde target'ın tamamı (sonuna kadar) silinecek demektir.
        if target.end - b >= _EDGE_EPS:
            if not timeline.split(b, clip_id=target.id):
                continue
            target = next((c for c in track.clips if abs(c.start - a) < 1e-3), target)

        if timeline.remove(target.id, ripple=True):
            cumulative_shift += target.duration
            count += 1
    return count


def apply_accepted_cuts(timeline: Timeline, clip_id: str, suggestions: list[Suggestion]) -> int:
    """Kabul edilmiş (`accepted=True`) kesim önerilerini (`CUT_KINDS`) bir klibe uygular."""
    ranges = [(s.start, s.end) for s in suggestions if s.accepted and s.kind in CUT_KINDS and s.end > s.start]
    return cut_ranges_in_clip(timeline, clip_id, ranges)


__all__ = ["merge_ranges", "cut_ranges_in_clip", "apply_accepted_cuts"]
