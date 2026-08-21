#!/usr/bin/env python3
"""Measure vertical ink coverage of rendered CV pages.

Usage:
    typst compile cv.typ page{p}.png --format png --ppi 90
    python3 measure_fill.py page*.png

Target: last ink row at ~(100 - bottom-margin%) - 0..2%.
E.g. with a 1.2cm bottom margin on US Letter (~4%), aim for 94-96%.
Requires Pillow (pip install Pillow). No numpy needed.

Also importable: `from measure_fill import measure` returns the same
string ("ink from X% to Y%" / "blank page") for one image path, and
`gaps(path)` returns (page height, internal all-white row runs) for the
canyon and section-boundary checks — both for callers (e.g. verify.py)
that want them in-process instead of via CLI.
"""
import sys
from PIL import Image


def measure(path):
    """Return 'ink from X% to Y%' (or 'blank page') for one page image."""
    im = Image.open(path).convert("L")
    w, h = im.size
    px = im.load()
    lo = hi = None
    for y in range(h):
        if any(px[x, y] < 245 for x in range(0, w, 3)):  # sample every 3rd column
            if lo is None:
                lo = y
            hi = y
    if lo is None:
        return "blank page"
    return f"ink from {lo / h * 100:.0f}% to {hi / h * 100:.0f}%"


def gaps(path, thr=150):
    """Return (page_height_px, [internal all-white row runs, in px]).

    Scanned inside the content area only (6-94% of the width, 2-97% of the
    height) and trimmed to what lies BETWEEN the first and last ink row, so
    the page margins are not counted as gaps. Two checks read this:
    the canyon scan (a run too tall is a hole) and the section-boundary check
    (the boundary runs must stand out from the intra-section rhythm).
    """
    im = Image.open(path).convert("L")
    w, h = im.size
    px = im.load()
    ink = [any(px[x, y] < thr for x in range(int(w * .06), int(w * .94), 4))
           for y in range(int(h * .02), int(h * .97))]
    runs, n = [], 0
    seen_ink = False
    for v in ink:
        if v:
            if n and seen_ink:
                runs.append(n)
            seen_ink, n = True, 0
        else:
            n += 1
    return h, runs


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for path in sys.argv[1:]:
        print(f"{path}: {measure(path)}")
        h, runs = gaps(path)
        if runs:
            import statistics
            runs_sorted = sorted(runs)
            med = statistics.median(runs_sorted)
            print(f"  gaps: median {med}px, biggest {runs_sorted[-3:]}px "
                  f"({runs_sorted[-1] / h * 100:.1f}% of page height)")
