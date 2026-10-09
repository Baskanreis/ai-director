"""Ana pencere sayfalari."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QHBoxLayout, QWidget, QPushButton

from app import __version__
from app.runtime import paths
from app.runtime.module_registry import MODULES, ModuleInfo
from app.runtime.system_check import run_checks

from .widgets import Badge, Card, row


def _muted(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Muted")
    return lbl


def _header(title: str, sub: str) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(2)
    t = QLabel(title)
    t.setObjectName("PageTitle")
    s = QLabel(sub)
    s.setObjectName("PageSub")
    s.setWordWrap(True)
    lay.addWidget(t)
    lay.addWidget(s)
    return w


class BasePage(QWidget):
    """Kaydirilabilir, basliklı sayfa iskeleti."""

    def __init__(self, title: str, sub: str) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        inner = QWidget()
        scroll.setWidget(inner)
        self.content = QVBoxLayout(inner)
        self.content.setContentsMargins(32, 28, 32, 28)
        self.content.setSpacing(18)
        self.content.addWidget(_header(title, sub))

    def finish(self) -> None:
        self.content.addStretch(1)


class DashboardPage(BasePage):
    def __init__(self) -> None:
        super().__init__(
            "AI Director",
            "Creator Operating System — video, Shorts, altyazi ve is akisi tek uygulamada.",
        )

        hero = Card()
        title = QLabel("Profesyonel video üretim merkezi")
        title.setStyleSheet("font-size: 21px; font-weight: 800; background: transparent;")
        desc = _muted("Kurgu, AI, altyazı, Shorts, render, proxy ve YouTube iş akışlarını tek projede yönetin.")
        desc.setWordWrap(True)
        hero.body.addWidget(title); hero.body.addWidget(desc)
        actions = QHBoxLayout()
        self.self_test_btn = QPushButton("Sistem Sağlık Testi")
        self.self_test_btn.clicked.connect(self._open_self_test)
        actions.addWidget(self.self_test_btn); actions.addStretch(1)
        hero.body.addLayout(actions)
        self.content.addWidget(hero)

        kpis = QHBoxLayout()
        for title_text, value, sub in [("Sürüm", f"v{__version__}", "stable runtime"), ("Modül", "10+", "aktif araç yüzeyleri"), ("Dağıtım", "Single Setup", "Program Files"), ("Runtime", "Self-Test", "kritik bağımlılık kontrolü")]:
            c = Card(); v = QLabel(value); v.setStyleSheet("font-size: 19px; font-weight: 800; background: transparent;"); t = QLabel(title_text); t.setObjectName("Muted"); st = QLabel(sub); st.setObjectName("Muted"); c.body.addWidget(t); c.body.addWidget(v); c.body.addWidget(st); kpis.addWidget(c)
        holder = QWidget(); holder.setLayout(kpis); self.content.addWidget(holder)

        checks = Card("Sistem Kontrolu")
        self._checks_card = checks
        loading = _muted("Kontroller arka planda çalıştırılıyor…")
        checks.body.addWidget(loading)
        self.content.addWidget(checks)
        # FFmpeg -version ve import/spec kontrolleri açılış frame'ini bloklamasın.
        QTimer.singleShot(0, self._load_checks)


        mods = Card("Moduller")
        for m in MODULES:
            if m.key in ("dashboard", "settings"):
                continue
            kind = "ok" if m.status == "hazir" else "info"
            mods.body.addWidget(row(QLabel(m.title), _muted(m.description), Badge(m.target_version, kind)))
        self.content.addWidget(mods)
        self.finish()

    def _open_self_test(self) -> None:
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTextEdit
        from PySide6.QtWidgets import QVBoxLayout
        from app.runtime.self_test import run_full_self_test
        dlg = QDialog(self); dlg.setWindowTitle("AI Director — Sistem Sağlık Testi"); dlg.resize(760, 520)
        lay = QVBoxLayout(dlg); out = QTextEdit(); out.setReadOnly(True); lay.addWidget(out)
        results = run_full_self_test(); ok = sum(r.ok for r in results)
        out.setPlainText("\n".join([f"Sonuç: {ok}/{len(results)}\n"] + [("✓" if r.ok else "✕") + f"  {r.name}: {r.detail}" for r in results]))
        box=QDialogButtonBox(QDialogButtonBox.Close); box.rejected.connect(dlg.reject); lay.addWidget(box); dlg.exec()

    def _load_checks(self) -> None:
        from .background import BackgroundTask, pool
        task = BackgroundTask(run_checks)
        task.signals.result.connect(self._apply_checks)
        task.signals.error.connect(lambda _e: None)
        pool().start(task)

    def _apply_checks(self, results) -> None:
        # İlk yükleme yazısını kaldır, sonuçları UI thread'inde çiz.
        while self._checks_card.body.count():
            item = self._checks_card.body.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for r in results:
            badge = Badge("OK", "ok") if r.ok else Badge("EKSIK", "bad" if r.required else "warn")
            self._checks_card.body.addWidget(row(QLabel(r.name), _muted(r.detail), badge))


class PlaceholderPage(BasePage):
    def __init__(self, module: ModuleInfo) -> None:
        super().__init__(module.title, module.description)
        card = Card("Yakinda")
        msg = _muted(
            f"Bu modul {module.target_version} surumunde eklenecek.\n"
            "Su an yalnizca yer tutucu sayfadir."
        )
        msg.setWordWrap(True)
        card.body.addWidget(msg)
        self.content.addWidget(card)


class SubtitlePage(BasePage):
    """AI Subtitle (v0.8): Whisper transkripsiyon aracini acan basit bir sayfa.

    Asil is akisi `SubtitleDialog`'da yapilir; bu sayfa yalnizca projeye
    (`set_project`) referans tutup diyalogu acar (Studio sayfasindaki
    'Altyazı…' butonuyla ayni islevi sagbar).
    """

    def __init__(self, project) -> None:
        super().__init__("AI Subtitle", "Whisper ile otomatik altyazi, SRT/VTT, videoya gomme.")
        self.project = project

        from PySide6.QtWidgets import QPushButton

        card = Card("Altyazı Aracı")
        info = _muted(
            "Timeline'daki bir klibin kaynak medyasını Whisper ile transkribe edin, "
            "SRT/VTT olarak dışa aktarın ya da videoya gömün. Türkçe öncelikli; "
            "İngilizce, Almanca ve Fransızca da desteklenir."
        )
        info.setWordWrap(True)
        card.body.addWidget(info)
        self.open_btn = QPushButton("Altyazı Aracını Aç")
        self.open_btn.clicked.connect(self._open_dialog)
        card.body.addWidget(self.open_btn)
        self.content.addWidget(card)
        self.finish()

    def set_project(self, project) -> None:
        self.project = project

    def _open_dialog(self) -> None:
        from .subtitle_dialog import SubtitleDialog

        if not self.project.timeline.all_clips():
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.information(
                self, "Timeline boş",
                "Önce Studio sayfasında timeline'a bir klip ekleyin.",
            )
            return
        media_paths = {m.id: m.path for m in self.project.media}
        dialog = SubtitleDialog(self.project.timeline, media_paths, self)
        dialog.exec()
        self.finish()


class AIEditPage(BasePage):
    """AI Video Edit (v0.8): sessizlik/tekrar/dolgu kelime analizi + kabul/ret araci.

    Asil is akisi `AIEditorDialog`'da yapilir; bu sayfa yalnizca projeye referans
    tutup diyalogu acar (`SubtitlePage` ile ayni desen).
    """

    def __init__(self, project) -> None:
        super().__init__(
            "AI Video Edit",
            "Sessizlik, uzun duraklama, tekrar ve dolgu kelimeleri bulur; "
            "her öneriyi kabul/ret edip timeline'a tek tıkla uygulayın.",
        )
        self.project = project

        from PySide6.QtWidgets import QPushButton

        card = Card("AI Düzenleme Aracı")
        info = _muted(
            "Timeline'daki bir klibi (opsiyonel olarak önce Whisper ile transkribe ederek) "
            "analiz edin: sessizlik, uzun duraklama, tekrar, dolgu kelime ve sahne değişimi "
            "tespit edilir; önemli kelimeler vurgu için önerilir. Her öneriyi ayrı ayrı kabul "
            "veya reddedebilir, kabul ettiklerinizi tek tıkla timeline'dan kesebilirsiniz."
        )
        info.setWordWrap(True)
        card.body.addWidget(info)
        self.open_btn = QPushButton("AI Video Edit Aracını Aç")
        self.open_btn.clicked.connect(self._open_dialog)
        card.body.addWidget(self.open_btn)
        self.content.addWidget(card)
        self.finish()

    def set_project(self, project) -> None:
        self.project = project

    def _open_dialog(self) -> None:
        from .ai_editor_dialog import AIEditorDialog

        if not self.project.timeline.all_clips():
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.information(
                self, "Timeline boş",
                "Önce Studio sayfasında timeline'a bir klip ekleyin.",
            )
            return
        media_paths = {m.id: m.path for m in self.project.media}
        dialog = AIEditorDialog(self.project.timeline, media_paths, self)
        dialog.exec()
        self.finish()


class AIAgentPage(BasePage):
    """Natural-language professional editor command surface."""
    def __init__(self, project) -> None:
        super().__init__("AI Editor", "Doğal dille kurgu, efekt, ses, yazı, geçiş ve Shorts kararlarını profesyonel editör gibi planla ve uygula.")
        self.project = project
        from PySide6.QtWidgets import QLineEdit, QPushButton, QTextEdit, QHBoxLayout
        from app.ai.professional_agent import plan as make_plan, apply_plan
        self._make_plan = make_plan
        self._apply_plan = apply_plan
        card = Card("Professional AI Editor")
        info = _muted("Örnek: 'Sinematik yap, sesi temizle, konuşma anlarında hafif zoom kullan ve altyazıyı kalın yap.' AI önce geri alınabilir bir plan üretir; sonra uygular.")
        info.setWordWrap(True); card.body.addWidget(info)
        roww = QHBoxLayout()
        self.command = QLineEdit(); self.command.setPlaceholderText("Editör komutunu yaz…")
        self.plan_btn = QPushButton("Plan Oluştur"); self.plan_btn.clicked.connect(self._preview)
        roww.addWidget(self.command, 1); roww.addWidget(self.plan_btn); card.body.addLayout(roww)
        self.output = QTextEdit(); self.output.setReadOnly(True); self.output.setMinimumHeight(220); card.body.addWidget(self.output)
        self.apply_btn = QPushButton("Planı Timeline'a Uygula"); self.apply_btn.setEnabled(False); self.apply_btn.clicked.connect(self._apply)
        card.body.addWidget(self.apply_btn)
        self.content.addWidget(card); self._plan = None; self.finish()

    def set_project(self, project) -> None:
        self.project = project

    def _preview(self) -> None:
        self._plan = self._make_plan(self.command.text())
        lines=[f"Komut: {self._plan.command}", "", "AI edit planı:"]
        for i,a in enumerate(self._plan.actions,1):
            lines.append(f"{i}. {a.kind} — güven {a.confidence:.0%} — {a.reason}")
        if self._plan.warnings: lines += ["", "Uyarılar:", *self._plan.warnings]
        self.output.setPlainText("\n".join(lines)); self.apply_btn.setEnabled(bool(self._plan.actions and self.project.timeline.all_clips()))

    def _apply(self) -> None:
        if not self._plan: return
        clip_id = self.project.timeline.all_clips()[0].id if self.project.timeline.all_clips() else None
        self._apply_plan(self.project.timeline, self._plan, clip_id)
        self.project.touch(); self.output.append("\n✓ Plan uygulandı. Timeline'ı kontrol edip gerekirse geri alabilirsiniz.")


class PipelinePage(BasePage):
    """AI Pipeline (v1.4): Import -> ... -> Render zincirini acan sayfa.

    Asil is akisi `PipelineDialog`da yapilir (`SubtitlePage`/`AIEditPage` ile
    ayni desen): bu sayfa yalnizca projeye referans tutup diyalogu acar.
    """

    def __init__(self, project) -> None:
        super().__init__(
            "AI Pipeline",
            "Import → Analysis → Transcription → Scene Detection → Edit Analysis → "
            "Camera → Effects → Subtitle → Render — tek diyalogda, Job Queue ile yürütülür.",
        )
        self.project = project

        from PySide6.QtWidgets import QPushButton

        card = Card("Pipeline Aracı")
        info = _muted(
            "Timeline'daki bir klibi tek seferde uçtan uca işleyin: teknik analiz, "
            "Whisper transkripsiyon, sahne algılama, kurgu önerileri, otomatik kamera "
            "hareketi (Keyframe Engine), renk ön ayarı ve altyazı üretimi; isterseniz "
            "sonunda projeyi doğrudan render edin. Her aşama ayrı bir iş (job) olarak "
            "sırayla kuyruğa alınır ve ilerlemesi canlı gösterilir."
        )
        info.setWordWrap(True)
        card.body.addWidget(info)
        self.open_btn = QPushButton("AI Pipeline Aracını Aç")
        self.open_btn.clicked.connect(self._open_dialog)
        card.body.addWidget(self.open_btn)
        self.content.addWidget(card)
        self.finish()

    def set_project(self, project) -> None:
        self.project = project

    def _open_dialog(self) -> None:
        from .pipeline_dialog import PipelineDialog

        if not self.project.timeline.all_clips():
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.information(
                self, "Timeline boş",
                "Önce Studio sayfasında timeline'a bir klip ekleyin.",
            )
            return
        media_paths = {m.id: m.path for m in self.project.media}
        dialog = PipelineDialog(self.project.timeline, media_paths, self)
        dialog.exec()
        self.finish()


class KeyframeInfoPage(BasePage):
    """Keyframe Engine (v1.4): tanitim sayfasi.

    Egri editoru, bir klip BAGLAMINDA calistigi icin (Studio'daki secili
    klip uzerinde) ayri bir sayfa yerine Studio'nun 'Keyframe'ler…' butonuyla
    acilir; bu sayfa yalnizca kisa bir tanitim + Studio'ya kisayol sunar.
    """

    def __init__(self, navigate_to_studio) -> None:
        super().__init__(
            "Keyframe Engine",
            "Position / Scale / Rotation / Opacity / Crop / Volume / Effects için "
            "Bezier/easing destekli profesyonel animasyon editörü.",
        )
        from PySide6.QtWidgets import QPushButton

        card = Card("Nasıl kullanılır")
        info = _muted(
            "Keyframe Engine, bir klip üzerinde çalıştığı için Studio sayfasından "
            "açılır: timeline'da bir klip seçip araç çubuğundaki \"Keyframe'ler…\" "
            "düğmesine tıklayın. Açılan grafik editöründe eğri üzerine tıklayarak "
            "keyframe ekleyebilir, sürükleyerek taşıyabilir, sağ tıklayarak "
            "Doğrusal/Basamak/Yumuşak Giriş-Çıkış/Bezier yumuşatma türlerinden "
            "birini seçebilirsiniz."
        )
        info.setWordWrap(True)
        card.body.addWidget(info)
        btn = QPushButton("Studio'ya Git")
        btn.clicked.connect(navigate_to_studio)
        card.body.addWidget(btn)
        self.content.addWidget(card)
        self.finish()


class SettingsPage(BasePage):
    def __init__(self, config) -> None:
        super().__init__("Ayarlar", "Uygulama tercihleri (v0.1'de salt okunur).")
        card = Card("Mevcut Ayarlar")
        provider_btn = QPushButton("AI Provider Studio…")
        provider_btn.clicked.connect(self._open_provider_studio)
        card.body.addWidget(provider_btn)
        for k, v in [
            ("Dil", config.language),
            ("Tema", config.theme),
            ("Ayar dosyasi", str(paths.config_file())),
            ("Log klasoru", str(paths.log_dir())),
        ]:
            val = _muted(v)
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            card.body.addWidget(row(QLabel(k), val))
        self.content.addWidget(card)
        self.finish()

    def _open_provider_studio(self) -> None:
        from .provider_dialog import ProviderStudioDialog
        ProviderStudioDialog(self).exec()
