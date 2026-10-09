"""AI Video Edit diyaloğu — v0.8 AI Basic Editor.

Akış: kaynak klip seç -> (opsiyonel) Whisper ile transkribe et -> analiz et
(sessizlik / uzun duraklama / tekrar / dolgu kelime / sahne değişimi / önemli
kelime) -> her öneriyi kabul/ret et (varsayılan: kesim önerileri kabul, sahne
değişimi bilgi amaçlı ve varsayılan kapalı) -> kabul edilenleri timeline'a uygula
(ripple-kesim). Analiz ve transkripsiyon arka planda (`QThread`) çalışır.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ai.apply import apply_accepted_cuts
from app.ai.director import EditProfile, EditStyle, build_director_plan, apply_director_plan
from app.ai.retention import run_autonomous_edit_pass
from app.ai.effects_director import build_sound_design_plan, build_creative_pass_plan
from app.ai.creative_composer import compose_creative_edit
from app.ai.creative_apply import apply_creative_pass
from app.ai.professional_editor import build_professional_edit_plan, apply_professional_edit
from app.ai.models import AnalysisReport, Suggestion, SuggestionKind
from app.ai.worker import AnalyzeWorker
from app.subtitle.models import Transcript
from app.subtitle.transcribe import DEFAULT_LANGUAGE, DEFAULT_MODEL_SIZE, SUPPORTED_LANGUAGES
from app.subtitle.worker import TranscribeWorker
from app.timeline.model import Timeline
from app.agents.worker import MultiAgentWorker

_KIND_TITLES: dict[SuggestionKind, str] = {
    SuggestionKind.SILENCE: "Sessizlik",
    SuggestionKind.LONG_PAUSE: "Uzun duraklama",
    SuggestionKind.REPETITION: "Tekrar",
    SuggestionKind.FILLER_WORD: "Dolgu kelime",
    SuggestionKind.SCENE_CHANGE: "Sahne değişimi (bilgi)",
    SuggestionKind.ADD_SUBTITLE: "Altyazı",
    SuggestionKind.HIGHLIGHT_WORD: "Önemli kelime",
}


class AIEditorDialog(QDialog):
    def __init__(self, timeline: Timeline, media_paths: dict[str, str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.timeline = timeline
        self.media_paths = media_paths
        self.transcribe_worker: TranscribeWorker | None = None
        self.analyze_worker: AnalyzeWorker | None = None
        self.multi_agent_worker: MultiAgentWorker | None = None
        self.last_compiled_edit_plan = None
        self.transcript: Transcript | None = None
        self.report: AnalysisReport | None = None
        self.last_director_plan = None
        self.changed = False  # en az bir kesim basariyla uygulandiysa True (Studio bununla undo/refresh karari verir)
        self.setWindowTitle("AI Video Edit — Analiz ve Otomatik Kurgu")
        self.setMinimumSize(560, 560)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.source_box = QComboBox()
        self._source_media_ids: list[str] = []
        self._source_clip_ids: list[str] = []
        for clip_id, media_id, label in self._candidate_sources():
            self._source_clip_ids.append(clip_id)
            self._source_media_ids.append(media_id)
            self.source_box.addItem(label)
        form.addRow("Kaynak klip", self.source_box)

        self.lang_box = QComboBox()
        self._lang_keys = [k for k in SUPPORTED_LANGUAGES if k != "auto"]
        self.lang_box.addItems([SUPPORTED_LANGUAGES[k] for k in self._lang_keys])
        self.lang_box.setCurrentIndex(self._lang_keys.index(DEFAULT_LANGUAGE))
        form.addRow("Dil", self.lang_box)

        hint = QLabel(
            "Konuşma/tekrar/dolgu kelime analizi için önce transkript gerekir (Whisper). "
            "Yalnızca sessizlik ve sahne değişimi, transkriptsiz de tespit edilebilir."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        run_row = QHBoxLayout()
        self.transcribe_btn = QPushButton("1) Transkribe Et (Whisper)")
        self.transcribe_btn.clicked.connect(self._start_transcribe)
        self.analyze_btn = QPushButton("2) Analiz Et")
        self.analyze_btn.clicked.connect(self._start_analyze)
        run_row.addWidget(self.transcribe_btn)
        run_row.addWidget(self.analyze_btn)
        layout.addLayout(run_row)

        director_row = QHBoxLayout()
        self.profile_box = QComboBox()
        self._director_profiles = [
            (EditProfile.YOUTUBE_LONGFORM, "YouTube — Longform"),
            (EditProfile.SHORTS, "YouTube — Shorts"),
            (EditProfile.TIKTOK, "TikTok"),
            (EditProfile.INSTAGRAM_REEL, "Instagram Reels"),
            (EditProfile.HIGH_RETENTION, "High Retention"),
        ]
        self.profile_box.addItems([label for _, label in self._director_profiles])
        self.style_box = QComboBox()
        self._edit_styles = [(EditStyle.CINEMATIC, "Cinematic"), (EditStyle.VIRAL_FAST, "Viral Fast"), (EditStyle.STORY_DRIVEN, "Story Driven"), (EditStyle.PODCAST, "Podcast"), (EditStyle.TALKING_HEAD, "Talking Head"), (EditStyle.EDUCATIONAL, "Educational"), (EditStyle.DOCUMENTARY, "Documentary"), (EditStyle.VLOG, "Vlog"), (EditStyle.GAMING, "Gaming"), (EditStyle.MUSIC_VIDEO, "Music Video"), (EditStyle.PRODUCT, "Product"), (EditStyle.NEWS, "News"), (EditStyle.SPORTS, "Sports"), (EditStyle.MEME, "Meme"), (EditStyle.MINIMAL, "Minimal"),]
        self.style_box.addItems([label for _, label in self._edit_styles])
        form.addRow("Edit stili", self.style_box)
        self.director_btn = QPushButton("3) Auto Director Planı")
        self.director_btn.setToolTip(
            "Analiz sonuçlarını seçilen formata göre puanlar, güvenli kesimleri seçer "
            "ve tahmini final süre/pacing raporu üretir."
        )
        self.director_btn.clicked.connect(self._run_director)
        self.autonomous_btn = QPushButton("4) Autonomous QA")
        self.autonomous_btn.setToolTip(
            "Director planını retention-aware QA'dan geçirir ve ikinci pass için "
            "güvenli pattern-break/B-roll/narrative aksiyonları çıkarır."
        )
        self.autonomous_btn.clicked.connect(self._run_autonomous)
        self.sound_btn = QPushButton("5) AI Sound Design")
        self.sound_btn.setToolTip("Hook, beat, B-roll ve pattern-break olaylarından otomatik müzik/SFX/efekt planı çıkarır.")
        self.sound_btn.clicked.connect(self._run_sound_design)
        self.creative_btn = QPushButton("6) AI Creative Pass")
        self.creative_btn.setToolTip("Efekt, transition, motion, text animasyonu, SFX ve müziği Director olaylarına göre non-destructive olarak seçer.")
        self.creative_btn.clicked.connect(self._run_creative_pass)
        self.apply_creative_btn = QPushButton("7) Creative Pass Uygula")
        self.apply_creative_btn.setToolTip("AI Creative Pass kararlarını timeline keyframe/transition olarak uygular; kaynak videoya dokunmaz.")
        self.apply_creative_btn.clicked.connect(self._apply_creative_pass)
        self.compose_creative_btn = QPushButton("8) AI Creative Composer")
        self.compose_creative_btn.setToolTip("Beat, müzik ducking, efekt, motion, yazı ve SFX kararlarını tek kompozisyonda planlar.")
        self.compose_creative_btn.clicked.connect(self._run_creative_composer)
        self.multi_agent_btn = QPushButton("9) Multi-Agent Director")
        self.multi_agent_btn.setToolTip("Video, ses, konuşma, caption, ritim, yaratıcı, platform ve kalite ajanlarını paralel çalıştırır; en sonda tek Edit Plan üretir.")
        self.multi_agent_btn.clicked.connect(self._run_multi_agent)
        self.pro_edit_btn = QPushButton("6) Profesyonel Otomatik Kurgu")
        self.pro_edit_btn.setToolTip(
            "Ham videoyu editör mantığıyla işler: anlamı koruyan kesimler, kontrollü pacing, "
            "subtle push/reframe ve ses sürekliliği. Efekt yağdırmaz; karar kalitesini optimize eder."
        )
        self.pro_edit_btn.clicked.connect(self._run_professional_edit)
        director_row.addWidget(self.profile_box)
        director_row.addWidget(self.director_btn)
        director_row.addWidget(self.autonomous_btn)
        director_row.addWidget(self.sound_btn)
        director_row.addWidget(self.creative_btn)
        director_row.addWidget(self.apply_creative_btn)
        director_row.addWidget(self.compose_creative_btn)
        director_row.addWidget(self.multi_agent_btn)
        director_row.addWidget(self.pro_edit_btn)
        layout.addLayout(director_row)

        self.director_summary = QLabel("")
        self.director_summary.setObjectName("Muted")
        self.director_summary.setWordWrap(True)
        layout.addWidget(self.director_summary)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status_label = QLabel("Hazır.")
        self.status_label.setObjectName("Muted")
        layout.addWidget(self.status_label)

        self.suggestion_list = QListWidget()
        layout.addWidget(self.suggestion_list, 1)

        bulk_row = QHBoxLayout()
        self.accept_all_btn = QPushButton("Tümünü Kabul Et")
        self.accept_all_btn.clicked.connect(lambda: self._set_all_checked(True))
        self.reject_all_btn = QPushButton("Tümünü Reddet")
        self.reject_all_btn.clicked.connect(lambda: self._set_all_checked(False))
        self.copy_highlights_btn = QPushButton("Önemli Kelimeleri Kopyala")
        self.copy_highlights_btn.setToolTip(
            "Kabul edilen 'önemli kelime' önerilerini panoya kopyalar; AI Subtitle "
            "diyaloğundaki 'Her Zaman Vurgula' alanına yapıştırılabilir."
        )
        self.copy_highlights_btn.clicked.connect(self._copy_highlight_words)
        for b in (self.accept_all_btn, self.reject_all_btn, self.copy_highlights_btn):
            b.setEnabled(False)
            bulk_row.addWidget(b)
        layout.addLayout(bulk_row)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("Muted")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.apply_btn = QPushButton("Kabul Edilenleri Timeline'a Uygula (Kes)")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply_accepted)
        layout.addWidget(self.apply_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    # ---------------- kaynak klip listesi ----------------
    def _candidate_sources(self) -> list[tuple[str, str, str]]:
        """(clip_id, media_id, gorunen_ad) ucluleri — her klip ayri bir secenek (farkli
        kesim istenebilir), AI Subtitle'daki medya-bazli listeden farkli olarak."""
        out: list[tuple[str, str, str]] = []
        for clip in self.timeline.all_clips():
            if clip.media_id in self.media_paths:
                out.append((clip.id, clip.media_id, f"{clip.name or clip.media_id}  [{clip.start:.1f}s]"))
        return out

    def _selected(self) -> tuple[str | None, str | None]:
        idx = self.source_box.currentIndex()
        if idx < 0 or idx >= len(self._source_clip_ids):
            return None, None
        return self._source_clip_ids[idx], self.media_paths.get(self._source_media_ids[idx])

    def _selected_media_path(self) -> str:
        _, path = self._selected()
        return path or ""

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.source_box.setEnabled(enabled)
        self.lang_box.setEnabled(enabled)
        self.profile_box.setEnabled(enabled)
        self.transcribe_btn.setEnabled(enabled)
        self.analyze_btn.setEnabled(enabled)
        self.director_btn.setEnabled(enabled and self.report is not None)
        for btn in (self.autonomous_btn, self.sound_btn, self.creative_btn, self.apply_creative_btn, self.compose_creative_btn, self.multi_agent_btn, self.pro_edit_btn):
            btn.setEnabled(enabled and self.last_director_plan is not None)

    # ---------------- 1) transkripsiyon (opsiyonel) ----------------
    def _start_transcribe(self) -> None:
        _, path = self._selected()
        if not path:
            QMessageBox.information(self, "Kaynak yok", "Transkribe edilecek bir klip bulunamadı.")
            return
        language = self._lang_keys[self.lang_box.currentIndex()]
        self._set_controls_enabled(False)
        self.progress.setVisible(True)
        self.status_label.setText("Transkribe ediliyor…")

        self.transcribe_worker = TranscribeWorker(path, language, DEFAULT_MODEL_SIZE, self)
        self.transcribe_worker.finished_ok.connect(self._on_transcribed)
        self.transcribe_worker.failed.connect(self._on_transcribe_failed)
        self.transcribe_worker.start()

    def _on_transcribed(self, transcript: Transcript) -> None:
        self.transcript = transcript
        self.progress.setVisible(False)
        self.status_label.setText(f"Transkript hazır — {len(transcript.segments)} satır. Şimdi Analiz Et'e basın.")
        self._set_controls_enabled(True)

    def _on_transcribe_failed(self, message: str) -> None:
        self.progress.setVisible(False)
        self.status_label.setText("Transkripsiyon başarısız — yalnızca sessizlik/sahne analizi yapılabilir.")
        self._set_controls_enabled(True)
        QMessageBox.warning(self, "Transkripsiyon başarısız", message)

    # ---------------- 2) analiz ----------------
    def _start_analyze(self) -> None:
        clip_id, path = self._selected()
        if not clip_id or not path:
            QMessageBox.information(self, "Kaynak yok", "Analiz edilecek bir klip bulunamadı.")
            return
        language = self._lang_keys[self.lang_box.currentIndex()]
        self._set_controls_enabled(False)
        self.progress.setVisible(True)
        self.status_label.setText("Analiz ediliyor (sessizlik, tekrar, dolgu kelime, sahne)…")
        self.suggestion_list.clear()

        self.analyze_worker = AnalyzeWorker(clip_id, path, self.transcript, language, self)
        self.analyze_worker.finished_ok.connect(self._on_analyzed)
        self.analyze_worker.failed.connect(self._on_analyze_failed)
        self.analyze_worker.start()

    def _on_analyzed(self, report: AnalysisReport) -> None:
        self.report = report
        self.progress.setVisible(False)
        self._set_controls_enabled(True)
        self.suggestion_list.clear()
        for s in report.suggestions:
            title = _KIND_TITLES.get(s.kind, s.kind.value)
            text = f"[{title}] {s.label}  ({s.start:.1f}–{s.end:.1f} sn)"
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if s.accepted else Qt.Unchecked)
            item.setData(Qt.UserRole, s)
            self.suggestion_list.addItem(item)
        has_suggestions = bool(report.suggestions)
        for b in (self.accept_all_btn, self.reject_all_btn, self.copy_highlights_btn, self.apply_btn):
            b.setEnabled(has_suggestions)
        self.status_label.setText(f"{len(report.suggestions)} öneri bulundu.")
        self._update_summary()
        self.suggestion_list.itemChanged.connect(self._on_item_changed)

    def _run_director(self) -> None:
        if not self.report:
            QMessageBox.information(self, "Önce analiz", "Önce Analiz Et ile kaynak klibi analiz edin.")
            return
        profile = self._director_profiles[self.profile_box.currentIndex()][0]
        style = self._edit_styles[self.style_box.currentIndex()][0]
        plan = build_director_plan(self.report, self.transcript, profile, style=style)
        apply_director_plan(self.report, plan)
        self.last_director_plan = plan
        self.director_summary.setText(
            f"Director: {plan.profile} — {plan.cut_seconds:.1f}s kesim adayı, "
            f"final ≈ {plan.estimated_final_duration:.1f}s, pacing {plan.pacing_score:.0f}/100 | "
            f"hook {plan.hook_score:.0f}/100, narrative {plan.narrative_score:.0f}/100 | "
            f"{len(plan.events)} yapısal olay, {len(plan.accepted_decisions())} otomatik karar."
        )
        self._on_analyzed(self.report)

    def _run_autonomous(self) -> None:
        if not self.report:
            QMessageBox.information(self, "Önce analiz", "Önce Analiz Et ve Auto Director Planı çalıştırın.")
            return
        profile = self._director_profiles[self.profile_box.currentIndex()][0]
        style = self._edit_styles[self.style_box.currentIndex()][0]
        plan = build_director_plan(self.report, self.transcript, profile, style=style)
        result = run_autonomous_edit_pass(plan, max_passes=2)
        apply_director_plan(self.report, result.plan)
        self.last_director_plan = result.plan
        actions = ", ".join(result.qa.actions) if result.qa.actions else "ek aksiyon yok"
        self.director_summary.setText(
            f"Autonomous QA: {result.qa.score:.0f}/100 — risk {result.qa.risk.value} | "
            f"{result.pass_number} pass | aksiyonlar: {actions}"
        )
        self._on_analyzed(self.report)

    def _run_professional_edit(self) -> None:
        if not self.report:
            QMessageBox.information(self, "Önce analiz", "Önce Analiz Et ile ham videoyu analiz edin.")
            return
        clip_id = self.report.clip_id
        found = self.timeline.find(clip_id)
        if not found:
            QMessageBox.warning(self, "Klip bulunamadı", "Kaynak klip timeline'da bulunamadı.")
            return
        _, clip = found
        profile_key = "professional"
        selected_profile = self._director_profiles[self.profile_box.currentIndex()][0]
        if selected_profile == EditProfile.HIGH_RETENTION:
            profile_key = "high_retention"
        elif selected_profile == EditProfile.SHORTS:
            profile_key = "high_retention"
        elif selected_profile in (EditProfile.TIKTOK, EditProfile.INSTAGRAM_REEL):
            profile_key = "high_retention"
        elif selected_profile == EditProfile.YOUTUBE_LONGFORM:
            profile_key = "professional"

        plan = build_professional_edit_plan(
            clip.name or clip.media_id,
            clip.source_out - clip.source_in,
            self.report,
            self.transcript,
            profile=profile_key,
        )
        n = apply_professional_edit(self.timeline, clip_id, plan)
        if n <= 0:
            QMessageBox.information(
                self, "Profesyonel kurgu",
                "Güvenli bir otomatik kesim bulunamadı. Kaynak korunarak yalnızca analiz sonucu üretildi."
            )
            self.director_summary.setText(
                f"Profesyonel Editor: {plan.editorial_score:.0f}/100 | kesim 0s | "
                f"final ≈ {plan.estimated_duration:.1f}s | {len(plan.actions)} edit aksiyonu."
            )
            return
        self.changed = True
        self.apply_btn.setEnabled(False)
        self.director_summary.setText(
            f"Profesyonel Editor: {plan.editorial_score:.0f}/100 | {n} güvenli kesim | "
            f"{sum(e-s for s,e in plan.cut_ranges):.1f}s temizlendi | "
            f"final ≈ {plan.estimated_duration:.1f}s | {len(plan.actions)} edit aksiyonu."
        )
        QMessageBox.information(
            self, "Profesyonel kurgu tamamlandı",
            f"{n} kesim uygulandı.\n\n"
            f"Edit skoru: {plan.editorial_score:.0f}/100\n"
            f"Temizlenen süre: {sum(e-s for s,e in plan.cut_ranges):.1f} sn\n"
            f"Tahmini final: {plan.estimated_duration:.1f} sn\n\n"
            "Kurgu; anlamı koruma, pacing, kontrollü motion ve ses sürekliliği önceliğiyle oluşturuldu."
        )

    def _run_sound_design(self) -> None:
        if self.last_director_plan is None:
            QMessageBox.information(self, "Önce Director", "Önce Auto Director Planı veya Autonomous QA çalıştırın.")
            return
        sound = build_sound_design_plan(self.last_director_plan)
        sfx = len(sound.sound_decisions)
        visuals = len(sound.visual_decisions)
        music = sound.music_asset or "uygun starter müzik bulunamadı"
        preview = "\n".join(
            f"• {d.start:.1f}s — {d.asset_id} ({d.reason})"
            for d in sound.sound_decisions[:10]
        ) or "SFX cue yok."
        QMessageBox.information(
            self, "AI Sound Design",
            f"Müzik: {music}\nMüzik seviyesi: {sound.music_gain_db:.1f} dB\n"
            f"SFX cue: {sfx} | Görsel efekt kararı: {visuals}\n\n"
            f"İlk cue'lar:\n{preview}\n\n"
            "Not: Bu sürüm planı güvenli/non-destructive olarak üretir; seçilen asset'in yayın lisansını kontrol edin."
        )

    def _run_creative_pass(self) -> None:
        if self.last_director_plan is None:
            QMessageBox.information(self, "Önce Director", "Önce Auto Director Planı veya Autonomous QA çalıştırın.")
            return
        creative = build_creative_pass_plan(self.last_director_plan)
        counts = {}
        for d in creative.decisions:
            counts[d.kind] = counts.get(d.kind, 0) + 1
        preview = "\n".join(
            f"• {d.start:.1f}s — {d.kind}: {d.asset_id} ({d.reason})"
            for d in creative.decisions[:14]
        ) or "Creative cue yok."
        self.director_summary.setText(
            f"AI Creative Pass: {len(creative.decisions)} karar | "
            f"Müzik: {creative.music_asset or 'yok'} | "
            f"{', '.join(f'{k}={v}' for k,v in sorted(counts.items()))}"
        )
        QMessageBox.information(
            self, "AI Creative Pass",
            f"Müzik: {creative.music_asset or 'yok'}\n"
            f"Müzik seviyesi: {creative.music_gain_db:.1f} dB\n"
            f"Toplam creative karar: {len(creative.decisions)}\n\n"
            f"İlk kararlar:\n{preview}\n\n"
            "Bu pass non-destructive'dir; kararlar timeline'a doğrudan basılmaz, render pipeline'ına güvenli şekilde aktarılabilir."
        )

    def _apply_creative_pass(self) -> None:
        if self.last_director_plan is None:
            QMessageBox.information(self, "Önce Director", "Önce Auto Director Planı veya Autonomous QA çalıştırın.")
            return
        creative = build_creative_pass_plan(self.last_director_plan)
        report = apply_creative_pass(self.timeline, creative)
        self.changed = self.changed or report.applied > 0
        self.director_summary.setText(
            f"Creative Pass uygulandı: {report.applied} karar | "
            f"efekt={report.effects}, motion={report.motions}, geçiş={report.transitions}, yazı={report.text_cues}"
        )
        QMessageBox.information(
            self, "Creative Pass uygulandı",
            f"{report.applied} karar timeline'a uygulandı.\n\n"
            f"Efekt: {report.effects}\nMotion: {report.motions}\n"
            f"Geçiş: {report.transitions}\nYazı cue: {report.text_cues}\n"
            f"Atlanan: {report.skipped}\n\n"
            "Kaynak medya değiştirilmedi. Export sırasında keyframe ve geçişler FFmpeg'e çevrilecek."
        )

    def _run_creative_composer(self) -> None:
        if self.last_director_plan is None:
            QMessageBox.information(self, "Önce Director", "Önce Auto Director Planı veya Autonomous QA çalıştırın.")
            return
        comp = compose_creative_edit(self.last_director_plan, bpm=120.0)
        self.director_summary.setText(
            f"AI Creative Composer: {len(comp.cues)} cue | BPM={comp.bpm:.0f} | "
            f"Duck={len(comp.duck_segments)} | QA={comp.quality.get('status','unknown')}"
        )
        preview = "\n".join(f"• {c.time:.2f}s — {c.kind}: {c.asset_id or '-'}" for c in comp.cues[:16]) or "Cue yok."
        QMessageBox.information(self, "AI Creative Composer",
            f"BPM: {comp.bpm:.0f}\nCue: {len(comp.cues)}\nMusic: {comp.music_asset or 'yok'}\n"
            f"Ducking segment: {len(comp.duck_segments)}\nQA: {comp.quality.get('status')}\n\n{preview}")

    def _run_multi_agent(self) -> None:
        if self.last_director_plan is None:
            QMessageBox.information(self, "Önce Director", "Önce Auto Director Planı veya Autonomous QA çalıştırın.")
            return
        speech=[]
        if self.transcript and self.transcript.segments:
            speech=[(float(x.start), float(x.end)) for x in self.transcript.segments]
        events=[{"kind":e.kind,"start":float(e.start),"end":float(e.end),"score":float(e.score),"reason":e.reason} for e in self.last_director_plan.events]
        context={
            "profile": str(self.last_director_plan.profile),
            "duration": float(self.last_director_plan.source_duration),
            "plan_events": events,
            "speech_segments": speech,
            "highlight_words": list(self.last_director_plan.highlight_words),
            "bpm": 120.0,
            "language": getattr(self.transcript, "language", "tr") if self.transcript else "tr",
            "source_fingerprint": self._selected_media_path(),
        }
        self.progress.setVisible(True)
        self.status_label.setText("Uzman AI ajanları paralel analiz yapıyor…")
        self._set_controls_enabled(False)
        self.multi_agent_worker=MultiAgentWorker(context,self)
        self.multi_agent_worker.finished_ok.connect(self._on_multi_agent_done)
        self.multi_agent_worker.failed.connect(self._on_multi_agent_failed)
        self.multi_agent_worker.start()

    def _on_multi_agent_done(self, result) -> None:
        self.progress.setVisible(False)
        self._set_controls_enabled(True)
        self.last_compiled_edit_plan=result.compiled
        ok=sum(r.status=="ok" for r in result.results.values())
        cached=sum(r.cached for r in result.results.values())
        self.status_label.setText("Multi-Agent plan hazır.")
        self.director_summary.setText(
            f"Multi-Agent Director: {ok}/{len(result.results)} ajan | cache={cached} | "
            f"timeline cue={len(result.compiled.timeline)} | render={result.compiled.render.get('width')}x{result.compiled.render.get('height')}"
        )
        preview="\n".join(f"• {a}: {r.status}{' (cache)' if r.cached else ''} — {r.confidence:.0%}" for a,r in sorted(result.results.items()))
        QMessageBox.information(self,"Multi-Agent Director",
            f"{ok}/{len(result.results)} uzman ajan tamamlandı.\nCache hit: {cached}\n"
            f"Compiler timeline cue: {len(result.compiled.timeline)}\n\n{preview}\n\n"
            "Ajanlar render yapmaz; yalnızca analiz/karar üretir. Final Compiler tek bir render planı oluşturur.")

    def _on_multi_agent_failed(self, message: str) -> None:
        self.progress.setVisible(False)
        self._set_controls_enabled(True)
        self.status_label.setText("Multi-Agent analiz başarısız.")
        QMessageBox.critical(self,"Multi-Agent Director",message)

    def _on_analyze_failed(self, message: str) -> None:
        self.progress.setVisible(False)
        self._set_controls_enabled(True)
        self.status_label.setText("Analiz başarısız.")
        QMessageBox.critical(self, "Analiz başarısız", message)

    # ---------------- oneri kabul/ret ----------------
    def _on_item_changed(self, item: QListWidgetItem) -> None:
        s: Suggestion = item.data(Qt.UserRole)
        s.accepted = item.checkState() == Qt.Checked
        self._update_summary()

    def _set_all_checked(self, checked: bool) -> None:
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.suggestion_list.count()):
            self.suggestion_list.item(i).setCheckState(state)

    def _update_summary(self) -> None:
        if not self.report:
            self.summary_label.setText("")
            return
        total = self.report.total_cut_seconds()
        n_accepted = len(self.report.accepted())
        self.summary_label.setText(
            f"{n_accepted} öneri kabul edildi — tahmini kesilecek süre: {total:.1f} sn"
        )

    def _copy_highlight_words(self) -> None:
        if not self.report:
            return
        words = [s.word for s in self.report.accepted() if s.kind == SuggestionKind.HIGHLIGHT_WORD and s.word]
        if not words:
            QMessageBox.information(self, "Kelime yok", "Kabul edilmiş bir 'önemli kelime' önerisi yok.")
            return
        QApplication.clipboard().setText(", ".join(words))
        QMessageBox.information(self, "Kopyalandı", f"{len(words)} kelime panoya kopyalandı.")

    # ---------------- uygula ----------------
    def _apply_accepted(self) -> None:
        if not self.report:
            return
        clip_id = self.report.clip_id
        if not self.timeline.find(clip_id):
            QMessageBox.warning(self, "Klip bulunamadı", "Bu klip timeline'dan kaldırılmış olabilir.")
            return
        n = apply_accepted_cuts(self.timeline, clip_id, self.report.suggestions)
        if n == 0:
            QMessageBox.information(self, "Uygulanacak kesim yok", "Kabul edilmiş bir kesim önerisi bulunamadı.")
            return
        QMessageBox.information(self, "Tamamlandı", f"{n} kesim timeline'a uygulandı.")
        self.changed = True
        self.apply_btn.setEnabled(False)

    def closeEvent(self, event) -> None:  # noqa: N802
        for w in (self.transcribe_worker, self.analyze_worker):
            if w and w.isRunning():
                w.wait(5000)
        super().closeEvent(event)
