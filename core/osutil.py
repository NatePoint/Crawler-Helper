import ctypes
import sys

WDA_EXCLUDEFROMCAPTURE = 0x11


def exclude_from_capture(hwnd: int) -> bool:
    if sys.platform != "win32":
        return False
    try:
        ok = ctypes.windll.user32.SetWindowDisplayAffinity(
            ctypes.c_void_p(hwnd), WDA_EXCLUDEFROMCAPTURE
        )
        return bool(ok)
    except Exception:
        return False
