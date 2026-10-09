"""Shorts Director Studio UI — v2.13."""
from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QProgressBar, QVBoxLayout, QWidget, QFileDialog
from app.shorts import extract_candidates, build_plan, build_remix
from app.shorts.remix_worker import RemixRenderWorker
from app.shorts.models import ShortsCandidate
from app.subtitle.models import Transcript
from app.subtitle.transcribe import DEFAULT_LANGUAGE, DEFAULT_MODEL_SIZE, SUPPORTED_LANGUAGES
from app.subtitle.style import PRESETS
from app.subtitle.worker import TranscribeWorker
from app.timeline.model import Clip, new_id
from app.project.project import Project

class ShortsDirectorDialog(QDialog):
    def __init__(self, project: Project, parent: QWidget | None = None):
        super().__init__(parent)
        self.project=project; self.transcript: Transcript|None=None; self.worker=None
        self.candidates: list[ShortsCandidate]=[]; self.plans=[]; self.changed=False; self.render_worker=None
        self.setWindowTitle("AI Shorts Director — Professional Short-Form")
        self.setMinimumSize(760,620)
        lay=QVBoxLayout(self)
        form=QFormLayout(); lay.addLayout(form)
        self.source=QComboBox(); self.media_ids=[]
        for m in project.media:
            if m.media_type=="video" and m.exists:
                self.media_ids.append(m.id); self.source.addItem(f"{m.name} — {m.duration:.1f}s")
        form.addRow("Uzun video",self.source)
        self.lang=QComboBox(); self.lang_keys=[k for k in SUPPORTED_LANGUAGES if k!="auto"]; self.lang.addItems([SUPPORTED_LANGUAGES[k] for k in self.lang_keys]); self.lang.setCurrentIndex(max(0,self.lang_keys.index(DEFAULT_LANGUAGE)))
        form.addRow("Dil",self.lang)
        self.target=QComboBox(); self.target.addItems(["YouTube Shorts","TikTok","Instagram Reels"]); form.addRow("Hedef",self.target)
        self.caption_style=QComboBox(); self.caption_style_keys=list(PRESETS.keys()); self.caption_style.addItems([PRESETS[k].name for k in self.caption_style_keys]); self.caption_style.setCurrentIndex(self.caption_style_keys.index("bold_hook") if "bold_hook" in self.caption_style_keys else 0); form.addRow("Caption stili",self.caption_style)
        hint=QLabel("AI; hook→build-up→payoff yapısını, bağlamı ve pacing'i birlikte optimize eder. “Viral” garanti edilmez; aşırı efekt yerine seyir akışını korur."); hint.setWordWrap(True); hint.setObjectName("Muted"); lay.addWidget(hint)
        row=QHBoxLayout(); self.transcribe=QPushButton("1) Videoyu Transkribe Et"); self.transcribe.clicked.connect(self._transcribe); self.analyze=QPushButton("2) Shorts Adaylarını Çıkar"); self.analyze.clicked.connect(self._analyze); self.apply=QPushButton("3) Seçili Short'u Timeline'a Aktar"); self.apply.clicked.connect(self._apply); self.apply.setEnabled(False); self.remix=QPushButton("4) Seçilenleri Remixle"); self.remix.clicked.connect(self._remix); self.remix.setEnabled(False); self.render=QPushButton("5) Remixi Render Et"); self.render.clicked.connect(self._render_remix); self.render.setEnabled(False); self.cancel_render=QPushButton("İptal"); self.cancel_render.clicked.connect(self._cancel_render); self.cancel_render.setEnabled(False); self.auto_short=QPushButton("✨ AI Short Oluştur"); self.auto_short.clicked.connect(self._auto_short); self.auto_short.setEnabled(False); row.addWidget(self.transcribe); row.addWidget(self.analyze); row.addWidget(self.apply); row.addWidget(self.remix); row.addWidget(self.render); row.addWidget(self.auto_short); row.addWidget(self.cancel_render); lay.addLayout(row)
        self.progress=QProgressBar(); self.progress.setRange(0,0); self.progress.hide(); lay.addWidget(self.progress)
        self.list=QListWidget(); self.list.setSelectionMode(QListWidget.MultiSelection); lay.addWidget(self.list,1)
        self.status=QLabel("Hazır."); self.status.setObjectName("Muted"); lay.addWidget(self.status)
        close=QPushButton("Kapat"); close.clicked.connect(self.accept); lay.addWidget(close)
        self.list.itemSelectionChanged.connect(self._selection_changed)

    def _selected_media(self):
        i=self.source.currentIndex()
        if i<0 or i>=len(self.media_ids): return None
        return next((m for m in self.project.media if m.id==self.media_ids[i]),None)

    def _transcribe(self):
        m=self._selected_media()
        if not m: QMessageBox.information(self,"Kaynak yok","Önce bir video seçin."); return
        self.progress.show(); self.transcribe.setEnabled(False); self.status.setText("Whisper transkripsiyonu hazırlanıyor…")
        language=self.lang_keys[self.lang.currentIndex()]
        self.worker=TranscribeWorker(m.path,language,DEFAULT_MODEL_SIZE,self)
        self.worker.finished_ok.connect(self._on_transcribed); self.worker.failed.connect(self._on_failed); self.worker.start()

    def _on_transcribed(self, tx):
        self.transcript=tx; self.progress.hide(); self.transcribe.setEnabled(True); self.status.setText(f"Transkript hazır: {len(tx.segments)} bölüm. Şimdi adayları çıkarabilirsiniz.")

    def _on_failed(self,msg):
        self.progress.hide(); self.transcribe.setEnabled(True); QMessageBox.warning(self,"Transkripsiyon başarısız",msg); self.status.setText("Transkripsiyon başarısız; Shorts analizi için transkript gerekir.")

    def _analyze(self):
        if not self.transcript: QMessageBox.information(self,"Önce transkript","Önce Videoyu Transkribe Et'e basın."); return
        self.candidates=extract_candidates(self.transcript,12,58,12); self.list.clear(); self.plans=[]
        for c in self.candidates:
            item=QListWidgetItem(f"{c.score:05.1f}/100  •  {c.duration:.1f}s  •  {c.source_start:.1f}–{c.source_end:.1f}s  •  {', '.join(c.tags) or 'balanced'}\n{c.text[:180]}")
            item.setData(Qt.UserRole,c.id); self.list.addItem(item)
        self.status.setText(f"{len(self.candidates)} farklı Short adayı bulundu. En yüksek skor; garanti edilmiş izlenme değil, editoryal sinyal skorudur.")
        if self.candidates:
            self.list.setCurrentRow(0)
            self.auto_short.setEnabled(len(self.candidates) >= 2)

    def _selection_changed(self):
        count = len(self.list.selectedItems())
        self.apply.setEnabled(count == 1)
        self.remix.setEnabled(count >= 2)

    def _remix(self):
        items = self.list.selectedItems()
        if len(items) < 2:
            return
        selected_ids = {item.data(Qt.UserRole) for item in items}
        selected = [c for c in self.candidates if c.id in selected_ids]
        target=["youtube_shorts","tiktok","instagram_reel"][self.target.currentIndex()]
        try:
            plan = build_remix(selected, target)
        except ValueError as exc:
            QMessageBox.warning(self, "Remix oluşturulamadı", str(exc))
            return
        self.project.editor_data.setdefault("shorts_director", {})["latest_remix"] = plan.to_dict()
        self.project.touch(); self.changed=True
        self.latest_remix = plan
        # Build one continuous caption timeline for the reordered Remix.
        self.latest_caption_cues = []
        by_id = {c.id: c for c in selected}
        out_cursor = 0.0
        for seg in plan.segments:
            candidate = by_id.get(seg.candidate_id)
            if candidate and self.transcript:
                candidate_plan = build_plan(candidate, self.transcript, target)
                for cue in candidate_plan.captions:
                    a = max(seg.source_start, cue.start)
                    b = min(seg.source_end, cue.end)
                    if b > a:
                        self.latest_caption_cues.append({
                            "start": round(out_cursor + (a - seg.source_start), 3),
                            "end": round(out_cursor + (b - seg.source_start), 3),
                            "text": cue.text,
                            "emphasis_words": list(cue.emphasis_words),
                        })
            out_cursor += seg.duration
        self.render.setEnabled(True)
        caption_note = f" • {len(self.latest_caption_cues)} dinamik altyazı" if self.latest_caption_cues else ""
        self.status.setText(f"Remix planı hazır: {len(plan.segments)} bölüm • {plan.total_duration:.1f}s • score {plan.score:.1f}{caption_note}")
        QMessageBox.information(self, "Short Remix hazır",
            f"{len(plan.segments)} ayrı bölüm tek akışta birleştirildi.\n\n"
            f"Akış: hook → build → payoff\nSüre: {plan.total_duration:.1f}s\nSkor: {plan.score:.1f}")

    def _auto_short(self):
        """One-click AI Short: choose diverse top candidates, build captions and render.

        The user still chooses the destination filename; source media is never modified.
        """
        if not self.transcript or len(self.candidates) < 2:
            QMessageBox.information(self, "Önce analiz", "Önce videoyu transkribe edip Shorts adaylarını çıkarın.")
            return
        selected = self.candidates[:3]
        target = ["youtube_shorts", "tiktok", "instagram_reel"][self.target.currentIndex()]
        try:
            plan = build_remix(selected, target)
        except ValueError as exc:
            QMessageBox.warning(self, "AI Short oluşturulamadı", str(exc)); return
        self.latest_remix = plan
        self.latest_caption_cues = []
        by_id = {c.id: c for c in selected}
        cursor = 0.0
        for seg in plan.segments:
            c = by_id.get(seg.candidate_id)
            if not c: continue
            cp = build_plan(c, self.transcript, target)
            for cue in cp.captions:
                a=max(seg.source_start,cue.start); b=min(seg.source_end,cue.end)
                if b>a:
                    self.latest_caption_cues.append({"start":round(cursor+a-seg.source_start,3),"end":round(cursor+b-seg.source_start,3),"text":cue.text,"emphasis_words":list(cue.emphasis_words)})
            cursor += seg.duration
        self.render.setEnabled(True)
        self.status.setText(f"AI Short hazır: {len(plan.segments)} bölüm • {plan.total_duration:.1f}s • Smart Reframe + dinamik altyazı")
        self._render_remix()

    def _render_remix(self):
        plan = getattr(self, "latest_remix", None)
        media = self._selected_media()
        if not plan or not media:
            QMessageBox.information(self, "Remix yok", "Önce en az iki aday seçip Remix oluşturun.")
            return
        default = str(Path(media.path).with_name("AI_Director_Remix.mp4"))
        out, _ = QFileDialog.getSaveFileName(self, "Remix çıktısını kaydet", default, "MP4 Video (*.mp4)")
        if not out:
            return
        self.progress.setRange(0, 100); self.progress.setValue(0); self.progress.show()
        self.render.setEnabled(False); self.remix.setEnabled(False); self.cancel_render.setEnabled(True)
        self.status.setText("Render kuyruğa alındı…")
        self.render_worker = RemixRenderWorker(media.path, plan, out, getattr(self, "latest_caption_cues", []), self)
        self.render_worker.progress_changed.connect(self._render_progress)
        self.render_worker.finished_ok.connect(self._render_finished)
        self.render_worker.failed.connect(self._render_failed)
        self.render_worker.cancelled.connect(self._render_cancelled)
        self.render_worker.finished.connect(self._render_worker_finished)
        self.render_worker.start()

    def _render_progress(self, frac, msg):
        self.progress.setValue(int(max(0.0, min(1.0, frac)) * 100))
        self.status.setText(msg)

    def _render_finished(self, result):
        plan = getattr(self, "latest_remix", None)
        self.project.editor_data.setdefault("shorts_director", {})["latest_render"] = {"path": result, "plan": plan.to_dict() if plan else {}}
        self.project.touch(); self.changed = True
        QMessageBox.information(self, "Remix hazır", f"Dikey Remix render edildi:\n\n{result}")
        self.status.setText(f"Render tamamlandı: {result}")

    def _render_failed(self, msg):
        QMessageBox.critical(self, "Render başarısız", msg)
        self.status.setText("Remix render başarısız.")

    def _render_cancelled(self):
        self.status.setText("Remix render iptal edildi.")

    def _cancel_render(self):
        if self.render_worker and self.render_worker.isRunning():
            self.cancel_render.setEnabled(False)
            self.status.setText("Render durduruluyor…")
            self.render_worker.cancel()

    def _render_worker_finished(self):
        self.progress.hide()
        self.render.setEnabled(True)
        self.cancel_render.setEnabled(False)
        self.remix.setEnabled(len(self.list.selectedItems()) >= 2)
        self.render_worker = None

    def _apply(self):
        items=self.list.selectedItems()
        if not items: return
        cid=items[0].data(Qt.UserRole); c=next(x for x in self.candidates if x.id==cid); m=self._selected_media()
        target=["youtube_shorts","tiktok","instagram_reel"][self.target.currentIndex()]
        plan=build_plan(c,self.transcript,target)
        plan=__import__('dataclasses').replace(plan,source=m.path)
        self.project.editor_data.setdefault("shorts_director",{})[cid]=plan.to_dict(); self.project.editor_data["shorts_director"]["latest"]=plan.to_dict()
        # Non-destructive timeline insertion: source range becomes a normal editable clip.
        video=self.project.timeline.first_track("video")
        start=video.end
        link = new_id()
        clip=Clip(m.id,f"Shorts • {cid}",c.source_start,c.source_end,start,link_id=link)
        video.add(clip)
        if m.has_audio:
            audio=self.project.timeline.first_track("audio")
            if not audio.overlaps(start,clip.end):
                audio.add(Clip(m.id,f"Shorts Audio • {cid}",c.source_start,c.source_end,start,link_id=link))
        self.project.touch(); self.changed=True
        self.status.setText(f"{cid} timeline'a eklendi: {c.duration:.1f}s • {target} • score {c.score:.1f}")
        QMessageBox.information(self,"Short oluşturuldu",f"{c.duration:.1f} saniyelik Short timeline'a eklendi.\n\nSonraki adım: Auto-Reframe, dinamik altyazı ve B-roll planını export/render aşamasında uygulayabilirsiniz.")
