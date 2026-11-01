"""Page measurement helpers, separated from the gates that use them.

Pixels and boxes in, numbers and bands out: ink bands outside the word boxes, which of them
sit at a section boundary, the colour-fill and icon candidates cut from a page raster, the
x-height band of a text line, relative luminance. Nothing here prints a finding, renders a PDF
or reads module state; verify.py owns the gates and the rendering, and imports these names
explicitly. The thresholds that locate a boundary live here with their calibration, for the
same reason: a value moved without its measurements would be tuned blind. This module never imports verify, and
holds no module state beyond constants and the sRGB lookup table.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Any, cast

from PIL import Image, ImageChops, ImageDraw, ImageFilter

# Box and Band repeat verify.py's definitions of the same names, written out structurally, because they cannot be
# imported: verify.py runs as __main__, so `import verify` here would execute that script a second time under the
# name `verify`. Keep the two in sync by hand (a word box is four floats, a band two ints); if they drift, the
# boxes and bands exchanged with verify.py stop meaning the same thing.
Box = tuple[float, float, float, float]            # x0, y0, x1, y1
Band = tuple[int, int]                             # first, last pixel row of a run


# BOUNDARY_RATIO is a LOCATOR, not a grade. It answers "is this white run tall
# enough to be a section boundary rather than a line gap", which is all that
# `boundary_ink` and the hole check need from it, and it is the only job the
# number survives.
#
# It used to also FAIL a page whose tallest run fell under it. That is gone,
# measured out on 2026-09-13 over the 30 rendered pages of the 29-deliverable
# corpus, with the current instrument (scripts/measure_fill.py, `gaps`):
#
#   max-gap / median-gap, all 30 pages, sorted:
#     1.89 2.00 2.00 2.12 2.15 2.21 2.27 2.31 2.38 2.40 2.56 2.62 2.73 2.78
#     2.86 2.86 2.90 3.00 3.25 3.29 3.50 3.57 3.60 3.60 3.86 4.00 4.17 5.00
#     5.14 5.14
#
# One continuum, no void anywhere: the widest step in the whole range is 0.83
# (4.17 → 5.00) and the rest are 0.01-0.4. A floor placed in it is a curve
# fitted to the corpus, which is exactly what 2.0 was — it sat one hundredth
# under two deliverables and failed a third at 1.89.
#
# Two further measurements say the statistic is not measuring separation at
# all, so no value would have worked:
#   * A synthetic page whose section gap EQUALS its line gap — no section
#     separation whatsoever — scores 2.69, above 10 of the 30 real pages,
#     which do separate. The ranking is inverted, not merely noisy.
#   * `max` is one run and `median` is a small set of quantized small
#     integers, so the ratio is noise at ±0.3: excluding the header block at
#     8 / 10 / 12 / 15% of the text span moves swiss-grid/resume through
#     1.70, 1.89, 2.00, 1.78 non-monotonically, and the 12% cut stacks five
#     deliverables on exactly 2.00. Taking the mean of the top 5 runs instead
#     of the max smooths it and still yields a continuum (1.64 … 4.91).
# Same conclusion as d7f67da reached for page-wide ink: the number is a
# prefilter, the verdict comes from LOCATION (boundary_ink), and the white
# ratio is reported, never failed.
BOUNDARY_RATIO = 2.0


# Rows whose longest dark run OUTSIDE every word box reaches this share of
# page width are furniture (a tick, a side bar) rather than a word's own
# ink. Measured plateau, not a fitted curve: the signal is identical from
# 0.01 to 0.03; below 0.005 contact icons and list bullets start appearing as
# "devices". The old detector's RULE_FLOOR needed to be 0.04 to separate a
# device from RAW TEXT on the same scan; this floor only has to separate a
# device from the residue text leaves after its own word boxes are
# subtracted, which is a much smaller gap to clear.
FURNITURE_FLOOR = 0.02
FURNITURE_PPI = 90                       # raster resolution of the furniture scan
FURNITURE_SCALE = FURNITURE_PPI / 72.0   # pdftotext boxes are in PDF points
FURNITURE_PAD = 1.0                      # pt padding so antialiasing at a
                                         # glyph's edge doesn't read as ink


def furniture_ink(png: str, boxes: Sequence[Box] | None) -> list[Band]:
    """Ink bands (start, end) that fall OUTSIDE every word box on the page.

    Interval arithmetic, not a per-pixel coverage mask: each row's covering
    boxes are merged into a handful of intervals, and only the GAPS between
    them are ever scanned pixel-by-pixel. A text-heavy row is almost entirely
    covered, so this looks at a sliver of it instead of the whole width.
    """
    if not boxes:
        return []
    im = Image.open(png).convert("L")
    w, h = im.size
    px: Any = im.load()
    sc = FURNITURE_SCALE
    cov: list[list[tuple[int, int]]] = [[] for _ in range(h)]
    for x0, y0, x1, y1 in boxes:
        ya = max(0, int((y0 - FURNITURE_PAD) * sc))
        yb = min(h - 1, int((y1 + FURNITURE_PAD) * sc))
        xa = max(0, int((x0 - FURNITURE_PAD) * sc))
        xb = min(w, int((x1 + FURNITURE_PAD) * sc) + 1)
        for y in range(ya, yb + 1):
            cov[y].append((xa, xb))

    def uncovered_dark_run(y: int) -> int:
        merged: list[tuple[int, int]] = []
        for a, b in sorted(cov[y]):
            if merged and a <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], b))
            else:
                merged.append((a, b))
        gaps, prev = [], 0
        for a, b in merged:
            if a > prev:
                gaps.append((prev, a))
            prev = max(prev, b)
        if prev < w:
            gaps.append((prev, w))
        best = run = 0
        for gs, ge in gaps:
            run = 0
            for x in range(gs, ge):
                if px[x, y] < 200:
                    run += 1
                    best = max(best, run)
                else:
                    run = 0
        return best

    rows = [uncovered_dark_run(y) / w for y in range(h)]
    bands: list[tuple[int, int]] = []
    cur: list[int] | None = None
    for y, r in enumerate(rows):
        if r >= FURNITURE_FLOOR:
            cur = [y, y] if cur is None else [cur[0], y]
        elif cur:
            bands.append((cur[0], cur[1]))
            cur = None
    if cur:
        bands.append((cur[0], cur[1]))
    return bands


def boundary_ink(white: list[Band], ink: list[Band], med: float) -> list[Band]:
    """The ink bands that sit AT a section boundary, not just anywhere.

    "Longest dark run on the page" cannot tell a rule from an underline: a
    `#show link: underline` on the contact line scores 21.8% of page width and
    a two-column table rule 86.4%, both wider than three of the corpus's real
    devices, while those devices sit at 5.65-7.61%. The clusters overlap
    INVERTED, so no threshold can separate them. Location can: there is no text
    inside a boundary, so ink found there is furniture by construction.

    A device at a boundary shows up four ways, all covered by the same sum:
    it caps the gap (white above it, text below), it sits under the gap, it
    SPLITS the gap in two, or it lies WHOLLY INSIDE it — the last one because
    the two scans read different thresholds: `keyline-corporate`'s 0.6pt `soft`
    hairline is too pale to count as dark for the white scan, so its rows stay
    inside the white run while still spanning 100% of the measure. So walk out
    from the band through whatever white touches or contains it, and ask whether
    that span reads as a boundary by the BOUNDARY_RATIO the white scan already
    uses. A thick band clears it on its own thickness, which is right: a
    knockout slab IS the boundary.
    """
    def span(a: int, b: int) -> int:
        up = next((a - x for x, y in white if x <= a <= y), 0)
        dn = next((y - b for x, y in white if x <= b <= y), 0)
        return up + (b - a) + dn

    return [(a, b) for a, b in ink if span(a, b) >= BOUNDARY_RATIO * med]


# How tall a white run must be, in median gaps, to count as the BOUNDARY a
# furniture band sits at. BOUNDARY_RATIO (2.0) cannot be reused here: it
# grades a SPAN (white above + band + white below), and a band typeset on the
# heading's own line only ever touches the white ABOVE it — the heading text
# is below, so the run under it is an ordinary line gap or nothing.
# Measured 2026-09-13 over the 14 families' `resume.typ`: tallest white run
# within `med` of each furniture band, in med units, two clusters —
#   AT a boundary (color-band, editorial-serif, engraved-card, margin-index,
#     quiet-luxury, swiss-grid, avant-poster): 1.54 1.60 1.73 1.73 1.73 1.73
#     1.73 1.73 1.86 1.86 2.00 …(11 more)… 2.86 3.00 3.14 3.29 4.71 4.86 5.14
#   inside a section (hard-edge's and avant-poster's link underlines): 0.00
#     0.00 0.40
# A void from 0.40 to 1.54 with nothing in it; 1.2 sits inside it, far from
# both edges. The proximity tolerance is `med` itself — one line height, what
# separates a band on the heading line from the gap above it.
BOUNDARY_ADJACENT = 1.2


def near_boundary(band: Band, white: list[Band], med: float) -> bool:
    """True when a FURNITURE band sits AT a section boundary.

    `boundary_ink`'s `span` cannot be reused here, and applying it would
    delete every band this detector exists to find: a tick or side bar
    typeset ON the heading's own line is not INSIDE any white run — the row
    carries text — so `up` and `dn` are both 0 and the span collapses to the
    band's own thickness. Furniture needs PROXIMITY, not containment: the
    band counts when it touches, or comes within one median gap of, a white
    run tall enough to be a boundary rather than a line gap.

    Without this the union was position-blind on the furniture half: a page
    with NO device at all but four underlined links mid-section satisfied
    DEVICE_QUORUM while the message claimed the bands sat "AT a section
    boundary".
    """
    a, b = band
    for x, y in white:
        near = y >= a - med and x <= b + med
        if near and (y - x) >= BOUNDARY_ADJACENT * med:
            return True
    return False


# sRGB channel value (0-255) to linear light, the table behind WCAG relative luminance.
_LIN = [((c / 255) / 12.92 if c / 255 <= 0.04045 else (((c / 255) + 0.055) / 1.055) ** 2.4)
        for c in range(256)]


def _lum(rgb: Sequence[int]) -> float:
    """WCAG relative luminance of an sRGB colour: 0 for black, 1 for white."""
    return 0.2126 * _LIN[rgb[0]] + 0.7152 * _LIN[rgb[1]] + 0.0722 * _LIN[rgb[2]]


# Tunables of crop_candidates and of the crops cut from its boxes. Sizes ending in `_IN` are inches, pixel counts
# are at CROP_SCAN_PPI. Where a value has no comment of its own, no calibration is recorded for it.
CROP_PPI = 300             # crops are cut from their own 300 ppi render (the page PNGs stay at --ppi)
CROP_SCAN_PPI = 150       # band detection scans the same 150 ppi raster the hidden-text gate uses (verify.py's HIDDEN_PPI)
CROP_DELTA = 24           # a pixel is non-background when any channel differs this much from the page's modal colour
CROP_ERODE = 9            # px at 150 ppi: strokes and glyph ink vanish, a solid aplat survives
CROP_FILL_MIN_IN = (0.5, 0.1)   # smallest aplat worth a look (inches, w x h)
CROP_ICON_MIN_IN = 0.08   # the ink of a mark smaller than this (a bullet dot, a speck) is not a glyph
CROP_ICON_MAX_IN = 0.45   # larger than this and it is a rule or a block, not an icon
CROP_ICON_GAP_IN = 0.01   # ink closer than this to a word box on its line is part of the text (glyph piece); the one no-break
                          # space between a mark and its value is 0.02 in, so a real mark clears it
CROP_ICON_SOLID = 0.85    # ink filling more of its box than this is a solid chip or square bullet, not a drawing...
CROP_ICON_CHIP = 0.97     # ...unless it has text beside it and is not a pure block: a drawn solid mark (a filled mail or phone, the LinkedIn square with its letters knocked out) fills 0.85-0.95 of its box, a bullet square or chip fills all of it
CROP_ICON_TEXT_IN = 0.12  # a mark this close to a word on its line sits beside its value (ranks first when the cap bites)
CROP_ICON_BLOCK = (1.3, 2.0)   # a pure block with text beside it passes when its proportions are neither a square nor a bar (a solid phone)
CROP_ICON_PEER_IN = 0.5   # a mark with another mark this close on its line, no text between, is one of a row (social links)
CROP_ICON_RANK = 10**6    # added to the score of a mark beside its value, so it outranks any loose ink when the cap bites
CROP_REPEAT = 3           # the same shape this many times on a page is a decoration (heading square, divider, bullet), not a mark
CROP_EDGE_SHARE = 0.9     # one colour covering this share of a ring inside the page is the paper, whatever else the page holds
CROP_RING_INSET = (0.02, 0.05)   # the rings sampled besides the one 4 px from the edge, as shares of the short side
CROP_FRAME_FILL = 0.35    # a 'fill' spanning the page whose solid core covers less than this is a frame stroke, not an aplat
CROP_ICON_ASPECT = 3.0    # longer than this many times its short side: a rule or a stem, not an icon
CROP_WHITE_PAPER = 0.2    # white covering this share of the page makes white the background, not the modal colour
CROP_PAD_IN = 0.08        # context around every crop
CROP_CAP = 8              # crops per page; fills first, then icons, both in reading order


def _components(grid: Image.Image, merge: int = 0) -> list[tuple[int, int, int, int]]:
    """8-connected blobs of the non-zero cells of a small 'L' grid, as (x0, y0, x1, y1) cell
    boxes (inclusive); `merge` cells of dilation first so a glyph's parts read as one blob."""
    if merge:
        grid = grid.filter(ImageFilter.MaxFilter(2 * merge + 1))
    gw, gh = grid.size
    on = grid.point(lambda v: 255 if v > 0 else 0).tobytes()
    seen = bytearray(gw * gh)
    boxes = []
    for start in range(gw * gh):
        if not on[start] or seen[start]:
            continue
        stack, seen[start] = [start], 1
        x0 = x1 = start % gw
        y0 = y1 = start // gw
        while stack:
            i = stack.pop()
            x, y = i % gw, i // gw
            x0, x1, y0, y1 = min(x0, x), max(x1, x), min(y0, y), max(y1, y)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < gw and 0 <= ny < gh and on[ny * gw + nx] and not seen[ny * gw + nx]:
                        seen[ny * gw + nx] = 1
                        stack.append(ny * gw + nx)
        boxes.append((x0, y0, x1, y1))
    return boxes


def crop_candidates(im: Image.Image, words: Sequence[Box] | None) -> list[tuple[str, tuple[int, int, int, int], int]]:
    """[(kind, (x0, y0, x1, y1) px of `im`, score), ...] in reading order: kind 'fill' (a solid colour
    band that text or marks sit on) or 'icon' (a small vector mark outside every word box). The score
    is the ink pixel count (what ranks icons when the per-page cap bites; a fill scores its area; a mark
    beside its value, within CROP_ICON_TEXT_IN of a word on its line, ranks above any other).
    Raster pass on the CROP_SCAN_PPI render: none of the gates keeps regions (the hidden-text gate
    only reads the colour behind each word box), so what is reused is its raster and its word
    boxes; `words` None (no word boxes) skips icons rather than calling every glyph an icon.
    Background: the colour that fills CROP_EDGE_SHARE of the innermost uniform ring (the edge, then 2% and
    5% in: a frame at the page edge does not become the paper, a dark page under a white card keeps its
    own colour), else white when white covers CROP_WHITE_PAPER of the page (a >50%
    sidebar must not become the 'paper'), else the modal colour (a tinted or dark page)."""
    im = im.convert("RGB")
    w, h = im.size
    colours = im.getcolors(maxcolors=w * h) or [(1, (255, 255, 255))]
    white = sum(n for n, c in colours if min(cast(tuple[int, ...], c)) >= 250)
    m = min(4, w // 4, h // 4)          # 4 px inside: poppler leaves a white last row and column on some page sizes
    bg: tuple[int, ...] | None = None
    for inset in sorted({m, round(CROP_RING_INSET[0] * min(w, h)), round(CROP_RING_INSET[1] * min(w, h))}, reverse=True):
        # The paper is what the innermost uniform ring shows: a frame stroked at the page edge colours
        # the outer rings, the paper lies inside it; a dark page keeps its colour under a white card
        # further in than the rings; a sidebar or a header band leaves every ring mixed.
        inset = min(inset, w // 4, h // 4)
        ring: Counter[Any] = Counter()
        for strip in ((0, inset, w, inset + 1), (0, h - inset - 1, w, h - inset), (inset, 0, inset + 1, h), (w - inset - 1, 0, w - inset, h)):
            for n, c in im.crop(strip).getcolors(maxcolors=w * h) or []:
                ring[c] += n
        top, top_n = ring.most_common(1)[0]
        if top_n >= CROP_EDGE_SHARE * sum(ring.values()):
            bg = cast(tuple[int, ...], top)
            break
    if bg is None:
        if white >= CROP_WHITE_PAPER * w * h:
            bg = (255, 255, 255)        # a >50% sidebar must not become the 'paper'
        else:
            bg = cast(tuple[int, ...], max(colours)[1])
    ink = ImageChops.difference(im, Image.new("RGB", im.size, bg)).convert("L").point(
        lambda v: 255 if v >= CROP_DELTA else 0)
    k = CROP_SCAN_PPI
    e = CROP_ERODE // 2
    fills: list[tuple[str, tuple[int, int, int, int], int]] = []
    solid = ink.filter(ImageFilter.MinFilter(CROP_ERODE))
    for x0, y0, x1, y1 in _components(solid.reduce(3).point(lambda v: 255 if v > 64 else 0)):
        box = (max(0, x0 * 3 - e), max(0, y0 * 3 - e), min(w, x1 * 3 + 3 + e), min(h, y1 * 3 + 3 + e))
        if box[2] - box[0] >= CROP_FILL_MIN_IN[0] * k and box[3] - box[1] >= CROP_FILL_MIN_IN[1] * k:
            area = (box[2] - box[0]) * (box[3] - box[1])
            if box[2] - box[0] >= 0.8 * w and box[3] - box[1] >= 0.8 * h and \
                    sum(1 for v in solid.crop(box).tobytes() if v) < CROP_FRAME_FILL * area:
                continue        # a frame stroked around the page, not a fill
            fills.append(("fill", box, area))
    icons: list[tuple[str, tuple[int, int, int, int], int]] = []
    if words is not None:
        rest = ink.copy()
        d = ImageDraw.Draw(rest)
        pt = k / 72.0
        wpx = [(wx0 * pt, wy0 * pt, wx1 * pt, wy1 * pt) for wx0, wy0, wx1, wy1 in words]
        for wx0, wy0, wx1, wy1 in words:
            d.rectangle((int((wx0 - 1) * pt), int((wy0 - 1) * pt), int((wx1 + 1) * pt) + 1, int((wy1 + 1) * pt) + 1), fill=0)
        for _, fb, _ in fills:
            d.rectangle(fb, fill=0)
        # Decorations repeat: the same shape (size, ink) CROP_REPEAT times on a page is a heading square,
        # a divider or a bullet, and goes before the marks are merged (a square above a phone glyph must
        # not fuse with it). A contact mark never repeats: each of pin, phone, mail, web has its own shape.
        parts = []
        for x0, y0, x1, y1 in _components(rest.reduce(3)):
            box = (x0 * 3, y0 * 3, min(w, x1 * 3 + 3), min(h, y1 * 3 + 3))
            tight = rest.crop(box).getbbox()
            if tight is not None:
                parts.append((box, tight[2] - tight[0], tight[3] - tight[1],
                              sum(1 for v in rest.crop(box).tobytes() if v)))
        for box, tw, th, n in parts:
            twins = sum(1 for _, w2, h2, n2 in parts if abs(w2 - tw) <= 1 and abs(h2 - th) <= 1 and abs(n2 - n) <= 0.15 * max(n, n2))
            if twins >= CROP_REPEAT:
                d.rectangle((box[0], box[1], box[2] - 1, box[3] - 1), fill=0)
        marks: list[tuple[tuple[int, int, int, int], tuple[int, int, int, int], int]] = []
        for x0, y0, x1, y1 in _components(rest.reduce(3), merge=1):
            bw, bh = (x1 - x0 + 1) * 3, (y1 - y0 + 1) * 3
            if not (CROP_ICON_MIN_IN * k <= max(bw, bh) <= CROP_ICON_MAX_IN * k and min(bw, bh) >= CROP_ICON_MIN_IN * k / 2):
                continue
            box = (x0 * 3, y0 * 3, min(w, x1 * 3 + 3), min(h, y1 * 3 + 3))
            tight = rest.crop(box).getbbox()      # the ink itself, without the blob's dilation margin
            if tight is None:
                continue
            n = sum(1 for v in rest.crop(box).tobytes() if v)
            ink_box = (box[0] + tight[0], box[1] + tight[1], box[0] + tight[2], box[1] + tight[3])
            marks.append((box, ink_box, n))
        for box, (tx0, ty0, tx1, ty1), n in marks:
            tw, th = tx1 - tx0, ty1 - ty0
            if max(tw, th) < CROP_ICON_MIN_IN * k or max(tw, th) > CROP_ICON_ASPECT * min(tw, th):
                continue        # a speck, a bullet dot, a rule or a stem
            beside = [wx0 - tx1 if wx0 >= tx1 else tx0 - wx1 for wx0, wy0, wx1, wy1 in wpx
                      if wy0 < ty1 and wy1 > ty0 and max(wx0 - tx1, tx0 - wx1, 0) < CROP_ICON_TEXT_IN * k]
            # a row of marks with no text (social links): the neighbours on its line vouch for it, as a word would
            peers = any(o[1] < ty1 and o[3] > ty0 and max(o[0] - tx1, tx0 - o[2], 0) < CROP_ICON_PEER_IN * k
                        for _, o, _ in marks if o != (tx0, ty0, tx1, ty1))
            if n > CROP_ICON_SOLID * tw * th and not ((beside or peers) and (n <= CROP_ICON_CHIP * tw * th or (beside and CROP_ICON_BLOCK[0] * min(tw, th) < max(tw, th) <= CROP_ICON_BLOCK[1] * min(tw, th)))):
                continue        # a solid square or chip (bullet marker, white-on-black letter)
            if any(wy0 < ty1 and wy1 > ty0 and max(wx0 - tx1, tx0 - wx1, 0) < CROP_ICON_GAP_IN * k
                   for wx0, wy0, wx1, wy1 in wpx):
                continue        # touching a word on its line: a glyph piece, not a mark of its own
            icons.append(("icon", box, n + (CROP_ICON_RANK if beside else 0)))
    return sorted(fills + icons, key=lambda b: (b[1][1], b[1][0]))


def crop_bands(im: Image.Image, words: Sequence[Box] | None) -> list[tuple[str, tuple[int, int, int, int]]]:
    """crop_candidates without the score: [(kind, (x0, y0, x1, y1)), ...] in reading order."""
    return [(kind, box) for kind, box, _ in crop_candidates(im, words)]


# Constants of the ink-gap measurement (the x-height band of each text line, in verify.py's _page_ink_gap).
INK_DPI = 300
INK_DELTA = 60          # a pixel counts as ink when it differs this much from the background
RULE_PT = 10.0          # an ink run this long in one pixel row is a rule / band / underline, not glyphs


def _row_stats(data: bytes, w: int, r: int, tbl: bytes) -> tuple[int, int]:
    """(ink pixels, longest contiguous ink run) of pixel row r of a w-wide crop."""
    s = data[r * w:(r + 1) * w].translate(tbl)
    n = s.count(b"\x01")
    return n, (max(map(len, s.split(b"\x00"))) if n else 0)


def _xheight_band(prof: list[int]) -> tuple[int, int] | None:
    """(top, bottom) row indexes of the dense x-height band of a text line from
    its ink row profile (None when there is no ink; a negative row is a rule row, skipped:
    an em dash is a 10 pt run too, and counting it as an empty row cut a bullet's band in
    two on pdfium's raster, 9 px off poppler's). Ascender, cap-overshoot and
    descender rows are sparse (only the letters that have them), the x-height band
    is dense (every letter), so the band is the stretch of rows that is mostly
    above half the peak density (maximum-sum run of prof - level): a line
    "across our users." with no ascender or descender gets the same band as one
    full of them, which is what makes the measured gap depend on the layout and
    not on the words."""
    nz = sorted(v for v in prof if v > 0)
    if not nz:
        return None
    peak = nz[int(0.9 * (len(nz) - 1))]          # robust: one hairline row must not set the level
    lvl = 0.5 * peak
    bi: tuple[int, int] | None
    best, cur, start, bi = 0.0, 0.0, 0, None
    for i, v in enumerate(prof):
        if v < 0:
            continue                       # a rule row (an em dash, an underline) neither adds nor costs
        if cur <= 0:
            cur, start = 0.0, i
        cur += v - lvl
        if cur > best:
            best, bi = cur, (start, i)
    return bi
