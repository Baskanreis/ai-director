"""Shorts Director Studio UI — v2.13."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QProgressBar, QVBoxLayout, QWidget
from app.shorts import extract_candidates, build_plan
from app.shorts.models import ShortsCandidate
from app.subtitle.models import Transcript
from app.subtitle.transcribe import DEFAULT_LANGUAGE, DEFAULT_MODEL_SIZE, SUPPORTED_LANGUAGES
from app.subtitle.worker import TranscribeWorker
from app.timeline.model import Clip, new_id
from app.project.project import Project

class ShortsDirectorDialog(QDialog):
    def __init__(self, project: Project, parent: QWidget | None = None):
        super().__init__(parent)
        self.project=project; self.transcript: Transcript|None=None; self.worker=None
        self.candidates: list[ShortsCandidate]=[]; self.plans=[]; self.changed=False
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
        hint=QLabel("AI; hook→build-up→payoff yapısını, bağlamı ve pacing'i birlikte optimize eder. “Viral” garanti edilmez; aşırı efekt yerine seyir akışını korur."); hint.setWordWrap(True); hint.setObjectName("Muted"); lay.addWidget(hint)
        row=QHBoxLayout(); self.transcribe=QPushButton("1) Videoyu Transkribe Et"); self.transcribe.clicked.connect(self._transcribe); self.analyze=QPushButton("2) Shorts Adaylarını Çıkar"); self.analyze.clicked.connect(self._analyze); self.apply=QPushButton("3) Seçili Short'u Timeline'a Aktar"); self.apply.clicked.connect(self._apply); self.apply.setEnabled(False); row.addWidget(self.transcribe); row.addWidget(self.analyze); row.addWidget(self.apply); lay.addLayout(row)
        self.progress=QProgressBar(); self.progress.setRange(0,0); self.progress.hide(); lay.addWidget(self.progress)
        self.list=QListWidget(); lay.addWidget(self.list,1)
        self.status=QLabel("Hazır."); self.status.setObjectName("Muted"); lay.addWidget(self.status)
        close=QPushButton("Kapat"); close.clicked.connect(self.accept); lay.addWidget(close)
        self.list.itemSelectionChanged.connect(lambda: self.apply.setEnabled(bool(self.list.selectedItems())))

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
        if self.candidates: self.list.setCurrentRow(0)

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
