"""AI Director giriş noktası.

Windows paketleri için de doğrudan çalıştırılabilir:
    python app/main.py

PyInstaller ile paketlendiğinde uygulama içindeki hatalar sessizce kaybolmasın
diye başlatma/çökme hataları kullanıcıya gösterilir ve log dosyasına yazılır.
"""
from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path


# Kaynak çalıştırmada proje kökünü; PyInstaller paketinde ise _MEIPASS'ı destekle.
ROOT = Path(__file__).resolve().parents[1]
if getattr(sys, "frozen", False):
    BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
else:
    BUNDLE_ROOT = ROOT

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _show_fatal_error(title: str, message: str) -> None:
    """GUI açılmadan önce bile Windows'ta görünür bir hata göster."""
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, title, message)
    except Exception:
        # PySide6 bile yüklenemiyorsa son çare Windows MessageBox.
        if os.name == "nt":
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
                return
            except Exception:
                pass
        print(f"{title}: {message}", file=sys.stderr)


def _install_exception_hook(log: logging.Logger) -> None:
    def handle(exc_type, exc_value, exc_tb):
        if exc_type is KeyboardInterrupt:
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        log.critical("Uygulama beklenmedik şekilde sonlandı:\n%s", details)
        _show_fatal_error(
            "AI Director başlatılamadı",
            "Uygulama başlatılırken beklenmeyen bir hata oluştu.\n\n"
            f"{exc_value}\n\n"
            "Ayrıntılar ~/.ai_director/logs/ai_director.log dosyasına yazıldı.",
        )

    sys.excepthook = handle


def main() -> int:
    from app import __version__
    from app.runtime.config import Config
    from app.runtime.logger import setup_logging

    setup_logging()
    log = logging.getLogger("ai_director")
    _install_exception_hook(log)
    log.info("AI Director %s başlatılıyor...", __version__)

    try:
        from PySide6.QtWidgets import QApplication
    except Exception as exc:
        message = (
            "PySide6 yüklenemedi. Kurulum bozuk veya eksik olabilir.\n\n"
            f"{exc}"
        )
        log.exception(message)
        _show_fatal_error("AI Director başlatılamadı", message)
        return 1

    try:
        from app.ui.main_window import MainWindow
        from app.ui.theme import STYLESHEET

        qt_app = QApplication(sys.argv)
        qt_app.setApplicationName("AI Director")
        qt_app.setApplicationVersion(__version__)
        qt_app.setOrganizationName("AI Director")
        qt_app.setStyleSheet(STYLESHEET)

        window = MainWindow(Config.load())
        window.show()
        window.raise_()
        window.activateWindow()
        log.info("Ana pencere açıldı.")
        return qt_app.exec()
    except Exception as exc:
        log.exception("Ana pencere oluşturulamadı.")
        _show_fatal_error(
            "AI Director başlatılamadı",
            "Ana pencere oluşturulurken hata oluştu.\n\n"
            f"{exc}\n\n"
            "Ayrıntılar ~/.ai_director/logs/ai_director.log dosyasına yazıldı.",
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
