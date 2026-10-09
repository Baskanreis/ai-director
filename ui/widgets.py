"""Tekrar kullanilabilir kucuk arayuz bilesenleri."""
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from . import theme


class Card(QFrame):
    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(18, 16, 18, 16)
        self.body.setSpacing(10)
        if title:
            label = QLabel(title)
            label.setObjectName("CardTitle")
            self.body.addWidget(label)


class Badge(QLabel):
    COLORS = {"ok": theme.OK, "warn": theme.WARN, "bad": theme.BAD, "info": theme.ACCENT}

    def __init__(self, text: str, kind: str = "info") -> None:
        super().__init__(text)
        self.setObjectName("Badge")
        color = self.COLORS.get(kind, theme.ACCENT)
        r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
        self.setStyleSheet(
            f"#Badge {{ background: rgba({r},{g},{b},50); color: {color};"
            f" border: 1px solid rgba({r},{g},{b},110);"
            " border-radius: 8px; padding: 2px 8px; font-size: 11px; font-weight: 600; }"
        )


def row(*widgets: QWidget) -> QWidget:
    """Yatay satir: ilk oge genisler, digerleri sagda kalir."""
    holder = QWidget()
    holder.setStyleSheet("background: transparent;")
    lay = QHBoxLayout(holder)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(12)
    for i, w in enumerate(widgets):
        lay.addWidget(w, 1 if i == 0 else 0)
    return holder
