"""Checks on the text extracted from the PDF: facts coverage, bullet characters, hidden text, metadata.

A leaf under verify_pdf: no `import verify`.
"""
from __future__ import annotations

import importlib
import math
import re
import shutil
import tempfile
import unicodedata
import warnings
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import partial

from PIL import Image

from vitae.core import proc
from vitae.core.base import HIDDEN_PPI, HiddenStat, WordBox
from vitae.core.colour import contrast_from_lum, counted_luminances, rel_luminance
from vitae.core.env import pdf_backend
from vitae.core.level import Finding, Level
from vitae.core.pdfium import PdfiumDoc
from vitae.verify.lang import is_latin, strip_latin_marks
from vitae.verify.pdf import (
    bbox_pages,
    boxes_unavailable,
    pdf_unreadable,
    pdfinfo_output,
    pdfium_doc,
    render_pages_png,
)

# Date and number patterns of check_facts_coverage, matched on folded text (`_fold`, `_fold1`).
_NUM_MY_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})[-/.](0?[1-9]|1[0-2])(?!\d)|(?<!\d)(0?[1-9]|1[0-2])[-/.]((?:19|20)\d{2})(?!\d)")


_YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")


_NUM_RE = re.compile(r"[$€£]?(\d+(?:[.,]\d+)*)\s?(%|[kKmM](?![^\W\d_])|)")


def _fold1(s: str) -> str:
    """Length-preserving fold (one output char per input char): accents go on Latin letters only, so the vowels
    and tones of Devanagari or Thai keep their code points."""
    out: list[str] = []
    for c in s:
        d = unicodedata.normalize("NFKD", c)[0] if is_latin(c) else c
        low = d.lower()
        out.append(low if len(low) == 1 else d)
    return "".join(out)


def _fold(s: str) -> str:
    """Lower-case, accents stripped from Latin letters, dashes unified, whitespace collapsed."""
    s = strip_latin_marks(s).lower()
    s = re.sub(r"[–—‒−]", "-", s).replace("’", "'")
    return re.sub(r"\s+", " ", s)


# A phone number is a contact detail, not a claim: its digit groups are neither years nor numbers.
_PHONE_RE = re.compile(
    r"(?<![\w])(?:\+?\d{1,2}[ .\-\u00a0]?)?(?:\(\d{3}\)|\d{3})[ .\-\u00a0]?\d{3}[ .\-\u00a0]?\d{4}(?!\d)")


# The same outside North America: "06 12 34 56 78", "+49 30 1234567", "0151-2345678". A leading + or 0, then digit groups
# split by space/dot/hyphen. Only 8+ digits in 2+ groups (or a + prefix) count as a number, so "300 staff", "840 ms",
# "1 500 000" (no leading 0) and "2019 - 2021" are never read as one.
_PHONE_GEN_RE = re.compile(r"(?<![\w.,])(?:\+\d{1,3}|0)(?:[ .\-\u00a0]?\(?\d{1,8}\)?)+(?!\d)")


# A numeric date ("01.03.2019", "05-06-2021") fits the pattern above when its day starts with 0, so dates are found first
# and masked: a phone match must never swallow one, and a phone beside a date is still blanked. The year is limited to
# 19xx/20xx and a date may not touch another digit group ("04-12-3456-7890", "05-06-2021-1234" are phones) unless that
# group is itself a date (a range such as "01.03.2019-05.06.2021").
_DATE_CORE = r"(?:0?[1-9]|[12]\d|3[01])([./-])(?:0?[1-9]|1[0-2])\1(?:19|20)\d\d"


_NUM_DATE_SCAN_RE = re.compile(r"(?<!\d)" + _DATE_CORE + r"(?!\d)(?![./-](?!" + _DATE_CORE.replace(r"\1", r"\2") + r")\d)")


_NUM_DATE_END_RE = re.compile(_DATE_CORE + r"$")


def _blank_phones(line: str) -> str:
    """`line` with every phone number replaced by spaces (same length: spans carry over)."""
    masked = list(line)
    dates: list[tuple[int, int]] = []
    for m in _NUM_DATE_SCAN_RE.finditer(line):
        i = m.start()
        # "1234-05-06-2021": a date glued to a digit group by a separator is part of a longer number, not a date.
        if i >= 2 and line[i - 1] in "./-" and line[i - 2].isdigit() and not _NUM_DATE_END_RE.search(line[:i - 1]):
            continue
        masked[i:m.end()] = "#" * (m.end() - i)
        dates.append((i, m.end()))
    text = "".join(masked)
    text = _PHONE_RE.sub(lambda m: " " * len(m.group(0)), text)

    def generic(m: re.Match[str]) -> str:
        t = m.group(0)
        digits = len(re.sub(r"\D", "", t))
        groups = len(re.findall(r"\d+", t))
        return " " * len(t) if digits >= 8 and (t.startswith("+") or groups >= 2) else t
    text = _PHONE_GEN_RE.sub(generic, text)
    out = list(text)
    for i, j in dates:      # the placeholders are the only non-phone text there: put the dates back
        out[i:j] = line[i:j]
    return "".join(out)


def _num_values(text: str) -> set[float]:
    text = re.sub(r"(?<=\d)[ \u00a0\u202f](?=\d{3}(?!\d))", "", text)
    out: set[float] = set()
    for m in _NUM_RE.finditer(text):
        u = m.group(2).lower()
        for v in _readings(m.group(1)):
            out.add(v * (1000 if u == "k" else 1_000_000 if u == "m" else 1))
    return out


def _readings(raw: str) -> list[float]:
    """Values a digit string can mean. "1.500" is BOTH 1500 (thousands: DE/ES/IT/PT/NL/TR) and 1.5 (decimal), so both
    readings are returned; "1,500" stays 1500 (thousands: EN), "1.5", "3,14" and "1,5000" are decimals;
    "1.500.000" and "1.500,5" read the dots as thousands. Any other shape reads as it always did."""
    parts = re.split(r"[.,]", raw)
    seps = re.findall(r"[.,]", raw)
    try:
        if seps == ["."] and len(parts[1]) == 3 and len(parts[0]) <= 3 and not parts[0].startswith("0"):
            return [float(parts[0] + parts[1]), float(parts[0] + "." + parts[1])]
        if len(seps) > 1 and all(len(p) == 3 for p in parts[1:]) and len(parts[0]) <= 3:
            return [float("".join(parts))]                        # 1,500,000 / 1.500.000
        if len(seps) > 1 and len(set(seps[:-1])) == 1 and seps[-1] != seps[0] and all(len(p) == 3 for p in parts[1:-1]):
            return [float("".join(parts[:-1]) + "." + parts[-1])]  # 1.500,50 / 1,500.50
        return [float(re.sub(r",(?=\d{3}(?!\d))", "", raw).replace(",", "."))]
    except ValueError:
        return []


def _figures_in(line: str, blank: list[tuple[int, int]]) -> list[tuple[str, set[float]]]:
    """The numbers of one line, as (token, values), once the `blank` spans (dates are not numbers) are blanked.
    "75%", "75 percent" and "75 pour cent" all compare as the value 75; a bare digit 0-9 is no signal
    ("3 teams" vs "three"), unless it carries a unit."""
    chars = list(line)
    for i, j in blank:
        chars[i:j] = " " * (j - i)
    rest = re.sub(r"(?<=\d)[ \u00a0\u202f](?=\d{3}(?!\d))", "", "".join(chars))
    out: list[tuple[str, set[float]]] = []
    for m in _NUM_RE.finditer(rest):
        if not m.group(2) and len(m.group(1)) == 1:
            continue
        vals = _num_values(m.group(0))
        if vals:
            out.append((m.group(0).strip(), vals))
    return out


def years_in(text: str) -> list[int]:
    """The 4-digit years (1900-2099) of `text`, in reading order."""
    return [int(y) for y in _YEAR_RE.findall(text)]


@dataclass(frozen=True)
class Figure:
    """One figure of the CV text, as the summary-repeat check compares them: `lo` (and `hi` for a range a-b) are the
    values it can mean ("1.500" reads both ways), `unit` the symbols stuck to it (% + and currency symbols)."""
    token: str
    unit: str
    lo: frozenset[float]
    hi: frozenset[float] = frozenset()

    def same(self, other: Figure) -> bool:
        if self.unit != other.unit or bool(self.hi) != bool(other.hi):
            return False
        return bool(self.lo & other.lo) and (not self.hi or bool(self.hi & other.hi))


_FIG_RE = re.compile(r"(\d+(?:[.,]\d+)*)(?:\s?[-\u2013]\s?(\d+(?:[.,]\d+)*))?\s?(%|[kKmM](?![^\W\d_])|)(\+?)")


def _scaled(raw: str, mult: int) -> frozenset[float]:
    return frozenset(v * mult for v in _readings(raw))


def figures_in(text: str) -> list[Figure]:
    """Every figure of `text` that is not a year, a numeric month+year or a phone number, in reading order. Unlike
    check_facts_coverage it keeps what makes two figures different things: an adjacent unit symbol (40% is not 40,
    $5 is not 5) and a range (10-20 is one figure, not 10 and 20). Same patterns and readings otherwise."""
    out: list[Figure] = []
    for raw in text.split("\n"):
        line = _blank_phones(raw.strip())
        fl = _fold1(line)
        chars = list(line)
        for i, j in [m.span() for m in _NUM_MY_RE.finditer(fl)] + [m.span() for m in _YEAR_RE.finditer(fl)]:
            chars[i:j] = " " * (j - i)
        rest = re.sub(r"(?<=\d)[ \u00a0\u202f](?=\d{3}(?!\d))", "", "".join(chars))
        for m in _FIG_RE.finditer(rest):
            pre = rest[m.start() - 1] if m.start() > 0 and unicodedata.category(rest[m.start() - 1]) == "Sc" else ""
            tail = rest[m.end():].lstrip(" ")[:1]
            post = tail if tail and unicodedata.category(tail) == "Sc" else ""
            unit = pre + ("%" if m.group(3) == "%" else "") + m.group(4) + post
            if not m.group(2) and not unit and not m.group(3) and len(m.group(1)) == 1:
                continue                    # bare 0-9: "3 teams" vs "three" is not a signal
            mult = 1000 if m.group(3).lower() == "k" else 1_000_000 if m.group(3).lower() == "m" else 1
            lo = _scaled(m.group(1), mult)
            if lo:
                out.append(Figure(m.group(0).strip(), unit, lo, _scaled(m.group(2), mult) if m.group(2) else frozenset()))
    return out


def check_facts_coverage(pdf_text: str, facts_text: str) -> list[str]:
    """Rule 1, mechanically, on digits only. WARN, never FAIL: a figure absent from the facts file is a prompt to
    confirm it with the candidate, and the facts file may be written in prose the patterns cannot read.

    WARN line for every year, numeric month+year (03/2020, 2020-03) and number in the CV text that the facts file does
    not contain. Case, number formats and thousands separators are normalized; phone numbers are ignored. It reads
    no word of any language, so names, titles and month names are left to the agent's own comparison."""
    facts = _fold(facts_text)
    facts_years = set(_YEAR_RE.findall(facts))
    facts_my: set[tuple[int, int]] = set()
    for m in _NUM_MY_RE.finditer(facts):
        y, mo = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
        facts_my.add((int(mo), int(y)))
    facts_nums = _num_values(facts_text)
    found: dict[str, None] = {}
    for raw in pdf_text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        line = _blank_phones(line)
        if not line.strip():
            continue
        fl = _fold1(line)                   # same length as `line`: spans carry over
        blank: list[tuple[int, int]] = []
        for m in _NUM_MY_RE.finditer(fl):
            blank.append(m.span())
            y, mo = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
            if (int(mo), int(y)) not in facts_my:
                found[m.group(0)] = None
        for m in _YEAR_RE.finditer(fl):
            blank.append(m.span())
            if m.group(0) not in facts_years:
                found[m.group(0)] = None
        for tok, vals in _figures_in(line, blank):
            if not vals & facts_nums:
                found[tok] = None
    return [f'WARN  not in facts file: "{t}" — remove it or confirm it with the candidate (rule 1)'
            for t in found]


# A bullet marker set as a CHARACTER survives into the ATS's text (measured:
# Banque Nationale showed it alone on a line above the bullet; Eightfold printed
# it literally). Markers must be drawn (references/ats.md). Private-use code
# points are what icon fonts (Font Awesome etc.) emit. Leading position only:
# an inline separator or a prose dash is not what this catches.
BULLET_CHAR_RE = re.compile("^[\u25c6\u25c7\u2022\u25aa\u25ab\u25ba\u25cf\u25a0\u25e6\u2023\u2219\u27a2\ue000-\uf8ff]")


def check_bullet_chars(txt: str) -> list[str]:
    """Extracted lines that start with a bullet or private-use character (the caller WARNs; see BULLET_CHAR_RE)."""
    return [l.strip() for l in txt.split("\n") if BULLET_CHAR_RE.match(l.strip())]


# Calibrated on the 29 templates and 294 palette renders (CHANGELOG): weakest legitimate contrast 4.55:1, smallest
# legitimate box 5.49 pt (a superscript). HIDDEN_PPI lives in verify_base.
HIDDEN_MIN_BOX_PT = 4.0   # word-box height floor (pt). Legit: 7.98 for 8.5pt text, 5.49 for a
                          # superscript in 7.5-9pt body. Hidden-text intent is invisibility, not
                          # small print: between 4.0 and the smallest legit box only the ink counts.
HIDDEN_FAIL_RATIO = 1.5   # WCAG contrast ratio of the strongest pixel in a word's box against the
HIDDEN_WARN_RATIO = 3.0   # box background: below 1.5 unreadable (FAIL), below 3 barely visible (WARN)
HIDDEN_PAD_PX = 1         # px added around each box (single-stem words like "i", "l", "二")


# Metadata gate (check_pdf_metadata): a Keywords field over KEYWORD_MAX_TERMS terms, or any other field over
# META_MAX_CHARS characters, is WARNed as stuffing (heuristic ceiling: a normal Title/Author/Subject is one
# short line, and a real keyword list is a handful of terms).
KEYWORD_MAX_TERMS = 15


META_MAX_CHARS = 200


def _contrast_in_box(crop: Image.Image) -> float:
    """Contrast ratio of a crop: its background (most common colour; a tie goes to the larger colour) against the
    strongest colour in it. Contrast against a fixed background rises with the distance of a luminance from it, so
    the strongest colour is the darkest or the lightest one: two luminances, not one per colour. Luminances come
    from the per-channel tables of `counted_luminances` (a noisy box holds over a thousand colours)."""
    cols: list[tuple[int, tuple[int, ...]]] = []
    for count, colour in crop.getcolors(crop.width * crop.height) or []:
        if not isinstance(colour, tuple):   # one band: Pillow gives a bare number per colour
            raise ValueError(f"_contrast_in_box needs a multi-band image, got {crop.mode!r}")
        cols.append((count, colour))
    values = counted_luminances(cols)
    lb = rel_luminance(max(cols)[1])
    return max(1.0, contrast_from_lum(min(values), lb), contrast_from_lum(max(values), lb))


def _page_raster(pngs: list[str] | None, pno: int) -> Image.Image | None:
    """The RGB raster of page `pno` (1-based), or None when no raster was given for it."""
    if pngs and pno - 1 < len(pngs):
        return Image.open(pngs[pno - 1]).convert("RGB")
    return None


def _word_pixels(box: tuple[float, float, float, float], im: Image.Image) -> tuple[int, int, int, int]:
    """The word's box at HIDDEN_PPI, padded by HIDDEN_PAD_PX and clipped to the raster: (xa, ya, xb, yb), empty
    (xb <= xa or yb <= ya) when the box rounds to nothing."""
    sc = HIDDEN_PPI / 72.0
    x0, y0, x1, y1 = box
    return (max(int(x0 * sc) - HIDDEN_PAD_PX, 0), max(int(y0 * sc) - HIDDEN_PAD_PX, 0),
            min(int(x1 * sc) + 1 + HIDDEN_PAD_PX, im.width), min(int(y1 * sc) + 1 + HIDDEN_PAD_PX, im.height))


def hidden_word_stats(pdf: str, pages: list[tuple[float, float, list[WordBox]]] | None = None,
                      pngs: list[str] | None = None) -> list[HiddenStat]:
    """[(page_no, word, (x0, y0, x1, y1), height_pt, contrast | None, off_page)] for
    every extracted word that carries a letter or digit.

    contrast: the WCAG contrast ratio between the box's own background (its most common
    colour) and the strongest pixel anywhere in the box (+1 px), at HIDDEN_PPI, either
    direction (dark ink on light, light ink on dark). White text on white paper, text in
    the band's colour, text under an opaque shape: a flat box, ratio 1.0. None when no
    raster is available."""
    pages = bbox_pages(pdf) if pages is None else pages
    out: list[HiddenStat] = []
    for pno, (pw, ph, items) in enumerate(pages or [], 1):
        im = _page_raster(pngs, pno)
        for box, word in items:
            if not re.search(r"[^\W_]", word):
                continue   # separators, bullets, rule glyphs: visible or meaningless either way
            x0, y0, x1, y1 = box
            # poppler drops chars past the page edge, so a word that crosses it is cut
            # short, and its box then ends just past the edge: any overshoot is off-page
            off = bool(x0 < -0.01 or y0 < -0.01 or (pw and x1 > pw + 0.01) or (ph and y1 > ph + 0.01))
            ratio = None
            if im is not None:
                xa, ya, xb, yb = _word_pixels(box, im)
                if xb > xa and yb > ya:
                    ratio = _contrast_in_box(im.crop((xa, ya, xb, yb)))
                elif not off:
                    ratio = 1.0   # the whole box rounds to nothing: no ink can be there
            out.append((pno, word, box, y1 - y0, ratio, off))
    return out


def _stuffed(text: str, max_terms: int | None = None) -> str | None:
    """Why `text` reads as keyword stuffing, or None.

    Three signals: more than `max_terms` terms (only when the caller passes it: the Keywords
    field), a term used twice, or a word of 3+ letters used three times. Terms are split on
    `,` and `;`; a field with no separator is split on whitespace so a space-separated list is
    counted too."""
    terms = [t.strip().lower() for t in re.split(r"[,;]", text) if t.strip()]
    if len(terms) <= 1:
        terms = text.lower().split()
    words = re.findall(r"\w+", text.lower())
    term_counts, word_counts = Counter(terms), Counter(words)
    repeated = sorted({t for t, n in term_counts.items() if n > 1} | {w for w, n in word_counts.items() if len(w) > 2 and n > 2})
    if (max_terms and len(terms) > max_terms) or repeated:
        return f"{len(terms)} terms" + (f", repeats {', '.join(r[:20] for r in repeated[:3])}" if repeated else "")
    return None


def check_pdf_metadata(pdf: str) -> list[str]:
    """WARN texts for stuffed document metadata (Keywords, Title, Author, Subject) and
    embedded attachments: ATS read them, the reader never sees them.

    Backends are tried in the order the other gates use (pdfium, poppler's pdfinfo, pypdf). A
    read that fails leaves `info` empty: unreadable metadata is no finding, never a FAIL."""
    info = {}
    scan_failed = ""
    doc: PdfiumDoc | None = None
    if pdf_backend() == "pdfium":
        try:
            doc = pdfium_doc(pdf)
            meta: dict[str, str] = doc.get_metadata_dict()
            info = {k: (meta.get(k) or "").strip() for k in ("Keywords", "Title", "Author", "Subject")}
        except (OSError, RuntimeError):   # pypdfium2 cannot open or read the file (PdfiumError is a RuntimeError)
            pass
    elif shutil.which("pdfinfo"):
        for line in pdfinfo_output(pdf).splitlines():
            k, _, v = line.partition(":")
            if k in ("Keywords", "Title", "Author", "Subject"):
                info[k] = v.strip()
    else:
        try:
            pypdf = importlib.import_module("pypdf")
        except ImportError:
            pypdf = None
        if pypdf is not None:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    md = pypdf.PdfReader(pdf).metadata
                info = {k: str((md.get("/" + k) if md else None) or "") for k in ("Keywords", "Title", "Author", "Subject")}
            except (OSError, ValueError, pypdf.errors.PyPdfError):   # file unreadable or malformed for pypdf
                pass
            except Exception as e:   # noqa: BLE001 - broad on purpose: pypdf parses untrusted input and raises NotImplementedError and more
                scan_failed = type(e).__name__
    out: list[str] = []
    if scan_failed:
        out.append(f"metadata pypdf scan failed: {scan_failed} — metadata not checked")
    for k, v in info.items():
        if not v:
            continue
        # Keywords: term count and repeats. Other fields: too long, plus repeats when both apply.
        why = _stuffed(v, KEYWORD_MAX_TERMS) if k == "Keywords" else (
            f"{len(v)} characters" if len(v) > META_MAX_CHARS else _stuffed(v))
        if k != "Keywords" and len(v) > META_MAX_CHARS and _stuffed(v):
            why = (why or "") + ", " + (_stuffed(v) or "")
        if why:
            out.append(f"metadata {'keyword stuffing' if k == 'Keywords' else k + ' stuffing'} ({why}) — "
                       f"shorten the document {k} to a few real terms; ATS read it, the reader never sees it")
    # Attachments: pdfium counts them directly, otherwise poppler's pdfdetach lists them.
    n_att = 0
    if doc is not None:
        n_att = doc.count_attachments()
    elif shutil.which("pdfdetach"):
        m = re.search(r"(\d+) embedded files?", proc.run(["pdfdetach", "-list", pdf], proc.POPPLER_S).stdout)
        n_att = int(m[1]) if m else 0
    if n_att:
        out.append(f"metadata: {n_att} embedded attachment(s) — remove them; ATS may read a file the reader never sees")
    return out


# Smallest legitimate text in the templates is 7.5-8.5pt metadata (superscripts exempted by script_of below);
# <5.0pt is unreadable print (WARN; boxes <4.0pt FAIL in check_hidden_text).
TINY_TEXT_PT = 5.0   # real font size under which a run is "tiny" (WARN): nobody reads it


Run = tuple[str, float, float, float]   # (text, x, y, real size) of one text run of a page


# (size, lowest y, highest y) of a run no comparison holds for (NaN size or y): no node containing it is ever skipped.
_NEVER_SKIP = (math.inf, -math.inf, math.inf)


@dataclass(frozen=True, slots=True)
class _Walk:
    """One neighbour search of `is_script`: from run `start` in direction `step` (+1 or -1), stopping at the first run
    that is larger than `limit` or off the baseline `y`."""
    start: int
    step: int
    limit: float
    y: float


class _ScriptIndex:
    """Which run is a super/subscript of a larger neighbour, in O(log k) per run instead of a walk over the neighbours
    (k tiny runs on one baseline walked O(k^2) before). From run i the walk skips neighbours that are no larger than
    1.15 x its size and on its baseline (|dy| < 0.5), and stops at the first one that is larger or off the baseline.
    A segment tree over the runs keeps, per node, the largest size and the lowest and highest y, so a whole node is
    skipped when every run in it would be: the same float comparisons as run by run, since each is monotone.
    Node 1 covers runs [0, k); node v covers [lo, hi) and its children cover [lo, mid) and [mid, hi)."""
    __slots__ = ("_runs", "_size", "_ymax", "_ymin")

    def __init__(self, runs: Sequence[Run]) -> None:
        self._runs = runs
        self._size = [0.0] * (4 * len(runs))
        self._ymin = [0.0] * (4 * len(runs))
        self._ymax = [0.0] * (4 * len(runs))
        if runs:
            self._build(1, 0, len(runs))

    def _build(self, node: int, lo: int, hi: int) -> None:
        if hi - lo == 1:
            _, _, y, sz = self._runs[lo]
            leaf = _NEVER_SKIP if math.isnan(y) or math.isnan(sz) else (sz, y, y)
            self._size[node], self._ymin[node], self._ymax[node] = leaf
            return
        mid = (lo + hi) // 2
        self._build(2 * node, lo, mid)
        self._build(2 * node + 1, mid, hi)
        self._size[node] = max(self._size[2 * node], self._size[2 * node + 1])
        self._ymin[node] = min(self._ymin[2 * node], self._ymin[2 * node + 1])
        self._ymax[node] = max(self._ymax[2 * node], self._ymax[2 * node + 1])

    def _skipped(self, node: int, limit: float, y: float) -> bool:
        """True if every run under `node` is no larger than `limit` and on the baseline `y`."""
        return (self._size[node] < limit and abs(self._ymin[node] - y) < 0.5 and abs(self._ymax[node] - y) < 0.5)

    def _stop(self, node: int, lo: int, hi: int, walk: _Walk) -> int:
        """Index of the first run from `walk.start` in direction `walk.step` inside node [lo, hi) that the walk stops at, or -1."""
        if (hi <= walk.start if walk.step > 0 else lo > walk.start) or self._skipped(node, walk.limit, walk.y):
            return -1
        if hi - lo == 1:
            return lo
        mid = (lo + hi) // 2
        first, second = ((2 * node, lo, mid), (2 * node + 1, mid, hi))[::walk.step]
        found = self._stop(*first, walk)
        return found if found >= 0 else self._stop(*second, walk)

    def is_script(self, i: int) -> bool:
        _, x, y, sz = self._runs[i]
        limit = 1.15 * sz
        for step in (-1, 1):
            j = self._stop(1, 0, len(self._runs), _Walk(i + step, step, limit, y))
            if j >= 0:
                _, xn, yn, szn = self._runs[j]
                if szn >= limit and 0.05 * szn < abs(yn - y) < 0.6 * szn and (x >= xn if step < 0 else xn >= x):
                    return True
        return False


def _classify_runs(runs: Sequence[Run], box: tuple[float, float, float, float]) -> tuple[list[str], list[tuple[str, float]]]:
    """([text of runs whose origin is outside the box], [(text, smallest size) of each block of consecutive tiny runs
    that are no super/subscript]) for one page: the geometry half of `_text_runs`."""
    x0, y0, x1, y1 = box
    off: list[str] = []
    block_texts: list[list[str]] = []   # one block per entry, joined once at the end
    block_sizes: list[float] = []       # the smallest size of the same block
    index: _ScriptIndex | None = None
    last_tiny = -2
    for i, (t, x, y, sz) in enumerate(runs):
        if x < x0 - 0.5 or x > x1 + 0.5 or y < y0 - 0.5 or y > y1 + 0.5:
            off.append(t)
        elif 0 < sz < TINY_TEXT_PT:
            if index is None:
                index = _ScriptIndex(runs)
            if index.is_script(i):
                continue
            # consecutive tiny runs are one block: report it once, at its smallest size
            if last_tiny == i - 1:
                block_texts[-1].append(t)
                block_sizes[-1] = min(block_sizes[-1], sz)
            else:
                block_texts.append([t])
                block_sizes.append(sz)
            last_tiny = i
    return off, [(" ".join(texts), sz) for texts, sz in zip(block_texts, block_sizes)]


def _append_run(runs: list[Run], text: str, cm: Sequence[float] | None, tm: Sequence[float] | None, fd: object,
                fs: float | None) -> None:
    """pypdf text visitor: records the run's text, origin and real size (Tf size times the matrices' scale)."""
    if not text.strip() or not cm or not tm:
        return
    x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
    y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
    det = abs((tm[0] * tm[3] - tm[1] * tm[2]) * (cm[0] * cm[3] - cm[1] * cm[2]))
    runs.append((" ".join(text.split()), x, y, (fs or 0) * det ** 0.5))


def _text_runs(pdf: str) -> tuple[list[tuple[int, str]], list[tuple[int, str, float]], bool, str]:
    """([(page_no, text, off_page)], [(page_no, text, real_size_pt)], ran, failure): text runs the
    PDF places outside the page box, and runs set under TINY_TEXT_PT. `ran` is False when pypdf
    is unusable, so the caller can say the check did not run instead of reporting a clean pass; `failure` is the
    exception type name when pypdf crashed on the file (ran is then False), else "".

    Poppler drops every glyph past the page edge, so a run placed wholly off the page is
    invisible to pdftotext; pypdf (optional) sees it. Geometry only (the run's origin
    through its text matrix and CTM against the CropBox) — never a text comparison, which
    breaks on every script pypdf shapes differently from poppler (Arabic, Thai...). The
    real size is the Tf size times the matrices' scale (the box height varies with the
    font, up to 2x the size). A run that is a superscript or subscript — smaller than a
    neighbouring run on the same line, raised or lowered, at or right of it — is not tiny."""
    try:
        pypdf = importlib.import_module("pypdf")
    except ImportError:
        return [], [], False, ""   # pypdf absent: the caller reports "not run"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            reader = pypdf.PdfReader(pdf)
            off: list[tuple[int, str]] = []
            tiny: list[tuple[int, str, float]] = []
            for pno, pg in enumerate(reader.pages, 1):
                box = pg.cropbox
                x0, y0, x1, y1 = float(box.left), float(box.bottom), float(box.right), float(box.top)
                runs: list[Run] = []
                pg.extract_text(visitor_text=partial(_append_run, runs))
                page_off, page_tiny = _classify_runs(runs, (x0, y0, x1, y1))
                off += [(pno, t) for t in page_off]
                tiny += [(pno, t, sz) for t, sz in page_tiny]
        return off, tiny, True, ""
    except (OSError, ValueError, pypdf.errors.PyPdfError) as e:
        if not pdf_unreadable(pdf):
            # the primary backend reads this PDF but pypdf rejects it: say the off-page/tiny-text scan did not run
            return [], [], False, type(e).__name__
        # unreadable overall: the other gates already FAIL it, so "ran, found nothing" adds no false pass
        return [], [], True, ""
    except Exception as e:   # noqa: BLE001 - broad on purpose: pypdf parses untrusted input and raises NotImplementedError and more
        return [], [], False, type(e).__name__


HIDDEN_TAIL = ("text a reader cannot see is still read by ATS and recruiters' tools, "
               "and disqualifies the CV.")


def _merged_runs(stats: Sequence[HiddenStat], pick: Callable[[HiddenStat], object]) -> list[tuple[int, str]]:
    """[(page_no, text)]: adjacent selected words of one page merged into one run, so a hidden sentence is one finding.
    Words are collected in a list and joined once per run (repeated `+` on a growing string is quadratic)."""
    pages: list[int] = []
    words: list[list[str]] = []
    prev: int | None = None
    for i, st in enumerate(stats):
        if pick(st):
            if prev is not None and i == prev + 1 and pages[-1] == st[0]:
                words[-1].append(st[1])
            else:
                pages.append(st[0])
                words.append([st[1]])
            prev = i
    return [(pno, " ".join(ws)) for pno, ws in zip(pages, words, strict=True)]


def check_hidden_text(pdf: str, detail: list[HiddenStat] | None = None) -> list[Finding]:
    """[(level, message)]: FAIL for text a pdf reader extracts but a human cannot see
    (contrast under 1.5:1 at its box, box under 4pt, box or run off or across the page
    edge); WARN for low contrast (under 3:1), stuffed metadata, attachments. Independent
    of the background colour.

    FAIL only where the text is certainly invisible (the CHANGELOG records the calibration:
    weakest legitimate contrast 4.55:1, smallest legitimate box 5.49pt). Anything merely
    hard to read, or a check that could not run, is a WARN.

    Known limits (a raster cannot tell): white text over a textured image or a gradient
    that has ink in the box; a visible strike or rule drawn through white text; hidden
    text laid exactly over visible text."""
    pages = bbox_pages(pdf)
    if pages is None:
        return [(Level.WARN, f"hidden-text gate skipped: {boxes_unavailable(pdf)}")]
    msgs: list[Finding] = []
    with tempfile.TemporaryDirectory() as tmp:
        pngs = render_pages_png(pdf, tmp)
        if not pngs:
            msgs.append((Level.WARN, "hidden-text ink check skipped: pdftoppm not found (install poppler-utils); "
                                 "size and off-page checks still ran"))
        stats = hidden_word_stats(pdf, pages=pages, pngs=pngs)
    if detail is not None:
        detail.extend(stats)

    found = _merged_runs(stats, lambda st: st[5] or st[3] < HIDDEN_MIN_BOX_PT
                 or (st[4] is not None and st[4] < HIDDEN_FAIL_RATIO))
    outside, tiny, ran, failure = _text_runs(pdf)
    if pdf_backend() == "pdfium":
        # pdfium keeps the glyphs placed past the page edge, so their word boxes are already
        # in `found`: poppler drops them, only pypdf then sees them
        seen = {(pno, w) for pno, t in found for w in t.split()}
        outside = [(pno, t) for pno, t in outside if not all((pno, w) in seen for w in t.split())]
    found += outside
    if failure:
        msgs.append((Level.WARN, f"hidden-text pypdf scan failed: {failure} — off-page and tiny-text checks not run"))
    elif not ran:
        if pdf_backend() == "pdfium":
            # pdfium keeps off-page glyphs, so the word-box check above covered them; the
            # tiny-text check is pypdf's alone
            msgs.append((Level.WARN, "hidden text: off-page check ran on pdfium word boxes only; tiny-text "
                                 "check not run (pypdf missing)"))
        else:
            msgs.append((Level.WARN, "hidden text: off-page check not run (pypdf missing)"))
    # Cap the output: five FAIL lines, the last one counting the rest; three lines per WARN kind.
    for n, (pno, text) in enumerate(found):
        if n == 5:
            msgs.append((Level.FAIL, f"hidden text: remove all {len(found) - 5} other hidden run(s) too — " + HIDDEN_TAIL))
            break
        msgs.append((Level.FAIL, f'hidden text: remove "{text[:60]}" (p.{pno}) — ' + HIDDEN_TAIL))
    for n, (pno, text) in enumerate(_merged_runs(stats, lambda st: st[4] is not None and HIDDEN_FAIL_RATIO <= st[4] < HIDDEN_WARN_RATIO
                                         and not st[5] and st[3] >= HIDDEN_MIN_BOX_PT)):
        if n == 3:
            break
        msgs.append((Level.WARN, f'low contrast: "{text[:60]}" (p.{pno}) — barely visible (under {HIDDEN_WARN_RATIO:g}:1), '
                             "raise its contrast or remove it"))
    for n, (pno, text, sz) in enumerate(tiny):
        if n == 3:
            break
        msgs.append((Level.WARN, f'tiny text: "{text[:60]}" (p.{pno}) is set at {sz:.1f}pt — below {TINY_TEXT_PT:g}pt '
                             "nobody reads it; if it is a keyword block, remove it"))
    msgs.extend((Level.WARN, m) for m in check_pdf_metadata(pdf))
    return msgs
