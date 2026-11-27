"""Optical line gap measured on a 300 dpi raster of the PDF (the measure group proximity is judged on)."""
from __future__ import annotations

import os
import subprocess
import tempfile

from PIL import Image

from vitae.core.base import GapFn, LineBox
from vitae.core.env import pdf_backend
from vitae.verify.page import INK_DELTA, INK_DPI, RULE_PT, row_stats, xheight_band
from vitae.verify.pdf import pdfium_render

_K = INK_DPI / 72.0     # pixels per point


def _render_page(pdf: str, page: int) -> Image.Image | None:
    """Page `page` of `pdf` as a 300 dpi gray raster, or None when it cannot be rendered."""
    try:
        if pdf_backend() == "pdfium":
            return pdfium_render(pdf, INK_DPI, gray=True, pages=[page])[0]
        # a 300 dpi page raster is ~9 MB: one scoped temp dir per page, removed even on a crash
        with tempfile.TemporaryDirectory(prefix="vitae-prox-") as d:
            pre = os.path.join(d, f"p{page}")
            r = subprocess.run(["pdftoppm", "-r", str(INK_DPI), "-gray", "-singlefile",
                                "-f", str(page), "-l", str(page), pdf, pre],
                               capture_output=True, check=False)
            if r.returncode == 0:
                gray = Image.open(pre + ".pgm").convert("L")
                gray.load()
                return gray
    except (OSError, ValueError, RuntimeError):
        pass
    return None


def _dominant_tone(im: Image.Image) -> int:
    """The most frequent gray value of an image."""
    hp = im.histogram()
    return max(range(256), key=hp.__getitem__)


def _tone_table(bg: int) -> bytes:
    """Translate table: 1 for a gray value that differs from `bg` by more than INK_DELTA (ink), else 0."""
    return bytes(1 if abs(v - bg) > INK_DELTA else 0 for v in range(256))


def _fill_band(im: Image.Image, box: tuple[int, int, int, int], lbg: int) -> tuple[int, int] | None:
    """(top, bottom) pixel rows of the fill (background tone `lbg`) the line in `box` = (xa, xb, ya, yb)
    sits on, found on a strip just left / right of the text; None when no band round the line."""
    xa, xb, ya, yb = box
    # line on a filled band (or field): its optical extent is the fill's rows
    m = int(3 * _K)
    for sx in ((max(xa - m, 0), max(xa - 1, 0)), (min(xb + 1, im.width), min(xb + m, im.width))):
        if sx[1] - sx[0] < 2:
            continue
        strip = im.crop((sx[0], 0, sx[1], im.height))
        sd, sw = strip.tobytes(), strip.width
        stb = bytes(1 if abs(v - lbg) <= INK_DELTA else 0 for v in range(256))

        def full(r: int, sd: bytes = sd, sw: int = sw, stb: bytes = stb) -> bool:
            return sd[r * sw:(r + 1) * sw].translate(stb).count(b"\x01") >= 0.9 * sw

        c = (ya + yb) // 2
        if not full(c):
            continue
        t = b = c
        while t > 0 and full(t - 1):
            t -= 1
        while b < im.height - 1 and full(b + 1):
            b += 1
        # <=3x the text line height: a title bar/pill around the line, whereas a sidebar or page fill is much taller.
        if b - t + 1 <= 3 * (yb - ya):       # a band round the line, not a page-high field
            return (t, b)
    return None


def _glyph_band(reg: Image.Image, lbg: int) -> tuple[int, int] | None:
    """(top, base) rows, relative to `reg`, of the x-height band of the ink on background `lbg`."""
    tbl = _tone_table(lbg)
    data, w = reg.tobytes(), reg.width
    prof: list[int] = []
    for r in range(reg.height):
        n, run = row_stats(data, w, r, tbl)
        prof.append(-1 if run >= RULE_PT * _K else n)    # underline / rule rows are not glyphs
    bd = xheight_band(prof)
    return (bd[0], bd[1]) if bd and bd[1] - bd[0] >= 2 else None


def _line_rows(im: Image.Image, page_bg: int, ln: LineBox) -> tuple[int, int] | None:
    """(top, base) pixel rows of one text line: x-height band of its ink, or the edges of the fill it sits on."""
    ya, yb = max(int(ln[2] * _K), 0), min(int(ln[3] * _K) + 1, im.height)
    xa, xb = max(int(ln[0] * _K), 0), min(int(ln[1] * _K) + 1, im.width)
    if not (yb - ya >= 3 and xb > xa):
        return None
    reg = im.crop((xa, ya, xb, yb))
    lbg = _dominant_tone(reg)
    if abs(lbg - page_bg) > INK_DELTA:
        band = _fill_band(im, (xa, xb, ya, yb), lbg)
        if band is not None:
            return band
    bd = _glyph_band(reg, lbg)
    return (ya + bd[0], ya + bd[1]) if bd else None


def _split_gap(im: Image.Image, page_bg: int, up: LineBox, lo: LineBox, a: int, b: int) -> float:
    """The gap between pixel rows a and b (between two lines), cut by the rules across it: the longest
    blank stretch, in pt."""
    xa = max(int(min(up[0], lo[0]) * _K), 0)
    xb = min(int(max(up[1], lo[1]) * _K) + 1, im.width)
    if xb <= xa:
        return (b - a) / _K
    reg = im.crop((xa, a, xb, b))
    tbl = _tone_table(page_bg)
    data, w = reg.tobytes(), reg.width
    edges: list[tuple[int, int]] = []
    last = a
    for r in range(reg.height):
        if row_stats(data, w, r, tbl)[1] >= RULE_PT * _K:
            edges.append((last, a + r))        # blank stretch [last, a+r)
            last = a + r + 1
    edges.append((last, b))
    return max(e1 - e0 for e0, e1 in edges) / _K


def page_ink_gap(pdf: str) -> GapFn:
    """gap_fn(page, up, lo) -> OPTICAL gap (pt) between two text lines
    ([x0, x1, y0, y1] pdftotext boxes), measured on a 300 dpi raster of `pdf`
    (pdftoppm; pages rendered lazily): from the BASELINE of the upper line to the
    x-HEIGHT TOP of the lower one. The baseline and x-height top come from each
    line's ink row profile (xheight_band), so ascenders, capitals and descenders
    do not move them: the gap depends on the layout, never on the words. A line
    on a filled band counts as the band (top/bottom edge of the fill); a rule
    between the two lines splits the gap, and the longest part is returned (a
    title bar is what separates the title from the block above). With no
    raster, the gap is the pdftotext box gap (lower top - upper bottom)."""
    # per-call state: rasters are rendered lazily, once per page
    cache: dict[int, Image.Image | None] = {}
    pbg: dict[int, int] = {}
    met: dict[tuple[float, ...], tuple[int, int] | None] = {}

    def img(page: int) -> Image.Image | None:
        if page not in cache:
            cache[page] = _render_page(pdf, page)
        return cache[page]

    def page_bg(page: int, im: Image.Image) -> int:
        # background = the PAGE's dominant tone, not the crop's (a reversed-out
        # band would otherwise count as "background")
        if page not in pbg:
            pbg[page] = _dominant_tone(im)
        return pbg[page]

    def metrics(page: int, im: Image.Image, ln: LineBox) -> tuple[int, int] | None:
        key = (page, *(round(v, 1) for v in ln))
        if key not in met:
            met[key] = _line_rows(im, page_bg(page, im), ln)
        return met[key]

    def gap(page: int, up: LineBox, lo: LineBox) -> float:
        im = img(page) if pdf else None
        if im is None:
            return lo[2] - up[3]
        mu, ml = metrics(page, im, up), metrics(page, im, lo)
        if mu is None or ml is None:
            return lo[2] - up[3]
        a, b = mu[1] + 1, ml[0]                    # first row below the upper baseline .. lower x-height top
        if b <= a:
            return 0.0
        return _split_gap(im, page_bg(page, im), up, lo, a, b)   # rules between the two lines split the gap

    return gap
