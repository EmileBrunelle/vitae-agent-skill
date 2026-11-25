"""Optical line gap measured on a 300 dpi raster of the PDF (the measure group proximity is judged on)."""
from __future__ import annotations

import os
import subprocess
import tempfile
from collections.abc import Callable

from PIL import Image

from vitae.core.base import GapFn, LineBox
from vitae.core.env import pdf_backend
from vitae.verify.page import INK_DELTA, INK_DPI, RULE_PT, _row_stats, _xheight_band
from vitae.verify.pdf import _pdfium_render


def _page_ink_gap(pdf: str) -> GapFn:
    """gap_fn(page, up, lo) -> OPTICAL gap (pt) between two text lines
    ([x0, x1, y0, y1] pdftotext boxes), measured on a 300 dpi raster of `pdf`
    (pdftoppm; pages rendered lazily): from the BASELINE of the upper line to the
    x-HEIGHT TOP of the lower one. The baseline and x-height top come from each
    line's ink row profile (_xheight_band), so ascenders, capitals and descenders
    do not move them: the gap depends on the layout, never on the words. A line
    on a filled band counts as the band (top/bottom edge of the fill); a rule
    between the two lines splits the gap, and the longest part is returned (a
    title bar is what separates the title from the block above). With no
    raster, the gap is the pdftotext box gap (lower top - upper bottom)."""
    # per-call state: rasters are rendered lazily, once per page
    cache: dict[int, Image.Image | None] = {}
    pbg: dict[int, int] = {}
    met: dict[tuple[float, ...], tuple[int, int] | None] = {}
    k = INK_DPI / 72.0

    def img(page: int) -> Image.Image | None:
        if page not in cache:
            cache[page] = None
            try:
                if pdf_backend() == "pdfium":
                    cache[page] = _pdfium_render(pdf, INK_DPI, gray=True, pages=[page])[0]
                    return cache[page]
                # a 300 dpi page raster is ~9 MB: one scoped temp dir per page, removed even on a crash
                with tempfile.TemporaryDirectory(prefix="vitae-prox-") as d:
                    pre = os.path.join(d, f"p{page}")
                    r = subprocess.run(["pdftoppm", "-r", str(INK_DPI), "-gray", "-singlefile",
                                        "-f", str(page), "-l", str(page), pdf, pre],
                                       capture_output=True)
                    if r.returncode == 0:
                        gray = Image.open(pre + ".pgm").convert("L")
                        cache[page] = gray
                        gray.load()
            except (OSError, ValueError, RuntimeError):
                cache[page] = None
        return cache[page]

    def page_bg(page: int, im: Image.Image) -> int:
        # background = the PAGE's dominant tone, not the crop's (a reversed-out
        # band would otherwise count as "background")
        if page not in pbg:
            hp = im.histogram()
            pbg[page] = max(range(256), key=hp.__getitem__)
        return pbg[page]

    def tbl_for(bg: int) -> bytes:
        return bytes(1 if abs(v - bg) > INK_DELTA else 0 for v in range(256))

    def metrics(page: int, im: Image.Image, ln: LineBox) -> tuple[int, int] | None:
        """(top, base) pixel rows of one text line: x-height band of its ink, or
        the edges of the fill it sits on."""
        key = (page,) + tuple(round(v, 1) for v in ln)
        if key in met:
            return met[key]
        res: tuple[int, int] | None = None
        ya, yb = max(int(ln[2] * k), 0), min(int(ln[3] * k) + 1, im.height)
        xa, xb = max(int(ln[0] * k), 0), min(int(ln[1] * k) + 1, im.width)
        if yb - ya >= 3 and xb > xa:
            reg = im.crop((xa, ya, xb, yb))
            hp = reg.histogram()
            lbg = max(range(256), key=hp.__getitem__)
            pg = page_bg(page, im)
            if abs(lbg - pg) > INK_DELTA:
                # line on a filled band (or field): its optical extent is the fill's
                # rows, found on a strip just left / right of the text
                m = int(3 * k)
                res = None
                for sx in ((max(xa - m, 0), max(xa - 1, 0)), (min(xb + 1, im.width), min(xb + m, im.width))):
                    if sx[1] - sx[0] < 2:
                        continue
                    strip = im.crop((sx[0], 0, sx[1], im.height))
                    sd, sw = strip.tobytes(), strip.width
                    stb = bytes(1 if abs(v - lbg) <= INK_DELTA else 0 for v in range(256))
                    full: Callable[..., bool] = lambda r, sd=sd, sw=sw, stb=stb: sd[r * sw:(r + 1) * sw].translate(stb).count(b"\x01") >= 0.9 * sw
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
                        res = (t, b)
                        break
            if res is None:
                tbl = tbl_for(lbg)
                data, w = reg.tobytes(), reg.width
                prof = []
                for r in range(reg.height):
                    n, run = _row_stats(data, w, r, tbl)
                    prof.append(-1 if run >= RULE_PT * k else n)    # underline / rule rows are not glyphs
                bd = _xheight_band(prof)
                if bd and bd[1] - bd[0] >= 2:
                    res = (ya + bd[0], ya + bd[1])
        met[key] = res
        return res

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
        # rules between the two lines split the gap
        xa = max(int(min(up[0], lo[0]) * k), 0)
        xb = min(int(max(up[1], lo[1]) * k) + 1, im.width)
        if xb <= xa:
            return (b - a) / k
        reg = im.crop((xa, a, xb, b))
        tbl = tbl_for(page_bg(page, im))
        data, w = reg.tobytes(), reg.width
        edges, last = [], a
        for r in range(reg.height):
            if _row_stats(data, w, r, tbl)[1] >= RULE_PT * k:
                edges.append((last, a + r))        # blank stretch [last, a+r)
                last = a + r + 1
        edges.append((last, b))
        return max(e1 - e0 for e0, e1 in edges) / k

    return gap
