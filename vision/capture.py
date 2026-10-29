from dataclasses import dataclass

import mss
from PIL import Image


class CaptureError(Exception):
    pass


@dataclass(frozen=True)
class Region:
    left: int
    top: int
    width: int
    height: int


class CaptureEngine:
    def __init__(self):
        self._sct = None

    def grab(self, region: Region) -> Image.Image:
        if region.width < 2 or region.height < 2:
            raise CaptureError("capture region is empty")
        box = {
            "left": region.left,
            "top": region.top,
            "width": region.width,
            "height": region.height,
        }
        try:
            if self._sct is None:
                self._sct = mss.mss()
            shot = self._sct.grab(box)
        except Exception as exc:
            self.close()
            raise CaptureError(f"screen capture failed: {exc}") from exc
        return Image.frombytes("RGB", shot.size, shot.rgb)

    def close(self):
        if self._sct is not None:
            try:
                self._sct.close()
            except Exception:
                pass
            self._sct = None
