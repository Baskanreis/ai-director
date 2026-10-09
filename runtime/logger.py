"""Uygulama loglama kurulumu."""
import logging
from logging.handlers import RotatingFileHandler

from .paths import log_dir


def setup_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:  # tekrar kurulumu engelle
        return
    root.setLevel(level)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    try:
        file_handler = RotatingFileHandler(
            log_dir() / "ai_director.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
    except OSError:
        root.warning("Log dosyasi acilamadi, sadece konsola yaziliyor.")
