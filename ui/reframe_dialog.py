from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import QComboBox,QDialog,QFileDialog,QFormLayout,QHBoxLayout,QLabel,QMessageBox,QProgressBar,QPushButton,QVBoxLayout
from app.project.project import Project
from app.shorts.remix import RemixPlan, RemixSegment
from app.shorts.remix_worker import RemixRenderWorker

class SmartReframeDialog(QDialog):
    """Standalone Smart Reframe entry point using the production Shorts renderer."""
    def __init__(self, project: Project, parent=None):
        super().__init__(parent); self.project=project; self.worker=None
        self.setWindowTitle("Smart Reframe — 9:16 Subject-Aware"); self.resize(620,360)
        root=QVBoxLayout(self); form=QFormLayout(); root.addLayout(form)
        self.source=QComboBox(); self.media_ids=[]
        for m in project.media:
            if m.media_type=="video" and m.exists:
                self.media_ids.append(m.id); self.source.addItem(f"{m.name} — {m.duration:.1f}s")
        form.addRow("Video",self.source)
        hint=QLabel("Yüz takibi varsa OpenCV ile odak noktası çıkarılır; bulunamazsa güvenli merkez crop kullanılır. Çıktı 1080×1920 MP4 olur."); hint.setWordWrap(True); hint.setObjectName("Muted"); root.addWidget(hint)
        row=QHBoxLayout(); self.render=QPushButton("Smart Reframe Render"); self.render.clicked.connect(self.start); self.cancel=QPushButton("İptal"); self.cancel.clicked.connect(self.stop); self.cancel.setEnabled(False); row.addWidget(self.render); row.addWidget(self.cancel); root.addLayout(row)
        self.progress=QProgressBar(); self.progress.hide(); root.addWidget(self.progress); self.status=QLabel("Hazır."); self.status.setObjectName("Muted"); root.addWidget(self.status)
    def start(self):
        i=self.source.currentIndex(); media=next((m for m in self.project.media if i>=0 and i<len(self.media_ids) and m.id==self.media_ids[i]),None)
        if not media: QMessageBox.information(self,"Medya yok","Önce bir video ekleyin."); return
        out,_=QFileDialog.getSaveFileName(self,"Smart Reframe çıktısı",str(Path(media.path).with_name(Path(media.path).stem+"_9x16.mp4")),"MP4 Video (*.mp4)")
        if not out: return
        seg=RemixSegment("reframe",0.0,float(media.duration),"reframe",1)
        plan=RemixPlan("Smart Reframe", "youtube_shorts", (seg,), float(media.duration), 100.0, "subject_aware_9x16", ("OpenCV face tracking when available",))
        self.progress.setRange(0,100); self.progress.show(); self.render.setEnabled(False); self.cancel.setEnabled(True); self.status.setText("Smart Reframe render başlatılıyor…")
        self.worker=RemixRenderWorker(media.path,plan,out,[],self); self.worker.progress_changed.connect(self.progress_changed); self.worker.finished_ok.connect(self.done); self.worker.failed.connect(self.failed); self.worker.cancelled.connect(lambda:self.status.setText("Render iptal edildi.")); self.worker.finished.connect(self.finished); self.worker.start()
    def progress_changed(self,frac,msg): self.progress.setValue(int(max(0,min(1,frac))*100)); self.status.setText(msg)
    def done(self,path): QMessageBox.information(self,"Smart Reframe hazır",f"9:16 video render edildi:\n\n{path}"); self.status.setText(f"Hazır: {path}")
    def failed(self,msg): QMessageBox.critical(self,"Smart Reframe başarısız",msg); self.status.setText("Render başarısız.")
    def finished(self): self.render.setEnabled(True); self.cancel.setEnabled(False); self.worker=None
    def stop(self):
        if self.worker and self.worker.isRunning(): self.worker.cancel(); self.cancel.setEnabled(False)
