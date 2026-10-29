import asyncio
import io
import os
import shutil
import sys

from PIL import Image, ImageOps

EASYOCR_CODES = {"eng": "en", "rus": "ru"}
WINDOWS_TAGS = {"eng": "en", "rus": "ru"}
WINDOWS_MAX_SIDE = 8000


class OCRError(Exception):
    pass


INSTALL_HINT = (
    "tesseract binary not found. Install Tesseract OCR "
    "(Windows: https://github.com/UB-Mannheim/tesseract/wiki, "
    "tick Russian language during setup) or pass the path via "
    "--tesseract-cmd / env TESSERACT_CMD"
)


def _candidate_paths():
    if sys.platform == "win32":
        roots = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
            os.environ.get("LOCALAPPDATA", ""),
        ]
        for root in roots:
            if root:
                yield os.path.join(root, "Tesseract-OCR", "tesseract.exe")
    else:
        yield from (
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
            "/opt/homebrew/bin/tesseract",
        )


def find_tesseract(explicit=""):
    """Return a working tesseract path or None."""
    for value in (explicit, os.environ.get("TESSERACT_CMD", "")):
        if value:
            found = value if os.path.isfile(value) else shutil.which(value)
            if found:
                return found
    found = shutil.which("tesseract")
    if found:
        return found
    for path in _candidate_paths():
        if os.path.isfile(path):
            return path
    return None


class OCREngine:
    def __init__(self, backend, langs, tesseract_cmd=""):
        self._backend = backend
        self._langs = tuple(langs) or ("eng",)
        self._cmd = tesseract_cmd
        self._reader = None
        self._windows_broken = False
        self._win_engine = None

    def recognize(self, image: Image.Image) -> str:
        prepared = self._prepare(image)
        if self._backend == "easyocr":
            return self._easyocr(prepared)
        if self._backend == "tesseract":
            return self._tesseract(prepared)
        if self._backend == "windows":
            return self._windows(prepared)
        errors = []
        methods = [self._tesseract] if self._windows_broken else [self._windows, self._tesseract]
        for method in methods:
            try:
                return method(prepared)
            except OCRError as exc:
                if method == self._windows:
                    self._windows_broken = True
                errors.append(str(exc))
        raise OCRError("; ".join(errors))

    @staticmethod
    def _prepare(image):
        gray = ImageOps.autocontrast(image.convert("L"))
        if gray.width < 1200:
            gray = gray.resize(
                (gray.width * 2, gray.height * 2), Image.Resampling.BICUBIC
            )
        return gray

    @staticmethod
    def _clean(text):
        lines = (line.strip() for line in text.splitlines())
        return "\n".join(line for line in lines if line)

    def _windows(self, image):
        if sys.platform != "win32":
            raise OCRError("Windows OCR is available only on Windows")
        try:
            import winrt.windows.media.ocr  # noqa: F401
        except ImportError as exc:
            raise OCRError(
                "winrt packages are not installed (pip install -r requirements.txt)"
            ) from exc
        if max(image.size) > WINDOWS_MAX_SIDE:
            image = image.copy()
            image.thumbnail((WINDOWS_MAX_SIDE, WINDOWS_MAX_SIDE))
        buffer = io.BytesIO()
        image.save(buffer, "PNG", compress_level=1)
        try:
            text = asyncio.run(self._windows_async(buffer.getvalue(), self._langs))
        except OCRError:
            raise
        except Exception as exc:
            raise OCRError(f"windows OCR failed: {exc}") from exc
        return self._clean(text)

    async def _windows_async(self, data, langs):
        from winrt.windows.globalization import Language
        from winrt.windows.graphics.imaging import BitmapDecoder
        from winrt.windows.media.ocr import OcrEngine
        from winrt.windows.storage.streams import (
            DataWriter,
            InMemoryRandomAccessStream,
        )

        engine = self._win_engine
        if engine is None:
            for code in langs:
                try:
                    engine = OcrEngine.try_create_from_language(
                        Language(WINDOWS_TAGS.get(code, code))
                    )
                except Exception:
                    engine = None
                if engine:
                    break
            if engine is None:
                engine = OcrEngine.try_create_from_user_profile_languages()
            if engine is None:
                raise OCRError(
                    "no OCR language in Windows (Settings > Time & language > "
                    "Language & region > add a language with OCR support)"
                )
            self._win_engine = engine
        stream = InMemoryRandomAccessStream()
        writer = DataWriter(stream)
        writer.write_bytes(data)
        await writer.store_async()
        writer.detach_stream()
        stream.seek(0)
        decoder = await BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()
        result = await engine.recognize_async(bitmap)
        return "\n".join(line.text for line in result.lines)

    def _tesseract(self, image):
        try:
            import pytesseract
        except ImportError as exc:
            raise OCRError("pytesseract is not installed") from exc
        path = find_tesseract(self._cmd)
        if not path:
            raise OCRError(INSTALL_HINT)
        pytesseract.pytesseract.tesseract_cmd = path
        candidates = list(dict.fromkeys(["+".join(self._langs), self._langs[0]]))
        last = None
        for lang in candidates:
            try:
                return self._clean(pytesseract.image_to_string(image, lang=lang))
            except pytesseract.TesseractNotFoundError as exc:
                raise OCRError(INSTALL_HINT) from exc
            except pytesseract.TesseractError as exc:
                last = exc
        raise OCRError(f"tesseract failed: {last}")

    def _easyocr(self, image):
        try:
            import easyocr
            import numpy
        except ImportError as exc:
            raise OCRError("easyocr is not installed") from exc
        try:
            if self._reader is None:
                codes = [EASYOCR_CODES.get(lang, lang) for lang in self._langs]
                self._reader = easyocr.Reader(codes)
            rows = self._reader.readtext(numpy.array(image), detail=0, paragraph=True)
        except Exception as exc:
            raise OCRError(f"easyocr failed: {exc}") from exc
        return self._clean("\n".join(rows))
