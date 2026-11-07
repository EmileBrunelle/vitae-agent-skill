#!/usr/bin/env python3
# AGENT: do not read this file — run it. Its printed output is the instruction.
# Usage: python3 scripts/verify.py <cv.typ> PAGES [FILL_MIN FILL_MAX]
#        python3 scripts/verify.py --tune <cv.typ> PAGES FILL_MIN FILL_MAX
# (Reading it wastes context: a small model read this file 3 times and never wrote the CV.)
"""One-command gate for the MECHANICAL subset of SKILL.md step 6 (any platform with Python 3: Linux, macOS,
Windows). Exits non-zero if any check fails. Left to do by hand: the visual PNG inspection, recomputing the
accent's contrast, the date-order check, and re-diffing bullets against the fact sheet.

Usage:
    verify.py cv.typ EXPECTED_PAGES [FILL_MIN FILL_MAX] [--facts facts.md]
    verify.py --all DIR
    verify.py --tune cv.typ PAGES FILL_MIN FILL_MAX [LEADING_LO LEADING_HI]
    verify.py --doctor
    verify.py --selftest

    e.g. verify.py cv.typ 1 94 96
         verify.py --tune cv.typ 1 94 96

--gates (the new gates alone on a compiled PDF), --render (one PNG per page) and --text (the text the gates read)
are agent-facing helpers; their usage text is in main(). That function also owns the usage text of every
mode: it is what a usage error and --help print, and this docstring is not printed anywhere.

Gate order for one CV (`_check_cv`; every line is printed as OK, WARN, FAIL or INFO, and the exit code is 1 if any
was a FAIL): dependency preflight, lib.typ integrity, compile, page count, then per rendered page the fill, the
text-clip gate and the whitespace structure; template-default markers; the checks on the extracted text (spaced
capitals, orphaned dates, no section split across a page break, --facts coverage of years and numbers,
bullet characters); last, the gates that need `typst query` (hidden text, font fallback,
group proximity, date adjacency, forced line breaks and `~`, duplicate names).

Design principle (scope): the scripts know no language and no country. They make only objective checks: what a PDF, a
Typst render, a number or a declared value says on its own. No word list is kept, none is extended, and a check that
needed one is removed. What a script cannot know comes from an explicit declaration by the user or the model (a TOML
key, a tagged mark in cv.typ) or is left to the model (references/steps/6-verify.md). So there is no INFO or WARN that
talks about a language: a script never guesses one, and never FAILs because of one.

The helpers live in sibling modules, which verify.py imports by name: verify_lang (Latin-script helpers),
verify_typst (cv.typ parsing: text in, values out), verify_fonts (font families asked for against drawn),
verify_page (page geometry and pixel measurement), and verify_selftest (--selftest). The first four never
`import verify`: verify.py runs as __main__, so importing it would execute the script a second time under the name
`verify`. verify_selftest does need verify's own functions, so --selftest imports it lazily, after registering the
running module as `verify` in sys.modules (its `import verify` then gets this module, not a copy); a normal run
never loads it.

--all checks EVERY deliverable in a directory instead of the one file just edited. This exists because of a real
regression: a padding tweak was verified on the 2-page CV while it silently pushed the 1-page CV onto two pages
("T'as fait ça en voulant modifier le padding"). The deliverables share lib.typ, so touching it invalidates the
whole family, not the file in hand.

Each .typ declares its own expectations in a header comment, so there is no manifest to keep in sync with the files:

    // vitae: pages=1 fill=94-96

A file without that line is still checked: its page count comes from its name (`[-_]2p`, `[-_]2page(s)`,
optionally with a space, e.g. `_2p`, `-2page`, `-2pages`, is two pages; anything else is one) and its fill is
reported instead of gated. Not one .typ in this repo carries the header, so demanding it made `--all` return 30
UNCHECKED and exit 1 on its own corpus.

--tune runs the page-fill loop BY BISECTION instead of by hand: it moves the `#set par(leading:, spacing:)`
declaration (keeping the family's own delta between the two) to the largest rhythm that still holds the expected
page count, writes the winning values into the file, and reports whether the resulting fill lands in the target. It
replaces the compile-measure-adjust loop an agent would otherwise run a dozen times per family. It tunes NOTHING
else: the section gap, the margins and the type sizes are recipe decisions. When no value in range reaches the
target, it says so rather than inventing one: that is the anti-filler clause (SKILL.md rule 5), and the fix is the
section gap, real content, or a different page count. But check the RANGE first: the default search is 0.80-1.30x
the current leading, and a font swap can need a bigger move than that. Pass LEADING_LO/LEADING_HI and re-run before
you touch a device: one family's second font pair looked unreachable, got its section gap cut by 6pt to compensate,
and landed with its boundary sitting exactly on the separation floor; a wider search range was the real fix.

--doctor runs only the dependency preflight (no cv.typ required), exit 0 if everything needed is present (a pip-only
fallback is printed as DEGRADED, with the skipped checks and install routes, and still exits 0 because compiling and
page counting work), 1 otherwise. It replaces the old check_env.sh / check_env.ps1 doctors.

Exit codes: 0 PASS, 1 FAIL (or missing dependency with no fallback), 2 usage error.

Prefers native tools (typst CLI, poppler pdfinfo/pdftotext) but falls back automatically to their Python
equivalents when only those are installed: the `typst` Python package (compiles via its API, no CLI needed),
`pypdfium2` (text, word boxes, raster) and `pypdf` (page count and indicative-only text extraction; see
references/ats.md for the caveat). There is no functional --install flag: that meant fetching a binary over HTTPS
with no checksum verification; the install commands are printed instead and the user chooses.
"""
from __future__ import annotations

import argparse
import atexit
import glob
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator, Sequence
from typing import Any, Literal, NoReturn, cast

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure_fill  # noqa: E402
from verify_base import (
    _FOOTER_GATE as _FOOTER_GATE,
)
from verify_base import (
    _FOOTER_TUNE as _FOOTER_TUNE,
)
from verify_base import (
    _FOOTER_TUNE_NOPAR as _FOOTER_TUNE_NOPAR,
)
from verify_base import (
    _FOOTER_TUNE_UNDER as _FOOTER_TUNE_UNDER,
)
from verify_base import (
    _FOOTER_TUNE_WIDE as _FOOTER_TUNE_WIDE,
)
from verify_base import (
    _NO_READ as _NO_READ,
)
from verify_base import (
    HIDDEN_PPI as HIDDEN_PPI,
)
from verify_base import (
    LEADING_WARN as LEADING_WARN,
)
from verify_base import (
    LOWERED_FILL_FLOOR as LOWERED_FILL_FLOOR,
)
from verify_base import (
    STATE as STATE,
)
from verify_base import (
    Band as Band,
)
from verify_base import (  # noqa: E402 -- shared shapes, constants and STATE (a leaf module); re-exported for callers
    Box as Box,
)
from verify_base import (
    DetailRow as DetailRow,
)
from verify_base import (
    GapFn as GapFn,
)
from verify_base import (
    GroupRow as GroupRow,
)
from verify_base import (
    HiddenStat as HiddenStat,
)
from verify_base import (
    LineBox as LineBox,
)
from verify_base import (
    Mark as Mark,
)
from verify_base import (
    SecRow as SecRow,
)
from verify_base import (
    Word as Word,
)
from verify_base import (
    WordBox as WordBox,
)
from verify_base import (
    _EntryRecord as _EntryRecord,
)
from verify_base import (
    _Line as _Line,
)
from verify_env import (
    _NEW_TYPST as _NEW_TYPST,
)
from verify_env import (
    _OLD_TYPST as _OLD_TYPST,
)
from verify_env import (
    TYPST_MIN as TYPST_MIN,
)
from verify_env import (
    PdfBackend as PdfBackend,
)
from verify_env import (
    _CountDegraded as _CountDegraded,
)
from verify_env import (
    _importable as _importable,
)
from verify_env import (
    _typst_py_probe as _typst_py_probe,
)
from verify_env import (
    _ver_tuple as _ver_tuple,
)
from verify_env import (
    check_fonts as check_fonts,
)
from verify_env import (
    check_pdf_tools as check_pdf_tools,
)
from verify_env import (  # noqa: E402 -- dependency preflight and typst probes; re-exported for callers
    check_pillow as check_pillow,
)
from verify_env import (
    check_typst as check_typst,
)
from verify_env import (
    pdf_backend as pdf_backend,
)
from verify_env import (
    pdf_tool as pdf_tool,
)
from verify_env import (
    preflight as preflight,
)
from verify_env import (
    typst_can_query as typst_can_query,
)
from verify_env import (
    typst_font_kw as typst_font_kw,
)
from verify_env import (
    typst_fonts as typst_fonts,
)
from verify_env import (
    typst_py as typst_py,
)
from verify_fonts import (  # noqa: E402 -- font families asked for vs drawn: pure text and tuples
    _fam_key as _fam_key,  # noqa: F401 -- re-exported: verify_selftest.py reads it from verify
)
from verify_fonts import (
    _family_requested as _family_requested,  # noqa: F401 -- re-exported: verify_selftest.py reads it from verify
)
from verify_fonts import (
    _font_sources,
)
from verify_fonts import (
    classify_font_fallback as classify_font_fallback,
)
from verify_fonts import (
    requested_families as requested_families,
)
from verify_level import Finding, Level  # noqa: E402
from verify_page import (  # noqa: E402 -- page geometry and pixel measurement: pixels and boxes in, numbers out
    BOUNDARY_RATIO,
    INK_DELTA,
    INK_DPI,
    RULE_PT,
    _row_stats,
    boundary_ink,
    near_boundary,
)
from verify_page import (
    FURNITURE_SCALE as FURNITURE_SCALE,  # noqa: F401 -- re-exported: verify_selftest.py reads it from verify
)
from verify_page import (
    _xheight_band as _xheight_band,
)
from verify_page import (
    furniture_ink as furniture_ink,
)
from verify_pdf import (
    LINE_GAP as LINE_GAP,
)
from verify_pdf import (
    _bbox_pages as _bbox_pages,
)
from verify_pdf import (
    _boxes_unavailable as _boxes_unavailable,
)
from verify_pdf import (
    _page_rasters as _page_rasters,
)
from verify_pdf import (
    _pdfium_bbox_pages as _pdfium_bbox_pages,
)
from verify_pdf import (
    _pdfium_doc as _pdfium_doc,
)
from verify_pdf import (
    _pdfium_error as _pdfium_error,
)
from verify_pdf import (
    _pdfium_page_text as _pdfium_page_text,
)
from verify_pdf import (
    _pdfium_render as _pdfium_render,
)
from verify_pdf import (
    _reading_order as _reading_order,
)
from verify_pdf import (
    _render_pages_png as _render_pages_png,
)
from verify_pdf import (
    _root_cli as _root_cli,
)
from verify_pdf import (
    _root_kw as _root_kw,
)
from verify_pdf import (  # noqa: E402 -- compile / page count / render; re-exported for callers
    auto_root as auto_root,
)
from verify_pdf import (
    compile_pdf as compile_pdf,
)
from verify_pdf import (
    count_pages as count_pages,
)
from verify_pdf import (
    ensure_icons as ensure_icons,
)
from verify_pdf import (
    extract_text as extract_text,
)
from verify_pdf import (
    family_from_path as family_from_path,
)
from verify_pdf import (
    pdf_unreadable as pdf_unreadable,
)
from verify_pdf import (
    render_crops as render_crops,
)
from verify_pdf import (
    render_pages as render_pages,
)
from verify_pdf import (
    render_pngs as render_pngs,
)
from verify_pdf import (
    typst_compile as typst_compile,
)
from verify_pdf import (
    word_boxes as word_boxes,
)
from verify_source import (
    _BANNER_RE as _BANNER_RE,
)
from verify_source import (
    _HEADER1_RE as _HEADER1_RE,
)
from verify_source import (
    FORCED_BREAK_RE as FORCED_BREAK_RE,
)
from verify_source import (
    LIST_ITEM_RE as LIST_ITEM_RE,
)
from verify_source import (
    PAGINATION_RE as PAGINATION_RE,
)
from verify_source import (
    SECTION_CALL_RE as SECTION_CALL_RE,
)
from verify_source import (
    TILDE_RE as TILDE_RE,
)
from verify_source import (
    _drawn_fill as _drawn_fill,
)
from verify_source import (
    _fill_args_ok as _fill_args_ok,
)
from verify_source import (
    _heading_words as _heading_words,
)
from verify_source import (
    _norm_heading as _norm_heading,
)
from verify_source import (
    check_forced_linebreak as check_forced_linebreak,
)
from verify_source import (
    check_literal_tilde as check_literal_tilde,
)
from verify_source import (
    check_no_split as check_no_split,
)
from verify_text import (
    _DATE_CORE as _DATE_CORE,
)
from verify_text import (
    _NUM_DATE_END_RE as _NUM_DATE_END_RE,
)
from verify_text import (
    _NUM_DATE_SCAN_RE as _NUM_DATE_SCAN_RE,
)
from verify_text import (
    _NUM_MY_RE as _NUM_MY_RE,
)
from verify_text import (
    _NUM_RE as _NUM_RE,
)
from verify_text import (
    _PHONE_GEN_RE as _PHONE_GEN_RE,
)
from verify_text import (
    _PHONE_RE as _PHONE_RE,
)
from verify_text import (
    _YEAR_RE as _YEAR_RE,
)
from verify_text import (
    BULLET_CHAR_RE as BULLET_CHAR_RE,
)
from verify_text import (
    HIDDEN_FAIL_RATIO as HIDDEN_FAIL_RATIO,
)
from verify_text import (
    HIDDEN_MIN_BOX_PT as HIDDEN_MIN_BOX_PT,
)
from verify_text import (
    HIDDEN_PAD_PX as HIDDEN_PAD_PX,
)
from verify_text import (
    HIDDEN_TAIL as HIDDEN_TAIL,
)
from verify_text import (
    HIDDEN_WARN_RATIO as HIDDEN_WARN_RATIO,
)
from verify_text import (
    KEYWORD_MAX_TERMS as KEYWORD_MAX_TERMS,
)
from verify_text import (
    META_MAX_CHARS as META_MAX_CHARS,
)
from verify_text import (
    TINY_TEXT_PT as TINY_TEXT_PT,
)
from verify_text import (
    _blank_phones as _blank_phones,
)
from verify_text import (
    _fold as _fold,
)
from verify_text import (
    _fold1 as _fold1,
)
from verify_text import (
    _num_values as _num_values,
)
from verify_text import (
    _readings as _readings,
)
from verify_text import (
    _stuffed as _stuffed,
)
from verify_text import (
    _text_runs as _text_runs,
)
from verify_text import (
    check_bullet_chars as check_bullet_chars,
)
from verify_text import (
    check_facts_coverage as check_facts_coverage,
)
from verify_text import (
    check_hidden_text as check_hidden_text,
)
from verify_text import (
    check_pdf_metadata as check_pdf_metadata,
)
from verify_text import (
    hidden_word_stats as hidden_word_stats,
)
from verify_tune import (
    SPACING_CAP as SPACING_CAP,
)
from verify_tune import (  # noqa: E402 -- --tune bisection; re-exported for callers
    _probe as _probe,
)
from verify_tune import (
    tune as tune,
)
from verify_typst import (  # noqa: E402 -- cv.typ parsing: pure text in, values out
    _doc_body_size,
    _doc_par_list,
)
from verify_typst import (
    _read_par as _read_par,
)
from verify_typst import (
    _strip_typst_comments as _strip_typst_comments,
)
from verify_typst import (
    _write_par as _write_par,
)

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
    px: Any = lum.load()
    rgb: Any = im.load()
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


# ---------- grouping / date / duplicate-name / forced-break gates ----------
# lib.typ tags every entry head and skill label with an invisible <vitae-head>
# metadata (text, org, page, x, y) and every section title with <vitae-sec>
# (pure metadata, no layout effect). `typst query` reads them back; the words
# come from the PDF (word_boxes(pdf, with_text=True)). Where a gate needs these
# marks and `typst query` is unavailable it WARNs "not checked" and the agent
# compares by hand; it never FAILs for that.

def _typst_query(typ: str, selector: str, root: str | None = None) -> list[Any] | None:
    """JSON list of the values of every element labelled `selector`, or None."""
    root = root or auto_root(typ)
    if not shutil.which("typst"):
        mod = typst_py()
        if mod is None:
            return None
        try:   # typst-py: same query / eval fallback and root as the CLI calls below
            comp = mod.Compiler(typ, root=root, **typst_font_kw()) if root else mod.Compiler(typ, **typst_font_kw())
            fn: Callable[[], Any]
            for fn in (lambda: comp.query(selector, field="value", one=False),
                       lambda: comp.eval(f"query({selector}).map(it => it.value)", format="json")):
                try:
                    out = fn()
                    if isinstance(out, str) and out.strip().startswith("["):
                        return cast("list[Any]", json.loads(out))
                except Exception:
                    continue
        except Exception:
            pass
        return None
    rootargs = ["--root", root] if root else []
    for cmd in (["typst", "query", typ, selector, "--field", "value"] + rootargs,
                ["typst", "eval", f"query({selector}).map(it => it.value)",
                 "--in", typ, "--target", "paged"] + rootargs):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
        except (FileNotFoundError, OSError):
            return None
        if r.returncode == 0 and r.stdout.strip().startswith("["):
            try:
                return cast("list[Any]", json.loads(r.stdout))
            except ValueError:
                continue
    return None


def _gnorm(t: str) -> str:
    """Comparison key for a word: letters and digits only, casefolded, so punctuation and
    spacing differences between the typst source and pdftotext do not break a match."""
    return "".join(ch for ch in t.casefold() if ch.isalnum())


def _lines(words: Sequence[Word], x_min: float) -> list[_Line]:
    """Words (x0, y0, x1, y1, text) at or right of x_min, clustered into text
    lines by y-centre -> sorted list of dicts {y0, y1, c, x0, words}."""
    ws = sorted((w for w in words if w[0] >= x_min), key=lambda w: (w[1] + w[3]) / 2)
    out: list[_Line] = []
    for w in ws:
        c = (w[1] + w[3]) / 2
        # 3.0pt y-centre tolerance: words of slightly different sizes/weights on one baseline stay in one line
        # while adjacent lines (~12-15pt baseline-to-baseline) never merge.
        if out and abs(c - out[-1]["c"]) <= 3.0:     # same text line: centres within 3pt
            ln = out[-1]
            ln["words"].append(w)
            ln["y0"], ln["y1"] = min(ln["y0"], w[1]), max(ln["y1"], w[3])
            ln["x0"] = min(ln["x0"], w[0])
            ln["c"] = (ln["y0"] + ln["y1"]) / 2
        else:
            out.append({"y0": w[1], "y1": w[3], "c": c, "x0": w[0], "words": [w]})
    return out


def _find_run(words: Sequence[Word], text: str, ytyp: float) -> list[Word] | None:
    """The words of `text` (first 4 tokens) nearest typst y `ytyp` -> list of
    word tuples, or None."""
    # Up to 4 tokens is enough to identify an entry head uniquely without crossing a line wrap.
    toks = [t for t in (_gnorm(w) for w in text.split()) if t][:4]
    if not toks:
        return None
    norm = [_gnorm(w[4]) for w in words]
    best = None
    for j in range(len(words)):
        if norm[j] != toks[0]:
            continue
        run, k = [j], j + 1
        for t in toks[1:]:
            while k < len(words) and norm[k] == "":
                k += 1
            if k < len(words) and norm[k] == t:
                run.append(k)
                k += 1
            else:
                break
        else:
            yc = (words[j][1] + words[j][3]) / 2
            if best is None or abs(yc - ytyp) < best[0]:
                best = (abs(yc - ytyp), run)
    # >30pt (~2 lines) from the <vitae-head> marker's y: a match that far away is a repeated word elsewhere on the page.
    if best is None or best[0] > 30:     # nearest match is over 30pt from the marker's y: not located
        return None
    return [words[k] for k in best[1]]


def _line_index(lines: list[_Line], run: list[Word]) -> int | None:
    """Index in `lines` of the line holding the first word of `run` (matched by identity)."""
    w = run[0]
    for i, ln in enumerate(lines):
        if any(x is w for x in ln["words"]):
            return i
    return None


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
    # per-call state: rasters are rendered lazily, once per page, into one temp dir
    cache: dict[int, Image.Image | None] = {}
    tmp: list[str] = []
    pbg: dict[int, int] = {}
    met: dict[tuple[float, ...], tuple[int, int] | None] = {}
    k = INK_DPI / 72.0

    def img(page: int) -> Image.Image | None:
        if page not in cache:
            cache[page] = None
            try:
                if not tmp:
                    tmp.append(tempfile.mkdtemp(prefix="vitae-prox-"))
                    # a 300 dpi page raster is ~9 MB: remove the directory at exit, even on a crash
                    atexit.register(shutil.rmtree, tmp[0], True)
                pre = os.path.join(tmp[0], f"p{page}")
                if pdf_backend() == "pdfium":
                    cache[page] = _pdfium_render(pdf, INK_DPI, gray=True, pages=[page])[0]
                    return cache[page]
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


def measure_groups(heads: list[Mark], secs: list[Mark], pages_words: list[list[Word]],
                   gap_fn: GapFn | None = None) -> tuple[list[DetailRow], int]:
    """Whole-group proximity. A group is an entry/skill row from its FIRST line
    (the role / label) through its LAST line (org line, bullets, wrapped lines
    included), up to the next block's head (entry head, skill label or section
    title of the same column flow). Per group: internal = the MAX gap between
    consecutive lines inside it, between = the gap from its last line to the
    next block's first line; ratio = between / internal. Gaps are ink gaps when
    gap_fn is given (default: pdftotext box gap). Section titles are measured
    too: sbefore = last line of the previous block -> title (its bar), safter =
    title -> first line of its section. Returns (rows, skipped); rows are
    {kind: "group"|"sec", text, page, ...}. Single-line groups, last blocks on a
    page, rail titles beside the body and unlocated text are skipped."""
    gap_fn = gap_fn or (lambda page, up, lo: lo[2] - up[3])
    rows: list[DetailRow] = []
    skipped = 0
    # the marks tagged with their kind ("h" head / "s" section): a widened dict, so Any
    marks: list[dict[str, Any]] = [dict(h, _k="h") for h in heads] + [dict(s, _k="s") for s in secs]
    box: Callable[[Any], list[Any]] = lambda ln: [ln["x0"], max(w[2] for w in ln["words"]), ln["y0"], ln["y1"]]
    for h in sorted(heads, key=lambda h: (h["page"], h["y"])):
        if h["page"] - 1 >= len(pages_words):
            skipped += 1
            continue
        words = pages_words[h["page"] - 1]
        run = _find_run(words, h["text"], h["y"])
        if run is None:
            skipped += 1
            continue
        hx = min(w[0] for w in run)
        lines = _lines(words, hx - 2)
        i0 = _line_index(lines, run)
        if i0 is None:
            skipped += 1
            continue
        # next block head on this page (entry head, skill label or section title)
        later = [m for m in marks if m["page"] == h["page"] and m["y"] > h["y"] + 2
                 and not (m["_k"] == "h" and abs(m["x"] - h["x"]) > 60)]
        if not later:
            continue                       # last block on its page: no next head
        m = min(later, key=lambda m: m["y"])
        mrun = _find_run(words, m["text"], m["y"])
        if mrun is None:
            skipped += 1
            continue
        # a rail title sits wholly LEFT of the body column (margin-index); a title
        # that merely starts left of an indented head (gutter-rail's skill rows
        # open with a drawn mark) is an in-flow title, its own line in the flow
        rail = max(w[2] for w in mrun) < hx - 2
        if rail:
            # Rail title beside the body: its y is the top of the title cell (rule
            # + gap), a few pt ABOVE the body's first line, so matching it by
            # y-centre lands one line too low. If an in-column head opens within
            # that window, THAT is the next block of this column's flow.
            h2 = [x for x in marks if x["_k"] == "h" and x["page"] == h["page"]
                  and abs(x["x"] - h["x"]) <= 60 and m["y"] - 3 <= x["y"] <= m["y"] + 15]
            if h2:
                m = min(h2, key=lambda x: x["y"])
                mrun = _find_run(words, m["text"], m["y"])
                if mrun is None:
                    skipped += 1
                    continue
        if not rail:
            mx0 = min(w[0] for w in mrun)
            if mx0 < hx - 2:               # in-flow title starting left of an indented head
                lines = _lines(words, mx0 - 2)
                i0 = _line_index(lines, run)
            i_next = _line_index(lines, mrun) if i0 is not None else None
        else:                              # title set in a rail beside the body
            mc = (mrun[0][1] + mrun[0][3]) / 2
            cand = [(abs(ln["c"] - mc), i) for i, ln in enumerate(lines)
                    if i > i0 and abs(ln["c"] - mc) <= 12]
            i_next = min(cand)[1] if cand else None
        if i_next is None or i0 is None or i_next <= i0 + 1:
            continue                       # single-line group (or no next head): nothing inside
        ls = [box(ln) for ln in lines[i0:i_next + 1]]
        tx = [" ".join(w[4] for w in sorted(ln["words"], key=lambda w: w[0])[:4])[:28]
              for ln in lines[i0:i_next + 1]]
        gaps = [gap_fn(h["page"], ls[i], ls[i + 1]) for i in range(len(ls) - 2)]
        between = gap_fn(h["page"], ls[-2], ls[-1])
        internal = max(gaps)
        wi = gaps.index(internal)              # the line pair behind the largest internal gap
        rows.append({"kind": "group", "text": h["text"], "page": h["page"], "n": len(ls) - 1,
                     "gaps": gaps, "internal": internal, "between": between,
                     "ratio": (between / internal) if internal > 0 else float("inf"), "ls": ls,
                     "pair_in": (tx[wi], tx[wi + 1]), "pair_btw": (tx[-2], tx[-1])})
    # sections: previous block's last line -> title (bar) vs title -> first line
    xs: dict[int, list[float]] = {}
    for h in heads:
        xs.setdefault(h["page"], []).append(h["x"])
    for sc in secs:
        pg = sc.get("page")
        if not pg or pg - 1 >= len(pages_words) or pg not in xs:
            continue
        words = pages_words[pg - 1]
        srun = _find_run(words, sc["text"], sc.get("y", 0))
        bx = min(xs[pg])
        if srun is None or min(w[0] for w in srun) < bx - 5:
            continue                       # unlocated, or a rail title beside the body
        lines = _lines(words, bx - 2)
        i = _line_index(lines, srun)
        if i is None or i < 1 or i + 1 >= len(lines):
            continue
        up, t, lo = box(lines[i - 1]), box(lines[i]), box(lines[i + 1])
        before, after = gap_fn(pg, up, t), gap_fn(pg, t, lo)
        rows.append({"kind": "sec", "text": sc["text"], "page": pg, "before": before,
                     "after": after, "ratio": (before / after) if after > 0 else float("inf")})
    return rows, skipped


# Gestalt-proximity thresholds on between/internal gap ratio; their calibration is recorded in
# check_group_proximity's docstring. Section titles use the same two.
PROX_FAIL, PROX_WARN = 0.7, 0.85


def check_group_proximity(typ: str, pdf: str, root: str | None = None,
                          heads: list[Mark] | None = None, secs: list[Mark] | None = None,
                          pages: list[list[Word]] | None = None,
                          detail: list[DetailRow] | None = None) -> list[Finding]:
    """[(level, message)], level FAIL/WARN/OK. Gestalt proximity on whole
    groups: for every entry/skill row (first line through last line, org line
    and bullets included), the gap from its last line to the NEXT block's first
    line must not be much smaller than the largest gap between two lines
    inside it (ratio between/internal; OPTICAL gaps at 300 dpi, baseline of
    the upper line to x-height top of the lower one, so the words never move
    the ratio): FAIL below PROX_FAIL (0.7 — the head visibly belongs to the
    wrong block), WARN below PROX_WARN (0.85). Calibrated by eye on templates,
    fixtures and real model output with the earlier ink-gap measure (groups
    at 0.24-0.49 read as attached to the next entry, 0.82-0.96 as acceptable),
    then re-mapped to the optical measure by sweeping entry `above` 8pt -> 3pt
    on 6 families: the old FAIL line (0.6) lands at 0.64-0.79 optical (mean
    0.71), the old WARN line (0.83-0.86) at 0.81-0.91; shipped templates and
    fixtures sit at >= 0.85. Section titles get the same thresholds on gap above
    the title (or its bar) / gap below it to the section's first line (DETAIL
    rows, kind "sec")."""
    heads = _typst_query(typ, "<vitae-head>", root) if heads is None else heads
    secs = (_typst_query(typ, "<vitae-sec>", root) or []) if secs is None else secs
    if pages is None:
        wb = word_boxes(pdf, with_text=True)
        pages = [[(b[0], b[1], b[2], b[3], t) for b, t in pg] for pg in wb] if wb else None
    if heads is None or pages is None:
        if pdf_backend() == "pdfium":
            return [(Level.WARN, "group proximity NOT checked (typst query unavailable or word positions "
                             "unreadable: " + _boxes_unavailable() + ")")]
        return [(Level.WARN, "group proximity NOT checked (typst query or pdftotext unavailable)")]
    if not heads:
        return [(Level.WARN, "group proximity not measured: no lib entry()/srow() heads")]
    # DETAIL lines are machine-readable and printed here, not returned: the self-test and --gates read them
    rows, skipped = measure_groups(heads, secs, pages, _page_ink_gap(pdf) if pdf else None)
    if detail is not None:
        detail.extend(rows)
    grp = [r for r in rows if r["kind"] == "group"]
    if not grp:
        return [(Level.WARN, f"group proximity: no checkable group ({skipped} head(s) not located) — unchecked")]
    for r in grp:
        print(f'DETAIL group "{r["text"][:30]}" p{r["page"]} lines={r["n"]} internal={r["internal"]:.2f}pt '
              f'between={r["between"]:.2f}pt ratio={r["ratio"]:.2f}')
    for row in rows:
        if row["kind"] == "sec":
            print(f'DETAIL section "{row["text"][:30]}" p{row["page"]} before-bar={row["before"]:.2f}pt '
                  f'bar-to-first={row["after"]:.2f}pt ratio={row["ratio"]:.2f}')
    out: list[Finding] = []
    if skipped:
        out.append((Level.WARN, f"group proximity not measured for {skipped} head(s) (multi-column layout, "
                    "rail title or head not located in the PDF text)"))
    sec = [r for r in rows if r["kind"] == "sec"]
    if sec:
        # a section title belongs to what FOLLOWS it: the gap above it (previous
        # block's last line -> title or its bar) must not be much smaller than
        # the gap below it (title -> first line). Same calibration as groups.
        s = min(sec, key=lambda r: r["ratio"])
        sw = (f'(worst "{s["text"][:30]}": gap above {s["before"]:.1f}pt, gap below '
              f'{s["after"]:.1f}pt, ratio {s["ratio"]:.2f}')
        sbad = [r for r in sec if not r["ratio"] >= PROX_FAIL]
        sweak = [r for r in sec if not r["ratio"] >= PROX_WARN]
        if sbad:
            out.append((Level.FAIL, f"section proximity: {len(sbad)}/{len(sec)} titles sit closer to the block "
                        f"above than to their own first line {sw}; need >= {PROX_FAIL}) — fix the family's "
                        "`section` (its `above` and the gap under the title), not the content file"))
        elif sweak:
            out.append((Level.WARN, f"section proximity: {len(sweak)}/{len(sec)} titles barely separated from "
                        f"the block above {sw}; aim for >= {PROX_WARN})"))
        else:
            out.append((Level.OK, f'section proximity: {len(sec)} titles, gap above >= {PROX_WARN} x gap below '
                        f'(tightest "{s["text"][:30]}": ratio {s["ratio"]:.2f})'))
    m = min(grp, key=lambda r: r["ratio"])
    q: Callable[[str], str] = lambda t: '"' + t + '"'
    worst = (f'(worst {q(m["text"][:30])}: largest gap inside {m["internal"]:.1f}pt '
             f'({q(m["pair_in"][0])} -> {q(m["pair_in"][1])}), gap to the next block '
             f'{m["between"]:.1f}pt ({q(m["pair_btw"][0])} -> {q(m["pair_btw"][1])}), ratio {m["ratio"]:.2f}')
    # `not x >= t` rather than `x < t`: a NaN ratio must count as failing
    bad = [r for r in grp if not r["ratio"] >= PROX_FAIL]
    if bad:
        return out + [(Level.FAIL, f'group proximity: {len(bad)}/{len(grp)} groups sit closer to the next block than '
                 f'their own lines are to each other {worst}; need >= {PROX_FAIL})\n'
                 "      do not override entry/srow above/gap/below per entry; look for a manual #v, linebreak "
                 "or blank line inside that entry (a gap that is too big inside is as bad as one too small after);\n"
                 "      if the CV uses the family file as shipped, report it: it is a template bug (never edit lib.typ)")]
    weak = [r for r in grp if not r["ratio"] >= PROX_WARN]
    if weak:
        return out + [(Level.WARN, f'group proximity: {len(weak)}/{len(grp)} groups barely separated from the next block '
                 f'{worst}; aim for >= {PROX_WARN})\n'
                 "      do not override entry/srow above/gap/below per entry; check for a manual #v, linebreak or "
                 "blank line inside that entry")]
    return out + [(Level.OK, f"group proximity: {len(grp)} groups, gap to next block >= {PROX_WARN} x internal gap "
             f'(tightest "{m["text"][:30]}": ratio {m["ratio"]:.2f}, {m["between"]:.1f}pt vs {m["internal"]:.1f}pt)')]


# Date adjacency is measured from POSITIONS, never from what a date looks like:
# lib.typ `entry` tags its head (<vitae-head>, with `dated`), its date cell and
# the line under the head (<vitae-part>: "date" / "org") with the x/y where
# their first glyph starts and the measured size of the cell. The date's words
# are the PDF words inside the date cell's box; their reading-order index is
# their position in `pdftotext -bbox` (the same layout analysis as the text an
# ATS reads). No regex decides what a date is, so an org "Vision 2020 Inc", a
# bullet "5000 users" or a role "Tier 2 Support" cannot be mistaken for one.
ENTRY_MARKS = "selector(<vitae-head>).or(<vitae-part>)"


def _entry_records(marks: list[Mark] | None) -> list[_EntryRecord]:
    """Marks in document order -> one record per entry head:
    {"head": mark, "date": mark|None, "org": mark|None, "date_first": bool}.
    A part mark belongs to the entry head emitted before it; `date_first` records which of the
    two was emitted first, since the emission order is what an ATS extraction follows."""
    recs: list[_EntryRecord] = []
    cur: _EntryRecord | None = None
    for m in marks or []:
        k = m.get("kind")
        if k == "entry":
            cur = {"head": m, "date": None, "org": None, "date_first": None}
            recs.append(cur)
        elif k in ("date", "org") and cur is not None:
            part = cast(Literal["date", "org"], k)
            if cur[part] is None:
                cur[part] = m
                if cur["date_first"] is None:
                    cur["date_first"] = part == "date"
        elif k == "skill":
            cur = None                     # other part kinds ("date-col") are ignored
    return recs


def _yc(w: WordBox) -> float:
    """Vertical centre of a word box."""
    return (w[0][1] + w[0][3]) / 2


def _first_word(words: Sequence[WordBox], x: float, y: float, y_end: float,
                x_end: float | None = None) -> int | None:
    """Reading-order index of the first word of the line starting at (x, y):
    words whose centre lies in [y - 2, y_end) and that start at or right of x
    (before x_end), top line first, then leftmost. None when nothing is there."""
    c = [i for i, w in enumerate(words)
         if y - 2 <= _yc(w) < y_end and w[0][0] >= x - 1.5
         and (x_end is None or w[0][0] < x_end)]
    if not c:
        return None
    top = min(_yc(words[i]) for i in c)
    return min((i for i in c if _yc(words[i]) <= top + 3), key=lambda i: words[i][0][0])


def check_date_adjacency(typ: str, pdf: str, marks: list[Mark] | None = None, root: str | None = None,
                         warns: list[str] | None = None, words: list[list[WordBox]] | None = None,
                         stats: dict[str, int] | None = None) -> list[str]:
    """FAIL messages: in the extracted text (what an ATS reads) an entry's date
    must come BEFORE the line under its head (org / descriptor: ats.md, the org
    line anchors the date) and before the NEXT entry's head. Positions come from
    lib.typ's markers; the order is pdftotext's. `warns` (list) collects
    "not measured" notes. An entry given no date (`dated: false`) is skipped.
    `stats` (dict) receives the counts: measured / undated / unmeasured lib
    entries (an entry not built with lib `entry` carries no marker and is in
    none of them).

    A FAIL only when the order was measured and is wrong. A missing marker, missing word
    positions or an entry the words could not be matched to is a "not measured" note,
    never a FAIL."""
    marks = _typst_query(typ, ENTRY_MARKS, root) if marks is None else marks
    out: list[str] = []
    warn: Callable[[str], object] = (lambda m: warns.append(m)) if warns is not None else (lambda m: None)
    why = (" (pdftotext, like the ATS extractors that cluster lines the same way, reads a "
           "right-flushed date in place only when a text line under it overlaps its x-range; "
           "references/ats.md, Entry-with-no-bullets trap)")

    def action(name: str, h: Mark, d: Mark, o: Mark | None) -> str:
        """The FIRST clause of a FAIL: what to change in cv.typ that clears it."""
        if "anchor" not in h:
            return (f"rebuild {name} with the current lib's entry() / the family's job() "
                    "(recopy the skill's lib.typ if the CV's copy is older): its markers come "
                    "from a lib whose entry() does not anchor its date")
        short = d["x"] - ((o["x"] + o.get("w", 0)) if o is not None else h["x"]) + 3
        if d.get("inline") or short <= 3:
            return (f"rebuild {name} with the family's unmodified job() / lib entry() (no "
                    "override of its org-st/date-st/meta-size, no hand-built head): lib entry() "
                    + ("already set its date inline after the role" if d.get("inline") else
                       "already runs its org line under the date")
                    + ", so only a modified entry is read out of order; if it already is "
                    "unmodified, report the .typ and PDF")
        return (f"lengthen the org/descriptor line of {name} by at least {short:.0f}pt so it runs "
                "under the date (a hand-built head: rebuild it with the family's job() / lib "
                "entry(), which sets such a date inline): nothing under the right-flushed date "
                "anchors it, so pdftotext does not read it in place")

    recs = _entry_records(marks)
    st = stats if stats is not None else {}
    st.update(measured=0, undated=0, unmeasured=0)
    if not recs:
        return out
    if not any("dated" in r["head"] for r in recs):
        warn("no lib markers (entry heads carry no date/org part marks: old lib.typ "
             "or hand-built heads)")
        return out
    words = word_boxes(pdf, with_text=True) if words is None else words
    if words is None:
        warn("pdftotext unavailable (word positions needed)" if pdf_backend() != "pdfium"
             else f"word positions needed, {_boxes_unavailable()}")
        return out
    for ix, r in enumerate(recs):
        h, d, o = r["head"], r["date"], r["org"]
        name = f'entry "{(h.get("text") or "")[:40]}"'
        if "dated" not in h:
            warn(f"{name}: no lib markers")
            continue
        if not h["dated"]:
            st["undated"] += 1
            continue                       # entry given no date: nothing to order
        st["unmeasured"] += 1              # counted unmeasured until the judgement below is reached; each `continue` before it keeps it so
        if d is None:
            warn(f"{name}: dated but no date marker")
            continue
        if o is not None and not r["date_first"]:
            out.append(f"rebuild {name} with the family's job() / lib entry(), cells in lib "
                       "order: its employer line is EMITTED before its date (hand-built or "
                       "reordered entry), so a parser reads the date as missing")
            continue
        pg = h.get("page") or 1
        if d.get("page") != pg:
            out.append(f"rebuild {name} with the family's job() / lib entry(): its date is set "
                       f"on page {d.get('page')}, its head on page {pg}, so the date is read with "
                       "the wrong entry")
            continue
        if not 0 < pg <= len(words):
            warn(f"{name}: page {pg} not in the PDF")
            continue
        pw = words[pg - 1]
        # the org line's first word: it starts exactly at the marker's x (the
        # lib's date anchor may have set the line flush right); nearest in y
        oi = None
        if o is not None and o.get("page") == pg and o["y"] > d["y"]:
            tol = max(o.get("h", 0), 6) + 10
            c = [i for i, w in enumerate(pw) if abs(w[0][0] - o["x"]) <= 1.5
                 and abs(_yc(w) - o["y"]) <= tol and _yc(w) > d["y"]]
            oi = min(c, key=lambda i: abs(_yc(pw[i]) - o["y"])) if c else None
        d_end = pw[oi][0][1] if oi is not None else d["y"] + 4 * max(d.get("h", 0), 6)
        di = [i for i, w in enumerate(pw)
              if w[0][0] >= d["x"] - 1.5 and w[0][2] <= d["x"] + d.get("w", 0) + 1.5
              and min(d["y"], h["y"]) - 2 <= _yc(w) < d_end]
        if d.get("inline") and di:
            # inline date (lib entry, after the role): one unbreakable box on ONE
            # line, maybe the role's second; keep the line nearest the marker
            yl = min({round(_yc(pw[i])) for i in di}, key=lambda y: abs(y - d["y"]))
            di = [i for i in di if abs(_yc(pw[i]) - yl) <= 3]
        hi = _first_word(pw, h["x"], h["y"], d_end, x_end=None if d.get("inline") else d["x"] - 1)
        if not di or hi is None:
            warn(f"{name}: {'date' if not di else 'head'} words not found at the marker position")
            continue
        last = max(di)
        # the entry's column: role start .. date end; "below" = under the date row
        cl, cr = h["x"] - 1.5, d["x"] + d.get("w", 0) + 1.5
        d_bot = max(pw[i][0][3] for i in di)
        nr = next((n for n in recs[ix + 1:]
                   if (n["head"].get("page") or 1) == pg and abs(n["head"]["x"] - h["x"]) <= 2), None)
        nxt = nr["head"] if nr is not None else None
        n_end = (nr["date"]["x"] - 1 if nr is not None and nr["date"] is not None
                 and nr["date"].get("page") == pg else cr)
        ni = _first_word(pw, nxt["x"], nxt["y"], nxt["y"] + 40, x_end=n_end) if nxt is not None else None
        # first word READ of anything set below the head block in this column
        # (org line, bullet, next head, next section title)
        bi = min((i for i, w in enumerate(pw)
                  if _yc(w) > d_bot and w[0][0] < cr and w[0][2] > cl), default=None)
        st["unmeasured"] -= 1
        st["measured"] += 1
        # words of the role (head rows, left of a right-flushed date / before an
        # inline one): the date must not be read before any of them. Checks below run
        # in order of how specific the symptom is; the first that matches is reported.
        dl = sum(_yc(pw[i]) for i in di) / len(di)
        rw = [i for i, w in enumerate(pw) if i not in di and w[0][0] >= h["x"] - 1.5
              and h["y"] - 2 <= _yc(w) <= dl + 3
              and (w[0][2] <= d["x"] - 1 if not d.get("inline") else
                   (_yc(w) < dl - 3 or w[0][2] <= d["x"] - 1))]
        if rw and max(rw) > min(di):
            out.append(action(name, h, d, o) + f" \u2014 measured: {name}'s date is read in the "
                       f'middle of its role (before "{pw[max(rw)][1][:30]}")' + why)
        elif ni is not None and last > ni:
            out.append(action(name, h, d, o) + f" — measured: {name}'s date is emitted AFTER "
                       "the next entry starts, so it is read with the wrong entry" + why)
        elif oi is not None and last > oi:
            out.append(action(name, h, d, o) + f" — measured: the extracted text reads "
                       f"{name}'s employer line BEFORE its date, so a parser reads the date as "
                       "missing" + why)
        elif bi is not None and last > bi:
            out.append(action(name, h, d, o) + f" — measured: {name}'s date is emitted "
                       f'AFTER text set below the entry head (read first: "{pw[bi][1][:30]}")' + why)
        elif o is not None and oi is None:
            warn(f"{name}: employer line words not found at the marker position")
    return out


def check_duplicate_names(secs: Sequence[Mark] | None, heads: Sequence[Mark] | None) -> list[str]:
    """FAIL messages: one name used both as a section title and as a row label
    (e.g. section LANGUAGES for spoken languages + skill label "Languages" for
    programming ones), compared case-insensitively. Two things with one name
    read as one list to a human and to an ATS. Compared on `_gnorm` keys, so case and
    punctuation do not hide a clash."""
    titles: dict[str, str] = {}
    for s in secs or []:
        if _gnorm(s.get("text", "")):
            titles.setdefault(_gnorm(s["text"]), s["text"])
    out = []
    for h in heads or []:
        if h.get("kind") == "skill" and _gnorm(h["text"]) in titles:
            out.append(f'"{h["text"].strip()}" is both a skill row label and the section title '
                       f'"{titles[_gnorm(h["text"])]}" — rename one (e.g. "Programming languages")')
    return out


# ---------- font actually rendered vs font asked for (the silent Typst fallback) ----------

def pdf_char_fonts(pdf: str) -> list[tuple[str, str]] | None:
    """[(character, PDF font name)] of every non-space character, or None without pypdfium2.

    Only pdfium exposes the font of each character; poppler's pdffonts lists fonts per file,
    which cannot say which characters fell back."""
    if not _importable("pypdfium2"):
        return None
    try:
        import ctypes
        raw: Any = importlib.import_module("pypdfium2.raw")
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


def run_hidden_gate(pdf: str) -> int:
    """Print the hidden-text gate's lines; return 1 if any FAIL."""
    det: list[HiddenStat] = []
    fail = 0
    msgs = check_hidden_text(pdf, detail=det)
    for lvl, msg in msgs:
        print(f"{lvl:<5} {msg}")
        fail |= lvl == Level.FAIL
    if det and not msgs:
        print(f"OK    hidden text: {len(det)} words, each visibly inked (weakest contrast "
              f"{min(d[4] for d in det if d[4] is not None):.1f}:1, smallest box {min(d[3] for d in det):.1f}pt)")
    return fail


def run_new_gates(typ: str, pdf: str, txt: str, src: str, root: str | None = None,
                  detail: list[DetailRow] | None = None) -> int:
    """Print the gates that need `typst query` and word positions (hidden text, font fallback,
    group proximity, date adjacency, forced breaks and `~`, duplicate names); return 1 if any
    FAIL. Shared by a normal run and `--gates`, so the two cannot drift apart."""
    fail = run_hidden_gate(pdf)
    for lvl, msg in check_font_fallback(typ, pdf, root=root):
        print(f"{lvl:<5} {msg}")
        fail |= lvl == Level.FAIL
    for lvl, msg in check_group_proximity(typ, pdf, root=root, detail=detail):
        print(f"{lvl:<5} {msg}")
        fail |= lvl == Level.FAIL
    marks = _typst_query(typ, ENTRY_MARKS, root)
    heads = None if marks is None else [m for m in marks if m.get("kind") in ("entry", "skill")]
    if heads is not None and not any(h.get("kind") == "entry" for h in heads):
        print("WARN  date adjacency not measured: no lib entry()/srow() heads")
    dwarn: list[str] = []
    dst: dict[str, int] = {}
    for msg in check_date_adjacency(typ, pdf, marks=marks or [], warns=dwarn, stats=dst):
        print("FAIL  date adjacency: " + msg)
        fail = 1
    if marks is not None:
        _n = dst.get("measured", 0)
        print(f"INFO  date adjacency: {_n} lib entr{'y' if _n == 1 else 'ies'} measured, "
              f"{dst.get('undated', 0)} undated, {dst.get('unmeasured', 0)} not measured "
              "(a dated entry not built with lib entry() is not counted)")
    if dwarn:
        print(f"WARN  date adjacency not measured: {len(dwarn)} entr{'y' if len(dwarn) == 1 else 'ies'} "
              f"({'; '.join(dwarn[:3])})")
    if marks is None:
        print("WARN  date adjacency not measured: typst query unavailable")
    for msg in check_forced_linebreak(src) + check_literal_tilde(src):
        print("FAIL  " + msg)
        fail = 1
    secs = _typst_query(typ, "<vitae-sec>", root)
    if not secs:   # no <vitae-sec> marks (a CV that never wrapped `section` in wd-section(), or no query): read the #section("...") calls instead
        secs = [{"text": t} for t in re.findall(r'#section\(\s*"((?:[^"\\]|\\.)*)"', src)]
    for msg in check_duplicate_names(secs, heads):
        print("FAIL  duplicate name: " + msg)
        fail = 1
    return fail


# ---------- main gate ----------

HEADER_RE = re.compile(r"^//\s*vitae:\s*pages=(\d+)(?:\s+fill=(\d+)-(\d+))?",
                       re.M)


def pages_from_name(typ: str) -> str:
    """The page count a headerless deliverable declares in its own file name."""
    return "2" if re.search(r"[-_]2\s*p(?:ages?)?(?![a-z])",
                            os.path.basename(typ), re.I) else "1"


# Whole-word stems of non-CV companion deliverables (step 7 application guide, cover letter, readme)
# that `verify.py --all` skips when they carry no `// vitae:` header (step 6).
NON_CV_RE = re.compile(
    r"(?<![^\W\d_])(?:guide|lettre|letter|cover|lisez-moi|readme)(?![^\W\d_])",
    re.I)


def is_gated(typ: str) -> bool:
    """--all's rule: gate every .typ except known non-CV deliverables (guide,
    letter, cover, lisez-moi, readme by name); a `// vitae:` header opts in."""
    if not NON_CV_RE.search(os.path.basename(typ)):
        return True
    try:
        with open(typ, encoding="utf-8") as fh:
            return bool(HEADER_RE.search(fh.read(4096)))
    except OSError:
        return False


# Both markers (and HEADER_RE in is_gated/check_all) are looked for in the first 4096 bytes:
# they sit on line 1 (or in the opening comment block) so reading 4 KiB avoids loading large files.
ACADEMIC_MARKER = "// vitae-academic:"
LETTER_MARKER = "// vitae letter template"


def is_academic(path: str) -> bool:
    """True for an academic CV, which this gate must NOT judge.

    An academic CV is a different genre: the atom is the ENTRY, not the
    section, there is no fill target at all, and its length is whatever the
    record is — 13 pages is ordinary. This gate is calibrated on one- and
    two-page industry resumes, and `check_all` guesses a headerless file's
    page count from its NAME (defaulting to 1), so a sweep would fail an
    academic CV for being itself. It carries its own gate:
    `scripts/verify_academic.py`. The marker is a line-1 comment the academic
    template emits (templates/academic/cv.typ).
    """
    try:
        with open(path, encoding="utf-8") as fh:
            return ACADEMIC_MARKER in fh.read(4096)
    except OSError:
        return False


def is_letter(path: str) -> bool:
    """True for a cover letter, which this gate must NOT judge either.

    A letter is prose with a letterhead, not a sectioned resume: it has ONE
    rule, by design (templates/letter.typ: « one thin rule in the CV's accent
    colour »), so the section-device quorum — which asks for a boundary
    SYSTEM, two devices minimum — is asking a letter for sections it does not
    have. It carries its own gate, `scripts/verify_letter.py`.

    It only surfaced on 2026-09-13, when the furniture/ink dedupe was moved
    into one coordinate frame: until then the letterhead rule was counted
    TWICE, once by each detector, and the letter cleared a quorum of 2 on a
    single device. The letter was never right; the double count hid it.

    The marker is the template's own line 1 — nothing new to emit, and it
    travels with a delivered copy the way the family banner does.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            return LETTER_MARKER in fh.read(4096)
    except OSError:
        return False


def check_all(directory: str) -> int:
    """Run the single-file gate over every .typ under `directory`.

    Re-invokes this script per file rather than refactoring main() apart: the
    point is that each deliverable gets EXACTLY the check it would get alone,
    and a subprocess guarantees that for free (including its exit code and its footer).
    lib*.typ and icons*.typ are shared code, not deliverables; academic CVs and letters carry
    their own gates (`is_academic`, `is_letter`).
    """
    typs = sorted(f for f in glob.glob(os.path.join(directory, "**", "*.typ"),
                                       recursive=True)
                  if not os.path.basename(f).startswith(("lib", "icons"))
                  and not is_academic(f) and not is_letter(f))
    for t in [t for t in typs if not is_gated(t)]:
        print(f"SKIP  {t}  (name matches a non-CV deliverable, no `// vitae:` header)")
    skipped = len(typs) - len([t for t in typs if is_gated(t)])
    typs = [t for t in typs if is_gated(t)]
    if not typs:
        print(f"{skipped} skipped, 0 checked" if skipped
              else f"no .typ found under {directory}")
        return 1
    fail, unchecked = 0, []
    for typ in typs:
        with open(typ, encoding="utf-8") as fh:
            m = HEADER_RE.search(fh.read(4096))
        if m:
            args = [m.group(1)] + ([m.group(2), m.group(3)] if m.group(2) else [])
        else:
            # No header: take the page count from the FILE NAME, which is the one expectation
            # this repo already states out loud (`*-2page.typ` is two pages, every other
            # deliverable is one; SKILL.md step 4 and the read-me sweep are written that way).
            # Not one of the repo's own 30 .typ files carries the header, so demanding it made
            # --all return 30 UNCHECKED and exit 1 on the very corpus it exists to guard. Fill
            # stays undeclared and is reported, not failed: a page count is inferable from a
            # name, a fill target is not, and inventing one would be the fitted-curve mistake
            # again. A `// vitae:` header on a deliverable whose fill matters wins over the name.
            args = [pages_from_name(typ)]
            unchecked.append(typ)
        print(f"\n=== {typ}  (expects {' '.join(args)}"
              f"{'' if m else ' — inferred from the file name, no header'})")
        r = subprocess.run([sys.executable, os.path.abspath(__file__), typ]
                           + args)
        fail |= bool(r.returncode)
    if unchecked:
        print("\nNOTE — page count inferred from the file name, fill not "
              "checked (add `// vitae: pages=N fill=A-B` to pin either):")
        for t in unchecked:
            print(f"  {t}")
    print("\n" + ("FAIL — see above" if fail else
                  f"PASS — {len(typs)} deliverable(s), "
                  f"all siblings checked together"))
    return fail


def digest_of(f: str) -> str:
    """sha256 of a lib file, BOM and CRLF normalised, so a copy re-saved on Windows still matches."""
    with open(f, "rb") as fh:
        data = fh.read()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def check_lib_integrity(typ_path: str, skill_dir: str | None = None) -> list[Finding]:
    """Return [(level, msg)] for the lib.typ the CV imports (Level.FAIL/Level.WARN);
    empty when it is the skill's own lib or the CV imports none. Runs before
    compilation so the message survives a Typst error.

    FAIL for a lib whose content differs from the skill's (older release or edited: a model once
    rewrote it from memory, dropped `derive()` and looped; BOM and CRLF are ignored); WARN, not FAIL,
    when a lib.typ sits beside the CV but no import resolves to it (integrity unchecked)."""
    skill_dir = skill_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ref = os.path.join(skill_dir, "templates", "lib.typ")
    # Follow local #import "x.typ" chains (cv.typ -> family.typ -> lib.typ).
    lib, shown, seen, todo = None, None, set(), [os.path.abspath(typ_path)]
    direct = False   # the CV's own file imports lib.typ (not a family file)
    while todo and lib is None:
        f = todo.pop(0)
        if f in seen:
            continue
        seen.add(f)
        try:
            with open(f, encoding="utf-8-sig", errors="replace") as fh:
                src = fh.read()
        except OSError:
            continue
        src = _strip_typst_comments(src)
        for imp in re.findall(r'\bimport\s*\(?\s*"([^"]+\.typ)"', src):
            base = os.path.dirname(os.path.abspath(typ_path)) if imp.startswith("/") else os.path.dirname(f)
            path = os.path.normpath(os.path.join(base, imp.lstrip("/") if imp.startswith("/") else imp))
            if os.path.basename(imp) == "lib.typ":
                lib, shown = path, imp
                direct = f == os.path.abspath(typ_path)
                break
            todo.append(path)
    if lib is None and os.path.isfile(ref) and os.path.isfile(
            os.path.join(os.path.dirname(os.path.abspath(typ_path)), "lib.typ")):
        return [(Level.WARN, "lib import not recognised: a lib.typ sits next to the CV but no #import "
                         "resolves to it, so its integrity was NOT checked")]
    if lib is None or not os.path.isfile(ref):
        return []
    cv_dir = os.path.dirname(lib)
    import shlex
    cp = f"cp {shlex.quote(ref)} {shlex.quote(cv_dir + '/')}"
    here = os.path.dirname(os.path.abspath(typ_path))
    if direct and os.path.normpath(cv_dir) != os.path.normpath(here):
        # A family template copied without its "change the import" step: the
        # import still climbs out of the CV folder. Copy lib.typ NEXT TO cv.typ.
        cp = f"cp {shlex.quote(ref)} {shlex.quote(here + '/')}"
        if not os.path.isfile(lib) or digest_of(lib) != digest_of(ref):
            return [(Level.FAIL, f'cv.typ imports "{shown}" (outside this folder): change the import to '
                             f'`#import "lib.typ": *` and copy lib.typ next to cv.typ: {cp}')]
    if not os.path.isfile(lib):
        return [(Level.FAIL, f"{shown} is imported but missing — copy it: {cp}")]
    if digest_of(lib) == digest_of(ref):
        return []
    return [(Level.FAIL, "lib.typ differs from the skill's (older release or edited): "
                     f"copy it again: {cp}")]


_LOWERED_WARN = ("WARN  fill target lowered below drawn target {a} — allowed ONLY if "
                 "the facts are exhausted; tell the user the page is under-filled and which "
                 "facts would fill it; never pad or invent to reach it (rule 1)")
_LOWERED_FAIL = ("FAIL  fill target lowered to {lo}-{hi}% is below the lowered-target floor "
                 "({fl}%, drawn target {a}) — an exhausted fact sheet lowers the target by a "
                 "few points, never below {fl}%; ask the user for more facts, drop to fewer "
                 "pages, or raise FILL_MIN")


_LEADING_WARN = ("WARN  leading {l:.3f}em reads as DOUBLE-SPACED on multi-line paragraphs "
                 "(shipped templates stay <= 0.96em; warns above {t:.2f}em) — the page is "
                 "padded with air, not content. Prefer adding a real fact (a bullet, a "
                 "result, a project) over leading; if the facts are exhausted, accept the "
                 "lower fill and tell the user")


# Relative twin of LEADING_WARN: prose leading against bullet spacing.
LEADING_RATIO_WARN = 1.95   # leading / list spacing; strictly above it the WARN fires (a real 1.0em/0.5em run, ratio 2.00, read double-spaced; highest shipped template is 1.89)
_LEADING_RATIO_WARN = ("WARN  leading {l:.3f}em vs bullet spacing {s:.3f}em (ratio {r:.2f}, warns above "
                       "{t:.2f}) — wrapped prose reads DOUBLE-SPACED next to the bullets. Lower the "
                       "leading (`--tune` downward, or reduce `#set par(leading:)`) or raise the "
                       "`#set list(spacing:)` so prose and bullets read with the same rhythm")


def _leading_warn(typ: str) -> str:
    """The WARN line when cv.typ's document leading is above LEADING_WARN (absolute check), or above
    LEADING_RATIO_WARN times the explicit top-level list spacing (relative check; the absolute one
    takes precedence), else ''. A WARN, never a FAIL: the page may be honestly full; the
    message points at the facts to add instead."""
    try:
        lead, lsp = _doc_par_list(open(typ, encoding="utf-8").read())
    except OSError:
        return ""
    if lead is None:
        return ""
    if lead > LEADING_WARN + 1e-9:
        return _LEADING_WARN.format(l=lead, t=LEADING_WARN)
    # Relative check: only when the list spacing is explicit (a list with no
    # `spacing:` follows Typst's own defaults, so the ratio is unknown: silent).
    if lsp and lsp > 0 and lead / lsp > LEADING_RATIO_WARN + 1e-9:
        return _LEADING_RATIO_WARN.format(l=lead, s=lsp, r=lead / lsp, t=LEADING_RATIO_WARN)
    return ""


# Type size is the other way to pad a page: LEADING_WARN's twin for the body size.
BODY_SIZE_WARN = 11.0   # pt; strictly above it the WARN fires (shipped templates: 10.5pt, margin-index and letter 11pt)
_BODY_SIZE_WARN = ("WARN  body text {z:g}pt (shipped templates stay at 10.5-11pt; warns above {t:g}pt) — "
                   "the page is padded with type size, not content, and the heading/role/meta "
                   "hierarchy inverts because the template sizes are absolute pt. Bring the body "
                   "back to the template size and add a real fact (a bullet, a result, a project) "
                   "instead; if the facts are exhausted, accept the lower fill and tell the user")


def _body_size_warn(typ: str) -> str:
    """The WARN line when cv.typ's top-level body text size is above BODY_SIZE_WARN, else ''."""
    try:
        size = _doc_body_size(open(typ, encoding="utf-8").read())
    except OSError:
        return ""
    if size is not None and size > BODY_SIZE_WARN + 1e-9:
        return _BODY_SIZE_WARN.format(z=size, t=BODY_SIZE_WARN)
    return ""


def _check_cv(typ: str, expected: str, fmin: str | None, fmax: str | None,
              facts: str | None = None) -> NoReturn:
    """The one-file gate: cv.typ PAGES [FILL_MIN FILL_MAX] [--facts facts.md]. Never returns:
    it exits 0 on PASS and 1 on any FAIL, after printing every line so one run lists every fix.
    The order of the gates is the one documented in the module docstring."""
    pdf = re.sub(r"\.typ$", "", typ) + ".pdf"
    fail = 0
    # The drawn fill target lives in the cv.typ header; the command line may
    # not quietly lower it (a lowered target is a WARN carried to the PASS line).
    # The leading and body-size WARNs print up front and again after PASS, where they are read.
    if not _fill_args_ok(fmin, fmax):
        sys.exit(1)
    drawn, drawn_warns = _drawn_fill(typ)
    for w in drawn_warns:
        print(w)
    lead_warn = _leading_warn(typ)
    if lead_warn:
        print(lead_warn)
    size_warn = _body_size_warn(typ)
    if size_warn:
        print(size_warn)
    lowered = ""
    if drawn:
        if not (fmin and fmax):
            fmin, fmax = str(drawn[0]), str(drawn[1])
            print(f"INFO  fill target {fmin}-{fmax}% drawn for this CV (family table / cv.typ header)")
        elif int(fmin) < min(drawn[0], LOWERED_FILL_FLOOR):
            print(_LOWERED_FAIL.format(lo=fmin, hi=fmax, fl=LOWERED_FILL_FLOOR,
                                       a=f"{drawn[0]}-{drawn[1]}"))
            fail = 1
        elif int(fmin) < drawn[0]:
            lowered = f"{drawn[0]}-{drawn[1]} → {fmin}-{fmax}"
            print(_LOWERED_WARN.format(a=f"{drawn[0]}-{drawn[1]}"))

    deps_ok, use_cli, backend = preflight()
    if not deps_ok:
        sys.exit(1)
    STATE.footer = _FOOTER_GATE     # armed only now: before this, a FAIL is not about cv.typ

    for level, msg in check_lib_integrity(typ):
        print(f"{level}  {msg}")
        fail |= level == Level.FAIL

    ensure_icons(typ)     # the icons file the CV imports must exist before it compiles
    ok, err = compile_pdf(typ, pdf, use_cli)
    if not ok:
        print("FAIL  compile")
        print(err)
        sys.exit(1)
    if "did not converge" in err:
        print("FAIL  compile: Typst warns the layout did not converge, so the PDF depends on "
              "which iteration it stopped at — either the CV's lib.typ is an older copy (recopy "
              "the skill's lib.typ next to it) or a construct in cv.typ reads its own layout "
              "(context / query / locate / measure) and changes it; remove that construct "
              "(the shipped lib converges)")
        fail = 1
    if err.strip():
        print("WARN  compile stderr (a missing font only warns and falls back):")
        print(err)

    pages = count_pages(pdf, backend)
    if pages == expected:
        print(f"OK    pages: {pages}")
    else:
        print(f"FAIL  pages: {pages} (expected {expected}) — cut or add real content in cv.typ "
              f"(or, if {expected} was the wrong target, re-run with the right page count)")
        fail = 1

    family = family_from_path(typ)
    pages_text = word_boxes(pdf, with_text=True)  # None => no word boxes: the dependent gates degrade to a WARN
    pages_boxes = [[b for b, _ in pg] for pg in pages_text] if pages_text is not None else None

    with tempfile.TemporaryDirectory() as tmp:
        pngs = render_pngs(typ, tmp, use_cli)
        if not pngs:
            # No PNG => measure_fill never ran => the fill target is UNTESTED.
            # Silently passing here is how a broken render reads as a PASS: this is a FAIL
            # because the tool is required (preflight), so a missing render is a fault.
            print("FAIL  no PNG rendered — fill unmeasured")
            fail = 1
        if not (fmin and fmax):
            print("WARN  fill NOT checked (no FILL_MIN FILL_MAX given) — rerun "
                  f"as scripts/verify.py {shlex.quote(typ)} {expected} FILL_MIN FILL_MAX; "
                  "the targets come from the pick_design.py report "
                  '("fill target : NN-NN%") and differ per family')
        under_fills: list[int] = []
        for i, path in enumerate(pngs):
            result = measure_fill.measure(path)
            if "blank page" in result:
                print(f"FAIL  fill: {path}: {result}")
                fail = 1
                continue
            if fmin and fmax:
                m = re.search(r"to (\d+)%", result)
                if not m:
                    continue
                y = int(m.group(1))
                if y < int(fmin) or y > int(fmax):
                    print(f"FAIL  fill: {path}: {result} (target {fmin}-{fmax}%) — "
                          f"run `scripts/verify.py --tune {shlex.quote(typ)} {expected} {fmin} {fmax}` "
                          "(adjusts leading), or add/cut real content")
                    if y < int(fmin):
                        under_fills.append(y)
                    fail = 1
                else:
                    print(f"OK    fill: {path}: {result}")
            else:
                print(f"INFO  fill: {path}: {result} (target = (100 - bottom-margin%) - 0..2%)")
            boxes = pages_boxes[i] if pages_boxes and i < len(pages_boxes) else None
            if pages_text is None and i == 0:
                print(f"WARN  text-clip gate skipped: {_boxes_unavailable()}")
            for msg in check_text_clip(path, pages_text[i] if pages_text and i < len(pages_text) else None):
                print("FAIL  " + msg)
                fail = 1
            for is_fail, msg in check_whitespace(path, boxes=boxes, family=family,
                                                 degraded=boxes is None):
                print(f"{'FAIL' if is_fail else 'OK  '}  {msg}")
                fail = fail or int(is_fail)

    if under_fills:
        lowest = min(under_fills)    # FILL_MIN applies to every page: the lowest page decides
        if lowest < LOWERED_FILL_FLOOR:
            print(f"NEXT  fill {lowest}% is below the {LOWERED_FILL_FLOOR}% floor, so a lowered target "
                  "cannot pass: a fact is missing — add real facts or ask the user"
                  + (", or drop to fewer pages" if int(expected) > 1 else ""))
        else:
            print("NEXT  if --tune already reported UNDER-FILLED, a fact is missing: add one, or — only "
                  "if the facts are exhausted — pass a lowered target: "
                  f"`scripts/verify.py {shlex.quote(typ)} {expected} {lowest} {fmax}` (FILL_MIN = the "
                  f"lowest fill the gate prints, not below {LOWERED_FILL_FLOOR}) and tell the user")
    # Clone markers: the template's own accent and its "Category: items" skills block, left in
    # place, make every CV from the skill look alike (references/design/core.md, three clone markers).
    typ_text = open(typ, encoding="utf-8").read()
    if "7d2231" in typ_text.lower():
        print("WARN  template default accent (#7d2231) — run scripts/pick_design.py and apply the family it draws (references/design/families/<family>.md)")
    if "[#cat:]" in typ_text:
        print("WARN  template skills block (\"Category: items\") — clone marker #2; use the chosen family's skills shape")

    if backend == "pypdf":     # the fallback extractor: say so once, `bad()` below then downgrades to WARN
        print("WARN  pypdf extraction is indicative only (spurious spaces inside words, e.g. \"FORMA TION\") — poppler's pdftotext is the reference extractor (references/ats.md)")

    txt = extract_text(pdf, backend)

    def bad(msg: str) -> None:
        """FAIL on the reference extractor, WARN on the pypdf fallback: pypdf's
        extraction is indicative only (this script says so above), so a hard
        FAIL on it would be a verdict the evidence does not support."""
        nonlocal fail
        if backend != "pypdf":
            print("FAIL  " + msg)
            fail = 1
        else:
            print("WARN  " + msg + " — pypdf extraction is indicative; confirm with pdftotext before believing it")

    if not txt.strip():
        bad("extraction empty")
    # Letterspaced capitals break keyword matching in an ATS. First pattern: 4+ STANDALONE
    # capitals (the \b anchors keep "B.Sc. C S M Sc", dotted abbreviations, out). Second
    # pattern: tracking's real pdftotext shape, chunked rather than fully spaced
    # ("S O F T WA RE"). Known limit: a space injected INSIDE a word ("FORMA TION") is not
    # detectable here: it is a pypdf extraction artefact, not a layout bug, and only the
    # pypdf path (WARN-only above) produces it.
    spaced: str | re.Match[str] | None = re.search(r"\b(?:[A-Z] ){3,}[A-Z]\b", txt)
    if not spaced:
        for line in txt.split("\n"):
            tok = line.split()
            if (len(tok) >= 4 and all(re.fullmatch(r"[A-Z]{1,2}", t) for t in tok)
                    and sum(len(t) == 1 for t in tok) >= 2):
                spaced = line
                break
    if spaced:
        bad("spaced-out text in extraction (letterspacing/tracking?)")
    # Per PAGE: a date alone at the foot of a page is read by an ATS as belonging to no entry;
    # it lands at the end of its own page, not only at the end of the document.
    for pageno, page in enumerate(txt.split("\f"), 1):
        non_blank = [l for l in page.split("\n") if l.strip()]
        last = non_blank[-1] if non_blank else ""
        if len(last) <= 25 and re.search(r"[0-9]{4}\s*$", last):
            bad(f'orphaned date at end of page {pageno} of the extraction ("{last}") — bullet-less grid entry; see the trap in references/ats.md')
    for is_fail, msg in check_no_split(typ_text, txt.split("\f")):
        if is_fail:
            bad(msg)
        else:
            print("OK    " + msg)

    if facts:
        try:
            facts_text = open(facts, encoding="utf-8").read()
        except OSError as e:
            print(f"FAIL  --facts: cannot read {facts} ({e.strerror})")
            fail = 1
        else:
            for w in check_facts_coverage(txt, facts_text):
                print(w)
    bullets = check_bullet_chars(txt)
    if bullets:
        print(f'WARN  {len(bullets)} line(s) start with a bullet character in the extraction (e.g. "{bullets[0][:30]}") — ATS prints it or puts it alone on a line; draw list markers as vector shapes (references/ats.md)')

    if use_cli or typst_can_query():
        fail |= run_new_gates(typ, pdf, txt, typ_text)
    else:
        # No `typst query`: say which gates are skipped, then run the ones that need only the
        # PDF or the source text, so the degraded run still covers as much as it can.
        print("WARN  grouping / date-adjacency / duplicate-name gates NOT checked (need the typst CLI or typst-py with query)")
        fail |= run_hidden_gate(pdf)
        for lvl, msg in check_font_fallback(typ, pdf):
            print(f"{lvl:<5} {msg}")
            fail |= lvl == Level.FAIL
        for msg in check_forced_linebreak(typ_text) + check_literal_tilde(typ_text):
            print("FAIL  " + msg)
            fail = 1

    # The extraction is printed last, whatever the verdict: the reading-order check is the
    # agent's, by hand (references/steps/6-verify.md), and needs the text next to the PASS/FAIL.
    print("──── extraction (check reading order, orphaned dates, intact skill lines) ────")
    print(txt)

    if fail == 0:
        if lowered:
            print(f"PASS (fill target lowered: {lowered}) all mechanical checks — now LOOK at the PNGs")
            print(_LOWERED_WARN.format(a=lowered.split(" ")[0]))
        elif fmin and fmax:
            print("PASS  all mechanical checks — now LOOK at the PNGs")
        else:
            print("PASS  mechanical checks except fill (no FILL_MIN FILL_MAX "
                  "given) — rerun with the fill targets from the pick_design.py "
                  "report, then LOOK at the PNGs")
        if lead_warn:        # repeated after PASS so a green run does not bury them
            print(lead_warn)
        if size_warn:
            print(size_warn)

    sys.exit(fail)


class _Parser(argparse.ArgumentParser):
    """An ArgumentParser that fails the way the hand-rolled argv code did: the
    usage text this script always printed, with the exit code it always used
    (argparse's own message and its exit 2 are never shown). `plain` is the old
    `sys.exit("usage: ...")` shape (stderr, exit 1); otherwise the text is
    printed to stderr and the script exits `code`. Every mode builds its own parser
    with its own usage text; main() is the one place those strings live."""

    def __init__(self, usage_text: str, code: int = 2, plain: bool = False) -> None:
        super().__init__(add_help=False, allow_abbrev=False)
        self._usage_text, self._code, self._plain = usage_text, code, plain

    def error(self, message: str) -> NoReturn:
        if self._plain:
            sys.exit(self._usage_text)
        print(self._usage_text, file=sys.stderr)
        sys.exit(self._code)


def main() -> None:
    """Mode dispatch, and the owner of every usage text (what a usage error and --help print).

    The first argument picks the mode, checked in this order: --all, --gates, --render/--text,
    --doctor, --selftest, --tune; anything else is the one-file gate. Modes that need no
    cv.typ (--doctor, --selftest, --render, --text) come before the positional parsing, which
    would otherwise reject them for a missing `typ`. Every mode ends in sys.exit, so a later
    branch is reached only when no earlier one matched."""
    argv = sys.argv[1:]
    prog = os.path.basename(sys.argv[0])

    if argv and argv[0] == "--all":
        ap = _Parser("usage: verify.py --all DIR", code=1, plain=True)
        ap.add_argument("dir")
        # "--" first: every later word is a positional, as before; extras are ignored
        sys.exit(check_all(ap.parse_known_args(["--"] + argv[1:])[0].dir))
    if argv and argv[0] == "--gates":
        # the typst-query gates only, on an already compiled PDF: --gates cv.typ cv.pdf [--root DIR]
        # (the test fixtures import ../../templates, so they need the repo as root)
        ap = _Parser("usage: verify.py --gates cv.typ cv.pdf [--root DIR]", code=1, plain=True)
        ap.add_argument("typ")
        ap.add_argument("pdf")
        ap.add_argument("--root", default=None)
        ga = ap.parse_known_args(argv[1:])[0]
        STATE.footer = _FOOTER_GATE
        rows: list[DetailRow] = []
        rc = run_new_gates(ga.typ, ga.pdf, extract_text(ga.pdf, pdf_backend()),
                           open(ga.typ, encoding="utf-8").read(), root=ga.root, detail=rows)
        print("DETAIL " + json.dumps(rows))
        sys.exit(rc)
    if argv and argv[0] in ("--render", "--text"):
        # agent-facing look/read helpers, so no instruction has to name pdftoppm or pdftotext
        ap = _Parser("usage: verify.py --render cv.pdf [--out DIR] [--ppi N] [--crops]   one PNG per page, <stem>-p<N>.png\n"
                     "         --crops: also 300 ppi crops of the fills and icons, <stem>-p<N>-<band>.png\n"
                     "       verify.py --text cv.pdf                          the text the gates read",
                     code=1, plain=True)
        ap.add_argument("pdf")
        ap.add_argument("--out", default=None)
        ap.add_argument("--ppi", type=int, default=HIDDEN_PPI)
        ap.add_argument("--crops", action="store_true")
        ra = ap.parse_known_args(argv[1:])[0]
        if not os.path.isfile(ra.pdf):
            sys.exit(f"FAIL  {argv[0]}: cannot read {ra.pdf}")
        if pdf_unreadable(ra.pdf):
            sys.exit(f"FAIL  {argv[0]}: {ra.pdf} is not a readable PDF (corrupt or not a PDF)")
        if argv[0] == "--text":
            backend = pdf_backend()
            if backend is None:
                sys.exit("FAIL  --text: no PDF reader (install poppler-utils, or `pip install pypdfium2`)")
            sys.stdout.write(extract_text(ra.pdf, backend))
            sys.exit(0)
        if ra.ppi < 1:
            sys.exit("FAIL  --render: --ppi must be a positive number")
        out_dir = ra.out or tempfile.mkdtemp(prefix="vitae-render-")
        pngs = render_pages(ra.pdf, out_dir, ra.ppi)
        if not pngs:
            sys.exit("FAIL  --render: no rasterizer (`pip install pypdfium2`, or install poppler-utils for pdftoppm)")
        print("\n".join(pngs))
        if ra.crops:
            crops, notes = render_crops(ra.pdf, out_dir)
            if crops:
                print("\n".join(crops))
            for note in notes:
                print(note, file=sys.stderr)
        sys.exit(0)
    if argv and argv[0] == "--doctor":     # dependency preflight only; no cv.typ, no footer
        ok, _, _ = preflight()
        sys.exit(0 if ok else 1)

    if argv and argv[0] == "--selftest":
        # Lazy, so a normal run never loads the self-test. It lives in verify_selftest.py and
        # needs this module's functions. Run as a script this module is __main__, so register it
        # as `verify` first: the self-test's `import verify` then gets THIS module, not a second
        # copy that would re-run the script.
        sys.modules.setdefault("verify", sys.modules[__name__])
        import verify_selftest  # noqa: PLC0415 -- lazy: imports verify
        verify_selftest.run()

    if argv and argv[0] == "--tune":
        # verify.py --tune cv.typ PAGES FILL_MIN FILL_MAX [LO HI]; the "--" makes every word a positional
        ap = _Parser("usage: verify.py --tune cv.typ PAGES FILL_MIN FILL_MAX "
                     "[LEADING_LO LEADING_HI]")
        ap.add_argument("typ")
        for name in ("pages", "fill_min", "fill_max"):
            ap.add_argument(name)
        ap.add_argument("lo", nargs="?")
        ap.add_argument("hi", nargs="?")
        ta = ap.parse_known_args(["--"] + argv[1:])[0]
        if not _fill_args_ok(ta.pages, ta.fill_min, ta.fill_max):
            sys.exit(1)
        # LO alone is ignored: the bounds come as a pair or not at all
        bounds = ((float(ta.lo), float(ta.hi)) if ta.hi is not None else (None, None))
        sys.exit(tune(ta.typ, int(ta.pages), int(ta.fill_min), int(ta.fill_max),
                      lo=bounds[0], hi=bounds[1]))

    # Default mode: the one-file gate. --facts is the only option here, so it is cut out by hand.
    facts_path: str | None = None
    if "--facts" in argv:                   # pulled out first: the parser below treats every word as positional
        i = argv.index("--facts")
        if i + 1 >= len(argv):
            sys.exit("usage: verify.py cv.typ EXPECTED_PAGES [FILL_MIN FILL_MAX] --facts facts.md")
        facts_path = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    ap = _Parser(f"usage: {prog} cv.typ EXPECTED_PAGES [FILL_MIN FILL_MAX] [--facts facts.md]\n"
                 f"         --facts: WARN on every year / numeric month+year / number in the CV absent from the facts file\n"
                 f"       {prog} --tune cv.typ PAGES FILL_MIN FILL_MAX [LO HI]\n"
                 f"       {prog} --all DIR\n"
                 f"       {prog} --doctor\n"
                 f"       {prog} --selftest")
    ap.add_argument("typ")
    ap.add_argument("expected")
    ap.add_argument("fill_min", nargs="?")
    ap.add_argument("fill_max", nargs="?")
    ca = ap.parse_known_args(["--"] + argv)[0]
    _check_cv(ca.typ, ca.expected, ca.fill_min, ca.fill_max, facts_path)


def _run() -> None:
    """Entry point: run main(), and on a non-zero exit print the armed `_footer` last, so the
    next step is the final thing a reader sees. Exit codes are passed through unchanged."""
    try:
        main()
    except SystemExit as e:
        if STATE.footer and isinstance(e.code, int) and e.code != 0:
            print(STATE.footer, flush=True)
        raise


if __name__ == "__main__":
    _run()
