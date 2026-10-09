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
from PySide6.QtWidgets import QMenu, QWidget

from app.audio.engine import generate_waveform_peaks
from app.runtime.util import fmt_time
from app.timeline.model import Clip, Timeline
from app.ai.retention_hotspots import RetentionHotspot, normalize_hotspots

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
    creative_asset_dropped = Signal(str, float, str)  # asset_id, timeline time, clip_id
    creative_asset_preview = Signal(str, float, str, float)  # asset_id, start, clip_id, duration
    asset_inspector_requested = Signal(str)  # selected clip id
    retention_hotspot_clicked = Signal(float, float, str)
    retention_hotspot_action_requested = Signal(float, float, str)  # start, end, reason

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
        self._retention_hotspots: tuple[RetentionHotspot, ...] = ()
        # Smart Drag & Drop: non-destructive ghost state only; no timeline mutation until drop.
        self._asset_ghost: dict | None = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAcceptDrops(True)

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
            self.update()

    def set_retention_hotspots(self, hotspots, duration: float | None = None) -> None:
        """Retention risk bölgelerini timeline üzerinde gösterir (non-destructive)."""
        dur = self._timeline.duration if duration is None else float(duration)
        self._retention_hotspots = normalize_hotspots(hotspots, dur)
        self.update()

    def retention_hotspots(self) -> tuple[RetentionHotspot, ...]:
        return self._retention_hotspots

    def clear_retention_hotspots(self) -> None:
        self._retention_hotspots = ()
        self.update()

    def _hotspot_at(self, x: float, y: float) -> RetentionHotspot | None:
        if y < RULER_HEIGHT:
            return None
        t = self._t(x)
        for h in self._retention_hotspots:
            if h.start <= t <= h.end:
                return h
        return None

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

    # ---------------- creative library drag/drop ----------------
    def _clear_asset_ghost(self) -> None:
        if self._asset_ghost is not None:
            self._asset_ghost = None
            self.update()

    def _update_asset_ghost(self, event) -> None:
        mime = event.mimeData()
        if not mime.hasFormat("application/x-ai-director-creative"):
            self._clear_asset_ghost()
            return
        try:
            asset_id = bytes(mime.data("application/x-ai-director-creative")).decode("utf-8")
        except Exception:
            self._clear_asset_ghost(); return
        pos = event.position()
        found = self._clip_at(pos.x(), pos.y())
        if not found:
            self._clear_asset_ghost(); event.ignore(); return
        _track, clip = found
        start = max(clip.start, min(self._t(pos.x()), clip.end))
        # Preview duration is intentionally conservative; the final drop resolves the real asset recipe.
        duration = min(0.8, max(0.05, clip.end - start))
        self._asset_ghost = {
            "asset_id": asset_id, "clip_id": clip.id, "start": start,
            "duration": duration, "row": self._row_at(pos.y()),
        }
        self.creative_asset_preview.emit(asset_id, start, clip.id, duration)
        self.update()
        event.acceptProposedAction()

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat("application/x-ai-director-creative"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        self._update_asset_ghost(event)

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self._clear_asset_ghost()
        event.accept()

    def dropEvent(self, event) -> None:  # noqa: N802
        mime = event.mimeData()
        if not mime.hasFormat("application/x-ai-director-creative"):
            event.ignore(); return
        try:
            asset_id = bytes(mime.data("application/x-ai-director-creative")).decode("utf-8")
        except Exception:
            event.ignore(); return
        pos = event.position()
        found = self._clip_at(pos.x(), pos.y())
        if found:
            _track, clip = found
            self._selected = clip.id
            start = self._t(pos.x())
            self.creative_asset_dropped.emit(asset_id, start, clip.id)
            self._clear_asset_ghost()
            event.acceptProposedAction()
            self.update()
        else:
            self._clear_asset_ghost()
            event.ignore()

    # ---------------- fare olaylari ----------------
    def mousePressEvent(self, event) -> None:  # noqa: N802
        pos = event.position()
        if event.button() == Qt.RightButton:
            found = self._clip_at(pos.x(), pos.y())
            if found:
                _track, clip = found
                self._selected = clip.id
                menu = QMenu(self)
                inspect = menu.addAction("Asset Inspector…")
                chosen = menu.exec(event.globalPosition().toPoint())
                if chosen == inspect:
                    self.asset_inspector_requested.emit(clip.id)
                self.clip_clicked.emit(clip.id)
                self.update()
                return
            hotspot = self._hotspot_at(pos.x(), pos.y())
            if hotspot is not None:
                menu = QMenu(self)
                jump = menu.addAction("Oynatma kafasını buraya götür")
                fix = menu.addAction("AI ile bu bölümü düzelt")
                chosen = menu.exec(event.globalPosition().toPoint())
                if chosen == jump:
                    self.set_playhead(hotspot.start, emit=True)
                    self.retention_hotspot_clicked.emit(hotspot.start, hotspot.end, hotspot.reason)
                elif chosen == fix:
                    self.set_playhead(hotspot.start, emit=True)
                    self.retention_hotspot_action_requested.emit(hotspot.start, hotspot.end, hotspot.reason)
                return
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

        # retention hotspots: timeline üzerindeki risk bölgeleri. Clip verisini değiştirmez.
        for hotspot in self._retention_hotspots:
            x1 = self._x(hotspot.start)
            x2 = self._x(hotspot.end)
            alpha = 42 if hotspot.severity == "low" else 60 if hotspot.severity == "medium" else 82
            fill = QColor("#f6b73c") if hotspot.severity != "high" else QColor("#ff5f6d")
            fill.setAlpha(alpha)
            painter.setBrush(fill)
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(x1, RULER_HEIGHT, max(1.0, x2-x1), bottom-RULER_HEIGHT))
            if x2 - x1 > 55:
                painter.setPen(QColor("#f2f4f8"))
                label = hotspot.reason.replace("_", " ")
                painter.drawText(QRectF(x1 + 4, RULER_HEIGHT + 2, max(20.0, x2-x1-8), 18), Qt.AlignLeft | Qt.AlignTop, "⚠ " + label)

        # Smart Drag & Drop ghost: rendered only while dragging, never committed to the model.
        ghost = self._asset_ghost
        if ghost is not None:
            row = ghost.get("row")
            if row is not None and 0 <= row < len(self._timeline.tracks):
                y = RULER_HEIGHT + row * (TRACK_HEIGHT + TRACK_GAP)
                gx = self._x(float(ghost["start"]))
                gw = max(10.0, float(ghost["duration"]) * self._px_per_sec)
                ghost_rect = QRectF(gx, y + 5, gw, TRACK_HEIGHT - 10)
                painter.save()
                painter.setOpacity(0.42)
                painter.setPen(QPen(QColor("#ffffff"), 2, Qt.DashLine))
                painter.setBrush(QColor("#7c5cff"))
                painter.drawRoundedRect(ghost_rect, 6, 6)
                painter.setOpacity(0.9)
                painter.setPen(QPen(QColor("#ffffff"), 1))
                painter.drawText(ghost_rect.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, "Preview • bırakınca uygula")
                painter.restore()

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
            # Creative layer badges: makes AI-generated stacks visible directly
            # on the timeline without opening a property panel.
            meta = getattr(clip, "creative_metadata", {}) or {}
            badges = []
            if meta.get("effect_id"): badges.append("FX")
            if meta.get("motion_id"): badges.append("M")
            if meta.get("transition") or clip.transition_in: badges.append("TR")
            if meta.get("text_id") or clip.creative_text_cues: badges.append("TXT")
            if clip.keyframes: badges.append("KF")
            if badges:
                painter.setPen(QColor("#d6d9e2"))
                painter.drawText(rect.adjusted(6, 28, -4, 0), Qt.AlignLeft | Qt.AlignTop, " · ".join(badges))

    def _waveform_for(self, media_id: str) -> list[float] | None:
        """`media_id`nin kaynak dosyasi icin peak listesini dondurur (onbellekli, v0.7).

        Diskte onbelleklenmis bir waveform yoksa ilk cagrida ffmpeg calistirir; bu
        yuzden bir kez hesaplanir ve widget omru boyunca bellekte tutulur (her
        paintEvent'te yeniden hesaplanmaz)."""
        if media_id in self._waveform_cache:
            return self._waveform_cache[media_id]
        path = self._media_paths.get(media_id)
        peaks: list[float] | None = None
        if path:
            try:
                peaks = generate_waveform_peaks(path, peaks_per_second=WAVEFORM_PEAKS_PER_SEC, max_peaks=1500)
            except Exception:
                peaks = None
        self._waveform_cache[media_id] = peaks
        return peaks

    def _paint_waveform(self, painter: QPainter, clip: Clip, rect: QRectF) -> None:
        peaks = self._waveform_for(clip.media_id)
        if not peaks:
            return
        start_idx = max(int(clip.source_in * WAVEFORM_PEAKS_PER_SEC), 0)
        end_idx = min(int(clip.source_out * WAVEFORM_PEAKS_PER_SEC) + 1, len(peaks))
        segment = peaks[start_idx:end_idx]
        if not segment:
            return
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
