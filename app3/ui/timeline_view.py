"""Etkilesimli timeline widget'i (v0.4).

Cizim + fare etkilesimi: klip secme, tasima (move), kenardan kirpma (trim),
snap (yapisma), zoom, playhead (oynatma kafasi) surukleme. Butun duzenlemeler
`Timeline` modeli uzerinden yapilir ve non-destructive'dir (kaynak medya
dosyalari degismez; yalnizca in/out ve start degerleri guncellenir).

Ozet
- Bos alana tiklamak: secimi kaldirir
- Klip govdesine tiklayip surumek: klibi tasir (+ linkli es klibi de tasir)
- Klip kenarina (~7px) tiklayip surumek: o kenardan kirpar (yalnizca o klip)
- Cetvele tiklamak/surumek: playhead'i o konuma tasir
- Ctrl + tekerlek: yakinlastir/uzaklastir (zoom)
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.audio.engine import generate_waveform_peaks
from app.ui.background import BackgroundTask, pool
from app.runtime.util import fmt_time
from app.timeline.model import Clip, Timeline

TRACK_HEIGHT = 52
TRACK_GAP = 6
RULER_HEIGHT = 24
MIN_PX_PER_SEC = 2.0
MAX_PX_PER_SEC = 800.0
EDGE_PX = 7.0  # trim tutamaci genisligi (piksel)
SNAP_PX = 8.0  # snap yakalama mesafesi (piksel)
ZOOM_STEP = 1.25
WAVEFORM_PEAKS_PER_SEC = 15  # v0.7: timeline'da cizilen dalga formu cozunurlugu

TRACK_COLORS = {"video": QColor("#5b7cff"), "audio": QColor("#38b6a3")}


class TimelineView(QWidget):
    clip_clicked = Signal(str)  # clip id (bos secimde "")
    edited = Signal()  # move/trim ile model degisti (dirty isaretlemek icin)
    playhead_changed = Signal(float)
    zoom_changed = Signal(float)  # px/sn
    before_edit = Signal()  # move/trim surukleme BASLAMADAN hemen once (undo snapshot icin)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(2 * (TRACK_HEIGHT + TRACK_GAP) + RULER_HEIGHT + 12)
        self._timeline = Timeline()
        self._px_per_sec = 40.0
        self._auto_fit = True
        self._selected: str | None = None
        self._playhead = 0.0
        self._snap_enabled = True
        self._drag_mode: str | None = None  # None | "move" | "trim_start" | "trim_end" | "playhead"
        self._drag_grab_offset = 0.0
        self._drag_pushed = True  # bu surukleme icin undo snapshot'i alindi mi
        self._media_paths: dict[str, str] = {}
        self._waveform_cache: dict[str, list[float] | None] = {}  # media_id -> peaks (v0.7)
        self._waveform_pending: set[str] = set()
        self._waveform_generation = 0
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    # ---------------- genel API ----------------
    def set_timeline(self, timeline: Timeline) -> None:
        self._timeline = timeline
        if self._auto_fit:
            self._fit_scale()
        self._playhead = min(self._playhead, max(self._timeline.duration, 0.0))
        if self._selected and not self._timeline.find(self._selected):
            self._selected = None
        self.updateGeometry()
        self.update()

    def set_media_paths(self, media_paths: dict[str, str]) -> None:
        """Ses klipleri icin dalga formu (waveform) cizebilmek icin medya yollarini
        kaydeder (v0.7). Yollar degistiginde onbellek temizlenir."""
        if media_paths != self._media_paths:
            self._media_paths = media_paths
            self._waveform_cache.clear()
            self._waveform_pending.clear()
            self._waveform_generation += 1
            self.update()

    def selected_clip_id(self) -> str | None:
        return self._selected

    def select(self, clip_id: str | None) -> None:
        self._selected = clip_id
        self.update()

    def playhead(self) -> float:
        return self._playhead

    def set_playhead(self, seconds: float, emit: bool = False) -> None:
        self._playhead = max(0.0, seconds)
        self.update()
        if emit:
            self.playhead_changed.emit(self._playhead)

    def set_snap_enabled(self, enabled: bool) -> None:
        self._snap_enabled = enabled

    def zoom_level(self) -> float:
        return self._px_per_sec

    def set_zoom(self, px_per_sec: float) -> None:
        self._auto_fit = False
        self._px_per_sec = max(MIN_PX_PER_SEC, min(MAX_PX_PER_SEC, px_per_sec))
        self.updateGeometry()
        self.update()
        self.zoom_changed.emit(self._px_per_sec)

    def zoom_in(self) -> None:
        self.set_zoom(self._px_per_sec * ZOOM_STEP)

    def zoom_out(self) -> None:
        self.set_zoom(self._px_per_sec / ZOOM_STEP)

    def zoom_fit(self) -> None:
        self._auto_fit = True
        self._fit_scale()
        self.updateGeometry()
        self.update()
        self.zoom_changed.emit(self._px_per_sec)

    def _fit_scale(self) -> None:
        dur = max(self._timeline.duration, 1.0)
        avail = max(self.width() - 16, 200)
        self._px_per_sec = max(MIN_PX_PER_SEC, avail / dur)

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt API)
        width = int(self._timeline.duration * self._px_per_sec) + 60
        height = len(self._timeline.tracks) * (TRACK_HEIGHT + TRACK_GAP) + RULER_HEIGHT + 12
        return QSize(max(width, 400), height)

    # ---------------- koordinat yardimcilari ----------------
    def _x(self, seconds: float) -> float:
        return 8 + seconds * self._px_per_sec

    def _t(self, x: float) -> float:
        return max(0.0, (x - 8) / self._px_per_sec)

    def _row_at(self, y: float) -> int | None:
        yy = y - RULER_HEIGHT
        if yy < 0:
            return None
        row = int(yy // (TRACK_HEIGHT + TRACK_GAP))
        if row >= len(self._timeline.tracks):
            return None
        return row

    def _clip_at(self, x: float, y: float) -> tuple[object, Clip] | None:
        row = self._row_at(y)
        if row is None:
            return None
        track = self._timeline.tracks[row]
        t = self._t(x)
        for clip in track.clips:
            if clip.start <= t <= clip.end:
                return track, clip
        return None

    def _snap(self, candidate: float, exclude_ids: frozenset[str]) -> float:
        if not self._snap_enabled:
            return candidate
        threshold = SNAP_PX / self._px_per_sec
        points = self._timeline.snap_points(exclude_ids) + [self._playhead]
        best = candidate
        best_dist = threshold
        for p in points:
            d = abs(p - candidate)
            if d < best_dist:
                best_dist = d
                best = p
        return best

    # ---------------- fare olaylari ----------------
    def mousePressEvent(self, event) -> None:  # noqa: N802
        pos = event.position()
        if pos.y() <= RULER_HEIGHT:
            self._drag_mode = "playhead"
            self.set_playhead(self._t(pos.x()), emit=True)
            return

        found = self._clip_at(pos.x(), pos.y())
        if not found:
            self._selected = None
            self._drag_mode = None
            self.update()
            self.clip_clicked.emit("")
            return

        _track, clip = found
        self._selected = clip.id
        self.clip_clicked.emit(clip.id)
        x1, x2 = self._x(clip.start), self._x(clip.end)
        if abs(pos.x() - x1) <= EDGE_PX:
            self._drag_mode = "trim_start"
        elif abs(pos.x() - x2) <= EDGE_PX:
            self._drag_mode = "trim_end"
        else:
            self._drag_mode = "move"
            self._drag_grab_offset = self._t(pos.x()) - clip.start
        if self._drag_mode:
            self._drag_pushed = False  # bu surukleme icin undo kaydi henuz alinmadi
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        pos = event.position()
        if self._drag_mode == "playhead":
            self.set_playhead(self._t(pos.x()), emit=True)
            return

        if self._drag_mode and self._selected:
            found = self._timeline.find(self._selected)
            if not found:
                self._drag_mode = None
                return
            _track, clip = found
            group_ids = frozenset(c.id for _, c in self._timeline.linked(clip))
            t = self._t(pos.x())
            changed = False
            if not getattr(self, "_drag_pushed", True):
                # Bu surukleme icin ilk gercek degisiklikten hemen once undo snapshot'i al.
                self._drag_pushed = True
                self.before_edit.emit()
            if self._drag_mode == "move":
                new_start = self._snap(max(0.0, t - self._drag_grab_offset), group_ids)
                changed = self._timeline.move(clip.id, new_start)
            elif self._drag_mode == "trim_start":
                new_t = self._snap(t, frozenset({clip.id}))
                changed = self._timeline.trim(clip.id, "start", new_t)
            elif self._drag_mode == "trim_end":
                new_t = self._snap(t, frozenset({clip.id}))
                changed = self._timeline.trim(clip.id, "end", new_t)
            if changed:
                # Moving a clip does not change the widget size. Avoiding
                # updateGeometry() on every mouse move keeps drag interaction
                # smooth; only trim operations can alter the timeline width.
                if self._drag_mode in ("trim_start", "trim_end"):
                    self.updateGeometry()
                self.edited.emit()
            self.update()
            return

        # surukleme yok: kenar uzerindeyse imleci degistir (kucuk kullanilabilirlik dokunusu)
        found = self._clip_at(pos.x(), pos.y())
        if found:
            _track, clip = found
            x1, x2 = self._x(clip.start), self._x(clip.end)
            if abs(pos.x() - x1) <= EDGE_PX or abs(pos.x() - x2) <= EDGE_PX:
                self.setCursor(QCursor(Qt.SizeHorCursor))
            else:
                self.setCursor(QCursor(Qt.OpenHandCursor))
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_mode = None

    def wheelEvent(self, event) -> None:  # noqa: N802
        if event.modifiers() & Qt.ControlModifier:
            factor = ZOOM_STEP if event.angleDelta().y() > 0 else 1 / ZOOM_STEP
            self.set_zoom(self._px_per_sec * factor)
            event.accept()
        else:
            event.ignore()

    # ---------------- cizim ----------------
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        dur = max(self._timeline.duration, 1.0)
        step = self._ruler_step(dur)
        painter.setPen(QColor("#8b93a7"))
        t = 0.0
        while t <= dur + step:
            x = self._x(t)
            painter.drawLine(int(x), RULER_HEIGHT - 6, int(x), RULER_HEIGHT)
            painter.drawText(int(x) + 2, RULER_HEIGHT - 8, fmt_time(t, ms=False))
            t += step

        bottom = RULER_HEIGHT + len(self._timeline.tracks) * (TRACK_HEIGHT + TRACK_GAP)
        for row, track in enumerate(self._timeline.tracks):
            y = RULER_HEIGHT + row * (TRACK_HEIGHT + TRACK_GAP)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#1e2230"))
            painter.drawRoundedRect(QRectF(8, y, max(self.width() - 16, 40), TRACK_HEIGHT), 6, 6)
            base_color = TRACK_COLORS.get(track.kind, QColor("#5b7cff"))
            for clip in track.clips:
                self._paint_clip(painter, clip, y, base_color, is_audio=track.kind == "audio")

        # playhead
        px = self._x(self._playhead)
        painter.setPen(QPen(QColor("#ff5f6d"), 2))
        painter.drawLine(int(px), 0, int(px), bottom)
        painter.setBrush(QColor("#ff5f6d"))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon([QPointF(px - 5, 0), QPointF(px + 5, 0), QPointF(px, 8)])

        painter.end()

    def _paint_clip(self, painter: QPainter, clip: Clip, y: float, base: QColor, is_audio: bool = False) -> None:
        x1 = self._x(clip.start)
        x2 = self._x(clip.end)
        rect = QRectF(x1 + 1, y + 3, max(x2 - x1 - 2, 2), TRACK_HEIGHT - 6)
        color = QColor(base)
        if clip.id == self._selected:
            color = color.lighter(130)
        painter.setBrush(color)
        painter.setPen(QPen(QColor("#0f1117"), 1))
        painter.drawRoundedRect(rect, 5, 5)
        if is_audio and rect.width() > 6:
            self._paint_waveform(painter, clip, rect)
        if clip.muted:
            painter.setPen(QColor("#0f1117"))
            painter.drawText(rect, Qt.AlignRight | Qt.AlignTop, "🔇")
        if clip.id == self._selected and rect.width() > 2 * EDGE_PX:
            handle_color = QColor("#0f1117")
            handle_color.setAlpha(90)
            painter.setBrush(handle_color)
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(rect.left(), rect.top(), EDGE_PX, rect.height()))
            painter.drawRect(QRectF(rect.right() - EDGE_PX, rect.top(), EDGE_PX, rect.height()))
        if rect.width() > 30:
            painter.setPen(QColor("#0f1117"))
            text = clip.name if len(clip.name) < 20 else clip.name[:17] + "…"
            painter.drawText(rect.adjusted(6, 0, -4, 0), Qt.AlignVCenter | Qt.AlignLeft, text)

    def _waveform_for(self, media_id: str) -> list[float] | None:
        """Return cached peaks and schedule missing waveforms off the UI thread.

        Never run FFmpeg from ``paintEvent``: waveform extraction can take
        hundreds of milliseconds for long media and used to freeze scrolling,
        zooming and clip dragging. A placeholder is painted until the worker
        finishes, then only this widget is invalidated.
        """
        if media_id in self._waveform_cache:
            return self._waveform_cache[media_id]
        if media_id in self._waveform_pending:
            return None
        path = self._media_paths.get(media_id)
        if not path:
            self._waveform_cache[media_id] = None
            return None
        self._waveform_pending.add(media_id)
        generation = self._waveform_generation
        task = BackgroundTask(
            lambda p=path: generate_waveform_peaks(
                p, peaks_per_second=WAVEFORM_PEAKS_PER_SEC, max_peaks=1500
            )
        )
        task.signals.result.connect(
            lambda peaks, mid=media_id, gen=generation: self._waveform_ready(gen, mid, peaks)
        )
        task.signals.error.connect(
            lambda _err, mid=media_id, gen=generation: self._waveform_ready(gen, mid, None)
        )
        pool().start(task)
        return None

    def _waveform_ready(self, generation: int, media_id: str, peaks) -> None:
        self._waveform_pending.discard(media_id)
        if generation != self._waveform_generation:
            return
        self._waveform_cache[media_id] = peaks
        self.update()

    def _paint_waveform(self, painter: QPainter, clip: Clip, rect: QRectF) -> None:
        peaks = self._waveform_for(clip.media_id)
        if not peaks:
            # Lightweight placeholder while FFmpeg decodes the waveform.
            pen = QPen(QColor("#0f1117"), 1)
            pen.setStyle(Qt.DotLine)
            painter.setPen(pen)
            painter.drawLine(rect.left() + 4, rect.center().y(), rect.right() - 4, rect.center().y())
            return
        start_idx = max(int(clip.source_in * WAVEFORM_PEAKS_PER_SEC), 0)
        end_idx = min(int(clip.source_out * WAVEFORM_PEAKS_PER_SEC) + 1, len(peaks))
        segment = peaks[start_idx:end_idx]
        if not segment:
            return
        # Downsample to roughly one vertical stroke per 2 px; drawing thousands
        # of peaks on a small clip wastes CPU without adding visual information.
        max_columns = max(8, int(rect.width() / 2.0))
        if len(segment) > max_columns:
            stride = len(segment) / max_columns
            reduced = []
            for i in range(max_columns):
                a = int(i * stride)
                b = max(a + 1, int((i + 1) * stride))
                reduced.append(max(segment[a:b]))
            segment = reduced
        mid_y = rect.center().y()
        half_h = max(rect.height() / 2 - 3, 2.0)
        pen_color = QColor("#0f1117")
        pen_color.setAlpha(140)
        painter.setPen(QPen(pen_color, 1))
        n = len(segment)
        for i, p in enumerate(segment):
            x = rect.left() + (i + 0.5) * rect.width() / n
            h = max(min(p, 1.0) * half_h, 0.5)
            painter.drawLine(QPointF(x, mid_y - h), QPointF(x, mid_y + h))

    @staticmethod
    def _ruler_step(duration: float) -> float:
        for step in (1, 2, 5, 10, 30, 60, 120, 300, 600):
            if duration / step <= 20:
                return float(step)
        return 900.0
