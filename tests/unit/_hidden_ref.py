"""Reference oracles for tests: `vitae.verify.text.hidden_word_stats` (a `_lum` per distinct colour of every word box) and
the text-run scan of `_text_runs` / `check_hidden_text` as they were before the per-page luminance table and the linear
passes. Kept verbatim so the equivalence tests compare the fast versions with the behaviour they replaced."""
from __future__ import annotations

import re
from collections.abc import Callable

from PIL import Image
from vitae.core.base import HIDDEN_PPI, HiddenStat, WordBox
from vitae.core.colour import rel_luminance as _lum
from vitae.core.pixels import colour_counts
from vitae.verify.pdf import _bbox_pages
from vitae.verify.text import HIDDEN_PAD_PX


def hidden_word_stats_per_colour(pdf: str, pages: list[tuple[float, float, list[WordBox]]] | None = None,
                      pngs: list[str] | None = None) -> list[HiddenStat]:
    """[(page_no, word, (x0, y0, x1, y1), height_pt, contrast | None, off_page)] for
    every extracted word that carries a letter or digit.

    contrast: the WCAG contrast ratio between the box's own background (its most common
    colour) and the strongest pixel anywhere in the box (+1 px), at HIDDEN_PPI, either
    direction (dark ink on light, light ink on dark). White text on white paper, text in
    the band's colour, text under an opaque shape: a flat box, ratio 1.0. None when no
    raster is available."""
    pages = _bbox_pages(pdf) if pages is None else pages
    out: list[HiddenStat] = []
    sc = HIDDEN_PPI / 72.0
    for pno, (pw, ph, items) in enumerate(pages or [], 1):
        im: Image.Image | None = None
        if pngs and pno - 1 < len(pngs):
            im = Image.open(pngs[pno - 1]).convert("RGB")
        for (x0, y0, x1, y1), word in items:
            if not re.search(r"[^\W_]", word):
                continue   # separators, bullets, rule glyphs: visible or meaningless either way
            # poppler drops chars past the page edge, so a word that crosses it is cut
            # short, and its box then ends just past the edge: any overshoot is off-page
            off = bool(x0 < -0.01 or y0 < -0.01 or (pw and x1 > pw + 0.01) or (ph and y1 > ph + 0.01))
            ratio = None
            if im is not None:
                xa, ya = int(x0 * sc) - HIDDEN_PAD_PX, int(y0 * sc) - HIDDEN_PAD_PX
                xb, yb = int(x1 * sc) + 1 + HIDDEN_PAD_PX, int(y1 * sc) + 1 + HIDDEN_PAD_PX
                xa, ya, xb, yb = max(xa, 0), max(ya, 0), min(xb, im.width), min(yb, im.height)
                if xb > xa and yb > ya:
                    cols = colour_counts(im.crop((xa, ya, xb, yb)), (xb - xa) * (yb - ya))
                    lb = _lum(max(cols)[1])
                    ratio = 1.0
                    for _, col in cols:
                        lc = _lum(col)
                        ratio = max(ratio, (max(lc, lb) + 0.05) / (min(lc, lb) + 0.05))
                elif not off:
                    ratio = 1.0   # the whole box rounds to nothing: no ink can be there
            out.append((pno, word, (x0, y0, x1, y1), y1 - y0, ratio, off))
    return out


def classify_runs_quadratic(runs: list[tuple[str, float, float, float]], box: tuple[float, float, float, float]
                            ) -> tuple[list[str], list[tuple[str, float]]]:
    """The off-page and tiny-run loop of `_text_runs` for one page, with its neighbour walk and its string `+`."""
    x0, y0, x1, y1 = box
    off: list[str] = []
    tiny: list[tuple[str, float, int]] = []

    def script_of(i: int) -> bool:
        _t, x, y, sz = runs[i]
        for step in (-1, 1):
            j = i + step
            while 0 <= j < len(runs) and runs[j][3] < 1.15 * sz and abs(runs[j][2] - y) < 0.5:
                j += step
            if 0 <= j < len(runs):
                _, xn, yn, szn = runs[j]
                if (szn >= 1.15 * sz and 0.05 * szn < abs(yn - y) < 0.6 * szn
                        and (x >= xn if step < 0 else xn >= x)):
                    return True
        return False
    for i, (t, x, y, sz) in enumerate(runs):
        if x < x0 - 0.5 or x > x1 + 0.5 or y < y0 - 0.5 or y > y1 + 0.5:
            off.append(t)
        elif 0 < sz < 5.0 and not script_of(i):
            if tiny and tiny[-1][2] == i - 1:
                tiny[-1] = (tiny[-1][0] + " " + t, min(tiny[-1][1], sz), i)
            else:
                tiny.append((t, sz, i))
    return off, [(t, sz) for t, sz, _ in tiny]


def merged_runs_concat(stats: list[HiddenStat], pick: Callable[[HiddenStat], object]) -> list[tuple[int, str]]:
    """The `runs` closure of `check_hidden_text`: the run text grown by `+`."""
    found: list[tuple[int, str]] = []
    prev: int | None = None
    for i, st in enumerate(stats):
        if pick(st):
            if prev is not None and i == prev + 1 and found[-1][0] == st[0]:
                found[-1] = (st[0], found[-1][1] + " " + st[1])
            else:
                found.append((st[0], st[1]))
            prev = i
    return found
