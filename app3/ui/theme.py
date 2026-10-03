"""Koyu tema stil dosyasi (QSS)."""

BG = "#0f1117"
PANEL = "#171a23"
CARD = "#1e2230"
BORDER = "#2a3042"
TEXT = "#e6e9f2"
MUTED = "#8b93a7"
ACCENT = "#7c5cff"
OK = "#2ecc71"
WARN = "#f5a623"
BAD = "#e74c3c"

STYLESHEET = f"""
QWidget {{ background: {BG}; color: {TEXT}; font-family: "Segoe UI", "Inter", "Noto Sans", sans-serif; font-size: 13px; }}
QMainWindow, QStackedWidget {{ background: {BG}; }}
#Sidebar {{ background: {PANEL}; border-right: 1px solid {BORDER}; }}
#Sidebar QLabel {{ background: transparent; }}
#Logo {{ font-size: 18px; font-weight: 700; color: {TEXT}; padding: 18px 16px 2px 16px; }}
#LogoSub {{ color: {MUTED}; padding: 0 16px 16px 16px; }}
QPushButton#NavButton {{ background: transparent; border: none; text-align: left; padding: 10px 16px; margin: 2px 8px; border-radius: 8px; color: {MUTED}; }}
QPushButton#NavButton:hover {{ background: {CARD}; color: {TEXT}; }}
QPushButton#NavButton:checked {{ background: {ACCENT}; color: white; font-weight: 600; }}
#PageTitle {{ font-size: 24px; font-weight: 700; background: transparent; }}
#PageSub {{ color: {MUTED}; background: transparent; }}
#Card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}
#Card QLabel {{ background: transparent; }}
#CardTitle {{ font-size: 14px; font-weight: 600; }}
#Muted {{ color: {MUTED}; }}
QStatusBar {{ background: {PANEL}; color: {MUTED}; border-top: 1px solid {BORDER}; }}
QScrollArea {{ border: none; }}
"""
