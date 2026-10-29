from dataclasses import dataclass

from PySide6.QtGui import QColor

# Палитра интерфейса: меняется здесь, в одном месте.
PANEL = QColor("#F4F5F7")
PANEL_TEXT = QColor("#1F2937")
MUTED = QColor("#6B7280")
BORDER = QColor("#C9CED6")
ACCENT = QColor("#2F5D9E")
ACCENT_TEXT = QColor("#FFFFFF")
BUTTON = QColor("#E6E9EE")
ERROR = QColor("#B42318")

FONT_FAMILIES = ["Segoe UI", "Arial", "Helvetica", "sans-serif"]

HOTKEYS = {
    "scan": "<ctrl>+<alt>+s",
    "live": "<ctrl>+<alt>+l",
    "toggle": "<ctrl>+<alt>+h",
    "mode": "<ctrl>+<alt>+m",
    "quit": "<ctrl>+<alt>+q",
}


@dataclass(frozen=True)
class Settings:
    width: int = 520
    height: int = 480
    min_width: int = 340
    min_height: int = 280
    header_height: int = 34
    result_height: int = 180
    frame_width: int = 2
    border_hit: int = 8
    handle_size: int = 16
    live_interval_ms: int = 1500
    settle_ms: int = 80
    ocr_backend: str = "auto"
    ocr_langs: tuple = ("rus", "eng")
    tesseract_cmd: str = ""
