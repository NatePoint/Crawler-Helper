import argparse
import sys
from dataclasses import replace

from config import Settings
from core.app import Application


def parse_args():
    parser = argparse.ArgumentParser(prog="crawler_help")
    parser.add_argument("--ocr", choices=("auto", "windows", "tesseract", "easyocr"), default="auto")
    parser.add_argument("--langs", default="rus,eng")
    parser.add_argument("--tesseract-cmd", default="")
    return parser.parse_args()


def main():
    args = parse_args()
    settings = replace(
        Settings(),
        ocr_backend=args.ocr,
        ocr_langs=tuple(code for code in args.langs.split(",") if code),
        tesseract_cmd=args.tesseract_cmd,
    )
    return Application(settings).run()


if __name__ == "__main__":
    sys.exit(main())
