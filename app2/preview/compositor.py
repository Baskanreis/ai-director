"""Timeline zamanini onizleme icin cozumleme (Qt'den bagimsiz, saf Python).

Onizleme, export'un aksine, video izindeki klibi kendi gomulu sesiyle birlikte
oynatir (bkz. ROADMAP/README): ayri ses izi mixi yalnizca export asamasinda
uygulanir. Bu modul, verilen bir timeline zamani icin hangi klibin aktif oldugunu
ve o klibin kaynak dosyasinda hangi zamana denk geldigini hesaplar; boylece
Qt/QMediaPlayer katmani (app/ui/preview_widget.py) yalnizca "ne zaman hangi
dosyayi, hangi konumdan oynat" sorusuna odaklanir.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.timeline.model import Timeline

EPS = 1e-3


@dataclass(frozen=True)
class PreviewFrame:
    """Belirli bir timeline anindaki onizleme durumu."""

    has_video: bool
    clip_id: str | None = None
    media_id: str | None = None
    media_path: str | None = None
    source_time: float = 0.0

    @property
    def is_gap(self) -> bool:
        return not self.has_video


_EMPTY = PreviewFrame(has_video=False)


def resolve_preview(timeline: Timeline, media_paths: dict[str, str], t: float) -> PreviewFrame:
    """`t` (timeline saniyesi) anindaki aktif video klibini ve kaynak zamanini bulur.

    Klipler arasinda bosluk varsa (veya video izi bossa) `has_video=False` doner;
    cagiran taraf bu durumda siyah/bos bir goruntu gostermelidir.
    """
    try:
        vtrack = timeline.first_track("video")
    except Exception:
        return _EMPTY
    clips = vtrack.sorted_clips()
    if not clips:
        return _EMPTY

    duration = timeline.duration
    t = max(0.0, min(t, duration))

    for clip in clips:
        if clip.start - EPS <= t < clip.end + EPS:
            source_time = min(max(clip.source_in + (t - clip.start), clip.source_in), clip.source_out)
            return PreviewFrame(
                has_video=True,
                clip_id=clip.id,
                media_id=clip.media_id,
                media_path=media_paths.get(clip.media_id),
                source_time=source_time,
            )

    # Tam bir klibin sonunda (veya timeline sonunda) son kareyi goster.
    last = clips[-1]
    if t >= last.end - EPS:
        return PreviewFrame(
            has_video=True,
            clip_id=last.id,
            media_id=last.media_id,
            media_path=media_paths.get(last.media_id),
            source_time=last.source_out,
        )

    return _EMPTY


def next_clip_start_after(timeline: Timeline, t: float) -> float | None:
    """`t`'den sonraki en yakin klip baslangicini dondurur (bosluklari atlamak icin)."""
    try:
        vtrack = timeline.first_track("video")
    except Exception:
        return None
    starts = sorted(c.start for c in vtrack.clips if c.start > t + EPS)
    return starts[0] if starts else None
