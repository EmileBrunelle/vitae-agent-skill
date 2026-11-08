"""Layout gates: whitespace (section boundaries, canyons), clipped text, and the silent font fallback.

No `import verify`.
"""
from __future__ import annotations

import importlib.util
from collections.abc import Iterator, Sequence

from PIL import Image

import vitae.fill as measure_fill
from vitae.core.base import Band, Box, WordBox
from vitae.core.env import _importable
from vitae.core.level import Finding, Level
from vitae.core.pixels import gray_pixels, rgb_pixels
from vitae.verify.fonts import _font_sources, classify_font_fallback, requested_families
from vitae.verify.page import BOUNDARY_RATIO, FURNITURE_SCALE, boundary_ink, furniture_ink, near_boundary
from vitae.verify.pdf import _pdfium_doc

# ---------- whitespace structure: section boundaries + canyons ----------

# BOUNDARY_RATIO, the boundary locator, lives in verify_page.py with its calibration. SEPARATION_CEILING is the
# other end of the same measurement, and it is a SMOKE ALARM, not a grade. Whitespace is
# the WEAK separator: piling it on is what an agent does when the boundary does
# not read and it has no device to reach for, and the page that carries no
# device at all AND a gap unlike anything the roster produces is the
# « séparateurs, pas des espaces vides » defect this catches.
# It cannot be calibrated between populations, because there is only one: the
# device-less pages run 2.38 2.56 2.86 2.86 3.29 3.57 3.86 4.00 4.17 5.00,
# continuously, and the roster's highest page of any kind is margin-index at
# 5.14 (a deliberately device-less family, which core.md says legitimately
# owes a HIGH ratio — failing it for that would contradict the rule it serves).
# So the ceiling is placed ABOVE the entire roster and BELOW the no-boundary-
# system pages the selftest draws (6.77 for one lone flourish, 7.92 for none at
# all). 5.0 kept the corpus green only by an exact tie (humanist-quiet/resume
# measures 5.00), which is not a calibration.
SEPARATION_CEILING = 6.0
# DEVICE_QUORUM: a device is a REPEATED element, and one mark on the page is an ornament,
# typically the flourish under the name. Two families passed the ink check on
# exactly that — `gutter-rail` on its header bar, `engraved-card` on the 56pt
# rule under the name — with nothing at any section boundary below.
# Known limit: a flat count, not a per-boundary tally; a page carrying a single
# section boundary (the tail of a 2-pager) would read as ornament-only. No such
# page exists in the corpus — the thinnest is page 2 of swiss-grid's 2-pager
# with 5 — so a per-boundary pairing is not worth its code yet.
DEVICE_QUORUM = 2
# Internal white runs are judged as fractions of page height, never pixels (references/design/core.md § Invariants &
# Page-fill tuning loop): >5% of page height (~1.4 cm on US Letter) is a canyon anywhere; >3.5% (~1.0 cm) inside
# a section is a hole unless it is a section boundary (a run >= BOUNDARY_RATIO x the median run).
CANYON = 0.035          # a hole this tall (fraction of page height) is a defect
BOUNDARY_CEILING = 0.05  # …unless it is a section boundary, which may run this tall

# Families whose boundary device is real but of a KIND no row scan can see: they are exempt from the DEVICE_QUORUM
# FAIL only (check_whitespace looks the family up with family_from_path). Measured 2026-09-13; each is a device
# nature, not a tuning miss:
DEVICELESS = {
    "humanist-quiet",   # no ink at all, by doctrine (core.md: pure gap)
    "clause-index",     # the device is a numeral — text, not furniture
    "gutter-rail",      # the bar is VERTICAL: never forms a row band
    "mono-technical",   # 6pt inline squares, ~1% of width, under any floor
    # Same instrument limit as mono-technical, NOT a missing device. Its
    # `section()` emits a 4.4pt accent lozenge above every title, so every
    # boundary carries one. Measured 2026-09-13 on the render: six marks of
    # 13x13px, 1.0% of a 1275px page, dead centre, at y=263 466 617 976 1148
    # 1446 — one per section, each directly above its centred title. The only
    # WIDE run on the page (9%, y=164) is the 56pt letterhead rule under the
    # name, which is not the section device at all. The floor cannot come down
    # to meet a 1% mark: the same scan reports dozens of 0.1-0.5% specks from
    # glyph fragments and punctuation, so 1% sits inside the noise.
    "engraved-card",
}


def check_text_clip(png: str, boxes: Sequence[WordBox] | None) -> list[str]:
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
    rgb = rgb_pixels(im)
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


def check_whitespace(path: str, boxes: Sequence[Box] | None = None, family: str | None = None,
                     degraded: bool = False) -> Iterator[tuple[bool, str]]:
    """Yield (is_fail, message) for one rendered page: the whitespace structure between sections.

    Catches a page whose section boundaries carry no ink (whitespace alone is the separator), a
    boundary gap wildly out of proportion to the rest, and white runs tall enough to read as a
    hole. Ratios and devices are WARN/OK text or FAIL as the individual yields below say.

    `boxes` is this page's pdftotext word-box list (from `word_boxes`), used
    to see furniture the old rule/bar scan is blind to (a tick or side bar
    typeset ON a heading's own line — no white row above it). `family` is
    the template family name (from `family_from_path`); it is the only thing
    that can exempt a page from the device quorum (see DEVICELESS), and only
    a template family, never a user's own CV.
    """
    import statistics
    h, white, all_ink = measure_fill.bands(path)
    runs = [b - a for a, b in white]
    if len(runs) < 6:
        return                              # not a text page: nothing to judge
    med = statistics.median(runs)
    top = max(runs)
    if med <= 0:
        return
    ratio = top / med
    ink = boundary_ink(white, all_ink, med)
    furniture = furniture_ink(path, boxes)
    # furniture_ink scans the whole PNG; measure_fill.bands reports rows of
    # its CROP, which cuts 2% off the top. EVERY use of a furniture band has
    # to be in the crop's frame — the position test, the dedupe against
    # `ink`, and what lands in `union` — or the two halves of the union are
    # counted in different coordinate systems and the dedupe never fires.
    # Until 2026-09-13 it did not fire: `ink` and `furniture` counted the
    # same band twice on color-band, swiss-grid, margin-index, editorial-serif
    # and engraved-card, inflating every union those families reported.
    off = int(h * 0.02)

    def _overlap(a: Band, b: Band) -> bool:
        # bands are (top, bottom) pixel rows; touching counts as overlapping
        return not (a[1] < b[0] or b[1] < a[0])

    union = list(ink)
    for band in furniture:
        band = (band[0] - off, band[1] - off)
        if near_boundary(band, white, med) and \
                not any(_overlap(band, u) for u in union):
            union.append(band)

    if ratio < BOUNDARY_RATIO:
        yield False, (f"section separation: biggest internal gap {top}px is "
                      f"{ratio:.2f}x the median {med}px — under the "
                      f"{BOUNDARY_RATIO}x a boundary is located by, so the ink "
                      f"check below may see fewer devices than the page "
                      f"carries. REPORTED, NOT FAILED: the ratio does not rank "
                      f"separation (see BOUNDARY_RATIO). Look at the page")
    # The half of the invariant the white scan alone could never check: a boundary carries
    # INK by default (core.md, "Boundaries carry ink by default"). With no device AT A
    # BOUNDARY, whitespace is the whole separator, and a wide boundary on top of that is
    # the failure this gate exists to catch: separators are wanted, not empty space.
    if len(union) < DEVICE_QUORUM:
        exempt = family in DEVICELESS
        # A MISSING TOOL IS NOT A DESIGN DEFECT (the design principle: never a FAIL for what
        # Python cannot judge). Without pdftotext the union is the old row scan alone, which
        # is the detector this gate was rewritten to stop trusting: it scores 0 on
        # quiet-luxury and avant-poster, whose devices are real but sit on the heading's own
        # line. So when the boxes are unavailable the quorum is REPORTED, never failed.
        yield (not (exempt or degraded)), (
            f"boundaries carry no ink: {len(union)} rule/bar/slab AT a section "
            f"boundary, need {DEVICE_QUORUM} ({len(all_ink)} wide dark run(s) "
            f"on the page — an underline, a table rule or a single flourish "
            f"under the name is not a boundary system)"
            + (" — NOT MEASURED: pdftotext is unavailable, so devices beside "
               "the heading (ticks, side bars) are invisible to this run. "
               "Install poppler-utils to restore the check"
               if degraded else
               " — add the family's device at each boundary, or a thin `soft` "
               "hairline above each section (core.md § Boundaries carry ink "
               "by default); if the gap is doing the work instead, give it "
               "back to body leading")
            + (f" — EXEMPT: {family} is on DEVICELESS (its device is real "
               f"but of a kind no row scan can see)" if exempt else ""))
    else:
        yield False, (f"boundary devices: {len(union)} ink band(s) at a section "
                      f"boundary, of {len(all_ink)} on the page "
                      f"({', '.join(str(b - a) + 'px' for a, b in union[:6])})")
    if ratio > SEPARATION_CEILING:
        yield False, (f"section separation: biggest gap {top}px = {ratio:.2f}x "
                      f"median {med}px — OVER {SEPARATION_CEILING}x. Legitimate "
                      f"only for a device-less family (whitespace is then the "
                      f"whole boundary). If the boundary carries ink, the gap is "
                      f"compensating for nothing: cut it and give the space back "
                      f"to body leading")
    else:
        yield False, (f"section separation: biggest gap {top}px = {ratio:.2f}x "
                      f"median {med}px")
    for g in sorted(set(runs), reverse=True):
        if g > BOUNDARY_CEILING * h:
            yield True, (f"canyon: {g}px white run = {g / h * 100:.1f}% of page "
                         f"height (max {BOUNDARY_CEILING * 100:.0f}% even at a "
                         f"section boundary) — take the space out of the "
                         f"intra-section rhythm instead")
        elif g > CANYON * h and g < BOUNDARY_RATIO * med:
            yield True, (f"hole: {g}px white run = {g / h * 100:.1f}% of page "
                         f"height inside a section (max {CANYON * 100:.1f}%; only "
                         f"a section boundary may exceed it)")


# ---------- font actually rendered vs font asked for (the silent Typst fallback) ----------

def pdf_char_fonts(pdf: str) -> list[tuple[str, str]] | None:
    """[(character, PDF font name)] of every non-space character, or None without pypdfium2.

    Only pdfium exposes the font of each character; poppler's pdffonts lists fonts per file,
    which cannot say which characters fell back."""
    if not _importable("pypdfium2"):
        return None
    try:
        import ctypes
        raw = importlib.import_module("pypdfium2.raw")
        out: list[tuple[str, str]] = []
        for pg in _pdfium_doc(pdf):
            tp = pg.get_textpage()
            if not tp.count_chars():
                continue
            buf = ctypes.create_string_buffer(256)
            flags = ctypes.c_int()
            idx = 0
            for ch in tp.get_text_range():
                # pdfium indexes UTF-16 code units: a character past the BMP takes two
                i, idx = idx, idx + (2 if ord(ch) > 0xFFFF else 1)
                if ch.isspace() or ord(ch) < 0x20:
                    continue
                n = raw.FPDFText_GetFontInfo(tp, i, buf, 256, ctypes.byref(flags))
                out.append((ch, buf.value.decode("latin-1") if n else ""))
        return out
    except Exception:
        return None


def check_font_fallback(typ: str, pdf: str, root: str | None = None) -> list[Finding]:
    """The characters the PDF drew in a family the sources never asked for (Typst's silent font
    fallback). Without pypdfium2 it WARNs and names the manual check; it cannot FAIL blind."""
    chars = pdf_char_fonts(pdf)
    if chars is None:
        return [(Level.WARN, "font fallback NOT checked (needs pypdfium2: pip install pypdfium2); "
                         "by hand: pdffonts cv.pdf, every family listed must be one cv.typ asks for")]
    firsts: set[str] = set()
    req = requested_families(_font_sources(typ, root), firsts)
    return classify_font_fallback(chars, req, firsts)
