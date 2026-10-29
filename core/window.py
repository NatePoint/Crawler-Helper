import time

from PySide6.QtCore import QTimer, Qt, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QVBoxLayout, QWidget

from core.osutil import exclude_from_capture
from ui.canvas import Canvas
from vision.capture import Region


class OverlayWindow(QWidget):
    scan_requested = Signal(object)
    quit_requested = Signal()

    def __init__(self, settings):
        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        super().__init__(None, flags)
        self._s = settings
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("Crawler Help")
        self.setMinimumSize(settings.min_width, settings.min_height)
        self.resize(settings.width, settings.height)
        self._canvas = Canvas(settings, self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)
        self._drag = None
        self._summary_mode = True
        self._busy = False
        self._started = 0.0
        self._excluded = False
        self._affinity_set = False
        self._live = QTimer(self)
        self._live.setInterval(settings.live_interval_ms)
        self._live.timeout.connect(self.request_scan)
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.move(screen.center() - self.rect().center())

    def showEvent(self, event):
        super().showEvent(event)
        if not self._affinity_set:
            self._affinity_set = True
            self._excluded = exclude_from_capture(int(self.winId()))

    def closeEvent(self, event):
        self._live.stop()
        super().closeEvent(event)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            event.ignore()
            return
        mode = self._canvas.hit_test(event.position().toPoint())
        if mode is None:
            event.ignore()
            return
        if mode.startswith("btn:"):
            self.handle_command(mode[4:])
            return
        self._drag = (mode, event.globalPosition().toPoint(), self.geometry())

    def mouseMoveEvent(self, event):
        if self._drag is None:
            return
        mode, origin, geometry = self._drag
        delta = event.globalPosition().toPoint() - origin
        if mode == "move":
            self.move(geometry.topLeft() + delta)
            return
        self.resize(
            max(self.minimumWidth(), geometry.width() + delta.x()),
            max(self.minimumHeight(), geometry.height() + delta.y()),
        )

    def mouseReleaseEvent(self, event):
        self._drag = None

    def wheelEvent(self, event):
        if self._canvas.in_result(event.position().toPoint()):
            self._canvas.scroll_by(event.angleDelta().y() // 3)

    def keyPressEvent(self, event):
        commands = {
            Qt.Key_S: "scan",
            Qt.Key_L: "live",
            Qt.Key_H: "toggle",
            Qt.Key_M: "mode",
            Qt.Key_Q: "quit",
            Qt.Key_Escape: "quit",
        }
        command = commands.get(event.key())
        if command:
            self.handle_command(command)

    @Slot(str)
    def handle_command(self, name):
        if name == "scan":
            self.request_scan()
        elif name == "live":
            self.toggle_live()
        elif name == "toggle":
            self.setVisible(not self.isVisible())
        elif name == "mode":
            self._summary_mode = not self._summary_mode
            self._canvas.set_mode(self._summary_mode)
            self._canvas.set_status(
                "Режим: " + ("краткое содержание" if self._summary_mode else "полный текст")
            )
        elif name == "quit":
            self.quit_requested.emit()

    def toggle_live(self):
        enable = not self._live.isActive()
        if enable:
            self._live.start()
        else:
            self._live.stop()
        self._canvas.set_live(enable)
        if enable:
            self.request_scan()

    def request_scan(self):
        if self._busy:
            return
        self._busy = True
        self._canvas.set_busy(True)
        if self._excluded:
            self._dispatch()
            return
        self._canvas.set_suppressed(True)
        QTimer.singleShot(self._s.settle_ms, self._dispatch)

    def _dispatch(self):
        rect = self._canvas.capture_rect()
        origin = self._canvas.mapToGlobal(rect.topLeft())
        ratio = self.devicePixelRatioF()
        self._started = time.perf_counter()
        self.scan_requested.emit(
            Region(
                round(origin.x() * ratio),
                round(origin.y() * ratio),
                round(rect.width() * ratio),
                round(rect.height() * ratio),
            )
        )

    def _finish(self):
        self._busy = False
        self._canvas.set_busy(False)
        self._canvas.set_suppressed(False)

    @Slot(object)
    def on_result(self, result):
        self._finish()
        elapsed = time.perf_counter() - self._started
        parts = [f"{len(result.text)} симв."]
        if result.calculations:
            parts.append(f"расчётов: {len(result.calculations)}")
        parts.append(f"{elapsed:.2f} с")
        use_summary = self._summary_mode and bool(result.summary)
        copied = result.summary if use_summary else result.text
        if copied and not self._live.isActive():
            QGuiApplication.clipboard().setText(copied)
            parts.append("скопировано (кратко)" if use_summary else "скопировано")
        calcs = [f"{expr} = {value}" for expr, value in result.calculations]
        body = result.summary if use_summary else result.text
        self._canvas.set_result(calcs, body, " · ".join(parts))

    @Slot(str)
    def on_failure(self, message):
        self._finish()
        self._canvas.set_error(message)
