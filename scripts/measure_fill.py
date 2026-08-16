#!/usr/bin/env python3
"""Measure vertical ink coverage of rendered CV pages.

Usage:
    typst compile cv.typ page{p}.png --format png --ppi 90
    python3 measure_fill.py page*.png

Target: last ink row at ~(100 - bottom-margin%) - 0..2%.
E.g. with a 1.2cm bottom margin on US Letter (~4%), aim for 94-96%.
Requires Pillow (pip install Pillow). No numpy needed.
"""
import sys
from PIL import Image

if len(sys.argv) < 2:
    sys.exit(__doc__)

for path in sys.argv[1:]:
    im = Image.open(path).convert("L")
    w, h = im.size
    px = im.load()
    lo = hi = None
    for y in range(h):
        if any(px[x, y] < 245 for x in range(0, w, 3)):  # ponytail: sample every 3rd column
            if lo is None:
                lo = y
            hi = y
    if lo is None:
        print(f"{path}: blank page")
    else:
        print(f"{path}: ink from {lo / h * 100:.0f}% to {hi / h * 100:.0f}%")
