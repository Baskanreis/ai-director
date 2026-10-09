"""AI Director ana penceresi."""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app import __version__
from app.project.autosave import (
    AutosaveManager,
    discard_session,
    find_recoverable_sessions,
    load_recovered_project,
    prune_stale_sessions,
)
from app.project.project import PROJECT_EXT, Project, ProjectError
from app.project.versioning import VersionManager
from app.runtime.config import Config
from app.runtime.module_registry import MODULES

from .recovery_dialog import RecoveryDialog
from .version_dialog import VersionDialog

log = logging.getLogger(__name__)

AUTOSAVE_INTERVAL_MS = 2 * 60 * 1000  # 2 dakika; yalnızca proje "dirty" iken gerçekten yazar


class MainWindow(QMainWindow):
    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.project = Project()

        self.resize(config.window_width, config.window_height)
        self.setMinimumSize(960, 600)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        self._nav_buttons: dict[str, QPushButton] = {}
        root.addWidget(self._build_sidebar())

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0); right.setSpacing(0)
        top = QWidget(); top.setObjectName("TopBar")
        top_lay = QHBoxLayout(top); top_lay.setContentsMargins(18, 8, 18, 8)
        self.top_project = QLabel("Yeni Proje"); self.top_project.setObjectName("TopProject")
        self.top_meta = QLabel(f"AI Director v{__version__}  •  Hazır"); self.top_meta.setObjectName("TopMeta")
        top_lay.addWidget(self.top_project); top_lay.addSpacing(14); top_lay.addWidget(self.top_meta); top_lay.addStretch(1)
        health_btn = QPushButton("● Sistem Sağlığı"); health_btn.clicked.connect(self.open_self_test); top_lay.addWidget(health_btn)
        right.addWidget(top)
        self.stack = QStackedWidget()
        right.addWidget(self.stack, 1)
        root.addLayout(right, 1)

        # Ağır editör sayfalarını başlangıçta oluşturma. Studio, Whisper/AI ve
        # pipeline bileşenleri Qt nesneleri + medya altyapısı kurduğu için eski
        # yaklaşım açılış RAM'ini ve ilk açılış süresini gereksiz yükseltiyordu.
        self.studio_page = None
        self.subtitle_page = None
        self.ai_edit_page = None
        self.pipeline_page = None
        self._page_index: dict[str, int] = {}
        self._pages: dict[str, QWidget] = {}
        self._build_lazy_page_registry()

        self._build_menu()
        self.statusBar().showMessage(f"Hazır  •  v{__version__}")
        start = config.last_page if config.last_page in self._page_index else "dashboard"
        # Pencere önce çizilsin; ağır sayfa ilk event-loop turunda yüklensin.
        # Böylece EXE açıldığında kullanıcı siyah/beyaz "dondu" hissi yaşamaz.
        self._show_loading_page()
        QTimer.singleShot(0, lambda: self.navigate(start))
        self._update_title()

        # ---- Autosave / Crash Recovery ----
        prune_stale_sessions()  # eski/artik gecersiz kayitlari sessizce temizle
        self.autosave = AutosaveManager(self.project)
        self.autosave.start_session()
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(AUTOSAVE_INTERVAL_MS)
        self._autosave_timer.timeout.connect(self._run_autosave)
        self._autosave_timer.start()
        # Kurtarma diyaloğu, pencere tamamen görünür olduktan SONRA gösterilsin
        # diye olay döngüsüne bırakılır (modal diyaloğun ana pencereden önce
        # açılması bazı platformlarda tuhaf görünebilir).
        QTimer.singleShot(0, self._check_crash_recovery)

    def _show_loading_page(self) -> None:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(40, 40, 40, 40)
        label = QLabel("AI Director hazırlanıyor…")
        label.setAlignment(Qt.AlignCenter)
        label.setObjectName("Muted")
        lay.addStretch(1); lay.addWidget(label); lay.addStretch(1)
        self._loading_page = page
        self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)

    # ---------------- lazy page loading ----------------
    def _build_lazy_page_registry(self) -> None:
        """Sayfaları yalnızca ilk kez açıldıklarında oluştur.

        Bu, özellikle Studio/AI Subtitle/Pipeline gibi ağır sayfaların
        uygulama açılışında Qt multimedia, timeline ve AI bağımlılıklarını
        aynı anda kurmasını engeller.
        """
        for m in MODULES:
            self._page_index[m.key] = -1

    def _ensure_page(self, key: str) -> QWidget:
        page = self._pages.get(key)
        if page is not None:
            return page

        from .pages import (
            AIEditPage, AIAgentPage, DashboardPage, KeyframeInfoPage, PipelinePage,
            PlaceholderPage, SettingsPage, SubtitlePage,
        )

        if key == "dashboard":
            page = DashboardPage()
        elif key == "settings":
            page = SettingsPage(self.config)
        elif key == "studio":
            from .studio_page import StudioPage
            page = self.studio_page = StudioPage(self.project)
        elif key == "subtitle":
            page = self.subtitle_page = SubtitlePage(self.project)
        elif key == "video":
            page = self.ai_edit_page = AIEditPage(self.project)
        elif key == "assistant":
            page = AIAgentPage(self.project)
        elif key == "pipeline":
            page = self.pipeline_page = PipelinePage(self.project)
        elif key in ("shorts", "reframe"):
            # These are real production features, not placeholder roadmap pages.
            # Keep navigation lightweight and open the appropriate production dialog.
            from .pages import DashboardPage
            page = DashboardPage()
        elif key == "keyframe":
            page = KeyframeInfoPage(lambda: self.navigate("studio"))
        else:
            page = PlaceholderPage(next(m for m in MODULES if m.key == key))

        self._pages[key] = page
        self._page_index[key] = self.stack.addWidget(page)
        return page

    # ---------------- arayuz kurulumu ----------------
    def _build_sidebar(self) -> QWidget:
        side = QWidget()
        side.setObjectName("Sidebar")
        side.setFixedWidth(230)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(0, 0, 0, 12)
        lay.setSpacing(0)

        section = QLabel("WORKSPACE"); section.setObjectName("NavSection"); lay.addWidget(section)
        logo = QLabel("AI Director")
        logo.setObjectName("Logo")
        sub = QLabel("Creator Operating System")
        sub.setObjectName("LogoSub")
        lay.addWidget(logo)
        lay.addWidget(sub)

        for m in MODULES:
            if m.key != "settings":
                lay.addWidget(self._nav_button(m.key, m.title))
        lay.addStretch(1)
        lay.addWidget(self._nav_button("settings", "Ayarlar"))
        return side

    def _nav_button(self, key: str, title: str) -> QPushButton:
        btn = QPushButton(title)
        btn.setObjectName("NavButton")
        btn.setCheckable(True)
        btn.clicked.connect(lambda _=False, k=key: self.navigate(k))
        self._nav_group.addButton(btn)
        self._nav_buttons[key] = btn
        return btn

    def _build_menu(self) -> None:
        menu = self.menuBar().addMenu("&Dosya")

        def act(text: str, shortcut: str, slot, target_menu=menu) -> QAction:
            a = QAction(text, self)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            a.triggered.connect(slot)
            target_menu.addAction(a)
            return a

        act("Yeni Proje", "Ctrl+N", self.new_project)
        act("Proje Aç…", "Ctrl+O", self.open_project_dialog)
        act("Kaydet", "Ctrl+S", self.save_project)
        act("Farklı Kaydet…", "Ctrl+Shift+S", self.save_project_as)

        self.recent_menu = menu.addMenu("Son Projeler")
        self._rebuild_recent_menu()

        menu.addSeparator()
        act("Çıkış", "Ctrl+Q", self.close)

        youtube_menu = self.menuBar().addMenu("&YouTube")
        yt_action = QAction("Channel Intelligence…", self)
        yt_action.triggered.connect(self.open_youtube_intelligence)
        youtube_menu.addAction(yt_action)
        yt_conn = QAction("Connection Center…", self)
        yt_conn.triggered.connect(self.open_youtube_connection)
        youtube_menu.addAction(yt_conn)

        edit_menu = self.menuBar().addMenu("&Düzen")
        act("Geri Al", "Ctrl+Z", lambda: self.studio_page and self.studio_page._undo(), edit_menu)
        act("İleri Al", "Ctrl+Y", lambda: self.studio_page and self.studio_page._redo(), edit_menu)
        edit_menu.addSeparator()
        act("Sürüm Geçmişi…", "Ctrl+Alt+V", self.open_version_history, edit_menu)

        tools_menu = self.menuBar().addMenu("&Araçlar")
        act("Sistem Sağlık Testi…", "Ctrl+Shift+H", self.open_self_test, tools_menu)

    def _launch_feature_dialog(self, dialog_cls) -> None:
        try:
            dlg = dialog_cls(self.project, self)
            dlg.exec()
        except Exception as exc:
            log.exception("Feature dialog failed")
            QMessageBox.critical(self, "AI Director", f"Özellik açılamadı:\n{exc}")

    def open_self_test(self) -> None:
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTextEdit, QVBoxLayout
        from app.runtime.self_test import run_full_self_test
        dlg = QDialog(self)
        dlg.setWindowTitle("AI Director — Sistem Sağlık Testi")
        dlg.resize(760, 520)
        lay = QVBoxLayout(dlg)
        out = QTextEdit(); out.setReadOnly(True); lay.addWidget(out)
        results = run_full_self_test()
        ok = sum(r.ok for r in results)
        lines = [f"Sonuç: {ok}/{len(results)} kontrol başarılı", ""]
        for r in results:
            lines.append(("✓" if r.ok else "✕") + f"  {r.name}: {r.detail}")
        out.setPlainText("\n".join(lines))
        box = QDialogButtonBox(QDialogButtonBox.Close); box.rejected.connect(dlg.reject); box.accepted.connect(dlg.accept); lay.addWidget(box)
        dlg.exec()

    def open_youtube_intelligence(self) -> None:
        from .youtube_intelligence_dialog import YouTubeIntelligenceDialog
        dlg = YouTubeIntelligenceDialog(self)
        dlg.exec()

    def open_youtube_connection(self) -> None:
        from .youtube_connection_dialog import YouTubeConnectionDialog
        YouTubeConnectionDialog(self).exec()

    def _rebuild_recent_menu(self) -> None:
        self.recent_menu.clear()
        if not self.config.recent_projects:
            empty = QAction("(boş)", self)
            empty.setEnabled(False)
            self.recent_menu.addAction(empty)
            return
        for path in self.config.recent_projects:
            a = QAction(path, self)
            a.triggered.connect(lambda _=False, p=path: self._open_project(p))
            self.recent_menu.addAction(a)

    def navigate(self, key: str) -> None:
        try:
            page = self._ensure_page(key)
            if key in ("shorts", "reframe"):
                self.stack.setCurrentWidget(page)
                btn = self._nav_buttons.get(key)
                if btn: btn.setChecked(True)
                if key == "shorts":
                    from .shorts_director_dialog import ShortsDirectorDialog
                    QTimer.singleShot(0, lambda: self._launch_feature_dialog(ShortsDirectorDialog))
                else:
                    from .reframe_dialog import SmartReframeDialog
                    QTimer.singleShot(0, lambda: self._launch_feature_dialog(SmartReframeDialog))
                return
        except Exception as exc:
            log.exception("Sayfa yüklenemedi: %s", key)
            QMessageBox.critical(
                self, "Özellik yüklenemedi",
                f"{key} özelliği yüklenemedi.\n\n{type(exc).__name__}: {exc}\n\n"
                "Uygulama kapanmadı. Araçlar → Sistem Sağlık Testi ile kurulumu kontrol edebilirsiniz."
            )
            return
        self.stack.setCurrentWidget(page)
        self._nav_buttons[key].setChecked(True)
        self.config.last_page = key

    def _update_title(self) -> None:
        star = " •" if self.project.dirty else ""
        self.setWindowTitle(f"AI Director {__version__} — {self.project.name}{star}")
        if hasattr(self, "top_project"):
            self.top_project.setText(self.project.name)
            self.top_meta.setText(f"v{__version__}  •  {'Değişiklikler var' if self.project.dirty else 'Hazır'}")

    # ---------------- proje islemleri ----------------
    def _swap_project(self, project: Project) -> None:
        self.project = project
        if self.studio_page:
            self.studio_page.set_project(project)
        if self.subtitle_page:
            self.subtitle_page.set_project(project)
        if self.ai_edit_page:
            self.ai_edit_page.set_project(project)
        if self.pipeline_page:
            self.pipeline_page.set_project(project)
        if hasattr(self, "autosave"):
            self.autosave.set_project(project)
        self._update_title()

    # ---------------- sürüm geçmişi (versioning) ----------------
    def open_version_history(self) -> None:
        manager = VersionManager(self.project)
        dialog = VersionDialog(manager, self)
        if dialog.exec() and dialog.restored_project is not None:
            self._swap_project(dialog.restored_project)
            self.navigate("studio")
            self.statusBar().showMessage("Sürüm geri yüklendi — unutmadan Kaydet'e basın.", 5000)

    # ---------------- autosave / crash recovery ----------------
    def _run_autosave(self) -> None:
        if self.autosave.tick():
            log.debug("Otomatik kayıt yazıldı: %s", self.autosave.autosave_path)
            self.statusBar().showMessage("Otomatik kaydedildi (kurtarma kopyası)", 2000)

    def _check_crash_recovery(self) -> None:
        sessions = [s for s in find_recoverable_sessions() if s.session_id != self.project.session_id]
        if not sessions:
            return
        dialog = RecoveryDialog(sessions, self)
        if not dialog.exec():
            return  # Vazgeç: oturumlar bir sonraki açılışta tekrar sorulur
        for session_id in dialog.to_discard:
            discard_session(session_id)
        if not dialog.to_recover:
            return
        # Birden fazla kurtarılabilir oturum seçilirse: ilkini mevcut pencerede
        # aç, kalanları (varsa) bilgilendirme amaçlı durum çubuğunda belirt.
        first, *rest = dialog.to_recover
        try:
            recovered = load_recovered_project(first)
        except ProjectError as exc:
            QMessageBox.critical(self, "Kurtarılamadı", str(exc))
            return
        self._swap_project(recovered)
        self.navigate("studio")
        msg = f'"{recovered.name}" kurtarıldı — unutmadan Kaydet\'e basın.'
        if rest:
            msg += f" ({len(rest)} oturum daha kurtarılabilir listede kaldı.)"
        self.statusBar().showMessage(msg, 8000)

    def _confirm_discard_if_dirty(self) -> bool:
        if not self.project.dirty:
            return True
        choice = QMessageBox.question(
            self,
            "Kaydedilmemiş değişiklikler",
            f'"{self.project.name}" içinde kaydedilmemiş değişiklikler var. Kaydetmek ister misiniz?',
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if choice == QMessageBox.Cancel:
            return False
        if choice == QMessageBox.Save:
            return self.save_project()
        return True

    def new_project(self) -> None:
        if not self._confirm_discard_if_dirty():
            return
        self._swap_project(Project())
        self.navigate("studio")

    def open_project_dialog(self) -> None:
        if not self._confirm_discard_if_dirty():
            return
        start = self.config.last_dir or ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Proje Aç", start, f"AI Director Projesi (*{PROJECT_EXT})"
        )
        if path:
            self._open_project(path)

    def _open_project(self, path: str) -> None:
        try:
            project = Project.load(path)
        except ProjectError as exc:
            QMessageBox.critical(self, "Proje açılamadı", str(exc))
            return
        self._swap_project(project)
        self.config.last_dir = str(Path(path).parent)
        self.config.add_recent(str(project.path))
        self._rebuild_recent_menu()
        missing = project.missing_media()
        if missing:
            names = "\n".join(f"• {m.path}" for m in missing[:6])
            QMessageBox.warning(
                self, "Eksik medya",
                f"{len(missing)} medya dosyası bulunamadı:\n{names}",
            )
        self.navigate("studio")

    def save_project(self) -> bool:
        if self.project.path is None:
            return self.save_project_as()
        try:
            self.project.save()
        except ProjectError as exc:
            QMessageBox.critical(self, "Kaydedilemedi", str(exc))
            return False
        self._after_save()
        return True

    def save_project_as(self) -> bool:
        start = str(Path(self.config.last_dir or Path.home()) / self.project.name)
        path, _ = QFileDialog.getSaveFileName(
            self, "Projeyi Farklı Kaydet", start, f"AI Director Projesi (*{PROJECT_EXT})"
        )
        if not path:
            return False
        was_unsaved = self.project.path is None
        try:
            self.project.save(path)
        except ProjectError as exc:
            QMessageBox.critical(self, "Kaydedilemedi", str(exc))
            return False
        self.config.last_dir = str(Path(path).parent)
        self.config.add_recent(str(self.project.path))
        self._rebuild_recent_menu()
        if was_unsaved:
            # Proje ILK KEZ kaydedildi: gecici session klasorundeki surumleri
            # (varsa) projenin yanindaki kalici .aidversions klasorune tasi.
            VersionManager(self.project).relocate_after_save(None)
        self._after_save()
        return True

    def _after_save(self) -> None:
        self._update_title()
        if self.studio_page:
            self.studio_page.refresh()
        rec = self.autosave.registry.get(self.project.session_id)
        if rec is not None:
            rec.project_path = str(self.project.path) if self.project.path else ""
            rec.project_name = self.project.name
            self.autosave.registry.upsert(rec)
        self.statusBar().showMessage(f"Kaydedildi: {self.project.path}", 4000)

    # ---------------- pencere yasam dongusu ----------------
    def closeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if not self._confirm_discard_if_dirty():
            event.ignore()
            return
        self._autosave_timer.stop()
        self.autosave.mark_clean_exit()
        self.config.window_width = self.width()
        self.config.window_height = self.height()
        self.config.save()
        log.info("Uygulama kapatıldı.")
        super().closeEvent(event)
