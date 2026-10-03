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

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

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

        edit_menu = self.menuBar().addMenu("&Düzen")
        act("Geri Al", "Ctrl+Z", lambda: self.studio_page and self.studio_page._undo(), edit_menu)
        act("İleri Al", "Ctrl+Y", lambda: self.studio_page and self.studio_page._redo(), edit_menu)
        edit_menu.addSeparator()
        act("Sürüm Geçmişi…", "Ctrl+Alt+V", self.open_version_history, edit_menu)

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
        page = self._ensure_page(key)
        self.stack.setCurrentWidget(page)
        self._nav_buttons[key].setChecked(True)
        self.config.last_page = key

    def _update_title(self) -> None:
        star = " •" if self.project.dirty else ""
        self.setWindowTitle(f"AI Director {__version__} — {self.project.name}{star}")

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
