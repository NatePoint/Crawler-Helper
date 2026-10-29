from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QWidget

from config import (
    ACCENT,
    ACCENT_TEXT,
    BORDER,
    BUTTON,
    ERROR,
    FONT_FAMILIES,
    MUTED,
    PANEL,
    PANEL_TEXT,
)

HIT = QColor(0, 0, 0, 1)
BUTTON_HEIGHT = 22
PAD = 10
WRAP = Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap
IDLE_STATUS = "Готов"
HINT = (
    "Поместите прозрачную область над текстом и нажмите Ctrl+Alt+S.\n"
    "L — непрерывно, M — краткое содержание или полный текст, H — скрыть, Q — выход."
)


class Canvas(QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self._s = settings
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self._font = QFont()
        self._font.setFamilies(FONT_FAMILIES)
        self._font.setPixelSize(13)
        self._bold = QFont(self._font)
        self._bold.setBold(True)
        self._small = QFont(self._font)
        self._small.setPixelSize(12)
        self._metrics = QFontMetrics(self._font)
        self._bold_metrics = QFontMetrics(self._bold)
        self._small_metrics = QFontMetrics(self._small)
        self._live = False
        self._busy = False
        self._suppressed = False
        self._error = False
        self._summary_mode = True
        self._calcs = ""
        self._body = ""
        self._status = IDLE_STATUS
        self._scroll = 0
        self._max_scroll = 0

    # --- геометрия -------------------------------------------------------
    def header_rect(self):
        return QRect(0, 0, self.width(), self._s.header_height)

    def result_rect(self):
        room = self.height() - self._s.header_height - 80
        height = max(80, min(self._s.result_height, room))
        return QRect(0, self.height() - height, self.width(), height)

    def frame_rect(self):
        top = self._s.header_height
        return QRect(0, top, self.width(), self.result_rect().top() - top)

    def capture_rect(self):
        w = self._s.frame_width
        return self.frame_rect().adjusted(w, w, -w, -w)

    def handle_rect(self):
        n = self._s.handle_size
        return QRect(self.width() - n, self.height() - n, n, n)

    def _buttons(self):
        header = self.header_rect()
        items = (
            ("mode", "Кратко" if self._summary_mode else "Текст", False),
            ("live", "Live", self._live),
            ("scan", "Сканировать", False),
        )
        x = header.right() - 8
        top = header.top() + (header.height() - BUTTON_HEIGHT) // 2
        result = []
        for name, label, active in items:
            width = self._small_metrics.horizontalAdvance(label) + 20
            result.append((name, QRect(x - width + 1, top, width, BUTTON_HEIGHT), label, active))
            x -= width + 6
        return result

    def hit_test(self, pos):
        for name, rect, _label, _active in self._buttons():
            if rect.contains(pos):
                return "btn:" + name
        if self.handle_rect().contains(pos):
            return "resize"
        if self.header_rect().contains(pos) or self.result_rect().contains(pos):
            return "move"
        frame = self.frame_rect()
        b = self._s.border_hit
        if frame.contains(pos) and not frame.adjusted(b, b, -b, -b).contains(pos):
            return "move"
        return None

    # --- состояние -------------------------------------------------------
    def set_live(self, value):
        self._live = value
        self.update()

    def set_busy(self, value):
        self._busy = value
        self.update()

    def set_suppressed(self, value):
        self._suppressed = value
        self.update()

    def set_mode(self, summary):
        self._summary_mode = summary
        self.update()

    def set_status(self, status):
        self._error = False
        self._status = status
        self.update()

    def set_result(self, calcs, body, status):
        self._error = False
        self._calcs = "\n".join(calcs)
        self._body = body
        self._status = status
        self._scroll = 0
        self.update()

    def set_error(self, message):
        self._error = True
        self._calcs = ""
        self._body = ""
        self._status = f"Ошибка: {message}"
        self._scroll = 0
        self.update()

    def in_result(self, pos):
        return self.result_rect().contains(pos)

    def scroll_by(self, delta):
        value = max(0, min(self._max_scroll, self._scroll - delta))
        if value != self._scroll:
            self._scroll = value
            self.update()

    # --- отрисовка -------------------------------------------------------
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        self._paint_hit(p)
        if not self._suppressed:
            self._paint_frame(p)
            self._paint_header(p)
            self._paint_result(p)
        p.end()

    def _paint_hit(self, p):
        frame = self.frame_rect()
        b = self._s.border_hit
        p.fillRect(QRect(frame.left(), frame.top(), b, frame.height()), HIT)
        p.fillRect(QRect(frame.right() - b + 1, frame.top(), b, frame.height()), HIT)

    def _paint_frame(self, p):
        f = self.frame_rect()
        w = self._s.frame_width
        p.fillRect(QRect(f.left(), f.top(), f.width(), w), ACCENT)
        p.fillRect(QRect(f.left(), f.bottom() - w + 1, f.width(), w), ACCENT)
        p.fillRect(QRect(f.left(), f.top(), w, f.height()), ACCENT)
        p.fillRect(QRect(f.right() - w + 1, f.top(), w, f.height()), ACCENT)

    def _paint_header(self, p):
        h = self.header_rect()
        p.fillRect(h, PANEL)
        p.fillRect(QRect(h.left(), h.bottom(), h.width(), 1), BORDER)
        buttons = self._buttons()
        p.setFont(self._bold)
        p.setPen(PANEL_TEXT)
        p.drawText(QRect(12, 0, h.width(), h.height()), Qt.AlignVCenter | Qt.AlignLeft, "Crawler Help")
        state = "Ошибка" if self._error else ("Сканирование…" if self._busy else "")
        if state:
            x = 12 + self._bold_metrics.horizontalAdvance("Crawler Help") + 12
            room = min(r.left() for _n, r, _l, _a in buttons) - x - 8
            if room > 20:
                p.setFont(self._small)
                p.setPen(ERROR if self._error else MUTED)
                text = self._small_metrics.elidedText(state, Qt.ElideRight, room)
                p.drawText(QRect(x, 0, room, h.height()), Qt.AlignVCenter | Qt.AlignLeft, text)
        p.setFont(self._small)
        for _name, rect, label, active in buttons:
            p.fillRect(rect, ACCENT if active else BUTTON)
            p.setPen(QPen(ACCENT if active else BORDER, 1))
            p.drawRect(rect.adjusted(0, 0, -1, -1))
            p.setPen(ACCENT_TEXT if active else PANEL_TEXT)
            p.drawText(rect, Qt.AlignCenter, label)

    def _paint_result(self, p):
        r = self.result_rect()
        p.fillRect(r, PANEL)
        p.setFont(self._small)
        p.setPen(ERROR if self._error else MUTED)
        width = r.width() - 2 * PAD
        status = self._small_metrics.elidedText(self._status, Qt.ElideRight, width)
        p.drawText(QRect(PAD, r.top() + 6, width, self._small_metrics.height()), Qt.AlignLeft, status)
        body = QRect(
            PAD,
            r.top() + 10 + self._small_metrics.height(),
            width,
            r.bottom() - 6 - (r.top() + 10 + self._small_metrics.height()),
        )
        self._paint_text(p, body)
        p.setPen(QPen(MUTED, 1))
        hr = self.handle_rect()
        for k in (4, 8, 12):
            p.drawLine(hr.right() - k, hr.bottom() - 1, hr.right() - 1, hr.bottom() - k)

    def _paint_text(self, p, body):
        calcs, text, color = self._calcs, self._body, PANEL_TEXT
        if not calcs and not text and not self._error:
            text, color = HINT, MUTED
        calcs_h = self._bold_metrics.boundingRect(body, WRAP, calcs).height() if calcs else 0
        gap = 6 if calcs and text else 0
        text_h = self._metrics.boundingRect(body, WRAP, text).height() if text else 0
        self._max_scroll = max(0, calcs_h + gap + text_h - body.height())
        self._scroll = min(self._scroll, self._max_scroll)
        p.save()
        p.setClipRect(body)
        p.translate(0, -self._scroll)
        if calcs:
            p.setFont(self._bold)
            p.setPen(ACCENT)
            p.drawText(body, WRAP, calcs)
        if text:
            p.setFont(self._font)
            p.setPen(color)
            p.drawText(body.translated(0, calcs_h + gap), WRAP, text)
        p.restore()
