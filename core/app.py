import sys

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from config import HOTKEYS
from core.hotkeys import HotkeyService
from core.pipeline import PipelineWorker
from core.window import OverlayWindow


class Application:
    def __init__(self, settings):
        self._qt = QApplication(sys.argv)
        self._qt.setQuitOnLastWindowClosed(False)
        self._thread = QThread()
        self._worker = PipelineWorker(settings)
        self._worker.moveToThread(self._thread)
        self._window = OverlayWindow(settings)
        self._hotkeys = HotkeyService(HOTKEYS)
        self._wire()

    def _wire(self):
        window = self._window
        window.scan_requested.connect(self._worker.run)
        window.quit_requested.connect(self._qt.quit)
        self._worker.finished.connect(window.on_result)
        self._worker.failed.connect(window.on_failure)
        self._hotkeys.triggered.connect(window.handle_command)
        self._qt.aboutToQuit.connect(self._cleanup)

    def run(self):
        self._thread.start()
        self._hotkeys.start()
        self._window.show()
        return self._qt.exec()

    def _cleanup(self):
        self._hotkeys.stop()
        self._thread.quit()
        self._thread.wait(3000)
