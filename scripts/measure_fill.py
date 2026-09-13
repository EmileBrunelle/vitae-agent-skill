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


# A dark run this wide (share of page width) is a candidate DEVICE. This is a
# PREFILTER, not the test: it cannot tell a rule from an underline, because
# "longest dark run" says nothing about WHERE the run is. Measured at 90 ppi
# over the 14 families, the two populations overlap head to tail — real devices
# as narrow as 5.65% (`quiet-luxury`'s inline tick), accidental text ink as wide
# as 21.8% (a `#show link: underline` on the contact line) and 86.4% (a
# two-column table rule). No value of this constant separates them. What does is
# verify.py's check that the run sits AT a section boundary (there is no text in
# a boundary), so this number only has to sit under the thinnest genuine device
# and over ordinary text: text tops out at 3.66% across the corpus, the thinnest
# real device is 5.65%, so 0.04 clears both with room. Do NOT raise it back to
# 0.08: that alone false-failed `editorial-serif` (7.61%) and `avant-poster`
# (7.29%), whose devices are real.
RULE_FLOOR = 0.04
RULE_CONTRAST = 20  # …and "dark" for a DEVICE means this much below the paper


def bands(path, thr=150, rule=RULE_FLOOR, contrast=RULE_CONTRAST):
    """Return (page height, [(start, end) white runs], [(start, end) ink bands]).

    One scan, two readings of the same rows, inside the content area only
    (6-94% of the width, 2-97% of the height) and trimmed to what lies BETWEEN
    the first and last ink row, so the page margins count as neither.

    A row is WHITE when it holds no dark pixel. A row is a BAND when its
    longest UNBROKEN dark run spans at least `rule` of the page width: a
    hairline, a filled bar or a knocked-out slab reads that way, and ordinary
    body text does not, because word gaps chop every text row into short runs.
    Text CAN still fake it — an underlined link runs 21.8% unbroken, a
    two-column table rule 86.4% — so a band here is a candidate, not a verdict;
    see RULE_FLOOR, and verify.py, which accepts only the bands that sit at a
    section boundary.

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

    THE INSTRUMENT CHANGED ON 2026-09-13, commit 42049f6 ("Measure section
    separation instead of only describing it"). Before it, this function
    sampled every 4th column (`range(x0, x1, 4)`); `bands` samples EVERY
    column, so a row carrying one thin dark pixel now reads as ink where it
    used to read as white. White runs shrank, medians shrank, and every ratio
    in the repo moved — that commit presented the rewrite as behaviour-
    preserving and it was not. Everything downstream was recalibrated on
    2026-09-13 against the 30 rendered pages of the 29-deliverable corpus.
    Any future change to the sampling step, the crop (6-94% x 2-97%) or `thr`
    invalidates every number in verify.py's separation block and in
    references/design.md § Invariants: re-measure the corpus before trusting
    them, and record the date and commit here as this note does.
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
