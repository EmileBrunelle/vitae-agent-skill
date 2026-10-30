#!/usr/bin/env python3
# AGENT: do not read this file — run it. Its printed output is the instruction.
# Usage: python3 scripts/verify.py <cv.typ> PAGES [FILL_MIN FILL_MAX]
#        python3 scripts/verify.py --tune <cv.typ> PAGES FILL_MIN FILL_MAX
# (Reading it wastes context: a small model read this file 3 times and never wrote the CV.)
"""One-command gate for the MECHANICAL subset of SKILL.md step 6 (any
platform with Python 3 -- Linux, macOS, Windows). Exits non-zero if any
check fails. Left to do by hand: the visual PNG inspection, recomputing
the accent's contrast, the date-order check, and re-diffing bullets
against the fact sheet.

Usage:
    verify.py cv.typ EXPECTED_PAGES [FILL_MIN FILL_MAX]
    verify.py --all DIR
    verify.py --tune cv.typ PAGES FILL_MIN FILL_MAX [LEADING_LO LEADING_HI]
    verify.py --doctor

    e.g. verify.py cv.typ 1 94 96
         verify.py --tune cv.typ 1 94 96

--all checks EVERY deliverable in a directory instead of the one file just
edited. This exists because of a real regression: a padding tweak was verified
on the 2-page CV while it silently pushed the 1-page CV onto two pages
("T'as fait ça en voulant modifier le padding"). The deliverables share
lib.typ, so touching it invalidates the whole family, not the file in hand.

Each .typ declares its own expectations in a header comment, so there is no
manifest to keep in sync with the files:

    // vitae: pages=1 fill=94-96

A file without that line is still checked: its page count comes from its name
(`[-_]2p`, `[-_]2page(s)`, optionally with a space, e.g. `_2p`, `-2page`,
`-2pages`, is two pages; anything else is one) and its fill is reported
instead of gated. Not one .typ in this repo carries the header, so demanding
it made `--all` return 30 UNCHECKED and exit 1 on its own corpus.

--tune runs the page-fill loop BY BISECTION instead of by hand: it moves the
`#set par(leading:, spacing:)` declaration (keeping the family's own delta
between the two) to the largest rhythm that still holds the expected page
count, writes the winning values into the file, and reports whether the
resulting fill lands in the target. It replaces the compile-measure-adjust
loop an agent would otherwise run a dozen times per family. It tunes NOTHING
else: the section gap, the margins and the type sizes are recipe decisions.
When no value in range reaches the target, it says so rather than inventing
one — that is the anti-filler clause (SKILL.md rule 5), and the fix is the
section gap, real content, or a different page count. But check the RANGE
first: the default search is 0.80-1.30x the current leading, and a font swap
can need a bigger move than that. Pass LEADING_LO/LEADING_HI and re-run before
you touch a device — one family's second font pair looked unreachable, got its
section gap cut by 6pt to compensate, and landed with its boundary sitting
exactly on the separation floor; a wider search range was the real fix.

--doctor runs only the dependency preflight (no cv.typ required), exit
0 if everything needed is present, 1 otherwise -- replaces the old
check_env.sh / check_env.ps1 doctors.

Exit codes: 0 PASS, 1 FAIL (or missing dependency with no fallback),
2 usage error.

Prefers native tools (typst CLI, poppler pdfinfo/pdftotext) but falls
back automatically to their Python equivalents when only those are
installed: the `typst` Python package (compiles via its API, no CLI
needed) and `pypdf` (page count + indicative-only text extraction --
see references/ats.md for the caveat). No functional --install flag:
that meant fetching a binary over HTTPS with no checksum verification;
print the install commands instead and let the user choose.
"""
import atexit
import glob
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure_fill  # noqa: E402


# ---------- dependency preflight ("doctor") ----------

def check_pillow():
    try:
        import PIL  # noqa: F401
        print(f"OK    Pillow {PIL.__version__}")
        return True
    except ImportError:
        print("MISSING  Pillow -- needed for the page-fill measurement:")
        print("  sudo dnf install python3-pillow | sudo apt install python3-pil   # distro Python: official repos first (PEP 668)")
        print("  uv pip install Pillow | pip3 install --user Pillow               # venvs / pip-only environments")
        return False


def check_typst():
    """Returns (available, use_cli)."""
    if shutil.which("typst"):
        try:
            ver = subprocess.run(["typst", "--version"], capture_output=True, text=True).stdout.split()[1]
        except Exception:
            ver = "?"
        print(f"OK    typst {ver} (CLI)")
        return True, True
    try:
        import typst  # noqa: F401
        print("OK    typst (Python API, no CLI)")
        return True, False
    except ImportError:
        print("MISSING  typst -- install with ONE of:")
        print("  brew install typst                          # macOS")
        print("  sudo dnf install typst                      # Fedora")
        print("  sudo apt install typst                      # Debian/Ubuntu (24.04+)")
        print("  sudo pacman -S typst                        # Arch")
        print("  winget install --id Typst.Typst             # Windows")
        print("  choco install typst | scoop install typst   # Windows, if you already use them")
        print("  cargo install typst-cli                      # any, via Rust")
        print("  pip install typst                            # no CLI: compiles via Python API (used automatically if present)")
        return False, False


def check_pdf_tools():
    """Returns (available, use_poppler)."""
    if shutil.which("pdfinfo") and shutil.which("pdftotext"):
        print("OK    poppler-utils (pdftotext, pdfinfo)")
        return True, True
    try:
        import pypdf  # noqa: F401
        print("OK    pypdf (Python fallback -- exact page count, indicative-only extraction)")
        return True, False
    except ImportError:
        print("MISSING  poppler-utils -- needed for page-count and ATS extraction checks:")
        print("  brew install poppler | sudo dnf install poppler-utils | sudo apt install poppler-utils")
        print("  choco install poppler | scoop install poppler          # Windows")
        print("  pip install pypdf                                      # fallback: exact page count, indicative extraction only (used automatically if present)")
        return False, False


def preflight():
    """Prints doctor output; returns (all_ok, use_cli_typst, use_poppler)."""
    pillow_ok = check_pillow()
    typst_ok, use_cli = check_typst()
    pdf_ok, use_poppler = check_pdf_tools()
    return (pillow_ok and typst_ok and pdf_ok), use_cli, use_poppler


# ---------- compile / page-count / extraction, native or fallback ----------

def ensure_icons(typ):
    """Guarantee an `icons.typ` beside the file being compiled.

    `lib.typ` does `#import "icons.typ": *`, and Typst resolves that against
    the importing file, so the deliverable folder needs one. Step 4 of
    SKILL.md copies the repo's EMPTY fallback there along with `lib.typ`, and
    `harvest_icons.py <folder>` overwrites it with the fetched path data. This
    covers the one case those two miss: a folder where the copy was forgotten
    — copy the empty fallback instead of failing the compile with a Typst
    import error. No network here; fetching stays harvest_icons.py's job.
    """
    d = os.path.dirname(os.path.abspath(typ))
    dst = os.path.join(d, "icons.typ")
    if not os.path.exists(dst):        # a broken symlink counts as missing
        src = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "templates", "icons.typ")
        if not os.path.exists(src):    # no repo fallback (nothing to copy)
            return
        shutil.copyfile(src, dst)
        print(f"NOTE  copied the empty fallback icons.typ into {d} — run "
              f"scripts/harvest_icons.py there for the real marks")


def compile_pdf(typ, pdf, use_cli):
    """Returns (ok, stderr_text)."""
    if use_cli:
        r = subprocess.run(["typst", "compile", typ, pdf], capture_output=True, text=True)
        return r.returncode == 0, (r.stdout + r.stderr)
    try:
        import typst
        typst.compile(typ, output=pdf)
        return True, ""
    except Exception as e:
        return False, str(e)


def render_pngs(typ, tmp_dir, use_cli):
    pattern = os.path.join(tmp_dir, "p{p}.png")
    if use_cli:
        subprocess.run(["typst", "compile", typ, pattern, "--format", "png", "--ppi", "90"],
                        capture_output=True, text=True)
    else:
        import typst
        try:
            typst.compile(typ, output=pattern, format="png", ppi=90)
        except TypeError:
            typst.compile(typ, output=pattern, format="png")
    return sorted(glob.glob(os.path.join(tmp_dir, "p*.png")))


def count_pages(pdf, use_poppler):
    if use_poppler:
        out = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if line.startswith("Pages:"):
                return line.split()[1]
        return None
    import pypdf
    return str(len(pypdf.PdfReader(pdf).pages))


def extract_text(pdf, use_poppler):
    if use_poppler:
        return subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True).stdout
    import pypdf
    reader = pypdf.PdfReader(pdf)
    return "\n".join(page.extract_text() or "" for page in reader.pages)



# ---------- no section split across a page break (SKILL.md rule 5) ----------

# The headings come from the SOURCE, not from a guess at what a heading looks
# like in the extraction: every family defines its own `#section(t, body)` and
# calls it `#section("Title")[...]`, so the call sites ARE the declared list.
# No font-size heuristic survives 14 families; a grep does.
SECTION_CALL_RE = re.compile(r'#section\(\s*"([^"]*)"')

# lib.typ's `runhead` emits `name #h(1fr) n / total` (design.md § the device
# table: placed IN THE FLOW, because a page `header:` field is dropped by many
# parsers). pdftotext may put the name and the `n / total` on one line or two,
# in either order, so the pagination token is what identifies the band — and a
# section heading never carries one.
PAGINATION_RE = re.compile(r"\b\d+\s*/\s*\d+\b|\bpage\s+\d+\b", re.I)


def _norm_heading(s):
    """Compare headings on letters and digits only: the extraction upper-cases
    them, and a family's device may add or drop punctuation around one."""
    return re.sub(r"[^a-z0-9]+", " ", s.casefold()).strip()


def check_no_split(source, pages):
    """SKILL.md rule 5 -- "no section may split across a page break".

    Reduced to one measurable statement: a section that starts on page P and
    is not finished there leaves content at the TOP of page P+1. So every page
    after the first must OPEN on a section heading. Contrapositive of the rule,
    not an approximation of it -- if every break lands exactly on a boundary,
    nothing straddles; if one does not, whatever section preceded it is split.

    Pure function of (source text, extracted pages) so the selftest can feed it
    synthetic text and needs no Typst. The academic gate checks the same
    property one level down (verify_academic.check_no_straddle: the atom is the
    ENTRY there, and its heading list comes from the declared JSON spec).
    """
    headings = {_norm_heading(t) for t in SECTION_CALL_RE.findall(source)}
    headings.discard("")
    if not headings:
        return [(False, 'no-split: no #section("...") call in the source '
                        "-- not checked")]
    # pdftotext TERMINATES the last page with \f rather than separating pages
    # with it, so a naive split leaves a trailing empty chunk — which read as
    # "page N+1 opens on nothing" and failed all 30 one-page deliverables.
    while pages and not pages[-1].strip():
        pages = pages[:-1]
    if len(pages) < 2:
        return [(False, "no-split: single page, nothing to split")]
    out = []
    for pageno, page in enumerate(pages[1:], 2):
        lines = [l.strip() for l in page.split("\n") if l.strip()]
        for j in range(min(2, len(lines))):       # the running-head band only
            if PAGINATION_RE.search(lines[j]):
                lines = lines[j + 1:]
                break
        first = lines[0] if lines else ""
        f = _norm_heading(first)
        # A long heading can wrap, so the opening line may be a PREFIX of one.
        # Loose in the only direction that is safe: the line still has to sit
        # at the very top of the page to be considered at all.
        ok = bool(f) and any(h == f or h.startswith(f + " ") for h in headings)
        out.append((not ok,
                    f'no-split: page {pageno} opens on "{first[:60]}"'
                    + ("" if ok else " -- not a section heading, so the "
                                     "section before the break is SPLIT "
                                     "across it (SKILL.md rule 5)")))
    return out

# ---------- whitespace structure: section boundaries + canyons ----------

# BOUNDARY_RATIO is a LOCATOR, not a grade. It answers "is this white run tall
# enough to be a section boundary rather than a line gap", which is all that
# `boundary_ink` and the hole check need from it, and it is the only job the
# number survives.
#
# It used to also FAIL a page whose tallest run fell under it. That is gone,
# measured out on 2026-09-13 over the 30 rendered pages of the 29-deliverable
# corpus, under the CURRENT instrument (see measure_fill.gaps — the sampling
# changed at 42049f6 and nothing downstream was re-measured until now):
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
# prefilter, the verdict comes from LOCATION (boundary_ink) — and the white
# ratio is now reported, never failed.
BOUNDARY_RATIO = 2.0
# …and the ceiling, which is a SMOKE ALARM, not a grade either. Whitespace is
# the WEAK separator: piling it on is what an agent does when the boundary does
# not read and it has no device to reach for, and the page that carries no
# device at all AND a gap unlike anything the roster produces is the
# « séparateurs, pas des espaces vides » defect this catches.
# It cannot be calibrated between populations, because there is only one: the
# device-less pages run 2.38 2.56 2.86 2.86 3.29 3.57 3.86 4.00 4.17 5.00,
# continuously, and the roster's highest page of any kind is margin-index at
# 5.14 (a deliberately device-less family, which design.md says legitimately
# owes a HIGH ratio — failing it for that would contradict the rule it serves).
# So the ceiling is placed ABOVE the entire roster and BELOW the no-boundary-
# system pages the selftest draws (6.77 for one lone flourish, 7.92 for none at
# all). 5.0 kept the corpus green only by an exact tie (humanist-quiet/resume
# measures 5.00), which is not a calibration.
SEPARATION_CEILING = 6.0
# …and a device is a REPEATED element: one mark on the page is an ornament,
# typically the flourish under the name. Two families passed the ink check on
# exactly that — `gutter-rail` on its header bar, `engraved-card` on the 56pt
# rule under the name — with nothing at any section boundary below.
# ponytail: a flat count, not a per-boundary tally; a page carrying a single
# section boundary (the tail of a 2-pager) would read as ornament-only. No such
# page exists in the corpus — the thinnest is page 2 of swiss-grid's 2-pager
# with 5 — so a per-boundary pairing is not worth its code yet.
DEVICE_QUORUM = 2
CANYON = 0.035          # a hole this tall (fraction of page height) is a defect
BOUNDARY_CEILING = 0.05  # …unless it is a section boundary, which may run this tall

# Families whose boundary device is real but of a KIND no row scan can see.
# Measured 2026-09-13; each is a device nature, not a tuning miss:
DEVICELESS = {
    "humanist-quiet",   # no ink at all, by doctrine (design.md: pure gap)
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


# ---------- ATS date and degree-token checks (references/ats.md) ----------

# A range whose START has a year and no month: "2019 – 2021", "2017 – present".
# The ATS parses these as 12-month or zero-length stints (ats.md § dates), so
# the rule is month+year both ends. WARN, never FAIL: SKILL.md rule 1 lets a
# candidate who cannot supply months keep year-only deliberately. A lone year
# (a degree year) is not a range and never matches.
# Explicit EN+FR months (full, abbreviated, accented) and seasons, so that
# "Marketing", "Mayor" or "Decorator" are never read as a month.
_MONTH = (r"(?:jan(?:uary|vier|v)?|f[ée]v(?:rier|r)?|feb(?:ruary)?|mar(?:ch|s)?"
          r"|apr(?:il)?|avr(?:il)?|may|mai|june?|juin|jul(?:y)?|juil(?:l(?:et)?)?"
          r"|aug(?:ust)?|ao[uû]t?|sep(?:t(?:ember|embre)?)?|oct(?:ober|obre)?"
          r"|nov(?:ember|embre)?|dec(?:ember)?|d[eé]c(?:embre)?)")
_SEASON = r"(?:fall|autumn|summer|winter|spring|automne|[ée]t[ée]|hiver|printemps)"
_DATED = r"(?:%s|%s)\.?\s+" % (_MONTH, _SEASON)
# Both ends of a range need a month (or season): `Aug 2019 – 2021` and
# `2019 – Aug 2021` WARN as well as `2019 – 2021`. Present/now as the end is fine.
YEAR_RANGE_RE = re.compile(
    r"(?<!\d)((?:19|20)\d{2})\s*[–—-]\s*"
    r"(%s)?"
    r"((?:19|20)\d{2}(?!\d)|present|now|aujourd.hui|pr[ée]sent)" % _DATED, re.I)
MONTH_BEFORE_RE = re.compile(r"(?<![^\W\d_])" + _DATED.replace(r"\s+", r"\s*") + r"$", re.I)


def check_year_only_dates(txt):
    """Lines carrying a range where either end lacks a month (or season)."""
    out = []
    for line in txt.split("\n"):
        for m in YEAR_RANGE_RE.finditer(line):
            end_ok = (m.group(2) is not None
                      or not m.group(3)[0].isdigit())
            if not (MONTH_BEFORE_RE.search(line[:m.start()]) and end_ok):
                out.append(line.strip())
                break
    return out


# A degree token next to a non-completion marker: the Eightfold-class parsers
# read "B.Eng. program" as a degree HELD (ats.md). Wording that says what it is
# ("Undergraduate coursework") carries no degree token and passes.
DEGREE_RE = re.compile(
    r"(?<!\w)(?:B\.?\s?Eng|B\.?\s?Sc|M\.?\s?Sc|Bachelor(?:'?s)?|Baccalaur[ée]at"
    r"|Bac(?![\w+])\.?|Master(?:'?s)?|Ma[iî]trise|Licence)(?!\w)", re.I)
# "Program Manager" etc. is a job title, not a non-completion marker. (The
# window stops at a comma/semicolon, so "Master's degree, program in CS" no
# longer WARNs; "Master's degree program in CS" does. Only a WARN either way.)
INCOMPLETE_RE = re.compile(
    r"\b(?:coursework|program(?:me)?(?!\s+(?:manager|director|coordinator|lead"
    r"|officer|analyst|gestionnaire|directeur|directrice|coordonnat)\w*)"
    r"|in progress|ongoing|scolarit[ée]|en cours|"
    r"incomplete|non compl[ée]t[ée]|not completed)\b", re.I)


# Adjacent, not merely on the same line: prose such as "coursework at Polytechnique Exemple, I am
# completing a bachelor's degree" says what it is and must not trip the check.
DEGREE_NEAR_RE = re.compile(
    "(?:%s)[^,;]{0,30}?(?:%s)|(?:%s)[^,;]{0,30}?(?:%s)"
    % (DEGREE_RE.pattern, INCOMPLETE_RE.pattern,
       INCOMPLETE_RE.pattern, DEGREE_RE.pattern), re.I)


def check_degree_tokens(txt):
    """Lines pairing a degree token with a non-completion marker within 30 chars."""
    return [l.strip() for l in txt.split("\n") if DEGREE_NEAR_RE.search(l)]


# A bullet marker set as a CHARACTER survives into the ATS's text (measured:
# Banque Nationale showed it alone on a line above the bullet; Eightfold printed
# it literally). Markers must be drawn (references/ats.md). Private-use code
# points are what icon fonts (Font Awesome etc.) emit. Leading position only:
# an inline separator or a prose dash is not what this catches.
BULLET_CHAR_RE = re.compile("^[\u25c6\u25c7\u2022\u25aa\u25ab\u25ba\u25cf\u25a0\u25e6\u2023\u2219\u27a2\ue000-\uf8ff]")


def check_bullet_chars(txt):
    """Extracted lines that start with a bullet or private-use character."""
    return [l.strip() for l in txt.split("\n") if BULLET_CHAR_RE.match(l.strip())]


def family_from_path(path):
    """The family this CV is built from, for the DEVICELESS exemption.

    Read from the `// FAMILY: <name>` banner every template carries on line 1,
    NOT from the directory. A delivered CV is a copy of the template living in
    the user's own folder (SKILL.md: "delivered copies are retailoring"), so a
    path-only rule exempts the template and fails the very file the skill
    ships — measured: a copy of `humanist-quiet` outside the tree FAILed the
    quorum while the family is legitimately device-less. The banner travels
    with the copy; the path does not. Directory name is the fallback, for a
    file whose banner was edited away."""
    try:
        with open(path, encoding="utf-8") as fh:
            m = re.match(r"\s*//\s*FAMILY:\s*([\w-]+)", fh.readline())
        if m:
            return m.group(1)
    except OSError:
        pass
    parts = os.path.normpath(path).split(os.sep)
    if "families" in parts:
        i = parts.index("families")
        if i + 1 < len(parts):
            return parts[i + 1]
    return None


def word_boxes(pdf, with_text=False):
    """Per-page list of pdftotext word boxes (x0, y0, x1, y1) in PDF points.

    With `with_text` each item is ((x0, y0, x1, y1), word) instead.

    Returns None (not a list of empties) when pdftotext is missing or fails,
    so callers can tell "no text found" from "couldn't check" and degrade to
    the old ink-only detector rather than treating every row as furniture.
    """
    try:
        r = subprocess.run(["pdftotext", "-bbox", pdf, "-"],
                            capture_output=True, text=True)
    except (FileNotFoundError, OSError):
        return None
    if r.returncode != 0:
        return None
    pages = []
    for pg in r.stdout.split("<page ")[1:]:
        items = [((float(m[1]), float(m[2]), float(m[3]), float(m[4])), html.unescape(m[5]))
                 for m in re.finditer(r'<word xMin="([\d.]+)" yMin="([\d.]+)" '
                                      r'xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>', pg)]
        pages.append(items if with_text else [b for b, _ in items])
    return pages


# Rows whose longest dark run OUTSIDE every word box reaches this share of
# page width are furniture (a tick, a side bar) rather than a word's own
# ink. Measured plateau, not a fitted curve: the signal is identical from
# 0.01 to 0.03; below 0.005 contact icons and list bullets start appearing as
# "devices". The old detector's RULE_FLOOR needed to be 0.04 to separate a
# device from RAW TEXT on the same scan; this floor only has to separate a
# device from the residue text leaves after its own word boxes are
# subtracted, which is a much smaller gap to clear.
FURNITURE_FLOOR = 0.02
FURNITURE_PPI = 90
FURNITURE_SCALE = FURNITURE_PPI / 72.0   # pdftotext boxes are in PDF points
FURNITURE_PAD = 1.0                      # pt padding so antialiasing at a
                                         # glyph's edge doesn't read as ink


def furniture_ink(png, boxes):
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
    px = im.load()
    sc = FURNITURE_SCALE
    cov = [[] for _ in range(h)]
    for x0, y0, x1, y1 in boxes:
        ya = max(0, int((y0 - FURNITURE_PAD) * sc))
        yb = min(h - 1, int((y1 + FURNITURE_PAD) * sc))
        xa = max(0, int((x0 - FURNITURE_PAD) * sc))
        xb = min(w, int((x1 + FURNITURE_PAD) * sc) + 1)
        for y in range(ya, yb + 1):
            cov[y].append((xa, xb))

    def uncovered_dark_run(y):
        merged = []
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
    bands, cur = [], None
    for y, r in enumerate(rows):
        if r >= FURNITURE_FLOOR:
            cur = [y, y] if cur is None else [cur[0], y]
        elif cur:
            bands.append((cur[0], cur[1]))
            cur = None
    if cur:
        bands.append((cur[0], cur[1]))
    return bands


def boundary_ink(white, ink, med):
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
    def span(a, b):
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


def near_boundary(band, white, med):
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


def check_text_clip(png, boxes):
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
    px, rgb = lum.load(), im.load()
    s = FURNITURE_SCALE
    found = []   # (kind, line-row, word) — folded into one FAIL per line below

    def column_edges(x, ya, yb):
        x = min(max(int(x), 0), w - 1)
        edges = []
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
        lines = []   # words of one kind, grouped by text line (rows within 4px)
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


def check_whitespace(path, boxes=None, family=None, degraded=False):
    """Yield (is_fail, message) for one rendered page.

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
    # It did not, until 2026-09-13: `ink` and `furniture` double-counted the
    # SAME band on color-band, swiss-grid, margin-index, editorial-serif and
    # engraved-card, inflating every union those families reported.
    off = int(h * 0.02)

    def _overlap(a, b):
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
    # The half of the invariant the white scan alone could never check. A
    # boundary is supposed to carry INK by default (design.md § Invariants);
    # with no device AT A BOUNDARY, whitespace is the whole separator,
    # and a WIDE boundary on top of that is the failure this gate exists to
    # catch: separators are wanted, not empty space.
    if len(union) < DEVICE_QUORUM:
        exempt = family in DEVICELESS
        # A MISSING TOOL IS NOT A DESIGN DEFECT. Without pdftotext the union
        # is the old row scan alone, which is exactly the detector this gate
        # was rewritten to stop trusting: it scores 0 on quiet-luxury and
        # avant-poster, whose devices are real but sit on the heading's own
        # line. Failing on that would report a valid CV as broken, so when the
        # boxes are unavailable the quorum is REPORTED, never failed.
        yield (not (exempt or degraded)), (
            f"boundaries carry no ink: {len(union)} rule/bar/slab AT a section "
            f"boundary, need {DEVICE_QUORUM} ({len(all_ink)} wide dark run(s) "
            f"on the page — an underline, a table rule or a single flourish "
            f"under the name is not a boundary system)"
            + (" — NOT MEASURED: pdftotext is unavailable, so devices beside "
               "the heading (ticks, side bars) are invisible to this run. "
               "Install poppler-utils to restore the check"
               if degraded else
               f" — add the family's device at each boundary, or a thin `soft` "
               f"hairline above each section (design.md § Boundaries carry ink "
               f"by default); if the gap is doing the work instead, give it "
               f"back to body leading")
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


# ---------- auto-tuner: the fill loop, run by bisection instead of by hand ----------

# What is being searched, and why a bisection is valid here: raising `leading`
# pushes every line further down, so the last ink row rises monotonically with
# it — until the last unbreakable section no longer fits and the page count
# jumps. The set of leading values that keep the expected page count is
# therefore an interval [lo, L*], and the best fill is at its top end. So:
# bisect for L*, then check the fill it produces.
#
# `spacing` moves WITH `leading`, keeping the family's own delta between the
# two: that delta is part of the recipe (a family with a wide paragraph
# spacing relative to its leading has a different rhythm, not just a different
# density), and tuning them independently would silently redesign the family.
#
# If the fill at L* is still under the target, no leading value reaches it:
# that is the anti-filler clause (SKILL.md rule 5) speaking — the content does
# not honestly fill that pagination. The tuner says so instead of inventing a
# value; the fix is the section gap, real content, or a different page count.

# ---------- grouping / date / duplicate-name / forced-break gates ----------
# lib.typ tags every entry head and skill label with an invisible <vitae-head>
# metadata (text, org, page, x, y) and every section title with <vitae-sec>
# (pure metadata, no layout effect). `typst query` reads them back; the words
# come from the PDF (word_boxes(pdf, with_text=True)).

def _typst_query(typ, selector, root=None):
    """JSON list of the values of every element labelled `selector`, or None."""
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
                return json.loads(r.stdout)
            except ValueError:
                continue
    return None


def _gnorm(t):
    return "".join(ch for ch in t.casefold() if ch.isalnum())


def _lines(words, x_min):
    """Words (x0, y0, x1, y1, text) at or right of x_min, clustered into text
    lines by y-centre -> sorted list of dicts {y0, y1, c, x0, words}."""
    ws = sorted((w for w in words if w[0] >= x_min), key=lambda w: (w[1] + w[3]) / 2)
    out = []
    for w in ws:
        c = (w[1] + w[3]) / 2
        if out and abs(c - out[-1]["c"]) <= 3.0:
            ln = out[-1]
            ln["words"].append(w)
            ln["y0"], ln["y1"] = min(ln["y0"], w[1]), max(ln["y1"], w[3])
            ln["x0"] = min(ln["x0"], w[0])
            ln["c"] = (ln["y0"] + ln["y1"]) / 2
        else:
            out.append({"y0": w[1], "y1": w[3], "c": c, "x0": w[0], "words": [w]})
    return out


def _find_run(words, text, ytyp):
    """The words of `text` (first 4 tokens) nearest typst y `ytyp` -> list of
    word tuples, or None."""
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
    if best is None or best[0] > 30:
        return None
    return [words[k] for k in best[1]]


def _line_index(lines, run):
    w = run[0]
    for i, ln in enumerate(lines):
        if any(x is w for x in ln["words"]):
            return i
    return None


INK_DPI = 300
INK_DELTA = 60          # a pixel counts as ink when it differs this much from the background
RULE_PT = 10.0          # an ink run this long in one pixel row is a rule / band / underline, not glyphs


def _row_stats(data, w, r, tbl):
    """(ink pixels, longest contiguous ink run) of pixel row r of a w-wide crop."""
    s = data[r * w:(r + 1) * w].translate(tbl)
    n = s.count(b"\x01")
    return n, (max(map(len, s.split(b"\x00"))) if n else 0)


def _xheight_band(prof):
    """(top, bottom) row indexes of the dense x-height band of a text line from
    its ink row profile (None when there is no ink). Ascender, cap-overshoot and
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
    best, cur, start, bi = 0.0, 0.0, 0, None
    for i, v in enumerate(prof):
        if cur <= 0:
            cur, start = 0.0, i
        cur += v - lvl
        if cur > best:
            best, bi = cur, (start, i)
    return bi


def _page_ink_gap(pdf):
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
    cache, tmp, pbg, met = {}, [], {}, {}
    k = INK_DPI / 72.0

    def img(page):
        if page not in cache:
            cache[page] = None
            try:
                if not tmp:
                    tmp.append(tempfile.mkdtemp(prefix="vitae-prox-"))
                    # a 300 dpi page raster is ~9 MB: never leave them behind
                    atexit.register(shutil.rmtree, tmp[0], True)
                pre = os.path.join(tmp[0], f"p{page}")
                r = subprocess.run(["pdftoppm", "-r", str(INK_DPI), "-gray", "-singlefile",
                                    "-f", str(page), "-l", str(page), pdf, pre],
                                   capture_output=True)
                if r.returncode == 0:
                    cache[page] = Image.open(pre + ".pgm").convert("L")
                    cache[page].load()
            except (OSError, ValueError):
                cache[page] = None
        return cache[page]

    def page_bg(page, im):
        # background = the PAGE's dominant tone, not the crop's (a reversed-out
        # band would otherwise count as "background")
        if page not in pbg:
            hp = im.histogram()
            pbg[page] = max(range(256), key=hp.__getitem__)
        return pbg[page]

    def tbl_for(bg):
        return bytes(1 if abs(v - bg) > INK_DELTA else 0 for v in range(256))

    def metrics(page, im, ln):
        """(top, base) pixel rows of one text line: x-height band of its ink, or
        the edges of the fill it sits on."""
        key = (page,) + tuple(round(v, 1) for v in ln)
        if key in met:
            return met[key]
        res = None
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
                    full = lambda r: sd[r * sw:(r + 1) * sw].translate(stb).count(b"\x01") >= 0.9 * sw
                    c = (ya + yb) // 2
                    if not full(c):
                        continue
                    t = b = c
                    while t > 0 and full(t - 1):
                        t -= 1
                    while b < im.height - 1 and full(b + 1):
                        b += 1
                    if b - t + 1 <= 3 * (yb - ya):       # a band round the line, not a page-high field
                        res = (t, b)
                        break
            if res is None:
                tbl = tbl_for(lbg)
                data, w = reg.tobytes(), reg.width
                prof = []
                for r in range(reg.height):
                    n, run = _row_stats(data, w, r, tbl)
                    prof.append(0 if run >= RULE_PT * k else n)    # underline / rule rows are not glyphs
                bd = _xheight_band(prof)
                if bd and bd[1] - bd[0] >= 2:
                    res = (ya + bd[0], ya + bd[1])
        met[key] = res
        return res

    def gap(page, up, lo):
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


def measure_groups(heads, secs, pages_words, gap_fn=None):
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
    rows, skipped = [], 0
    marks = [dict(h, _k="h") for h in heads] + [dict(s, _k="s") for s in secs]
    box = lambda ln: [ln["x0"], max(w[2] for w in ln["words"]), ln["y0"], ln["y1"]]
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
        if i_next is None or i_next <= i0 + 1:
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
    xs = {}
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


PROX_FAIL, PROX_WARN = 0.7, 0.85


def check_group_proximity(typ, pdf, root=None, heads=None, secs=None, pages=None, detail=None):
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
        return [("WARN", "group proximity NOT checked (typst query or pdftotext unavailable)")]
    if not heads:
        return [("WARN", "group proximity not measured: no lib entry()/srow() heads")]
    rows, skipped = measure_groups(heads, secs, pages, _page_ink_gap(pdf) if pdf else None)
    if detail is not None:
        detail.extend(rows)
    grp = [r for r in rows if r["kind"] == "group"]
    if not grp:
        return [("WARN", f"group proximity: no checkable group ({skipped} head(s) not located) — unchecked")]
    for r in grp:
        print(f'DETAIL group "{r["text"][:30]}" p{r["page"]} lines={r["n"]} internal={r["internal"]:.2f}pt '
              f'between={r["between"]:.2f}pt ratio={r["ratio"]:.2f}')
    for r in rows:
        if r["kind"] == "sec":
            print(f'DETAIL section "{r["text"][:30]}" p{r["page"]} before-bar={r["before"]:.2f}pt '
                  f'bar-to-first={r["after"]:.2f}pt ratio={r["ratio"]:.2f}')
    out = []
    if skipped:
        out.append(("WARN", f"group proximity not measured for {skipped} head(s) (multi-column layout, "
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
            out.append(("FAIL", f"section proximity: {len(sbad)}/{len(sec)} titles sit closer to the block "
                        f"above than to their own first line {sw}; need >= {PROX_FAIL}) — fix the family's "
                        "`section` (its `above` and the gap under the title), not the content file"))
        elif sweak:
            out.append(("WARN", f"section proximity: {len(sweak)}/{len(sec)} titles barely separated from "
                        f"the block above {sw}; aim for >= {PROX_WARN})"))
        else:
            out.append(("OK", f'section proximity: {len(sec)} titles, gap above >= {PROX_WARN} x gap below '
                        f'(tightest "{s["text"][:30]}": ratio {s["ratio"]:.2f})'))
    m = min(grp, key=lambda r: r["ratio"])
    q = lambda t: '"' + t + '"'
    worst = (f'(worst {q(m["text"][:30])}: largest gap inside {m["internal"]:.1f}pt '
             f'({q(m["pair_in"][0])} -> {q(m["pair_in"][1])}), gap to the next block '
             f'{m["between"]:.1f}pt ({q(m["pair_btw"][0])} -> {q(m["pair_btw"][1])}), ratio {m["ratio"]:.2f}')
    bad = [r for r in grp if not r["ratio"] >= PROX_FAIL]
    if bad:
        return out + [("FAIL", f'group proximity: {len(bad)}/{len(grp)} groups sit closer to the next block than '
                 f'their own lines are to each other {worst}; need >= {PROX_FAIL})\n'
                 "      do not override entry/srow above/gap/below per entry; look for a manual #v, linebreak "
                 "or blank line inside that entry (a gap that is too big inside is as bad as one too small after);\n"
                 "      if the CV uses the family file as shipped, report it: it is a template bug (never edit lib.typ)")]
    weak = [r for r in grp if not r["ratio"] >= PROX_WARN]
    if weak:
        return out + [("WARN", f'group proximity: {len(weak)}/{len(grp)} groups barely separated from the next block '
                 f'{worst}; aim for >= {PROX_WARN})\n'
                 "      do not override entry/srow above/gap/below per entry; check for a manual #v, linebreak or "
                 "blank line inside that entry")]
    return out + [("OK", f"group proximity: {len(grp)} groups, gap to next block >= {PROX_WARN} x internal gap "
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


def _entry_records(marks):
    """Marks in document order -> one record per entry head:
    {"head": mark, "date": mark|None, "org": mark|None, "date_first": bool}.
    A part mark belongs to the entry head emitted before it."""
    recs, cur = [], None
    for m in marks or []:
        k = m.get("kind")
        if k == "entry":
            cur = {"head": m, "date": None, "org": None, "date_first": None}
            recs.append(cur)
        elif k in ("date", "org") and cur is not None and cur[k] is None:
            cur[k] = m
            if cur["date_first"] is None:
                cur["date_first"] = k == "date"
        elif k not in ("date", "org"):
            cur = None
    return recs


def _yc(w):
    return (w[0][1] + w[0][3]) / 2


def _first_word(words, x, y, y_end, x_end=None):
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


def check_date_adjacency(typ, pdf, marks=None, root=None, warns=None, words=None, stats=None):
    """FAIL messages: in the extracted text (what an ATS reads) an entry's date
    must come BEFORE the line under its head (org / descriptor: ats.md, the org
    line anchors the date) and before the NEXT entry's head. Positions come from
    lib.typ's markers; the order is pdftotext's. `warns` (list) collects
    "not measured" notes. An entry given no date (`dated: false`) is skipped.
    `stats` (dict) receives the counts: measured / undated / unmeasured lib
    entries (an entry not built with lib `entry` carries no marker and is in
    none of them)."""
    marks = _typst_query(typ, ENTRY_MARKS, root) if marks is None else marks
    out = []
    warn = (lambda m: warns.append(m)) if warns is not None else (lambda m: None)
    fix = ('fix: give the date a month range ("Sep 2011 – Jun 2012", rule: month+year) '
           "or put a line of text after the date inside the same entry "
           "(institution / descriptor line), so the date is not alone at the end "
           "of the entry (references/ats.md, Entry-with-no-bullets trap)")
    late = ("— a parser then reads the date as missing. Most common cause: a narrow "
            "date (bare year such as \"2012\") right-flushed on the role row whose "
            "following lines do not reach under it, so pdftotext clusters it alone and "
            "emits it late. ")
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
        warn("pdftotext unavailable (word positions needed)")
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
        st["unmeasured"] += 1              # until the judgement below is reached
        if d is None:
            warn(f"{name}: dated but no date marker")
            continue
        if o is not None and not r["date_first"]:
            out.append(f"{name}: the employer line is EMITTED before the date (entry "
                       "rebuilt out of lib order?) " + late + fix)
            continue
        pg = h.get("page") or 1
        if d.get("page") != pg:
            out.append(f"{name}: its date is set on page {d.get('page')}, its head on page {pg} "
                       "— the date is read with the wrong entry. " + fix)
            continue
        if not 0 < pg <= len(words):
            warn(f"{name}: page {pg} not in the PDF")
            continue
        pw = words[pg - 1]
        oy = o["y"] if o is not None and o.get("page") == pg and o["y"] > d["y"] else None
        d_end = oy if oy is not None else d["y"] + 4 * max(d.get("h", 0), 6)
        di = [i for i, w in enumerate(pw)
              if w[0][0] >= d["x"] - 1.5 and w[0][2] <= d["x"] + d.get("w", 0) + 1.5
              and d["y"] - 2 <= _yc(w) < d_end]
        hi = _first_word(pw, h["x"], h["y"], d_end, x_end=d["x"] - 1)
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
        oi = (_first_word(pw, o["x"], o["y"], o["y"] + max(o.get("h", 0), 6) + 4, x_end=cr)
              if oy is not None else None)
        # first word READ of anything set below the head block in this column
        # (org line, bullet, next head, next section title)
        bi = min((i for i, w in enumerate(pw)
                  if _yc(w) > d_bot and w[0][0] < cr and w[0][2] > cl), default=None)
        st["unmeasured"] -= 1
        st["measured"] += 1
        if ni is not None and last > ni:
            out.append(f"{name}: its date is emitted AFTER the next entry starts "
                       "— a narrow date (bare year such as \"2012\") right-flushed on the role "
                       "row, with no line under it reaching below the date, is clustered alone by "
                       "pdftotext and emitted late. " + fix)
        elif oi is not None and last > oi:
            out.append(f"{name}: the extracted text reads the employer line "
                       "BEFORE the date (role/org boxes overlap? raise the in-head gap in lib.typ entry) "
                       + late + fix)
        elif bi is not None and last > bi:
            out.append(f"{name}: its date is emitted AFTER text set below the entry head "
                       f'(read first: "{pw[bi][1][:30]}") ' + late + fix)
        elif o is not None and oi is None:
            warn(f"{name}: employer line words not found at the marker position")
    return out


LIST_ITEM_RE = re.compile(r"^(\s*)(?:[-+]|\d+\.)\s")
FORCED_BREAK_RE = re.compile(r"(?<!\\)\\(?:\s|$)|#linebreak\s*\(")


def check_forced_linebreak(src):
    """FAIL messages: a forced line break (`\\ ` or `#linebreak()`) inside a
    bullet / list item. A bullet is one sentence that wraps on its own; a hard
    break mid-bullet leaves a ragged half-line and, in the extraction, splits
    the bullet in two."""
    out, indent = [], None
    for n, raw in enumerate(src.split("\n"), 1):
        line = re.sub(r"(?:^|(?<=\s))//.*$", "", raw)
        m = LIST_ITEM_RE.match(line)
        if m:
            indent = len(m.group(1))
        elif indent is not None:
            if not line.strip() or len(line) - len(line.lstrip()) <= indent:
                indent = None
        if indent is not None and FORCED_BREAK_RE.search(line):
            out.append(f"line {n}: forced line break inside a bullet "
                       f'("{raw.strip()[:50]}") — let the bullet wrap itself; '
                       "split it into two bullets or shorten it")
    return out


def check_duplicate_names(secs, heads):
    """FAIL messages: one name used both as a section title and as a row label
    (e.g. section LANGUAGES for spoken languages + skill label "Languages" for
    programming ones), compared case-insensitively. Two things with one name
    read as one list to a human and to an ATS."""
    titles = {}
    for s in secs or []:
        if _gnorm(s.get("text", "")):
            titles.setdefault(_gnorm(s["text"]), s["text"])
    out = []
    for h in heads or []:
        if h.get("kind") == "skill" and _gnorm(h["text"]) in titles:
            out.append(f'"{h["text"].strip()}" is both a skill row label and the section title '
                       f'"{titles[_gnorm(h["text"])]}" — rename one (e.g. "Programming languages")')
    return out


def run_new_gates(typ, pdf, txt, src, root=None, detail=None):
    """Print the new gates' lines; return 1 if any FAIL."""
    fail = 0
    for lvl, msg in check_group_proximity(typ, pdf, root=root, detail=detail):
        print(f"{lvl:<5} {msg}")
        fail |= lvl == "FAIL"
    marks = _typst_query(typ, ENTRY_MARKS, root)
    heads = None if marks is None else [m for m in marks if m.get("kind") in ("entry", "skill")]
    if heads is not None and not any(h.get("kind") == "entry" for h in heads):
        print("WARN  date adjacency not measured: no lib entry()/srow() heads")
    dwarn, dst = [], {}
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
    for msg in check_forced_linebreak(src):
        print("FAIL  " + msg)
        fail = 1
    secs = _typst_query(typ, "<vitae-sec>", root)
    if not secs:   # a CV that never wrapped `section` in wd-section(): read the calls
        secs = [{"text": t} for t in re.findall(r'#section\(\s*"((?:[^"\\]|\\.)*)"', src)]
    for msg in check_duplicate_names(secs, heads):
        print("FAIL  duplicate name: " + msg)
        fail = 1
    return fail


PAR_RE = re.compile(r"(#set\s+par\([^)]*?leading:\s*)([0-9.]+)(em[^)]*?spacing:\s*)([0-9.]+)(em)")


def _read_par(text):
    m = PAR_RE.search(text)
    if not m:
        return None
    return float(m.group(2)), float(m.group(4))


def _write_par(text, leading, spacing):
    return PAR_RE.sub(
        lambda m: "%s%.3f%s%.3f%s" % (m.group(1), leading, m.group(3), spacing,
                                      m.group(5)), text, count=1)


def _probe(typ, text, leading, spacing, expected, use_cli, use_poppler):
    """Compile at (leading, spacing); return (pages_ok, fill_pct or None)."""
    open(typ, "w", encoding="utf-8").write(_write_par(text, leading, spacing))
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "t.pdf")
        ok, _ = compile_pdf(typ, pdf, use_cli)
        if not ok:
            return False, None
        if count_pages(pdf, use_poppler) != str(expected):
            return False, None
        pngs = render_pngs(typ, tmp, use_cli)
        if not pngs:
            return False, None
        m = re.search(r"to (\d+)%", measure_fill.measure(pngs[-1]))
        return True, (int(m.group(1)) if m else None)


def tune(typ, expected, fmin, fmax, lo=None, hi=None, step=0.005):
    deps_ok, use_cli, use_poppler = preflight()
    if not deps_ok:
        return 1
    global _footer
    _footer = _FOOTER_TUNE
    original = open(typ, encoding="utf-8").read()
    cur = _read_par(original)
    if cur is None:
        _footer = _FOOTER_TUNE_NOPAR
        print("FAIL  no `#set par(... leading: Xem, spacing: Yem)` line to tune "
              "— the tuner edits that one declaration and nothing else")
        return 2
    l0, s0 = cur
    delta = s0 - l0                       # the family's own rhythm, preserved
    lo_arg = lo
    lo = l0 * 0.80 if lo is None else lo
    # The default ceiling is relative, but a family with an already-tight
    # leading gets a range too narrow to ever reach the fill target, so the
    # ceiling never sits below 1.10em.
    hi = max(l0 * 1.30, 1.10) if hi is None else hi
    hi_arg = hi
    print("tuning %s: leading %.3fem (spacing %+.3fem), searching [%.3f, %.3f], "
          "target %s pages / fill %s-%s%%"
          % (typ, l0, delta, lo, hi, expected, fmin, fmax))
    try:
        ok_lo, fill_lo = _probe(typ, original, lo, lo + delta, expected,
                                use_cli, use_poppler)
        if not ok_lo:
            open(typ, "w", encoding="utf-8").write(original)   # undo the probe
            print("FAIL  even the floor leading %.3fem does not give %s page(s) "
                  "— either the content is too long for %s page(s), or the search range starts "
                  "too high: try an explicit lower range, e.g. `--tune %s %s %s %s 0.45 1.0` "
                  "(FILL_MIN FILL_MAX LEAD_LO LEAD_HI)"
                  % (lo, expected, expected, typ, expected, fmin, fmax))
            return 1
        best, best_fill = lo, fill_lo
        # The top of the feasible interval is not always the ANSWER: the last
        # value before the page breaks can overshoot fmax (the fill target has
        # a ceiling too — ink is not supposed to reach into the bottom margin).
        # So remember the largest probe that landed INSIDE the target and
        # prefer it over the interval's top end.
        in_target = None
        while hi - lo > step:             # bisect for the top of the interval
            mid = (lo + hi) / 2
            ok, fill = _probe(typ, original, mid, mid + delta, expected,
                              use_cli, use_poppler)
            print("  leading %.3fem -> %s" % (
                mid, ("fill %s%%" % fill) if ok else "page count off"))
            if ok:
                lo, best, best_fill = mid, mid, fill
                if fill is not None and fmin <= fill <= fmax:
                    in_target = (mid, fill)
            else:
                hi = mid
        if in_target and not (best_fill is not None and fmin <= best_fill <= fmax):
            best, best_fill = in_target
        won = best_fill is not None and fmin <= best_fill <= fmax
        if not won:
            # A losing value is worse than no value: it silently replaces a
            # rhythm the family was designed with. Put the original back and
            # let the caller decide.
            open(typ, "w", encoding="utf-8").write(original)
            if lo_arg is not None and lo_arg <= 0.40 and hi_arg >= 1.40:
                _footer = _FOOTER_TUNE_WIDE
            print("FAIL  best leading %.3fem / spacing %.3fem -> fill %s%% "
                  "(target %s-%s%%); restored the original %.3fem/%.3fem"
                  % (best, best + delta, best_fill, fmin, fmax, l0, s0))
            print("      no leading in the searched range reaches the target at "
                  "%s page(s). Widen the range by passing the bounds "
                  "positionally after FILL_MAX, e.g.\n"
                  "        verify.py --tune %s %s %s %s %.2f %.2f\n"
                  "      or take the space out of the section gap / add real "
                  "content / change the page count (anti-filler clause, "
                  "SKILL.md rule 5)."
                  % (expected, typ, expected, fmin, fmax,
                     max(0.40, l0 * 0.65), max(1.40, l0 * 1.60)))
            return 1
        open(typ, "w", encoding="utf-8").write(
            _write_par(original, best, best + delta))
        print("OK    wrote leading %.3fem / spacing %.3fem -> fill %s%% "
              "(target %s-%s%%)" % (best, best + delta, best_fill, fmin, fmax))
        print("      now run the gate itself: verify.py %s %s %s %s"
              % (typ, expected, fmin, fmax))
        return 0
    except BaseException:
        open(typ, "w", encoding="utf-8").write(original)   # never leave a probe
        raise


# ---------- main gate ----------

HEADER_RE = re.compile(r"^//\s*vitae:\s*pages=(\d+)(?:\s+fill=(\d+)-(\d+))?",
                       re.M)


def pages_from_name(typ):
    """The page count a headerless deliverable declares in its own file name."""
    return "2" if re.search(r"[-_]2\s*p(?:ages?)?(?![a-z])",
                            os.path.basename(typ), re.I) else "1"


NON_CV_RE = re.compile(
    r"(?<![^\W\d_])(?:guide|lettre|letter|cover|lisez-moi|readme)(?![^\W\d_])",
    re.I)


def is_gated(typ):
    """--all's rule: gate every .typ except known non-CV deliverables (guide,
    letter, cover, lisez-moi, readme by name); a `// vitae:` header opts in."""
    if not NON_CV_RE.search(os.path.basename(typ)):
        return True
    try:
        with open(typ, encoding="utf-8") as fh:
            return bool(HEADER_RE.search(fh.read(4096)))
    except OSError:
        return False


ACADEMIC_MARKER = "// vitae-academic:"
LETTER_MARKER = "// vitae letter template"


def is_academic(path):
    """True for an academic CV, which this gate must NOT judge.

    An academic CV is a different genre: the atom is the ENTRY, not the
    section, there is no fill target at all, and its length is whatever the
    record is — 13 pages is ordinary. This gate is calibrated on one- and
    two-page industry resumes, and `check_all` guesses a headerless file's
    page count from its NAME (defaulting to 1), so a sweep would fail an
    academic CV for being itself. It carries its own gate:
    `scripts/verify_academic.py`. The marker is a line-1 comment the academic
    template emits; see academic-mode.md § 5.2.3.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            return ACADEMIC_MARKER in fh.read(4096)
    except OSError:
        return False


def is_letter(path):
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


def check_all(directory):
    """Run the single-file gate over every .typ under `directory`.

    Re-invokes this script per file rather than refactoring main() apart: the
    point is that each deliverable gets EXACTLY the check it would get alone,
    and a subprocess guarantees that for free.
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
            # No header: take the page count from the FILE NAME, which is the
            # one expectation this repo already states out loud — `*-2page.typ`
            # is two pages, every other deliverable is one (SKILL.md step 4,
            # and the reference sweep in the read-me is written exactly that
            # way). This is the smallest thing that makes --all useful: not one
            # of the repo's own 30 .typ files carries the header, so the
            # command returned 30 UNCHECKED and exit 1 on the very corpus it
            # exists to guard. Fill stays undeclared and is reported, not
            # failed — a page count is inferable from a name, a fill target is
            # not, and inventing one would be the fitted-curve mistake again.
            # Add the header to a deliverable whose fill matters; it wins.
            args = [pages_from_name(typ)]
            unchecked.append(typ)
        print(f"\n=== {typ}  (expects {' '.join(args)}"
              f"{'' if m else ' — inferred from the file name, no header'})")
        r = subprocess.run([sys.executable, os.path.abspath(__file__), typ]
                           + args)
        fail |= bool(r.returncode)
    if unchecked:
        print(f"\nNOTE — page count inferred from the file name, fill not "
              f"checked (add `// vitae: pages=N fill=A-B` to pin either):")
        for t in unchecked:
            print(f"  {t}")
    print("\n" + ("FAIL — see above" if fail else
                  f"PASS — {len(typs)} deliverable(s), "
                  f"all siblings checked together"))
    return fail


# sha256 of every templates/lib.typ ever committed (past releases). A CV whose
# lib.typ matches one of these is a stale-but-honest copy (WARN); anything else
# was rewritten or edited (FAIL). The CURRENT lib is not listed: it is compared
# by content against the skill's own file. Regenerate after each release commit:
#   for c in $(git log --format=%H -- templates/lib.typ); do
#     git show $c:templates/lib.typ | sha256sum | cut -c1-64; done | sort -u
# (a model once rewrote lib.typ from memory, dropped `derive()`, and looped.)
KNOWN_LIB_SHA256 = {
    "a1b12d2fc073111d24bfb7f8ddd8ddff071ec313b213eaf9892a6448b2de7970",
    "b8fc908c0b36bdcd923fa867b212c7f5d12347ef1b4ca1411d18008b0f0bbb80",
    "ce6baaaa89b851cfdfced2bfcc436a67094adef8e13a89879a7d3d4f5daf3411",
    "61dc57dfd3c47aa14dbc0a84d1eced9afffc4e2e2a248242ce01ebec2f8da74c",
    "3bc21e1423e38f6b86234046c7f12ed2dc04eb7941ff574cf1e79c44a3269d2a",
    "6ba83f076ddf631218165bcda09a0198a19a7f0f13c94abddbdf1b66716de368",
    "67f96ab972f0f672e6885ead87e5b789bb37d160905127ef34590318327dc98c",
    "e77ad87885a2e310fec8bb2b7f751f412af7878d03f1470f47ed5bdaec15675b",
    "d8f3e08332cafa4fe8e8a2125175a1e66d94fc7ca9060adbd5bd6cc736bab38c",
    "5cf956d8341d41f9970e23074ac362cdf52d6d79f649d8f620a53b31e5a2989f",
    "7f50222c3394eee82bbfc1ac470c691c4b3756da0c0615d91e23d6d1394af8f9",
    "c037a4309decb8dfcf10058624f0b0ded8d466606bcabf9e327766bb99e6a99b",
}


def _strip_typst_comments(src):
    """src without // line comments and (nested) /* */ blocks. Double-quoted
    strings are respected but never span a newline (a stray 6" in markup must
    not swallow the rest of the file); backtick raw spans are skipped whole."""
    out, i, n, q = [], 0, len(src), False
    while i < n:
        c = src[i]
        if c == "\n":
            q = False
            out.append(c)
        elif q:
            out.append(c)
            if c == "\\" and i + 1 < n and src[i + 1] != "\n":
                out.append(src[i + 1]); i += 1
            elif c == '"':
                q = False
        elif c == "\\" and i + 1 < n and src[i + 1] != "\n":
            out.append(c + src[i + 1]); i += 1          # escaped char (\//, \", \`)
        elif c == "`":
            e = len(src[i:]) - len(src[i:].lstrip("`"))   # opening run of backticks
            close = src.find("`" * e, i + e)
            j = n if close < 0 else close + e
            out.append(" ")                # raw text is not code: drop it
            i = j
            continue
        elif c == '"':
            q = True; out.append(c)
        elif src.startswith("//", i) and (i == 0 or src[i - 1] != ":"):
            while i < n and src[i] != "\n":
                i += 1
            continue
        elif src.startswith("/*", i):
            depth, i = 1, i + 2
            while i < n and depth:
                if src.startswith("/*", i):
                    depth += 1; i += 2
                elif src.startswith("*/", i):
                    depth -= 1; i += 2
                else:
                    i += 1
            continue
        else:
            out.append(c)
        i += 1
    return "".join(out)


def check_lib_integrity(typ_path, skill_dir=None, known=None):
    """Return [(level, msg)] for the lib.typ the CV imports ("FAIL"/"WARN");
    empty when it is the skill's own lib or the CV imports none. Runs before
    compilation so the message survives a Typst error."""
    skill_dir = skill_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    known = KNOWN_LIB_SHA256 if known is None else known
    ref = os.path.join(skill_dir, "templates", "lib.typ")
    # Follow local #import "x.typ" chains (cv.typ -> family.typ -> lib.typ).
    lib, shown, seen, todo = None, None, set(), [os.path.abspath(typ_path)]
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
                break
            todo.append(path)
    if lib is None and os.path.isfile(ref) and os.path.isfile(
            os.path.join(os.path.dirname(os.path.abspath(typ_path)), "lib.typ")):
        return [("WARN", "lib import not recognised: a lib.typ sits next to the CV but no #import "
                         "resolves to it, so its integrity was NOT checked")]
    if lib is None or not os.path.isfile(ref):
        return []
    cv_dir = os.path.dirname(lib)
    import shlex
    cp = f"cp {shlex.quote(ref)} {shlex.quote(cv_dir + '/')}"
    if not os.path.isfile(lib):
        return [("FAIL", f"{shown} is imported but missing — copy it: {cp}")]
    import hashlib
    def digest(f):
        with open(f, "rb") as fh:
            data = fh.read()
        if data.startswith(b"\xef\xbb\xbf"):
            data = data[3:]
        return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()
    h = digest(lib)
    if h == digest(ref):
        return []
    if h in known:
        return [("WARN", f"lib.typ is from an older vitae release; recopy to get fixes: {cp}")]
    return [("FAIL", "lib.typ is not a copy of the skill's lib (rewritten or edited) "
                     f"— recopy it byte-for-byte: {cp}")]


# The last lines printed when a run ends on a FAIL. A reader (human or model)
# acts on what it sees LAST, so the instruction is here, not only in the header.
# Armed (set non-None) only after preflight succeeded, per mode, so a missing
# dependency or a usage error never gets a footer that blames cv.typ.
_NO_READ = ("      Do not open verify.py or lib.typ: their code is not the fix, and "
            "reading them costs your context.")
_FOOTER_GATE = ("NEXT  Apply the fix each FAIL above names, then re-run the same command. "
                "Edit cv.typ only; a lib.typ FAIL is fixed by the printed `cp` command "
                "(recopy it, never edit it).\n" + _NO_READ)
_FOOTER_TUNE = ("NEXT  Run the command printed above (wider range), or add real content / "
                "change the page count in cv.typ; do not edit leading by hand.\n" + _NO_READ)
_FOOTER_TUNE_NOPAR = ("NEXT  Add the `#set par(leading: Xem, spacing: Yem)` line to cv.typ "
                      "(copy it from the template), then re-run the same command.\n" + _NO_READ)
_FOOTER_TUNE_WIDE = ("NEXT  The range was already wide: do not re-run --tune. Add real content "
                     "or change the page count in cv.typ.\n" + _NO_READ)
_footer = None


def main():
    argv = sys.argv[1:]

    if argv and argv[0] == "--all":
        if len(argv) < 2:
            sys.exit("usage: verify.py --all DIR")
        sys.exit(check_all(argv[1]))
    if argv and argv[0] == "--gates":
        # new gates only, on a compiled PDF: --gates cv.typ cv.pdf [--root DIR]
        # (fixtures import ../../templates, so they need the repo as root)
        if len(argv) < 3:
            sys.exit("usage: verify.py --gates cv.typ cv.pdf [--root DIR]")
        root = argv[argv.index("--root") + 1] if "--root" in argv else None
        global _footer
        _footer = _FOOTER_GATE
        rows = []
        rc = run_new_gates(argv[1], argv[2], extract_text(argv[2], True),
                           open(argv[1], encoding="utf-8").read(), root=root, detail=rows)
        print("DETAIL " + json.dumps(rows))
        sys.exit(rc)
    if argv and argv[0] == "--doctor":
        ok, _, _ = preflight()
        sys.exit(0 if ok else 1)

    if argv and argv[0] == "--selftest":
        # The one piece of non-trivial logic here that can break silently: the
        # regex the tuner edits with. A miss makes --tune a no-op that still
        # reports success, so it gets a check.
        src = ('#set page(paper: "us-letter")\n'
               '#set par(justify: false, leading: 0.555em, spacing: 0.615em)\n'
               'body 0.999em\n')
        assert _read_par(src) == (0.555, 0.615), _read_par(src)
        out = _write_par(src, 0.61, 0.7)
        assert "leading: 0.610em, spacing: 0.700em" in out, out
        assert "body 0.999em" in out, "edited past the par declaration"
        assert _read_par(out) == (0.610, 0.700)
        # a file with no par declaration must be reported, never guessed at
        assert _read_par("#set text(size: 10.5pt)\n") is None
        # spacing-before-leading is not the template's order and must not match
        # silently in a way that swaps the two values
        alt = "#set par(spacing: 0.7em, leading: 0.6em)\n"
        assert _read_par(alt) is None, "would write the two values swapped"
        # --all's headerless fallback: the page count read off the name. Wrong
        # here and every 2-page deliverable is silently gated as a 1-pager.
        assert pages_from_name("a/resume-2page.typ") == "2"
        assert pages_from_name("a/resume.typ") == "1"
        for n in ("CV_X_2p.typ", "cv_2page.typ", "cv_2pages.typ", "cv-2p.typ",
                  "cv-2pages.typ", "CV-2 page.typ"):
            assert pages_from_name(n) == "2", n
        for n in ("CV_X_1p.typ", "cv_2pager.typ", "cv_12p.typ"):
            assert pages_from_name(n) == "1", n
        assert is_gated("CV_A_1p.typ") and not is_gated("Guide_X.typ")
        assert is_gated("Jane_Doe.typ") and is_gated("lebenslauf.typ")
        with tempfile.TemporaryDirectory() as td:
            for n, body in (("Odd_Letter.typ", "// vitae: pages=1\n"),
                            ("Guide_Candidature_X.typ", "x\n"),
                            ("Guide_Hdr.typ", "// vitae: pages=1\n"),
                            ("Jane_Doe.typ", "x\n")):
                with open(os.path.join(td, n), "w", encoding="utf-8") as fh:
                    fh.write(body)
            g = {n for n in os.listdir(td) if is_gated(os.path.join(td, n))}
            assert g == {"Odd_Letter.typ", "Guide_Hdr.typ", "Jane_Doe.typ"}, g
        assert pages_from_name("a/resume-pair-b.typ") == "1"
        assert pages_from_name("a/CV-2 page.typ") == "2"  # a space still counts
        assert pages_from_name("2page/resume.typ") == "1", "directory, not file"
        # The other piece that can break silently: the ink-band detector. If
        # it stopped seeing devices, every CV would pass the "carries ink"
        # check by accident, which is the exact rule that kept regressing.
        # Two synthetic pages, drawn with PIL so the check needs no Typst.
        from PIL import Image, ImageDraw

        def _page(rule_luma=None, gap=45, rule_len=975, underline=0, rules=4,
                  want_boxes=False):
            # `underline` is a COUNT of sections that get an underlined link
            # mid-body; `want_boxes` also returns the word boxes for the body
            # text (never for the underlines — pdftotext does not box a rule),
            # which is what lets furniture_ink see them.
            im = Image.new("L", (1275, 1650), 255)
            d = ImageDraw.Draw(im)
            boxes = []
            y = 200
            for s in range(4):
                if rule_luma is not None and s < rules:  # a hairline AT the boundary
                    d.line([(150, y), (150 + rule_len, y)], fill=rule_luma, width=2)
                y += gap                        # …or nothing but empty space
                for i in range(6):              # body text: short dark runs
                    for x in range(150, 1100, 60):
                        d.rectangle([x, y, x + 44, y + 8], fill=30)
                        boxes.append((x / FURNITURE_SCALE, y / FURNITURE_SCALE,
                                      (x + 44) / FURNITURE_SCALE,
                                      (y + 8) / FURNITURE_SCALE))
                    y += 22
                    if s < underline and i == 2:
                        # an underlined link mid-section: a 24%-of-width
                        # unbroken run, wider than any real device on the
                        # roster, but nowhere near a boundary
                        d.line([(150, y - 6), (450, y - 6)], fill=30, width=2)
            f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            im.save(f.name)
            return (f.name, boxes) if want_boxes else f.name

        # inked: a tight page whose boundaries are pale full-measure hairlines.
        # thin: the same, with a device deliberately SHORTER than the text
        # column (5.5% of page width — `quiet-luxury`'s tick is 5.65%); it must
        # still pass, which is what breaks if RULE_FLOOR is raised back to 0.08.
        # linked: the false positive the old page-wide scan could not see — no
        # device at all, but an underlined link supplying a wide dark run. bare:
        # the same defect without even that.
        inked, bare = _page(rule_luma=180), _page(rule_luma=None, gap=90)
        # gap=75 puts this page's white ratio OVER SEPARATION_CEILING, so it
        # passes only while the short rule is seen: miss the device and the
        # same page is the "empty space is doing the whole job" failure.
        thin = _page(rule_luma=30, rule_len=70, gap=75)
        linked = _page(rule_luma=None, gap=90, underline=1)
        # one rule at the top and nothing below it: the `engraved-card` /
        # `gutter-rail` case, a flourish under the name and bare space after
        lone = _page(rule_luma=30, gap=75, rules=1)
        assert measure_fill.bands(inked)[2], "a pale hairline must read as ink"
        assert not measure_fill.bands(bare)[2], "body text must not read as ink"
        assert measure_fill.bands(linked)[2], \
            "the underline must register as a wide dark run (else the next " \
            "assert passes for the wrong reason)"
        for p in (inked, thin):
            msgs = list(check_whitespace(p))
            assert not any(f for f, _ in msgs), \
                "a page whose boundaries carry a hairline must not FAIL"
            # …and POSITIVELY, that the device was seen. Asserting only "does
            # not FAIL" stopped proving that once SEPARATION_CEILING rose
            # above `thin`'s 5.62x ratio: miss the short rule and the page
            # merely reports "carries no ink" and still passes. This is the
            # assertion RULE_FLOOR = 0.08 has to break (a 5.5%-of-width rule
            # falls under an 8% floor), and the ceiling can no longer stand in
            # for it.
            assert any("boundary devices:" in m for _, m in msgs), \
                "a pale or short hairline AT a boundary must be COUNTED as a " \
                "device, not merely fail to trigger a failure"
        for p in (bare, linked, lone):
            assert any(f and "no ink" in m for f, m in check_whitespace(p)), \
                "empty-space-only separation must FAIL on the ink check, " \
                "whatever ink the page carries away from its boundaries"

        # --- furniture: the blind spot no row-wide scan can see ---
        # A device typeset ON the heading's own text line (a tick, a side
        # bar) never shows up in `all_ink`: the row also carries word ink, so
        # its longest UNBROKEN run is just one word's width — under
        # RULE_FLOOR — same as any ordinary text row. Only a word-box list
        # that does NOT cover the device can tell the two apart.
        def _page_with_tick():
            im = Image.new("L", (1275, 1650), 255)
            d = ImageDraw.Draw(im)
            boxes = []
            y = 200
            for s in range(4):
                first_row = True
                for i in range(6):
                    for x in range(150, 1100, 60):
                        d.rectangle([x, y, x + 44, y + 8], fill=30)
                        boxes.append((x / FURNITURE_SCALE, y / FURNITURE_SCALE,
                                      (x + 44) / FURNITURE_SCALE,
                                      (y + 8) / FURNITURE_SCALE))
                    if first_row:
                        # the tick: same row as text (never a white gap), and
                        # deliberately left OUT of `boxes` above. 30px of
                        # 1275 = 2.35%, above FURNITURE_FLOOR (2%) and below
                        # RULE_FLOOR (4%) so the old row-wide scan is blind
                        # to it on its own width too.
                        d.rectangle([1130, y, 1160, y + 8], fill=20)
                        first_row = False
                    y += 22
                y += 45
            f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            im.save(f.name)
            return f.name, boxes

        tick_png, tick_boxes = _page_with_tick()
        assert not any("boundary devices:" in m for _, m
                       in check_whitespace(tick_png)), \
            "without word boxes the OLD detector alone must MISS a device " \
            "sitting beside a text line (not in any white gap)"
        assert any("boundary devices:" in m for _, m
                   in check_whitespace(tick_png, boxes=tick_boxes)), \
            "furniture_ink must SEE the same tick once word boxes are given " \
            "— ink not covered by any word box, on a line that carries text"
        os.unlink(tick_png)

        # …and the other half of the same coin: furniture is only a device
        # when it sits AT a boundary. A page with NO device anywhere but four
        # underlined links deep inside its sections used to satisfy
        # DEVICE_QUORUM the moment word boxes were available — `linked` above
        # only ever exercised the BOX-LESS path, where the links are caught by
        # boundary_ink instead, so it could not see this. Word boxes cover the
        # body text and not the underlines, so furniture_ink finds all four.
        link_png, link_boxes = _page(rule_luma=None, gap=90, underline=4,
                                     want_boxes=True)
        assert len(furniture_ink(link_png, link_boxes)) >= DEVICE_QUORUM, \
            "the underlines must reach furniture_ink at all, else the next " \
            "assert passes for the wrong reason"
        assert any(f and "no ink" in m for f, m in
                   check_whitespace(link_png, boxes=link_boxes)), \
            "link underlines in the MIDDLE of a section must not count " \
            "towards the quorum just because word boxes are available — the " \
            "gate claims the bands are AT a section boundary"
        os.unlink(link_png)

        # --- one device, seen by BOTH detectors, must count ONCE. This is
        # the frame bug: `furniture_ink` scans the whole PNG while
        # `measure_fill.bands` reports rows of a crop that cuts 2% off the
        # top, so the `_overlap` dedupe was comparing two coordinate systems
        # and never fired. A single rule at a boundary therefore scored 2 and
        # cleared DEVICE_QUORUM on its own — which is how the cover letter
        # (one letterhead rule, by design) and engraved-card passed. ---
        one_png, one_boxes = _page(rule_luma=30, rules=1, gap=90,
                                   want_boxes=True)
        assert len(furniture_ink(one_png, one_boxes)) >= 1, \
            "the lone rule must reach furniture_ink at all, else the next " \
            "assert passes for the wrong reason"
        assert any(f and "no ink" in m for f, m in
                   check_whitespace(one_png, boxes=one_boxes)), \
            "a page carrying ONE device must FAIL the quorum: both scans " \
            "see that same rule, and counting it twice is the mixed-frame " \
            "bug — a boundary SYSTEM is two devices, not one counted twice"
        os.unlink(one_png)

        with tempfile.NamedTemporaryFile("w", suffix=".typ", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("// vitae letter template — one letter per posting\n")
            lettre = fh.name
        assert is_letter(lettre), \
            "a cover letter must be recognised by its line-1 marker, or a " \
            "sweep asks a one-rule letter for a section boundary SYSTEM"
        assert not is_letter(__file__), \
            "is_letter must not fire on an ordinary file"
        os.unlink(lettre)

        # --- the gate must actually FAIL now (2026-09-13 fix): a page with
        # no device anywhere used to pass whenever its whitespace ratio sat
        # under SEPARATION_CEILING (6.0) — which the WHOLE corpus does (max
        # measured: 5.14). Quorum failure is now unconditional unless the
        # family is in DEVICELESS. ---
        bare_tight = _page(rule_luma=None, gap=10)  # ratio well under 6.0
        assert any(f for f, _ in check_whitespace(bare_tight)), \
            "zero boundary devices must FAIL the quorum even when the " \
            "whitespace ratio is nowhere near SEPARATION_CEILING — this is " \
            "exactly the case that never failed before"
        assert not any(f for f, _ in
                       check_whitespace(bare_tight, family="humanist-quiet")), \
            "a DEVICELESS-exempt family must not FAIL on zero devices"
        # A missing pdftotext must not masquerade as a design defect: without
        # word boxes the union is the old row scan alone, which scores 0 on
        # real pages whose device sits on the heading's line.
        assert not any(f for f, _ in
                       check_whitespace(bare_tight, degraded=True)), \
            "with no word boxes the quorum must be REPORTED, not failed"
        assert any("NOT MEASURED" in m for _, m in
                   check_whitespace(bare_tight, degraded=True)), \
            "degraded mode must say so, not silently pass"
        os.unlink(bare_tight)

        with tempfile.NamedTemporaryFile("w", suffix=".typ", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("// vitae-academic: sections=13 entries=212\n#set page()\n")
            acad = fh.name
        assert is_academic(acad), \
            "an academic CV must be recognised by its line-1 marker, or a " \
            "sweep judges a 13-page CV against a 1-page resume gate"
        assert not is_academic(__file__), \
            "is_academic must not fire on an ordinary file"
        os.unlink(acad)

        assert family_from_path("templates/families/quiet-luxury/resume.typ") \
            == "quiet-luxury"
        assert family_from_path("/home/x/my-own-cv.typ") is None, \
            "a path outside templates/families/ must never carry an exemption"

        # --- the 2026-09-13 recalibration, pinned from both sides ---
        # tight: boundaries carry a hairline but the gap is only 1.77x the
        # median — BELOW the old 2.0 floor, which failed it. The corpus says
        # that ratio does not rank separation (a page with NO section gap at
        # all scores 2.69), so an inked page must pass at any ratio. This is
        # the `engraved-card/resume-pair-b` case, which measured 1.89.
        tight = _page(rule_luma=30, gap=25)
        assert not any(f for f, _ in check_whitespace(tight)), \
            "the white ratio must no longer FAIL a page whose boundaries " \
            "carry ink, however tight the gap"
        # airy: no device anywhere and a ratio of ~5.1 — the top of the real
        # roster (margin-index 5.14). SEPARATION_CEILING still must not fail
        # it on the ratio alone; but the ratio was never what covered a truly
        # device-less family — DEVICELESS does. margin-index itself is not
        # exempt (it measures a union of 14: its "device-less" reputation was
        # an artifact of the old ink-blind scan), so this is a synthetic
        # stand-in and must only pass WITH an exemption.
        airy = _page(rule_luma=None, gap=53)
        assert not any(f for f, _ in
                       check_whitespace(airy, family="humanist-quiet")), \
            "SEPARATION_CEILING must sit above the roster's highest page " \
            f"(5.14x); at {SEPARATION_CEILING} an exempt device-less family " \
            "that compensates with white — which design.md requires of it " \
            "— must not fail on the ratio"
        assert any(f for f, _ in check_whitespace(airy)), \
            "the same page with no family exemption must FAIL the quorum"
        # --- rule 5, "no section may split across a page break": the
        # headline rule of the whole skill, and until 2026-09-13 NOTHING on
        # the industry side measured it (the academic gate measured its own
        # entry-level analogue; lib.typ only sets `breakable: false`, which
        # says what the template INTENDS, not what the PDF did).
        ns_src = ('#section("Profile")[a]\n#section("Selected Projects")[b]\n'
                  '#section("Certifications & Professional Development")[c]\n')
        one = ["NAME\nProfile\ntext"]
        assert not any(f for f, _ in check_no_split(ns_src, one)), \
            "a single-page deliverable has no break and must never fail"
        good = ["NAME\nPROFILE\ntext", "SELECTED PROJECTS\nProject Name\n2024"]
        assert not any(f for f, _ in check_no_split(ns_src, good)), \
            "a page opening on a declared heading is a clean break"
        split = ["NAME\nPROFILE\ntext", "kept the API under 200 ms\n2024"]
        assert any(f for f, _ in check_no_split(ns_src, split)), \
            "page 2 opening mid-section is the SPLIT this check exists for"
        # the running head must not be mistaken for the split it hides:
        # lib.typ's runhead extracts as name and `n / total`, over one line or
        # two, in either order.
        # Only the order the device actually produces: pdftotext reads left
        # to right, so `name #h(1fr) n / total` extracts as the name first —
        # measured on swiss-grid/resume-2page, the corpus's only 2-pager.
        # Pagination-first is not handled and is not a case that occurs.
        for band in ("Firstname Lastname\n2 / 2",
                     "Firstname Lastname — Backend Developer 2 / 2"):
            rh = ["NAME\nPROFILE\ntext", band + "\nSELECTED PROJECTS\nProject"]
            assert not any(f for f, _ in check_no_split(ns_src, rh)), \
                f"the running head band ({band!r}) must be skipped, not judged"
            bad_rh = ["NAME\nPROFILE\ntext", band + "\nkept the API under 200 ms"]
            assert any(f for f, _ in check_no_split(ns_src, bad_rh)), \
                "skipping the running head must not swallow the line AFTER it"
        # a heading long enough to wrap still opens its page
        wrapped = ["NAME\nPROFILE\ntext", "CERTIFICATIONS &\nPROFESSIONAL DEVELOPMENT"]
        assert not any(f for f, _ in check_no_split(ns_src, wrapped)), \
            "a wrapped heading must match on its first line, not fail"
        # the pdftotext terminator: a trailing empty chunk is not a page
        assert not any(f for f, _ in check_no_split(ns_src, one + [""])), \
            "pdftotext's trailing \\f must not read as an empty second page"
        assert any(f for f, _ in check_no_split(ns_src, split + [""])), \
            "dropping the terminator must not drop a real trailing page"
        # and a source with no #section() call is reported, never guessed at
        assert not any(f for f, _ in check_no_split("#let x = 1\n", split)), \
            "no declared heading list means NOT CHECKED, not a free pass fail"

        # ATS date / degree-token checks: each must fire on its defect and stay
        # quiet on the legitimate shape, else the WARN is noise or a no-op.
        for bad_d in ("Engineer  2019 – 2021", "Player 2017 – present",
                      "2019–aujourd'hui", "Dev 2018 - 2020", "2015 — now"):
            assert check_year_only_dates(bad_d), bad_d
        for ok_d in ("Aug 2019 – Dec 2021", "janv. 2019 – présent",
                     "Sept. 2019 – Dec 2021", "Summer 2019 – Fall 2021",
                     "B.Eng., Software Engineering — 2020",
                     "June 2026 – present", "Fall 2013"):
            assert not check_year_only_dates(ok_d), ok_d
        for bad_d in ("Marketing 2019 – 2021", "Mayor 2019 – 2021",
                      "Aug 2019 – 2021", "2019 – Aug 2021", "août 2018 – 2020"):
            assert check_year_only_dates(bad_d), bad_d
        for t in ("Bac en cours", "Bac. en cours"):
            assert check_degree_tokens(t), t
        for t in ("Mastercard program", "Bac+3",
                  "Program Manager | Master Builder, Bachelor of Arts",
                  "Program director — Bachelor of Arts"):
            assert not check_degree_tokens(t), t
        assert check_degree_tokens(
            "Undergraduate B.Eng. program, software engineering")
        assert check_degree_tokens("Baccalauréat en cours, génie logiciel")
        assert not check_degree_tokens(
            "Undergraduate coursework, software engineering")
        assert not check_degree_tokens("B.Eng., Software Engineering — 2020")
        assert not check_degree_tokens(
            "After coursework at Polytechnique Exemple, I am completing a bachelor's degree")

        for t in ("\u25c6 Built the API", "  \u2022", "\u25aa item", "\uf0b7 item"):
            assert check_bullet_chars(t), t
        for t in ("Built the API", "City \u2022 phone", "\u2013 prose dash",
                  "Bilingual English / French"):
            assert not check_bullet_chars(t), t

        for f in (inked, bare, thin, linked, lone, tight, airy):
            os.unlink(f)
        # check_text_clip: a word straddling a filled band's bottom edge FAILs;
        # the same word wholly inside the band, or wholly on paper, does not.
        # A line hidden past a short band (white on white) FAILs; a word flanked
        # by hairline rules (grid(1fr, auto, 1fr) + line, 1-2pt gutter) does not.
        with tempfile.TemporaryDirectory() as td:
            def _png(draw, name="t.png"):
                im = Image.new("RGB", (400, 200), (255, 255, 255))
                draw(im)
                p = os.path.join(td, name); im.save(p)
                return p

            def _word(y_word, x0=40, x1=200):
                return [((x0 / FURNITURE_SCALE, y_word / FURNITURE_SCALE,
                          x1 / FURNITURE_SCALE, (y_word + 14) / FURNITURE_SCALE), "linkedin.com")]

            def _ink(im, y, col=(255, 255, 255), x0=60, x1=180):   # fake glyphs
                for x in range(x0, x1, 6):
                    im.paste(col, (x, y + 3, x + 3, y + 11))

            def _band(im):
                im.paste((60, 60, 60), (0, 0, 400, 100))   # band, bottom edge y=100

            def _at(y):                                    # band + visible glyphs at y
                def d(im):
                    _band(im); _ink(im, y, (255, 255, 255) if y + 14 <= 100 else (200, 30, 30))
                return _png(d)
            assert check_text_clip(_at(92), _word(92)), "word cut by the band edge must FAIL"
            assert not check_text_clip(_at(70), _word(70)), "word inside the band must pass"
            assert not check_text_clip(_at(120), _word(120)), "word on paper must pass"
            # (a) line wholly past the band: white glyphs on white paper
            def _hidden(im):
                _band(im); _ink(im, 120)
            assert any("indistinguishable" in m for m in check_text_clip(_png(_hidden), _word(120))), \
                "text whose colour matches the paper must FAIL"
            # (b) word flanked by rules at mid-height, 1-2pt gutter
            for thick in (1, 2):
                def _rules(im, thick=thick):
                    for x in range(60, 180, 6):
                        im.paste((0, 0, 0), (x, 105, x + 3, 113))      # dark glyphs
                    im.paste((0, 0, 0), (0, 108, 37, 108 + thick))     # rule left
                    im.paste((0, 0, 0), (203, 108, 400, 108 + thick))  # rule right
                assert not check_text_clip(_png(_rules), _word(100, 40, 200)), \
                    f"a word flanked by {thick}px rules is not cut by a fill"

        # group proximity: the gap to the next block must be >= the largest gap inside
        # the group (role->org included). Synthetic: internal gaps 3pt; next head at
        # 149 (1pt, tight -> FAIL) or 160 (12pt -> OK).
        def _words(next_top):
            def ln(top, h, txt):
                return [(50.0, top, 90.0, top + h, w) for w in txt.split()]
            return [ln(100, 10, "Role One") + ln(113, 9, "Acme Corp") + ln(125, 10, "first bullet")
                    + ln(138, 10, "second bullet") + ln(next_top, 10, "Role Two") + ln(next_top + 13, 9, "Beta Inc")
                    + ln(next_top + 25, 10, "only bullet") + ln(next_top + 38, 10, "last bullet")]
        _flat = lambda ws: [w for part in ws for w in part]
        _hd = [{"kind": "entry", "text": "Role One", "org": "Acme Corp", "page": 1, "x": 50.0, "y": 105.0},
               {"kind": "entry", "text": "Role Two", "org": "Beta Inc", "page": 1, "x": 50.0, "y": 0.0}]
        for top, want_fail in ((149, True), (160, False)):
            hh = [dict(_hd[0]), dict(_hd[1], y=top + 5.0)]
            got = check_group_proximity("", "", heads=hh, secs=[], pages=[_flat(_words(top))])
            assert (got[0][0] == "FAIL") == want_fail, (top, got)
        # raster path: the measured gap is OPTICAL (baseline -> x-height top), so the
        # same layout with different words (no ascenders / descenders at all vs
        # full of them) must give the same ratio; a squeezed layout must still FAIL.
        if shutil.which("typst") and shutil.which("pdftoppm") and shutil.which("pdftotext"):
            def _rast(last, squeeze=0):
                with tempfile.TemporaryDirectory() as d:
                    src = ('#set page(width: 240pt, height: 170pt, margin: 20pt)\n'
                           '#set text(font: "Liberation Sans", size: 10pt)\n'
                           '#set par(leading: 0.65em, spacing: 0.65em)\n'
                           '*Role One*\n\nOrg Name\n\nFirst bullet line here\n\n' + last + '\n\n'
                           f'#v({6 - squeeze}pt)\n*Role Two*\n\nOrg Two\n\nOnly bullet\n\nLast bullet\n')
                    t, f = os.path.join(d, "x.typ"), os.path.join(d, "x.pdf")
                    open(t, "w", encoding="utf-8").write(src)
                    subprocess.run(["typst", "compile", t, f], check=True, capture_output=True)
                    wb = word_boxes(f, with_text=True)
                    pg = [(b[0], b[1], b[2], b[3], w) for b, w in wb[0]]
                    hd = [{"kind": "entry", "text": txt, "org": "", "page": 1, "x": w[0], "y": w[1]}
                          for txt, w in (("Role One", next(w for w in pg if w[4] == "One")),
                                         ("Role Two", next(w for w in pg if w[4] == "Two")))]
                    det = []
                    got = check_group_proximity(t, f, heads=hd, secs=[], pages=[pg], detail=det)
                    return [r for r in det if r["kind"] == "group"][0]["ratio"], got[-1][0]
            _ra, _la = _rast("a sure sun runs very scarce, even once")        # x-height letters only
            _rb, _lb = _rast("Kill Hill, ghj. Thick fly (gypsy) Jeff's pig")   # ascenders and descenders
            assert abs(_ra - _rb) <= 0.1 and 0.85 <= _ra < 3, (_ra, _rb)
            assert _la == _lb == "OK", (_la, _lb)
            _rt, _lt = _rast("a sure sun runs very scarce, even once", squeeze=11)
            assert _lt == "FAIL" and _rt < PROX_FAIL, (_rt, _lt)
            print(f"selftest raster path: ratio {_ra:.2f} (x-height words) vs {_rb:.2f} (ascender words); squeezed {_rt:.2f} FAILs")
        else:
            print("selftest raster path SKIPPED (typst / pdftoppm / pdftotext not on PATH)")
        _nh = check_group_proximity("", "", heads=[], secs=[], pages=[[]])[0]
        assert _nh[0] == "WARN" and "not measured" in _nh[1], \
            "a CV without head markers is WARN (not measured), not FAIL"
        # rail-title pairing: skill row (single line) at the end of a section whose
        # next section title sits in a left rail ~7pt above the next body line.
        # Next block must be that in-column head, so the row has no sub-line (skipped),
        # instead of the rail title matching one line too low and faking a 26pt "sub-line".
        def _rail():
            def ln(x, top, h, txt):
                return [(x, top, x + 30.0, top + h, w) for w in txt.split()]
            pg = (ln(100, 100, 10, "Methodologies Agile") + ln(100, 130, 10, "Label evidence drawn")
                  + ln(100, 143, 10, "Mentoring example") + ln(20, 140, 10, "Strengths"))
            hh = [{"kind": "skill", "text": "Methodologies", "org": "", "page": 1, "x": 100.0, "y": 105.0},
                  {"kind": "skill", "text": "Label", "org": "", "page": 1, "x": 100.0, "y": 135.0},
                  {"kind": "skill", "text": "Mentoring", "org": "", "page": 1, "x": 100.0, "y": 148.0}]
            return hh, [{"text": "Strengths", "page": 1, "y": 129.0}], [pg]
        _hh, _ss, _pp = _rail()
        _rows, _sk = measure_groups(_hh, _ss, _pp)
        assert not _rows, _rows

        # date adjacency: measured from lib markers + pdftotext word ORDER, so every
        # case is a real layout. `ok(...)` is lib `entry` (role -> date -> org)
        # with a descriptor line reaching under the date, as every template has
        # (an org line that stops short of a far-right date IS read before it:
        # that is the trap);
        # `bad(...)` keeps the markers but sets the org line 2pt under the role row,
        # so the boxes overlap and pdftotext reads role, org, date (the trap);
        # `inl(...)` puts the org on the head line and the date under it.
        # Each case is one page of one document: one compile, one query.
        if shutil.which("typst") and shutil.which("pdftotext"):
            _lib = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
            _pre = ('#import "lib.typ": *\n#set page(width: 14cm, height: 12cm, margin: 2cm)\n'
                    '#set text(size: 10pt)\n'
                    '#let ok(r, o, d, ..b) = { entry(r, o, d, [Montreal · what the employer is, in one clause · full-time, hybrid])\n'
                    '  b.pos().map(x => list(x)).join() }\n'
                    '#let bad(r, o, d, ..b) = block[#grid(columns: (1fr, auto), align: (left + bottom, right + bottom),\n'
                    '  [#head-mark("entry", r, org: o, dated: true)#text(size: 11pt, weight: "bold", r)],\n'
                    '  [#part-mark("date", text(size: 9pt, d))#text(size: 9pt, d)])\n'
                    '  #v(-8pt)\n  #text(size: 9pt)[#part-mark("org", o)#o]\n'
                    '  #b.pos().map(x => list(x)).join()]\n'
                    '#let inl(r, o, d) = block[#head-mark("entry", r, org: o, dated: true)#r #part-mark("org", o)#o \\\n'
                    '  #part-mark("date", d)#d]\n'
                    '#let bare(r, d) = entry(r, [], d, none)\n'
                    '#let old(r, o) = block[#context [#metadata((kind: "entry", text: r, org: o, page: here().page(),\n'
                    '  x: 0, y: 0)) <vitae-head>]#r \\ #o \\ 2020 – 2023]\n')
            # (name, typst body, expected: "fail" | "pass" | "warn")
            _cases = [
                ("lib order", 'ok("Backend Developer", "Acme Corp", "Mar 2024 – present")', "pass"),
                ("trap order", 'bad("Backend Developer", "Acme Corp", "Mar 2024 – present")', "fail"),
                ("org with year", 'bad("Engineer", "Vision 2020 Inc", "2021 – 2023")', "fail"),
                ("org with year, lib", 'ok("Engineer", "Vision 2020 Inc", "2021 – 2023")', "pass"),
                ("org address", 'bad("Engineer", "Acme, 1234 Main St", "2021 – 2023")', "fail"),
                ("org Current", 'bad("Engineer", "Current", "2021 – 2023")', "fail"),
                ("org Now", 'bad("Engineer", "Now", "2021 – 2023")', "fail"),
                ("org Now, lib", 'ok("Engineer", "Now", "2021 – 2023")', "pass"),
                ("org Currentware", 'bad("Eng", "Currentware", "2020 – 2021")', "fail"),
                ("org 3M", 'bad("Engineer", "3M Corp", "2020 – 2023")', "fail"),
                ("org 3M, lib", 'ok("Engineer", "3M Corp", "2020 – 2023")', "pass"),
                ("org 10-15 staff", 'bad("Eng", "Acme, 10-15 staff", "03/20 – 04/22")', "fail"),
                ("role Tier 2", 'bad("Tier 2 Support", "Acme Corp", "2020 – 2023")', "fail"),
                ("role Tier 2, lib", 'ok("Tier 2 Support", "Acme Corp", "2020 – 2023")', "pass"),
                ("role dash+year", 'bad("Eng – Tier 2024", "Acme", "2021 – 2022")', "fail"),
                ("role with comma", 'bad("Engineer, Montreal", "Acme Corp", "2020 – 2023")', "fail"),
                ("role with comma, lib", 'ok("Engineer, Montreal", "Acme Corp", "2020 – 2023")', "pass"),
                ("4-word org on head line", 'inl("Engineer", "Acme Global Systems Ltd", "2020 – 2023")', "fail"),
                ("same-line org with year", 'inl("Engineer", "Vision 2020 Inc", "2021 – 2023")', "fail"),
                ("Jan to Present, trap", 'bad("Eng", "Acme", "Jan to Present")', "fail"),
                ("Janvier présent, trap", 'bad("Eng", "Acme", "Janvier – présent")', "fail"),
                ("Present alone", 'ok("Eng", "Acme", "Present")', "pass"),
                ("empty role", 'ok("", "Acme", "2020 – 2023")', "warn"),
                ("undated cert then dated w/ bullet year",
                 'ok("AWS Cert", "", ""); ok("Dev", "Acme", "2020 – 2023", [Won award 2022])', "pass"),
                ("org-less 2012, bullet short of the date, last on page",
                 'bare("Engineer", "2012"); list([a long bullet that runs across])', "fail"),
                ("org-less 2012, bullet wrapping under the date",
                 'bare("Engineer", "2012"); list([a long bullet that runs across the whole line width of the page for sure, yes yes yes])', "pass"),
                ("org-less 2012 before next section title",
                 'bare("Engineer", "2012"); list([b]); v(1em); text(weight: "bold")[EDUCATION]; bare("BSc", "2010"); list([x])', "fail"),
                ("next entry with empty role", 'ok("Engineer", "Acme", "2020 – 2023"); ok("", "Beta", "2019 – 2020")', "warn"),
                ("bullet number then date", 'bad("Engineer", "Acme Corp", "2020 – 2023", [Led 3 years of work])', "fail"),
                ("en cours, trap", 'bad("Eng", "Acme", "03/24 – en cours")', "fail"),
                ("Jan - Mar no year, trap", 'bad("Eng", "Acme", "Jan – Mar")', "fail"),
                ("Present alone, trap", 'bad("Eng", "Acme", "Present")', "fail"),
                ("Sep 2011, trap", 'bad("Eng", "Acme", "Sep 2011 – Jun 2012")', "fail"),
                ("en cours", 'ok("Eng", "Acme", "03/24 – en cours")', "pass"),
                ("Janvier présent", 'ok("Eng", "Acme", "Janvier – présent")', "pass"),
                ("arabic digits", 'ok("Eng", "Acme", "٢٠٢٤")', "pass"),
                ("reiwa", 'ok("Eng", "Acme", "令和6年")', "pass"),
                ("thai digits", 'ok("Eng", "Acme", "๒๕๖๗")', "pass"),
                ("date on two lines", 'ok("Eng", "Acme", [Jan 2020 – \\ Dec 2021])', "pass"),
                ("empty date", 'ok("Backend Developer", "Acme Corp", "")', "pass"),
                ("undated, bullet year", 'ok("Engineer", "Acme", "", [Shipped in 2019 the thing])', "pass"),
                ("undated, bullet 5000", 'ok("Engineer", "Acme", "", [Served 5000 users])', "pass"),
                ("undated, wrapped now", 'ok("Engineer", "Acme", "", [Did the thing right ' + "x " * 60 + 'now])', "pass"),
                ("undated, no org", 'ok("Engineer", "", "", [Cut cost 30%])', "pass"),
                ("undated then dated w/ bullet years",
                 'ok("Volunteer", "Club", ""); ok("Engineer", "Acme", "2020 – 2023", [Shipped in 2019 the thing], [Won award 2022])', "pass"),
                ("undated then dated, trailing section",
                 'ok("Volunteer", "Club", ""); ok("Engineer", "Acme", "2020 – 2023", [bullet]); [EDUCATION \\ BSc \\ 2012 \\ Cert 2020]', "pass"),
                ("B.Sc. 2012 orphan", 'bare("B.Sc. Physics", "2012"); ok("Backend Developer", "Acme Corp", "Mar 2024 – present")', "fail"),
                ("B.Sc. month range", 'ok("B.Sc. Physics", "Université Laval", "Sep 2008 – Jun 2012"); ok("Backend Developer", "Acme Corp", "Mar 2024 – present")', "pass"),
                ("same role twice, one trap", 'ok("Engineer", "Acme", "2020 – 2023"); bare("Engineer", "2019"); ok("Engineer", "Beta", "2015 – 2019")', "fail"),
                ("old lib heads", 'old("Engineer", "Acme")', "warn"),
            ]
            with tempfile.TemporaryDirectory(prefix="vitae-date-") as _td:
                for _f in ("lib.typ", "icons.typ"):
                    shutil.copy(os.path.join(_lib, _f), _td)
                _src = os.path.join(_td, "t.typ")
                with open(_src, "w", encoding="utf-8") as _fh:
                    _fh.write(_pre + "\n#pagebreak()\n".join(f"#{{ {b} }}" for _, b, _ in _cases))
                _pdf = os.path.join(_td, "t.pdf")
                _r = subprocess.run(["typst", "compile", _src, _pdf], capture_output=True, text=True)
                assert _r.returncode == 0, _r.stderr
                _marks = _typst_query(_src, ENTRY_MARKS)
                _words = word_boxes(_pdf, with_text=True)
                assert _marks is not None and _words is not None and len(_words) == len(_cases)
            for _p, (_n, _b, _exp) in enumerate(_cases, 1):
                _w = []
                _f = check_date_adjacency("", "", marks=[m for m in _marks if m.get("page") == _p],
                                          warns=_w, words=_words)
                _got = "fail" if _f else "warn" if _w else "pass"
                assert _got == _exp, (_n, _got, _f or _w)
                if _n == "B.Sc. 2012 orphan":
                    assert len(_f) == 1 and "B.Sc. Physics" in _f[0] and "next entry starts" in _f[0], _f
                if _n == "trap order":
                    assert "month range" in _f[0] and "Backend Developer" in _f[0], _f
                if _n == "same role twice, one trap":
                    assert len(_f) == 1, _f
                if _n.startswith("org-less 2012") and _exp == "fail":
                    assert any("below the entry head" in m for m in _f), _f
                if _n == "next entry with empty role":
                    assert len(_w) == 1 and "head words not found" in _w[0], _w
                if _n == "old lib heads":
                    assert any("no lib markers" in m for m in _w), _w
            print(f"selftest date adjacency: {len(_cases)} typst layouts measured")
        else:
            print("selftest date adjacency SKIPPED (typst / pdftotext not on PATH)")
        # _first_word honours the column bound: a word right of x_end (the next
        # entry's date cell, a sidebar) is never taken for a head / org line
        _fw = [((300.0, 10.0, 330.0, 20.0), "2019"), ((50.0, 12.0, 90.0, 22.0), "Beta")]
        assert _first_word(_fw, 50.0, 10.0, 40.0) == 1
        assert _first_word(_fw[:1], 50.0, 10.0, 40.0) == 0
        assert _first_word(_fw[:1], 50.0, 10.0, 40.0, x_end=299.0) is None
        # date adjacency without word boxes / markers never crashes
        assert not check_date_adjacency("", "", marks=[])
        _w = []
        assert not check_date_adjacency("", "", marks=[{"kind": "entry", "text": "A", "page": 1, "x": 0, "y": 0, "dated": True}],
                                        warns=_w, words=[[]]) and _w
        # comment stripping: nested blocks, stray quote, raw span
        assert "lib.typ" not in _strip_typst_comments('/* a /* b */ #import "lib.typ" */\n')
        assert "lib.typ" in _strip_typst_comments('a 6" pipe\n#import "lib.typ"\n')
        assert "lib.typ" not in _strip_typst_comments('`#import "lib.typ"`\n')
        assert "lib.typ" in _strip_typst_comments('#let u = "a//b"\n#import "lib.typ"\n')

        # forced line break inside a bullet: a hard break mid-bullet FAILs,
        # the same text wrapped by itself, or a break outside any bullet, does not.
        assert check_forced_linebreak("- Led the migration \\ to the new stack\n")
        assert check_forced_linebreak("- Led the migration #linebreak() to the new stack\n")
        assert check_forced_linebreak("- Led the migration,\n  continued \\\n  here\n")
        assert not check_forced_linebreak("- Led the migration to the new stack\n  and shipped it\n")
        assert not check_forced_linebreak("Name \\ Title\n\n- Bullet one\n")
        assert not check_forced_linebreak("- see https://example.com/a // and path C:\\\\dir\n")

        # duplicate name: a section title reused as a row label (any case) FAILs
        _sec = [{"text": "LANGUAGES", "page": 1, "y": 10.0}, {"text": "Skills", "page": 1, "y": 80.0}]
        assert check_duplicate_names(_sec, [{"kind": "skill", "text": "Languages"}])
        assert check_duplicate_names(_sec, [{"kind": "skill", "text": "languages:"}])
        assert not check_duplicate_names(_sec, [{"kind": "skill", "text": "Programming languages"}])
        assert not check_duplicate_names(_sec, [{"kind": "entry", "text": "Languages"}])

        # lib.typ integrity: current / older release / rewritten / no import
        with tempfile.TemporaryDirectory() as _d:
            _sk = os.path.join(_d, "skill"); _cv = os.path.join(_d, "cv")
            os.makedirs(os.path.join(_sk, "templates")); os.makedirs(_cv)
            _w = lambda p, t: open(p, "w", encoding="utf-8").write(t)
            _w(os.path.join(_sk, "templates", "lib.typ"), "#let derive() = 1\n")
            _w(os.path.join(_cv, "cv.typ"), '#import "lib.typ": *\n')
            _old = hashlib.sha256(b"#let old = 1\n").hexdigest()
            _chk = lambda: check_lib_integrity(os.path.join(_cv, "cv.typ"), _sk, {_old})
            _w(os.path.join(_cv, "lib.typ"), "#let derive() = 1\n")
            assert _chk() == [], _chk()
            _w(os.path.join(_cv, "lib.typ"), "#let old = 1\n")
            assert [l for l, _ in _chk()] == ["WARN"], _chk()
            _w(os.path.join(_cv, "lib.typ"), "#let mine = 1\n")
            _r = _chk()
            assert [l for l, _ in _r] == ["FAIL"] and "cp " in _r[0][1], _r
            _w(os.path.join(_cv, "cv.typ"), "hello\n")
            assert [l for l, _ in _chk()] == ["WARN"], _chk()      # lib next to CV, no import: never silent
            os.remove(os.path.join(_cv, "lib.typ"))
            assert _chk() == []
            _w(os.path.join(_cv, "lib.typ"), "#let mine = 1\n")
            # CRLF copy of the current lib is still current; commented / root-absolute imports
            open(os.path.join(_cv, "lib.typ"), "wb").write(b"#let derive() = 1\r\n")
            _w(os.path.join(_cv, "cv.typ"), '#import "lib.typ": *\n')
            assert _chk() == [], _chk()
            _w(os.path.join(_cv, "cv.typ"), '// #import "lib.typ": *\n/* #import "lib.typ" */\n')
            assert [l for l, _ in _chk()] == ["WARN"], _chk()     # commented imports do not count
            for _src, _exp in (('#{ import "lib.typ": * }\n', "FAIL"), ('#import("lib.typ")\n', "FAIL"),
                               ('/* a /* b */ #import "lib.typ" */\n#set page()\n', "WARN"),
                               ('a 6" pipe\n#import "lib.typ": *\n', "FAIL"),
                               ('`#import "lib.typ"`\n', "WARN")):
                _w(os.path.join(_cv, "lib.typ"), "#let mine = 1\n")
                _w(os.path.join(_cv, "cv.typ"), _src)
                assert [l for l, _ in _chk()] == [_exp], (_src, _chk())
            open(os.path.join(_cv, "lib.typ"), "wb").write(b"\xef\xbb\xbf#let derive() = 1\n")
            _w(os.path.join(_cv, "cv.typ"), '#import "lib.typ": *\n')
            assert _chk() == [], "BOM lib must not false-FAIL"
            open(os.path.join(_cv, "cv.typ"), "wb").write(b'// caf\xe9\n#import "lib.typ": *\n')
            assert _chk() == [], "non-UTF-8 cv must not crash"
            os.makedirs(os.path.join(_cv, "sub"))
            _w(os.path.join(_cv, "sub", "cv.typ"), '#import "/lib.typ": *\n')
            _w(os.path.join(_cv, "lib.typ"), "#let mine = 1\n")
            _r = check_lib_integrity(os.path.join(_cv, "sub", "cv.typ"), _sk, {_old})
            assert [l for l, _ in _r] == ["FAIL"], _r
            assert "cp " in _r[0][1]
        print("selftest OK — lib.typ integrity (current / older / rewritten); tuner regex reads, writes and round-trips; "
              "an unrecognised par declaration is reported, not guessed; "
              "a pale or short hairline AT a boundary reads as a device, while "
              "an underlined link away from one does not — empty-space-only "
              "separation FAILs either way; furniture_ink sees a device beside "
              "text that the old row-wide scan is blind to, and only where a "
              "boundary is (link underlines mid-section do not count, word "
              "boxes or not); the quorum FAILs "
              "unconditionally on zero devices unless the family is DEVICELESS; "
              "and the white ratio fails nothing on its own, at either end "
              "(tight-but-inked passes, and the ceiling clears the roster's "
              "highest page)")
        sys.exit(0)

    if argv and argv[0] == "--tune":
        # verify.py --tune cv.typ PAGES FILL_MIN FILL_MAX [LO HI]
        if len(argv) < 5:
            print("usage: verify.py --tune cv.typ PAGES FILL_MIN FILL_MAX "
                  "[LEADING_LO LEADING_HI]", file=sys.stderr)
            sys.exit(2)
        bounds = (float(argv[5]), float(argv[6])) if len(argv) >= 7 else (None, None)
        sys.exit(tune(argv[1], int(argv[2]), int(argv[3]), int(argv[4]),
                      lo=bounds[0], hi=bounds[1]))

    if len(argv) < 2:
        print(f"usage: {os.path.basename(sys.argv[0])} cv.typ EXPECTED_PAGES [FILL_MIN FILL_MAX]\n"
              f"       {os.path.basename(sys.argv[0])} --tune cv.typ PAGES FILL_MIN FILL_MAX [LO HI]\n"
              f"       {os.path.basename(sys.argv[0])} --all DIR\n"
              f"       {os.path.basename(sys.argv[0])} --doctor\n"
              f"       {os.path.basename(sys.argv[0])} --selftest", file=sys.stderr)
        sys.exit(2)

    typ, expected = argv[0], argv[1]
    fmin = argv[2] if len(argv) >= 3 else None
    fmax = argv[3] if len(argv) >= 4 else None
    pdf = re.sub(r"\.typ$", "", typ) + ".pdf"
    fail = 0

    deps_ok, use_cli, use_poppler = preflight()
    if not deps_ok:
        sys.exit(1)
    _footer = _FOOTER_GATE

    for level, msg in check_lib_integrity(typ):
        print(f"{level}  {msg}")
        fail |= level == "FAIL"

    ensure_icons(typ)
    ok, err = compile_pdf(typ, pdf, use_cli)
    if not ok:
        print("FAIL  compile")
        print(err)
        sys.exit(1)
    if err.strip():
        print("WARN  compile stderr (a missing font only warns and falls back):")
        print(err)

    pages = count_pages(pdf, use_poppler)
    if pages == expected:
        print(f"OK    pages: {pages}")
    else:
        print(f"FAIL  pages: {pages} (expected {expected}) — cut or add real content in cv.typ "
              f"(or, if {expected} was the wrong target, re-run with the right page count)")
        fail = 1

    family = family_from_path(typ)
    pages_text = word_boxes(pdf, with_text=True)  # None => pdftotext missing, degrades below
    pages_boxes = [[b for b, _ in pg] for pg in pages_text] if pages_text is not None else None

    with tempfile.TemporaryDirectory() as tmp:
        pngs = render_pngs(typ, tmp, use_cli)
        if not pngs:
            # No PNG => measure_fill never ran => the fill target is UNTESTED.
            # Silently passing here is how a broken render reads as a PASS.
            print("FAIL  no PNG rendered — fill unmeasured")
            fail = 1
        if not (fmin and fmax):
            print("WARN  fill NOT checked (no FILL_MIN FILL_MAX given) — rerun "
                  f"as scripts/verify.py {typ} {expected} FILL_MIN FILL_MAX; "
                  "the targets come from the pick_design.py report "
                  '("fill target : NN-NN%") and differ per family')
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
                          f"run `scripts/verify.py --tune {typ} {expected} {fmin} {fmax}` "
                          "(adjusts leading), or add/cut real content")
                    fail = 1
                else:
                    print(f"OK    fill: {path}: {result}")
            else:
                print(f"INFO  fill: {path}: {result} (target = (100 - bottom-margin%) - 0..2%)")
            boxes = pages_boxes[i] if pages_boxes and i < len(pages_boxes) else None
            if pages_text is None and i == 0:
                print("WARN  text-clip gate skipped: pdftotext not found (install poppler-utils)")
            for msg in check_text_clip(path, pages_text[i] if pages_text and i < len(pages_text) else None):
                print("FAIL  " + msg)
                fail = 1
            for is_fail, msg in check_whitespace(path, boxes=boxes, family=family,
                                                 degraded=boxes is None):
                print(f"{'FAIL' if is_fail else 'OK  '}  {msg}")
                fail = fail or int(is_fail)

    typ_text = open(typ, encoding="utf-8").read()
    if "7d2231" in typ_text.lower():
        print("WARN  template default accent (#7d2231) — run scripts/pick_design.py and apply the family it draws (references/design.md § Design families)")
    if "[#cat:]" in typ_text:
        print("WARN  template skills block (\"Category: items\") — clone marker #2; use the chosen family's skills shape")

    if not use_poppler:
        print("WARN  pypdf extraction is indicative only (spurious spaces inside words, e.g. \"FORMA TION\") — poppler's pdftotext is the reference extractor (references/ats.md)")

    txt = extract_text(pdf, use_poppler)

    def bad(msg):
        """FAIL on the reference extractor, WARN on the pypdf fallback: pypdf's
        extraction is indicative only (this script says so above), so a hard
        FAIL on it would be a verdict the evidence does not support."""
        nonlocal fail
        if use_poppler:
            print("FAIL  " + msg)
            fail = 1
        else:
            print("WARN  " + msg + " — pypdf extraction is indicative; confirm with pdftotext before believing it")

    if not txt.strip():
        bad("extraction empty")
    # ≥4 STANDALONE capitals: the \b anchors keep "B.Sc. C S M Sc" (dotted
    # abbreviations) out. Second pattern catches tracking's real pdftotext
    # shape, which is chunked rather than fully spaced ("S O F T WA RE").
    # Known limit: a space injected INSIDE a word ("FORMA TION") is not
    # detectable here — it is a pypdf extraction artefact, not a layout bug,
    # and only the pypdf path (WARN-only above) produces it.
    spaced = re.search(r"\b(?:[A-Z] ){3,}[A-Z]\b", txt)
    if not spaced:
        for line in txt.split("\n"):
            tok = line.split()
            if (len(tok) >= 4 and all(re.fullmatch(r"[A-Z]{1,2}", t) for t in tok)
                    and sum(len(t) == 1 for t in tok) >= 2):
                spaced = line
                break
    if spaced:
        bad("spaced-out text in extraction (letterspacing/tracking?)")
    # Per PAGE: the orphaned date lands at the end of the page it belongs to,
    # not only at the end of the document.
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

    for line in check_year_only_dates(txt):
        print(f'WARN  year-only date range ("{line}") — month+year both ends unless the candidate cannot supply months (SKILL.md rule 1; references/ats.md)')
    for line in check_degree_tokens(txt):
        print(f'WARN  degree token beside a non-completion marker ("{line}") — ATS (Eightfold) read "B.Eng. program" as a degree held; say "coursework" (references/ats.md)')

    bullets = check_bullet_chars(txt)
    if bullets:
        print(f'WARN  {len(bullets)} line(s) start with a bullet character in the extraction (e.g. "{bullets[0][:30]}") — ATS prints it or puts it alone on a line; draw list markers as vector shapes (references/ats.md)')

    if use_cli:
        fail |= run_new_gates(typ, pdf, txt, typ_text)
    else:
        print("WARN  grouping / date-adjacency / duplicate-name gates NOT checked (need the typst CLI)")
        for msg in check_forced_linebreak(typ_text):
            print("FAIL  " + msg)
            fail = 1

    print("──── extraction (check reading order, orphaned dates, intact skill lines) ────")
    print(txt)

    if fail == 0:
        if fmin and fmax:
            print("PASS  all mechanical checks — now LOOK at the PNGs")
        else:
            print("PASS  mechanical checks except fill (no FILL_MIN FILL_MAX "
                  "given) — rerun with the fill targets from the pick_design.py "
                  "report, then LOOK at the PNGs")

    sys.exit(fail)


def _run():
    try:
        main()
    except SystemExit as e:
        if _footer and isinstance(e.code, int) and e.code != 0:
            print(_footer, flush=True)
        raise


if __name__ == "__main__":
    _run()
