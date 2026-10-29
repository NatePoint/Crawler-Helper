from PySide6.QtCore import QObject, Signal


class HotkeyService(QObject):
    triggered = Signal(str)

    def __init__(self, mapping, parent=None):
        super().__init__(parent)
        self._mapping = mapping
        self._listener = None

    def start(self) -> bool:
        try:
            from pynput import keyboard
        except ImportError:
            return False
        binds = {
            combo: (lambda name=name: self.triggered.emit(name))
            for name, combo in self._mapping.items()
        }
        try:
            self._listener = keyboard.GlobalHotKeys(binds)
            self._listener.start()
        except Exception:
            self._listener = None
            return False
        return True

    def stop(self):
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
