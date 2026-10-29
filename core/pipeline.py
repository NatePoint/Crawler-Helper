import hashlib

from PySide6.QtCore import QObject, Signal, Slot

from ocr.engine import OCREngine, OCRError
from ocr.processor import TextProcessor
from vision.capture import CaptureEngine, CaptureError


class PipelineWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, settings):
        super().__init__()
        self._capture = CaptureEngine()
        self._ocr = OCREngine(
            settings.ocr_backend, settings.ocr_langs, settings.tesseract_cmd
        )
        self._processor = TextProcessor()
        self._last_key = None
        self._last_result = None

    @Slot(object)
    def run(self, region):
        try:
            image = self._capture.grab(region)
            key = (image.size, hashlib.blake2b(image.tobytes(), digest_size=16).digest())
            if key != self._last_key or self._last_result is None:
                text = self._ocr.recognize(image)
                self._last_result = self._processor.process(text)
                self._last_key = key
            self.finished.emit(self._last_result)
        except (CaptureError, OCRError) as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"internal error: {exc}")
