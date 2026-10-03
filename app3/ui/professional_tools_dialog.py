"""Professional editor tools dialog."""
from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QListWidget,QMessageBox,QFileDialog,QDoubleSpinBox,QCheckBox,QInputDialog
from app.pro import MarkerStore, MediaRelinker, RenderQueue, ProfessionalEditEngine, EditingWorkspace, EDIT_MODES, AdvancedEditorState, CompoundClip, AdjustmentLayer, ProxyAsset, MulticamSequence, MulticamAngle

class ProfessionalToolsDialog(QDialog):
    def __init__(self, project, history, refresh, parent=None):
        super().__init__(parent); self.project=project; self.history=history; self.refresh=refresh
        self.setWindowTitle("Professional Edit Suite"); self.resize(620,480)
        self.markers=MarkerStore.from_dict(project.editor_data.get("markers",[]))
        self.queue=RenderQueue.from_dict(project.editor_data.get("render_queue",[]))
        self.workspace=EditingWorkspace.from_dict(project.editor_data.get("workspace",{}))
        lay=QVBoxLayout(self)
        lay.addWidget(QLabel("<h2>Professional Edit Suite</h2><p>Hızlı kurgu, marker, medya relink ve render kuyruğu araçları.</p>"))
        row=QHBoxLayout()
        self.time=QDoubleSpinBox(); self.time.setRange(0,99999); self.time.setDecimals(3); self.time.setSingleStep(0.001)
        row.addWidget(QLabel("Marker zamanı:")); row.addWidget(self.time)
        add=QPushButton("Marker Ekle"); add.clicked.connect(self.add_marker); row.addWidget(add)
        lay.addLayout(row)
        self.marker_list=QListWidget(); lay.addWidget(self.marker_list)
        mrow=QHBoxLayout(); rm=QPushButton("Marker Sil"); rm.clicked.connect(self.remove_marker); mrow.addWidget(rm)
        snap=QPushButton("Playhead'e Git"); snap.clicked.connect(self.goto_marker); mrow.addWidget(snap); lay.addLayout(mrow)
        rel=QPushButton("Eksik Medyayı Klasörden Bul…"); rel.clicked.connect(self.relink); lay.addWidget(rel)
        lay.addWidget(QLabel("<b>Edit Workspace</b>"))
        wrow=QHBoxLayout()
        for mode in EDIT_MODES:
            b=QPushButton(mode.title()); b.setCheckable(True); b.clicked.connect(lambda checked, m=mode: self.set_edit_mode(m)); wrow.addWidget(b)
        lay.addLayout(wrow)
        mfr=QPushButton("Playhead'de Match Frame"); mfr.clicked.connect(self.match_frame); lay.addWidget(mfr)
        lay.addWidget(QLabel("<b>Render Kuyruğu</b>"))
        self.queue_list=QListWidget(); lay.addWidget(self.queue_list)
        qrow=QHBoxLayout(); addq=QPushButton("Çıktı Kuyruğuna Ekle…"); addq.clicked.connect(self.add_render_job); qrow.addWidget(addq)
        clear=QPushButton("Tamamlananları Temizle"); clear.clicked.connect(self.clear_done); qrow.addWidget(clear); lay.addLayout(qrow)
        lay.addWidget(QLabel("<b>Advanced NLE</b>"))
        self.advanced=AdvancedEditorState.from_dict(project.editor_data.get("advanced_nle",{}))
        self.proxy_check=QCheckBox("Proxy kullanımını etkinleştir"); self.proxy_check.setChecked(self.advanced.use_proxies); self.proxy_check.toggled.connect(self.toggle_proxies); lay.addWidget(self.proxy_check)
        arow=QHBoxLayout()
        for label, fn in (("Compound oluştur",self.add_compound),("Adjustment Layer",self.add_adjustment),("Multicam oluştur",self.add_multicam)):
            b=QPushButton(label); b.clicked.connect(fn); arow.addWidget(b)
        lay.addLayout(arow)
        self.advanced_info=QLabel(""); self.advanced_info.setWordWrap(True); lay.addWidget(self.advanced_info); self._refresh_advanced()
        close=QPushButton("Kapat"); close.clicked.connect(self.accept); lay.addWidget(close)
        self._refresh_lists()

    def _persist(self):
        self.project.editor_data["markers"]=self.markers.to_dict()
        self.project.editor_data["render_queue"]=self.queue.to_dict()
        self.project.editor_data["workspace"]=self.workspace.to_dict()
        self.project.editor_data["advanced_nle"]=self.advanced.to_dict()
        self.project.touch(); self.refresh()

    def _refresh_lists(self):
        self.marker_list.clear()
        for m in self.markers.markers: self.marker_list.addItem(f"{m.time:09.3f}  {m.name or 'Marker'}  {m.note}")
        self.queue_list.clear()
        for j in self.queue.jobs: self.queue_list.addItem(f"{j.state.value.upper():10}  {j.name}  → {j.output_path}")

    def toggle_proxies(self, checked):
        self.advanced.use_proxies=bool(checked); self._persist(); self._refresh_advanced()

    def _refresh_advanced(self):
        self.advanced_info.setText(f"Compound: {len(self.advanced.compounds)}  |  Adjustment: {len(self.advanced.adjustments)}  |  Proxy: {len(self.advanced.proxies.assets)}  |  Multicam: {len(self.advanced.multicam)}")

    def add_compound(self):
        name, ok=QInputDialog.getText(self,"Compound Clip","Ad:")
        if not ok or not name.strip(): return
        self.advanced.compounds.append(CompoundClip(name.strip(),0.0)); self._persist(); self._refresh_advanced()

    def add_adjustment(self):
        start=self.workspace.playhead; end=start+5.0
        self.advanced.adjustments.append(AdjustmentLayer("Adjustment Layer",start,end)); self._persist(); self._refresh_advanced()

    def add_multicam(self):
        name, ok=QInputDialog.getText(self,"Multicam","Sekans adı:")
        if not ok or not name.strip(): return
        m=MulticamSequence(name.strip()); m.add_angle(MulticamAngle("Camera 1","")); self.advanced.multicam.append(m); self._persist(); self._refresh_advanced()

    def set_edit_mode(self, mode):
        self.workspace.set_mode(mode); self._persist()

    def match_frame(self):
        hit=ProfessionalEditEngine(self.project.timeline).match_frame(self.workspace.playhead)
        if hit:
            QMessageBox.information(self,"Match Frame",f"Klip: {hit['clip_id']}\nKaynak zamanı: {hit['source_time']:.3f} s")
        else:
            QMessageBox.information(self,"Match Frame","Playhead altında klip bulunamadı.")

    def add_marker(self):
        m=self.markers.add(self.time.value(),f"Marker {len(self.markers.markers)+1}")
        self._persist(); self._refresh_lists()

    def remove_marker(self):
        i=self.marker_list.currentRow()
        if 0<=i<len(self.markers.markers):
            self.markers.markers.pop(i); self._persist(); self._refresh_lists()

    def goto_marker(self):
        i=self.marker_list.currentRow()
        if i>=0:
            t=self.markers.markers[i].time
            # TimelineView is intentionally not hard-coupled here; caller can reopen at this time.
            QMessageBox.information(self,"Marker",f"Marker zamanı: {t:.3f} s")

    def relink(self):
        folder=QFileDialog.getExistingDirectory(self,"Medya klasörü seç")
        if not folder: return
        results=MediaRelinker(self.project).scan([folder])
        matched=[r for r in results if r.new_path]
        if matched:
            self.history.push()
            for r in matched: MediaRelinker(self.project).apply(r)
            self._persist()
        QMessageBox.information(self,"Relink",f"{len(matched)} eksik medya eşleştirildi. {len(results)-len(matched)} öğe manuel inceleme gerektiriyor.")

    def add_render_job(self):
        path,_=QFileDialog.getSaveFileName(self,"Render çıktısı",str(Path.home()/ "video.mp4"),"Video (*.mp4 *.mkv *.mov)")
        if not path: return
        from app.pro.render_queue import RenderJob
        self.queue.add(RenderJob(path, name=Path(path).stem))
        self._persist(); self._refresh_lists()

    def clear_done(self):
        self.queue.jobs=[j for j in self.queue.jobs if j.state.value not in ("done","cancelled")]
        self._persist(); self._refresh_lists()
