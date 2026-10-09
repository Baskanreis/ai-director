from __future__ import annotations
from datetime import date, timedelta
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QSpinBox,QPushButton,QPlainTextEdit,QMessageBox,QFileDialog,QComboBox,QCheckBox,QTableWidget,QTableWidgetItem,QProgressBar,QHeaderView
from .widgets import Card
from app.youtube.health import check_youtube_health

class YouTubeIntelligenceDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent); self.setWindowTitle("YouTube Intelligence"); self.resize(760,560)
        root=QVBoxLayout(self)
        card=Card("Kanal DNA + Analytics")
        root.addWidget(card)
        form=QHBoxLayout(); self.channel=QLineEdit(); self.channel.setPlaceholderText("UCxxxxxxxxxxxxxxxxxxxxxxxx")
        self.sample=QSpinBox(); self.sample.setRange(5,200); self.sample.setValue(50)
        form.addWidget(QLabel("Kanal ID")); form.addWidget(self.channel,1); form.addWidget(QLabel("Örnek")); form.addWidget(self.sample)
        card.body.addLayout(form)
        row=QHBoxLayout(); self.public_btn=QPushButton("Kanalı Analiz Et"); self.oauth_btn=QPushButton("YouTube Analytics Bağla")
        self.public_btn.clicked.connect(self.analyze); self.oauth_btn.clicked.connect(self.connect)
        row.addWidget(self.public_btn); row.addWidget(self.oauth_btn); card.body.addLayout(row)
        creator=QHBoxLayout(); self.video_url=QLineEdit(); self.video_url.setPlaceholderText("YouTube video / Shorts / kanal / @handle URL'si")
        self.creator_btn=QPushButton("Creator Paketi Oluştur"); self.creator_btn.clicked.connect(self.creator_package)
        creator.addWidget(self.video_url,1); creator.addWidget(self.creator_btn); card.body.addLayout(creator)
        self.status=QLabel("Kanal ID girerek herkese açık kanal DNA'sını çıkarabilirsiniz. Analytics bağlantısı yalnızca kendi hesabınız için OAuth kullanır."); self.status.setWordWrap(True); card.body.addWidget(self.status)
        health = check_youtube_health()
        self.health_label = QLabel()
        self.health_label.setWordWrap(True)
        self.health_label.setText("YouTube durumu: " + ("Hazır" if health.critical_modules_ok else "Modül hatası") + "\n" + "\n".join(health.messages))
        card.body.addWidget(self.health_label)
        self.public_btn.setEnabled(health.data_api_configured and health.critical_modules_ok)
        self.oauth_btn.setEnabled(health.oauth_configured and health.google_packages_available and health.critical_modules_ok)
        publish=Card("YouTube Auto-Publish")
        root.addWidget(publish)
        prow=QHBoxLayout(); self.video_file=QLineEdit(); self.video_file.setPlaceholderText("Render edilmiş video dosyası"); browse=QPushButton("Video Seç"); browse.clicked.connect(lambda: self.video_file.setText(QFileDialog.getOpenFileName(self,"Video Seç",filter="Video (*.mp4 *.mov *.mkv);;Tüm Dosyalar (*)")[0])); prow.addWidget(self.video_file,1); prow.addWidget(browse); publish.body.addLayout(prow)
        prow2=QHBoxLayout(); self.publish_title=QLineEdit(); self.publish_title.setPlaceholderText("YouTube başlığı"); self.privacy=QComboBox(); self.privacy.addItems(["private","unlisted","public"]); self.publish_btn=QPushButton("YouTube'a Yükle"); self.publish_btn.clicked.connect(self.publish_video); prow2.addWidget(self.publish_title,1); prow2.addWidget(self.privacy); prow2.addWidget(self.publish_btn); publish.body.addLayout(prow2)
        queue=Card("YouTube Production Manager")
        root.addWidget(queue)
        self.queue_manager = None
        try:
            from app.youtube.production_manager import YouTubeProductionManager
            self.queue_manager = YouTubeProductionManager()
            qrow=QHBoxLayout()
            self.queue_kind=QComboBox(); self.queue_kind.addItems(["long_video","short","thumbnail"])
            self.queue_name=QLineEdit(); self.queue_name.setPlaceholderText("İş adı")
            self.queue_output=QLineEdit(); self.queue_output.setPlaceholderText("Çıktı dosyası")
            addq=QPushButton("Kuyruğa Ekle"); addq.clicked.connect(self.add_queue_job)
            qrow.addWidget(self.queue_kind); qrow.addWidget(self.queue_name,1); qrow.addWidget(self.queue_output,1); qrow.addWidget(addq)
            queue.body.addLayout(qrow)
            self.queue_table=QTableWidget(0,4); self.queue_table.setHorizontalHeaderLabels(["İş","Tür","Durum","İlerleme"]); self.queue_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.queue_table.setEditTriggers(QTableWidget.NoEditTriggers)
            queue.body.addWidget(self.queue_table)
            qactions=QHBoxLayout(); self.cancel_queue_btn=QPushButton("Seçili İşi İptal Et"); self.cancel_queue_btn.clicked.connect(self.cancel_queue_job); self.refresh_queue_btn=QPushButton("Yenile"); self.refresh_queue_btn.clicked.connect(self.refresh_queue)
            qactions.addWidget(self.cancel_queue_btn); qactions.addWidget(self.refresh_queue_btn); qactions.addStretch(1); queue.body.addLayout(qactions)
            self.refresh_queue()
        except Exception as exc:
            self.queue_manager = None
            self.status.setText(f"YouTube Production Manager yüklenemedi: {exc}")
        self.output=QPlainTextEdit(); self.output.setReadOnly(True); root.addWidget(self.output,1)

    def add_queue_job(self):
        if not self.queue_manager: return
        name=self.queue_name.text().strip() or "Yeni İş"; path=self.queue_output.text().strip()
        if not path: QMessageBox.warning(self,"Production Queue","Çıktı dosyası girin."); return
        self.queue_manager.add_job(self.queue_kind.currentText(),name,path); self.refresh_queue(); self.status.setText("İş kuyruğa eklendi.")

    def refresh_queue(self):
        if not self.queue_manager: return
        jobs=self.queue_manager.queue.jobs; self.queue_table.setRowCount(len(jobs))
        for row,j in enumerate(jobs):
            self.queue_table.setItem(row,0,QTableWidgetItem(j.name)); self.queue_table.setItem(row,1,QTableWidgetItem(j.kind)); self.queue_table.setItem(row,2,QTableWidgetItem(j.state.value)); self.queue_table.setItem(row,3,QTableWidgetItem(f"{j.progress*100:.0f}%"))

    def cancel_queue_job(self):
        if not self.queue_manager: return
        row=self.queue_table.currentRow()
        if row < 0 or row >= len(self.queue_manager.queue.jobs): return
        self.queue_manager.cancel(self.queue_manager.queue.jobs[row].id); self.refresh_queue()

    def analyze(self):
        cid=self.channel.text().strip()
        if not cid: QMessageBox.warning(self,"Eksik bilgi","Kanal ID girin."); return
        self.public_btn.setEnabled(False); self.status.setText("YouTube kanalı analiz ediliyor…")
        from .background import BackgroundTask,pool
        task=BackgroundTask(lambda: __import__('app.youtube.manager',fromlist=['YouTubeIntelligenceManager']).YouTubeIntelligenceManager().analyze_public_channel(cid,self.sample.value()))
        task.signals.result.connect(self._result); task.signals.error.connect(self._error); pool().start(task)
    def _result(self,dna):
        self.public_btn.setEnabled(True); self.status.setText(f"Analiz tamamlandı • güven: {dna.confidence:.0%}"); self.output.setPlainText(json.dumps(dna.to_dict(),ensure_ascii=False,indent=2))
    def _error(self,exc): self.public_btn.setEnabled(True); self.status.setText("Analiz başarısız."); QMessageBox.critical(self,"YouTube Intelligence",str(exc))
    def creator_package(self):
        value=self.video_url.text().strip()
        if not value: QMessageBox.warning(self,"Eksik bilgi","YouTube URL'si girin."); return
        try:
            from app.youtube.creator import parse_youtube_url, build_creator_package
            ref=parse_youtube_url(value)
            if ref.kind != "video":
                self.output.setPlainText(json.dumps({"reference":ref.__dict__,"message":"Bu kaynak kanal/handle referansı. Kanal DNA analizini kullanabilirsiniz."},ensure_ascii=False,indent=2)); return
            # Metadata is intentionally not scraped; the package is safe to fill from imported project metadata.
            package=build_creator_package(f"YouTube Video {ref.identifier}")
            self.output.setPlainText(json.dumps({"reference":ref.__dict__,"creator_package":package.to_dict()},ensure_ascii=False,indent=2))
            self.status.setText(f"Creator paketi hazır • SEO {package.seo.score:.0f}/100")
        except Exception as exc:
            QMessageBox.critical(self,"YouTube Creator",str(exc))

    def publish_video(self):
        path=self.video_file.text().strip(); title=self.publish_title.text().strip()
        if not path or not title:
            QMessageBox.warning(self,"Eksik bilgi","Video dosyası ve başlık gerekli."); return
        try:
            from app.youtube.publish import PublishPlan
            plan=PublishPlan(video_path=path,title=title,privacy_status=self.privacy.currentText())
            from app.youtube.manager import YouTubeIntelligenceManager
            qc=YouTubeIntelligenceManager().validate_publish_plan(plan)
            if not qc.ok:
                QMessageBox.warning(self,"Upload QC","\n".join(qc.errors)); return
            self.publish_btn.setEnabled(False); self.status.setText("YouTube'a yükleniyor…")
            from .background import BackgroundTask,pool
            task=BackgroundTask(lambda: YouTubeIntelligenceManager().upload(plan))
            task.signals.result.connect(lambda out: (self.publish_btn.setEnabled(True),self.status.setText("Yayın yüklendi."),self.output.setPlainText(json.dumps(out,ensure_ascii=False,indent=2))))
            task.signals.error.connect(lambda exc: (self.publish_btn.setEnabled(True),self.status.setText("Upload başarısız."),QMessageBox.critical(self,"YouTube Upload",str(exc))))
            pool().start(task)
        except Exception as exc:
            self.publish_btn.setEnabled(True); QMessageBox.critical(self,"YouTube Upload",str(exc))

    def connect(self):
        self.oauth_btn.setEnabled(False); self.status.setText("Google izin ekranı açılıyor…")
        from .background import BackgroundTask,pool
        task=BackgroundTask(lambda: __import__('app.youtube.manager',fromlist=['YouTubeIntelligenceManager']).YouTubeIntelligenceManager().connect_analytics())
        task.signals.result.connect(lambda ok: (self.oauth_btn.setEnabled(True),self.status.setText("YouTube Analytics hesabı bağlandı." if ok else "Bağlantı kurulamadı.")))
        task.signals.error.connect(lambda exc: (self.oauth_btn.setEnabled(True),self.status.setText("Analytics bağlantısı başarısız."),QMessageBox.critical(self,"YouTube Analytics",str(exc))))
        pool().start(task)
