"""Reference oracles for tests: `vitae.verify.layout.check_text_clip` and `vitae.fill.bands` as they were before Pillow
did the pixel counting (a Python loop over every pixel of a word box, over every row of the page). Kept verbatim so the
equivalence tests compare the fast versions with the behaviour they replaced."""
from __future__ import annotations

from collections.abc import Callable, Sequence

from PIL import Image
from vitae.core.base import WordBox
from vitae.core.pixels import gray_pixels
from vitae.fill import RULE_CONTRAST, RULE_FLOOR
from vitae.verify.page import FURNITURE_SCALE


class RgbPixels:
    """`px[x, y]` of an "RGB" image: its (r, g, b)."""
    __slots__ = ("_data", "_h", "_w")

    def __init__(self, im: Image.Image) -> None:
        if im.mode != "RGB":
            raise ValueError(f'RgbPixels needs an "RGB" image, got {im.mode!r}')
        self._w, self._h = im.size
        self._data = im.tobytes()

    def __getitem__(self, xy: tuple[int, int]) -> tuple[int, int, int]:
        x, y = xy
        if not (0 <= x < self._w and 0 <= y < self._h):
            raise IndexError("image index out of range")
        i = 3 * (y * self._w + x)
        d = self._data
        return d[i], d[i + 1], d[i + 2]


def check_text_clip_per_pixel(png: str, boxes: Sequence[WordBox] | None) -> list[str]:  # noqa: C901 (verbatim copy of the replaced code)
    """List of FAIL messages for text a filled region hides or cuts (a header
    band shorter than its own text; white-on-colour text that runs past the
    band onto white paper). Text parsers still read such a line, so no other
    gate sees it. `boxes` is this page's [((x0,y0,x1,y1), word)] list
    (`word_boxes(pdf, with_text=True)`). Two signals:

    1. CUT: a word whose box straddles a fill edge. The background just left AND
       just right of the box must both step by a large luminance jump at the same
       row, strictly inside the middle half of the box. A step counts only if it
       PERSISTS (flat for 3px on each side): a hairline rule flanking the word
       (grid(1fr, auto, 1fr) with `line`) is a stroke, not a fill, and is not flat.
    2. HIDDEN: a word whose box holds a single flat colour — text colour ~ the
       background under it (white text left on white paper past a short band).
    """
    if not boxes:
        return []
    im = Image.open(png).convert("RGB")
    lum = im.convert("L")
    w, h = im.size
    px = gray_pixels(lum)
    rgb = RgbPixels(im)
    s = FURNITURE_SCALE
    found: list[tuple[str, int, str]] = []   # (kind, line-row, word) — folded into one FAIL per line below

    def column_edges(x: float, ya: int, yb: int) -> list[int]:
        x = min(max(int(x), 0), w - 1)
        edges: list[int] = []
        # 3px above and 3px below at 90 ppi (~2.4pt each): a filled band is flat (spread <=30 luma) on both
        # sides and steps by >60 luma across its edge; a 1-2px hairline rule is not flat over 3px.
        for y in range(max(ya, 3), min(yb, h - 3) + 1):
            above = [px[x, y - k] for k in (3, 2, 1)]
            below = [px[x, y + k] for k in (0, 1, 2)]
            if max(above) - min(above) > 30 or max(below) - min(below) > 30:
                continue   # not flat on both sides: a stroke / glyph edge, not a fill
            if abs(sum(above) / 3 - sum(below) / 3) > 60:
                edges.append(y)
        return edges

    for (x0, y0, x1, y1), word in boxes:
        ya, yb = int(y0 * s), min(int(y1 * s), h - 1)
        xa, xb = max(int(x0 * s), 0), min(int(x1 * s), w - 1)
        if yb - ya < 6 or xb - xa < 3 or len(word) < 2:
            continue   # lone punctuation sits between neighbours' glyph edges: noise
        region = [rgb[x, y] for y in range(ya, yb + 1) for x in range(xa, xb + 1)]
        base = max(set(region), key=region.count)
        # <40 RGB delta across the whole word box: no visible glyph contrast against the box modal colour
        if max(max(abs(c - b) for c, b in zip(p, base)) for p in region) < 40:
            found.append(("hidden", ya, word))
            continue
        lo, hi = ya + (yb - ya) * 0.25, yb - (yb - ya) * 0.25
        left = [y for y in column_edges(x0 * s - 2, ya, yb) if lo <= y <= hi]
        right = [y for y in column_edges(x1 * s + 2, ya, yb) if lo <= y <= hi]
        if any(abs(a - b) <= 2 for a in left for b in right):
            found.append(("cut", ya, word))
    out = []
    for kind in ("cut", "hidden"):
        lines: list[tuple[int, list[str]]] = []   # words of one kind, grouped by text line (rows within 4px)
        for _, row, word in sorted(f for f in found if f[0] == kind):
            if lines and row - lines[-1][0] <= 4:
                lines[-1][1].append(word)
            else:
                lines.append((row, [word]))
        for row, words in lines:
            first = " ".join(words[:4]) + (" …" if len(words) > 4 else "")
            if kind == "cut":
                out.append(f'text line at y~{row / s:.0f}pt ({len(words)} word(s): "{first}") is cut by '
                           "the edge of a filled region (header band / bar shorter than its "
                           "content?) — grow the container with its text (lib.typ masthead), "
                           "never a fixed height")
            else:
                out.append(f'text line at y~{row / s:.0f}pt ({len(words)} word(s): "{first}") is '
                           "indistinguishable from its background (clipped band, white-on-white "
                           "or too pale) — it extracts fine but a reader cannot see it")
    return out


def bands_per_row(path: str, thr: int = 150, rule: float = RULE_FLOOR,
          contrast: int = RULE_CONTRAST) -> tuple[int, list[tuple[int, int]], list[tuple[int, int]]]:
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
    body = im.point([255 if v < thr else 0 for v in range(256)]).tobytes()
    dev = im.point([255 if v < paper - contrast else 0 for v in range(256)]).tobytes()
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

    def runs_of(pred: Callable[[int], bool]) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []
        start: int | None = None
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
