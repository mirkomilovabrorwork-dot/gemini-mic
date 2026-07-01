"""Generates icon.ico (blue mic circle) next to this script.

Run manually if you need to regenerate the icon:
    python generate_icon.py
build.bat calls this automatically before pyinstaller.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image  # noqa: E402
from gemini_mic import make_icon_image, COLOR_IDLE  # noqa: E402


def main():
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    base = make_icon_image(COLOR_IDLE, size=256)
    images = [base.resize((s, s), resample=Image.LANCZOS) for s in sizes]
    base.save(out_path, format="ICO", sizes=[(s, s) for s in sizes], append_images=images[1:])
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
