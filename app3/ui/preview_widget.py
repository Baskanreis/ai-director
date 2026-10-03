"""Timeline video onizleme oynaticisi (v0.5).

`QMediaPlayer` tek bir dosyayi oynatabildigi icin, timeline uzerinde birden
fazla klip varsa oynatma sirasinda hangi klibin aktif oldugu her tick'te
`app.preview.compositor.resolve_preview` ile hesaplanir; aktif klip degistiginde
oynaticinin kaynagi sorunsuzca degistirilir. "Master saat" duvar-saati tabanlidir
(oynaticinin kendi pozisyonu degil): boylece klipler arasi gecislerde ve
bosluklarda (klip olmayan araliklarda) playhead duzgun ilerlemeye devam eder.

Ozellikler: Play/Pause, Seek (surgu), Frame step (ileri/geri kare), Volume,
Fullscreen, timeline ile cift yonlu senkronizasyon (`position_changed` sinyali).
"""
from __future__ import annotations

import time

from PySide6.QtCore import QUrl, Qt, QTimer, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from app.preview.compositor import resolve_preview
from app.preview.engine import PreviewEngine
from app.preview.proxy_manager import PreviewProxyManager
from app.preview.compositor_backend import PreviewCompositorBackend
from app.preview.qt_video_bridge import QVideoFrameBridge
from app.runtime.util import fmt_timecode
from app.timeline.model import Timeline

TICK_MS = 33  # ~30 Hz UI/senkron guncelleme
RESYNC_THRESHOLD = 0.15  # saniye; oynaticinin gercek konumu bu kadar sapinca duzeltilir


class PreviewPlayer(QWidget):
    position_changed = Signal(float)  # timeline saniyesi (kullanici disi guncellemelerde de)
    playing_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._timeline = Timeline()
        self._media_paths: dict[str, str] = {}
        self._playhead = 0.0
        self._playing = False
        self._scrubbing = False
        self._seek_debounce = QTimer(self)
        self._seek_debounce.setSingleShot(True)
        self._seek_debounce.setInterval(30)
        self._seek_debounce.timeout.connect(self._apply_pending_seek)
        self._pending_seek_value: float | None = None
        self._wall_start = 0.0
        self._playhead_at_wall_start = 0.0
        self._current_media_path: str | None = None
        self._current_source_path: str | None = None
        self._proxy_manager = PreviewProxyManager(parent=self)
        self._engine = PreviewEngine(seek_threshold=RESYNC_THRESHOLD)
        self._proxy_manager.ready.connect(self._on_proxy_ready)
        self._preview_cache = None
        self._preview_cache_bounds: tuple[float, float] | None = None
        self._muted = False
        self._volume_before_mute = 80

        self._player = QMediaPlayer(self)
        self._audio_out = QAudioOutput(self)
        self._audio_out.setVolume(0.8)
        self._player.setAudioOutput(self._audio_out)

        self._video_widget = QVideoWidget()
        self._video_widget.setStyleSheet("background: black;")
        self._player.setVideoOutput(self._video_widget)

        # QVideoWidget owns the real QVideoSink used by Qt's accelerated
        # presentation path. Observe that sink instead of creating a second
        # decode/output path. GPU frames stay RHI-backed; no CPU mapping occurs
        # unless a future effect explicitly asks for pixels.
        self._compositor_backend = PreviewCompositorBackend()
        self._video_sink = self._video_widget.videoSink()
        self._video_bridge = QVideoFrameBridge(
            self._video_sink,
            self._compositor_backend.backend.name,
            self._on_gpu_video_frame,
        )

        self._last_video_frame_info = None
        self._gpu_preview_frames = 0
        self._cpu_preview_frames = 0

        self._empty_label = QLabel("Önizleme için timeline'a bir klip ekleyin")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("background: black; color: #888;")

        self._view_container = QWidget()
        self._view_container.setMinimumHeight(220)
        self._view_stack = QStackedLayout(self._view_container)
        self._view_stack.addWidget(self._video_widget)
        self._view_stack.addWidget(self._empty_label)

        self._fullscreen_host: QWidget | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)
        outer.addWidget(self._view_container, 1)
        outer.addLayout(self._build_transport())

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._on_tick)

        self._sync_frame(force=True)

    def _on_gpu_video_frame(self, info) -> None:
        """Feed real QVideoFrame -> compositor telemetry without mapping pixels."""
        self._last_video_frame_info = info
        self._compositor_backend.accept_qvideo_frame(info)
        if info.gpu_backed:
            self._gpu_preview_frames += 1
        else:
            self._cpu_preview_frames += 1

    def preview_gpu_stats(self) -> dict[str, int | str]:
        stats = self._compositor_backend.stats
        return {
            "backend": self._compositor_backend.backend.name,
            "frames": stats.frames,
            "gpu_frames": stats.gpu_frames,
            "cpu_frames": stats.cpu_frames,
            "zero_copy_frames": stats.zero_copy_frames,
        }

    # ---------------- arayuz kurulumu ----------------
    def _build_transport(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)

        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setToolTip("Durdur (başa dön)")
        self.stop_btn.setFixedWidth(32)
        self.stop_btn.clicked.connect(self.stop)

        self.step_back_btn = QPushButton("⏮")
        self.step_back_btn.setToolTip("Bir kare geri")
        self.step_back_btn.setFixedWidth(32)
        self.step_back_btn.clicked.connect(lambda: self.step_frame(-1))

        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedWidth(36)
        self.play_btn.clicked.connect(self.toggle_play)

        self.step_fwd_btn = QPushButton("⏭")
        self.step_fwd_btn.setToolTip("Bir kare ileri")
        self.step_fwd_btn.setFixedWidth(32)
        self.step_fwd_btn.clicked.connect(lambda: self.step_frame(1))

        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderPressed.connect(self._on_scrub_start)
        self.seek_slider.sliderReleased.connect(self._on_scrub_end)
        self.seek_slider.sliderMoved.connect(self._on_scrub_move)

        self.time_label = QLabel("00:00:00:00 / 00:00:00:00")
        self.time_label.setStyleSheet("font-family: monospace;")

        self.fps_label = QLabel("— fps")
        self.fps_label.setToolTip("Timeline kare hızı (FPS)")
        self.fps_label.setStyleSheet("font-family: monospace; color: #8b93a7;")

        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setToolTip("Sessize al")
        self.mute_btn.setFixedWidth(28)
        self.mute_btn.clicked.connect(self.toggle_mute)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setFixedWidth(90)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.valueChanged.connect(self.set_volume)

        self.fullscreen_btn = QPushButton("⛶")
        self.fullscreen_btn.setToolTip("Tam ekran")
        self.fullscreen_btn.setFixedWidth(32)
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)

        row.addWidget(self.stop_btn)
        row.addWidget(self.step_back_btn)
        row.addWidget(self.play_btn)
        row.addWidget(self.step_fwd_btn)
        row.addWidget(self.seek_slider, 1)
        row.addWidget(self.time_label)
        row.addWidget(self.fps_label)
        row.addWidget(self.mute_btn)
        row.addWidget(self.volume_slider)
        row.addWidget(self.fullscreen_btn)
        return row

    # ---------------- genel API ----------------
    def set_timeline(self, timeline: Timeline, media_paths: dict[str, str]) -> None:
        """Timeline veya medya yollari degistiginde cagrilir (proje yenilendiginde)."""
        was_playing = self._playing
        self.pause()
        self._timeline = timeline
        self._media_paths = media_paths
        self._engine.set_project(timeline, media_paths)
        self._preview_cache = None
        self._preview_cache_bounds = None
        self._playhead = min(self._playhead, max(timeline.duration, 0.0))
        self.seek_slider.setRange(0, int(round(timeline.duration * 1000)))
        fps = timeline.fps or 30.0
        self.fps_label.setText(f"{fps:g} fps")
        self._sync_frame(force=True)
        self._update_labels()
        if was_playing:
            self.play()

    def playhead(self) -> float:
        return self._playhead

    def seek(self, seconds: float) -> None:
        self._playhead = max(0.0, min(seconds, self._timeline.duration))
        if self._playing:
            self._wall_start = time.monotonic()
            self._playhead_at_wall_start = self._playhead
        self._sync_frame(force=True)
        self._update_labels()
        self.position_changed.emit(self._playhead)

    def play(self) -> None:
        if self._timeline.duration <= 0:
            return
        if self._playhead >= self._timeline.duration - 1e-3:
            self._playhead = 0.0
        self._playing = True
        self._wall_start = time.monotonic()
        self._playhead_at_wall_start = self._playhead
        self.play_btn.setText("⏸")
        self._sync_frame(force=True)
        self._timer.start()
        self.playing_changed.emit(True)

    def pause(self) -> None:
        if not self._playing:
            return
        self._playing = False
        self._timer.stop()
        self._player.pause()
        self.play_btn.setText("▶")
        # Build the current preview proxy only while paused. This keeps FFmpeg
        # transcoding from stealing CPU during real-time playback.
        if self._current_source_path:
            self._proxy_manager.request(self._current_source_path)
        # Prefetch the adjacent clip while paused so a later cut does not wait
        # for proxy creation. This is de-duplicated by PreviewProxyManager.
        self._engine.prefetch_adjacent(self._playhead, self._proxy_manager.request)
        self.playing_changed.emit(False)

    def toggle_play(self) -> None:
        self.pause() if self._playing else self.play()

    def stop(self) -> None:
        """Oynatmayi durdurur ve playhead'i basa (0) alir (klasik 'Stop' davranisi)."""
        self.pause()
        self.seek(0.0)

    def step_frame(self, delta: int) -> None:
        self.pause()
        fps = self._timeline.fps or 30.0
        self.seek(self._playhead + delta / fps)

    def set_volume(self, percent: int) -> None:
        percent = max(0, min(100, percent))
        if percent > 0 and self._muted:
            # Kullanici surguyu hareket ettirdiyse sessize alma otomatik kalkar.
            self._muted = False
            self.mute_btn.setText("🔊")
        self._audio_out.setVolume(0.0 if self._muted else percent / 100.0)

    def toggle_mute(self) -> None:
        self._muted = not self._muted
        if self._muted:
            self._volume_before_mute = self.volume_slider.value()
            self._audio_out.setVolume(0.0)
            self.mute_btn.setText("🔇")
            self.mute_btn.setToolTip("Sesi aç")
        else:
            self._audio_out.setVolume(self._volume_before_mute / 100.0)
            self.mute_btn.setText("🔊")
            self.mute_btn.setToolTip("Sessize al")

    def toggle_fullscreen(self) -> None:
        if self._fullscreen_host is not None:
            self._exit_fullscreen()
        else:
            self._enter_fullscreen()

    # ---------------- ic isleyis ----------------
    def _on_tick(self) -> None:
        elapsed = time.monotonic() - self._wall_start
        target = self._playhead_at_wall_start + elapsed
        if target >= self._timeline.duration:
            self._playhead = self._timeline.duration
            self.pause()
            self._sync_frame(force=True)
            self._update_labels()
            self.position_changed.emit(self._playhead)
            return
        self._playhead = target
        self._sync_frame(force=False)
        self._update_labels()
        self.position_changed.emit(self._playhead)

    def _sync_frame(self, force: bool) -> None:
        # resolve_preview() klipleri lineer tarar. Oynatma sırasında aynı klip
        # içinde her 33 ms'de bunu tekrar yapmak gereksiz CPU tüketir. Cache
        # yalnızca klip sınırı geçildiğinde veya kullanıcı seek yaptığında çözülür.
        cached = self._preview_cache
        bounds = self._preview_cache_bounds
        if (not force and cached is not None and bounds is not None
                and bounds[0] - 1e-3 <= self._playhead <= bounds[1] + 1e-3):
            source_time = cached.source_time + (self._playhead - bounds[0])
            frame = type(cached)(
                has_video=cached.has_video, clip_id=cached.clip_id,
                media_id=cached.media_id, media_path=cached.media_path,
                source_time=max(cached.source_time, source_time),
            )
        else:
            frame = self._engine.resolve(self._playhead)
            self._preview_cache = frame
            if frame.clip_id:
                found = self._timeline.find(frame.clip_id)
                if found:
                    _track, clip = found
                    self._preview_cache_bounds = (clip.start, clip.end)
                else:
                    self._preview_cache_bounds = None
            else:
                self._preview_cache_bounds = None
        if not frame.has_video or not frame.media_path:
            self._view_stack.setCurrentWidget(self._empty_label)
            if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self._player.pause()
            self._current_media_path = None
            return

        self._view_stack.setCurrentWidget(self._video_widget)
        target_ms = int(round(frame.source_time * 1000))
        if frame.media_path != self._current_source_path:
            self._current_source_path = frame.media_path
            # Start background preparation of neighboring clips; the current
            # media player remains untouched until the clip boundary is reached.
            self._engine.prefetch_adjacent(self._playhead, self._proxy_manager.request)
        if frame.media_path != self._current_media_path:
            self._current_media_path = self._proxy_manager.proxy_for(frame.media_path) or frame.media_path
            self._player.setSource(QUrl.fromLocalFile(self._current_media_path))
            self._player.setPosition(target_ms)
            if self._playing:
                self._player.play()
        else:
            drift = abs(self._player.position() - target_ms) / 1000.0
            if force or drift > RESYNC_THRESHOLD:
                self._player.setPosition(target_ms)
            playing_now = self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
            if self._playing and not playing_now:
                self._player.play()
            elif not self._playing and playing_now:
                self._player.pause()

    def _on_proxy_ready(self, source: str, proxy: str) -> None:
        if source != self._current_source_path or self._playing:
            return
        # Re-open the current frame from the lightweight proxy when available.
        self._current_media_path = proxy
        self._sync_frame(force=True)

    def _update_labels(self) -> None:
        fps = self._timeline.fps or 30.0
        cur = fmt_timecode(self._playhead, fps)
        total = fmt_timecode(self._timeline.duration, fps)
        self.time_label.setText(f"{cur} / {total}")
        if not self._scrubbing:
            self.seek_slider.blockSignals(True)
            self.seek_slider.setValue(int(round(self._playhead * 1000)))
            self.seek_slider.blockSignals(False)

    def _on_scrub_start(self) -> None:
        self._scrubbing = True
        self._was_playing_before_scrub = self._playing
        self.pause()

    def _on_scrub_move(self, value: int) -> None:
        # Mouse move can emit hundreds of events per second. Update the UI
        # immediately, but coalesce expensive media seeks to ~33 Hz.
        self._pending_seek_value = value / 1000.0
        self._playhead = self._pending_seek_value
        self._engine.queue_seek(self._playhead)
        self._update_labels()
        self.position_changed.emit(self._playhead)
        self._seek_debounce.start()

    def _apply_pending_seek(self) -> None:
        value = self._engine.consume_seek()
        if value is None:
            value = self._pending_seek_value
        self._pending_seek_value = None
        if value is None:
            return
        self._playhead = value
        self._sync_frame(force=True)
        self._update_labels()

    def _on_scrub_end(self) -> None:
        self._scrubbing = False
        self._seek_debounce.stop()
        self._apply_pending_seek()
        if getattr(self, "_was_playing_before_scrub", False):
            self.play()

    def closeEvent(self, event) -> None:
        try:
            self._video_bridge.close()
        finally:
            super().closeEvent(event)

    def _enter_fullscreen(self) -> None:
        self._fullscreen_host = QWidget()
        self._fullscreen_host.setStyleSheet("background: black;")
        lay = QVBoxLayout(self._fullscreen_host)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._view_container)
        self._fullscreen_host.setWindowFlag(Qt.Window, True)
        self._fullscreen_host.keyPressEvent = self._fullscreen_key_press
        self._fullscreen_host.showFullScreen()
        self.fullscreen_btn.setText("⤢")

    def _fullscreen_key_press(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self._exit_fullscreen()

    def _exit_fullscreen(self) -> None:
        if self._fullscreen_host is None:
            return
        outer_layout = self.layout()
        outer_layout.insertWidget(0, self._view_container, 1)
        self._fullscreen_host.close()
        self._fullscreen_host.deleteLater()
        self._fullscreen_host = None
        self.fullscreen_btn.setText("⛶")
