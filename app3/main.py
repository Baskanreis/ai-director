"""AI Director giris noktasi.

Calistirma:
    python app/main.py
"""
import logging
import sys
from pathlib import Path

# `python app/main.py` ile dogrudan calistirildiginda proje kokunu yola ekle
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    from app import __version__
    from app.runtime.config import Config
    from app.runtime.logger import setup_logging

    setup_logging()
    log = logging.getLogger("ai_director")
    log.info("AI Director %s baslatiliyor...", __version__)

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        log.error("PySide6 bulunamadi. Once calistirin: pip install -r requirements.txt")
        return 1

    from app.ui.main_window import MainWindow
    from app.ui.theme import STYLESHEET

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("AI Director")
    qt_app.setApplicationVersion(__version__)
    qt_app.setStyleSheet(STYLESHEET)

    window = MainWindow(Config.load())
    window.show()
    return qt_app.exec()


if __name__ == "__main__":
    sys.exit(main())
