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
`bands(path)` returns (page height, white runs, ink bands) — an ink band is a
row group whose horizontal coverage marks it as a boundary DEVICE (rule, filled
bar, knockout slab) rather than text.
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


# A dark run this wide (share of page width) is a DEVICE. 0.25 was the first
# guess and it produced a FALSE FAIL on `margin-index`, whose accent rule is
# real but lives in a 2.5cm margin column: measured at 150 ppi it spans 11.5%,
# and no text row on that page comes close. The corpus separates cleanly —
# text tops out near 2.8% (`humanist-quiet`, genuinely device-less), a short
# margin rule lands at 11.5%, a full-measure rule at 35.7% and up. 0.08 sits
# between the two clusters with room on both sides. Raising it back will fail
# any family whose device is deliberately shorter than the text column.
RULE_FLOOR = 0.08
RULE_CONTRAST = 20  # …and "dark" for a DEVICE means this much below the paper


def bands(path, thr=150, rule=RULE_FLOOR, contrast=RULE_CONTRAST):
    """Return (page height, [(start, end) white runs], [(start, end) ink bands]).

    One scan, two readings of the same rows, inside the content area only
    (6-94% of the width, 2-97% of the height) and trimmed to what lies BETWEEN
    the first and last ink row, so the page margins count as neither.

    A row is WHITE when it holds no dark pixel. A row is a BAND when its
    longest UNBROKEN dark run spans at least `rule` of the page width: that is
    the signature of a boundary DEVICE — a hairline, a filled bar, a knocked-out
    slab — and text cannot fake it, because word gaps chop every text row into
    short runs. Measured at 150 ppi on freshly compiled pages, longest run as a
    share of page width: humanist-quiet (no device by design) 2.8%, hard-edge
    (short accent rule) 35.7%, swiss-grid (full-measure hairline) 86.0%,
    color-band (bleed bar) 100%. The floor sits in the gap between the first
    two, which is an order of magnitude wide — it is not a tuned number.

    A device is measured against the PAPER (the page's modal luma), not against
    absolute black: the default `soft` hairline is a pale rule — luma ~180 on
    white — and an ink threshold tuned for body text scores it as blank, which
    is how a page carrying a hairline above every section was first read here
    as carrying none. Families printing on a tinted ground need the same
    relative reading.

    Note what this does NOT use: the *fraction* of dark pixels in a row. That
    was tried first and cannot separate the two cases — a dense text row and a
    filled bar both land near 0.5 once the row is sampled every few pixels.
    Only continuity tells them apart.

    This is the measurement the section-separation rule was missing: the white
    scan can see that a boundary is wide, never that it carries ink, so
    « séparateurs, pas des espaces vides » had no instrument behind it.
    """
    im = Image.open(path).convert("L")
    w, h = im.size
    x0, x1 = int(w * .06), int(w * .94)
    im = im.crop((x0, int(h * .02), x1, int(h * .97)))
    cw, ch = im.size
    # The paper, not the absolute value 255: several families print on a tinted
    # ground, and a device is whatever sits CONTRASTED against that ground. The
    # modal luma is the paper — it is the most common pixel on any CV page.
    paper = max(range(256), key=im.histogram().__getitem__)
    body = im.point(lambda v: 255 if v < thr else 0).tobytes()
    dev = im.point(lambda v: 255 if v < paper - contrast else 0).tobytes()
    floor = rule * w
    dark, longest = [], []
    for y in range(ch):
        dark.append(cw - body[y * cw:(y + 1) * cw].count(0))
        longest.append(max(len(r) for r in
                           dev[y * cw:(y + 1) * cw].split(b"\x00")))
    rows = [i for i, d in enumerate(dark) if d]
    if not rows:
        return h, [], []
    lo, hi = rows[0], rows[-1]

    def runs_of(pred):
        out, start = [], None
        for i in range(lo, hi + 1):
            if pred(i):
                start = i if start is None else start
            elif start is not None:
                out.append((start, i))
                start = None
        if start is not None:
            out.append((start, hi + 1))
        return out

    return (h, runs_of(lambda i: dark[i] == 0),
            runs_of(lambda i: longest[i] >= floor))


def gaps(path, thr=150):
    """Return (page height, [internal all-white row runs, in px]).

    Thin wrapper over `bands` — kept because the canyon scan and the
    section-boundary check read only the lengths.
    """
    h, white, _ = bands(path, thr)
    return h, [b - a for a, b in white]


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
