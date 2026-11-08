"""Checks on the text extracted from the PDF: facts coverage, bullet characters, hidden text, metadata.

A leaf under verify_pdf: no `import verify`.
"""
from __future__ import annotations

import importlib
import re
import shutil
import subprocess
import tempfile
import unicodedata
from collections.abc import Callable, Sequence
from typing import cast

from PIL import Image

from vitae.core.base import HIDDEN_PPI, HiddenStat, WordBox
from vitae.core.env import pdf_backend
from vitae.core.level import Finding, Level
from vitae.core.pdfium import PdfiumDoc
from vitae.verify.lang import _is_latin, _strip_latin_marks
from vitae.verify.page import _lum
from vitae.verify.pdf import _bbox_pages, _boxes_unavailable, _pdfium_doc, _render_pages_png

# Date and number patterns of check_facts_coverage, matched on folded text (`_fold`, `_fold1`).
_NUM_MY_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})[-/.](0?[1-9]|1[0-2])(?!\d)|(?<!\d)(0?[1-9]|1[0-2])[-/.]((?:19|20)\d{2})(?!\d)")


_YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")


_NUM_RE = re.compile(r"[$€£]?(\d+(?:[.,]\d+)*)\s?(%|[kKmM](?![^\W\d_])|)")


def _fold1(s: str) -> str:
    """Length-preserving fold (one output char per input char): accents go on Latin letters only, so the vowels
    and tones of Devanagari or Thai keep their code points."""
    out = []
    for c in s:
        d = unicodedata.normalize("NFKD", c)[0] if _is_latin(c) else c
        low = d.lower()
        out.append(low if len(low) == 1 else d)
    return "".join(out)


def _fold(s: str) -> str:
    """Lower-case, accents stripped from Latin letters, dashes unified, whitespace collapsed."""
    s = _strip_latin_marks(s).lower()
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


def check_facts_coverage(pdf_text: str, facts_text: str) -> list[str]:
    """Rule 1, mechanically, on digits only. WARN, never FAIL: a figure absent from the facts file is a prompt to
    confirm it with the candidate, and the facts file may be written in prose the patterns cannot read.

    WARN line for every year, numeric month+year (03/2020, 2020-03) and number in the CV text that the facts file does
    not contain. Case, number formats and thousands separators are normalized; phone numbers are ignored. It reads
    no word of any language, so names, titles and month names are left to the agent's own comparison."""
    facts = _fold(facts_text)
    facts_years = set(_YEAR_RE.findall(facts))
    facts_my = set()
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
        # dates are not numbers: blank them before the number scan
        chars = list(line)
        for i, j in blank:
            chars[i:j] = " " * (j - i)
        rest = "".join(chars)
        # "75%", "75 percent" and "75 pour cent" all compare as the value 75
        for m in _NUM_RE.finditer(re.sub(r"(?<=\d)[ \u00a0\u202f](?=\d{3}(?!\d))", "", rest)):
            if not m.group(2) and len(m.group(1)) == 1:
                continue                    # bare 0-9: "3 teams" vs "three" is not a signal
            vals = _num_values(m.group(0))
            if vals and not vals & facts_nums:
                found[m.group(0).strip()] = None
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


def hidden_word_stats(pdf: str, pages: list[tuple[float, float, list[WordBox]]] | None = None,
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
                    cols = cast(list[tuple[int, tuple[int, ...]]],
                                im.crop((xa, ya, xb, yb)).getcolors(maxcolors=(xb - xa) * (yb - ya)))
                    lb = _lum(max(cols)[1])
                    ratio = 1.0
                    for _, col in cols:
                        lc = _lum(col)
                        ratio = max(ratio, (max(lc, lb) + 0.05) / (min(lc, lb) + 0.05))
                elif not off:
                    ratio = 1.0   # the whole box rounds to nothing: no ink can be there
            out.append((pno, word, (x0, y0, x1, y1), y1 - y0, ratio, off))
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
    repeated = sorted({t for t in terms if terms.count(t) > 1} | {w for w in words if len(w) > 2 and words.count(w) > 2})
    if (max_terms and len(terms) > max_terms) or repeated:
        return f"{len(terms)} terms" + (f", repeats {', '.join(r[:20] for r in repeated[:3])}" if repeated else "")
    return None


def check_pdf_metadata(pdf: str) -> list[str]:
    """WARN texts for stuffed document metadata (Keywords, Title, Author, Subject) and
    embedded attachments: ATS read them, the reader never sees them.

    Backends are tried in the order the other gates use (pdfium, poppler's pdfinfo, pypdf). A
    read that fails leaves `info` empty: unreadable metadata is no finding, never a FAIL."""
    info = {}
    doc: PdfiumDoc | None = None
    if pdf_backend() == "pdfium":
        try:
            doc = _pdfium_doc(pdf)
            meta: dict[str, str] = doc.get_metadata_dict()
            info = {k: (meta.get(k) or "").strip() for k in ("Keywords", "Title", "Author", "Subject")}
        except Exception:
            pass
    elif shutil.which("pdfinfo"):
        for line in subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout.splitlines():
            k, _, v = line.partition(":")
            if k in ("Keywords", "Title", "Author", "Subject"):
                info[k] = v.strip()
    else:
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pypdf = importlib.import_module("pypdf")
                md = pypdf.PdfReader(pdf).metadata or {}
            info = {k: str(md.get("/" + k) or "") for k in ("Keywords", "Title", "Author", "Subject")}
        except Exception:
            pass
    out: list[str] = []
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
        m = re.search(r"(\d+) embedded files?", subprocess.run(["pdfdetach", "-list", pdf],
                                                                 capture_output=True, text=True).stdout)
        n_att = int(m[1]) if m else 0
    if n_att:
        out.append(f"metadata: {n_att} embedded attachment(s) — remove them; ATS may read a file the reader never sees")
    return out


# Smallest legitimate text in the templates is 7.5-8.5pt metadata (superscripts exempted by script_of below);
# <5.0pt is unreadable print (WARN; boxes <4.0pt FAIL in check_hidden_text).
TINY_TEXT_PT = 5.0   # real font size under which a run is "tiny" (WARN): nobody reads it


def _text_runs(pdf: str) -> tuple[list[tuple[int, str]], list[tuple[int, str, float]], bool]:
    """([(page_no, text, off_page)], [(page_no, text, real_size_pt)], ran): text runs the
    PDF places outside the page box, and runs set under TINY_TEXT_PT. `ran` is False when pypdf
    is unusable, so the caller can say the check did not run instead of reporting a clean pass.

    Poppler drops every glyph past the page edge, so a run placed wholly off the page is
    invisible to pdftotext; pypdf (optional) sees it. Geometry only (the run's origin
    through its text matrix and CTM against the CropBox) — never a text comparison, which
    breaks on every script pypdf shapes differently from poppler (Arabic, Thai...). The
    real size is the Tf size times the matrices' scale (the box height varies with the
    font, up to 2x the size). A run that is a superscript or subscript — smaller than a
    neighbouring run on the same line, raised or lowered, at or right of it — is not tiny."""
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pypdf = importlib.import_module("pypdf")
            reader = pypdf.PdfReader(pdf)
            off: list[tuple[int, str]] = []
            tiny: list[tuple[int, str, float, int]] = []
            for pno, pg in enumerate(reader.pages, 1):
                box = pg.cropbox
                x0, y0, x1, y1 = float(box.left), float(box.bottom), float(box.right), float(box.top)
                runs: list[tuple[str, float, float, float]] = []   # (text, x, y, real size)

                def visit(text: str, cm: Sequence[float] | None, tm: Sequence[float] | None, fd: object, fs: float | None,
                          runs: list[tuple[str, float, float, float]] = runs) -> None:
                    if not text.strip() or not cm or not tm:
                        return
                    x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
                    y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
                    det = abs((tm[0] * tm[3] - tm[1] * tm[2]) * (cm[0] * cm[3] - cm[1] * cm[2]))
                    runs.append((" ".join(text.split()), x, y, (fs or 0) * det ** 0.5))
                pg.extract_text(visitor_text=visit)

                def script_of(i: int, runs: list[tuple[str, float, float, float]] = runs) -> bool:
                    # True if run i is a super/subscript of a larger neighbour on the same line
                    t, x, y, sz = runs[i]
                    for step in (-1, 1):
                        j = i + step
                        # skip neighbours that are scripts too (same size, same baseline): "10th" may be two runs
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
                        off.append((pno, t))
                    elif 0 < sz < TINY_TEXT_PT and not script_of(i):
                        # consecutive tiny runs are one block: report it once, at its smallest size
                        if tiny and tiny[-1][0] == pno and tiny[-1][3] == i - 1:
                            tiny[-1] = (pno, tiny[-1][1] + " " + t, min(tiny[-1][2], sz), i)
                        else:
                            tiny.append((pno, t, sz, i))
        return off, [(p_, t, sz) for p_, t, sz, _ in tiny], True
    except Exception as e:
        # ImportError: pypdf is absent, so the caller reports "not run". Any other error
        # counts as "ran, found nothing".
        return [], [], not isinstance(e, ImportError)


HIDDEN_TAIL = ("text a reader cannot see is still read by ATS and recruiters' tools, "
               "and disqualifies the CV.")


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
    pages = _bbox_pages(pdf)
    if pages is None:
        return [(Level.WARN, f"hidden-text gate skipped: {_boxes_unavailable(pdf)}")]
    msgs: list[Finding] = []
    with tempfile.TemporaryDirectory() as tmp:
        pngs = _render_pages_png(pdf, tmp)
        if not pngs:
            msgs.append((Level.WARN, "hidden-text ink check skipped: pdftoppm not found (install poppler-utils); "
                                 "size and off-page checks still ran"))
        stats = hidden_word_stats(pdf, pages=pages, pngs=pngs)
    if detail is not None:
        detail.extend(stats)

    def runs(pick: Callable[[HiddenStat], object]) -> list[tuple[int, str]]:
        # merge adjacent selected words of one page into one run, so a hidden sentence is one finding
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

    found = runs(lambda st: st[5] or st[3] < HIDDEN_MIN_BOX_PT
                 or (st[4] is not None and st[4] < HIDDEN_FAIL_RATIO))
    outside, tiny, ran = _text_runs(pdf)
    if pdf_backend() == "pdfium":
        # pdfium keeps the glyphs placed past the page edge, so their word boxes are already
        # in `found`: poppler drops them, only pypdf then sees them
        seen = {(pno, w) for pno, t in found for w in t.split()}
        outside = [(pno, t) for pno, t in outside if not all((pno, w) in seen for w in t.split())]
    found += outside
    if not ran:
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
    for n, (pno, text) in enumerate(runs(lambda st: st[4] is not None and HIDDEN_FAIL_RATIO <= st[4] < HIDDEN_WARN_RATIO
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
    for m in check_pdf_metadata(pdf):
        msgs.append((Level.WARN, m))
    return msgs
