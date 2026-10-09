"""AI Director profesyonel koyu tema."""

BG = "#0b0e14"
PANEL = "#11151e"
PANEL_2 = "#151a24"
CARD = "#171d28"
CARD_HOVER = "#1c2330"
BORDER = "#273044"
TEXT = "#f1f4fb"
MUTED = "#8994aa"
ACCENT = "#7657ff"
ACCENT_2 = "#9b7cff"
OK = "#38d996"
WARN = "#ffbd59"
BAD = "#ff667a"

STYLESHEET = f"""
QWidget {{ background: {BG}; color: {TEXT}; font-family: "Segoe UI", "Inter", sans-serif; font-size: 13px; }}
QMainWindow {{ background: {BG}; }}
QMenuBar {{ background: {PANEL}; color: {MUTED}; border-bottom: 1px solid {BORDER}; padding: 3px 8px; }}
QMenuBar::item {{ padding: 7px 10px; border-radius: 6px; }}
QMenuBar::item:selected {{ background: {CARD_HOVER}; color: {TEXT}; }}
QMenu {{ background: {PANEL_2}; border: 1px solid {BORDER}; padding: 6px; }}
QMenu::item {{ padding: 8px 24px; border-radius: 5px; }}
QMenu::item:selected {{ background: {ACCENT}; color: white; }}
#Sidebar {{ background: {PANEL}; border-right: 1px solid {BORDER}; }}
#Sidebar QLabel {{ background: transparent; }}
#Logo {{ font-size: 20px; font-weight: 800; color: {TEXT}; padding: 20px 18px 2px 18px; }}
#LogoSub {{ color: {MUTED}; padding: 0 18px 18px 18px; }}
#NavSection {{ color: {MUTED}; font-size: 10px; font-weight: 700; letter-spacing: 1.2px; padding: 12px 18px 5px 18px; }}
QPushButton#NavButton {{ background: transparent; border: none; text-align: left; padding: 11px 14px; margin: 2px 10px; border-radius: 9px; color: {MUTED}; font-weight: 500; }}
QPushButton#NavButton:hover {{ background: {CARD_HOVER}; color: {TEXT}; }}
QPushButton#NavButton:checked {{ background: rgba(118,87,255,0.20); color: {ACCENT_2}; border: 1px solid rgba(118,87,255,0.28); font-weight: 700; }}
#TopBar {{ background: {PANEL}; border-bottom: 1px solid {BORDER}; }}
#TopProject {{ font-size: 15px; font-weight: 700; background: transparent; }}
#TopMeta {{ color: {MUTED}; background: transparent; }}
#PageTitle {{ font-size: 28px; font-weight: 800; background: transparent; letter-spacing: -0.4px; }}
#PageSub {{ color: {MUTED}; background: transparent; font-size: 13px; }}
#Card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 14px; }}
#Card:hover {{ border-color: #35415b; }}
#Card QLabel {{ background: transparent; }}
#CardTitle {{ font-size: 14px; font-weight: 700; }}
#Muted {{ color: {MUTED}; }}
QPushButton {{ background: {PANEL_2}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 8px; padding: 9px 14px; font-weight: 600; }}
QPushButton:hover {{ background: {CARD_HOVER}; border-color: #3a4660; }}
QPushButton:pressed {{ background: {ACCENT}; border-color: {ACCENT}; }}
QPushButton:disabled {{ color: #5c6679; background: #121620; }}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background: #0e121a; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 8px; padding: 8px 10px; selection-background-color: {ACCENT}; }}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QProgressBar {{ background: #0d1118; border: 1px solid {BORDER}; border-radius: 6px; text-align: center; height: 10px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 5px; }}
QStatusBar {{ background: {PANEL}; color: {MUTED}; border-top: 1px solid {BORDER}; }}
QScrollArea {{ border: none; background: transparent; }}
QToolTip {{ background: {PANEL_2}; color: {TEXT}; border: 1px solid {BORDER}; padding: 6px; }}
"""
