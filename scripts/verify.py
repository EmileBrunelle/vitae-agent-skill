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
capitals, orphaned dates, no section split across a page break, year-only dates, degree tokens, --facts coverage,
summary and entry repeats, bullet characters); last, the gates that need `typst query` (hidden text, font fallback,
group proximity, date adjacency, forced line breaks and `~`, duplicate names).

Design principle: Python keeps the deterministic checks. Where it cannot judge (a language it has no word lists for,
a render without `typst query`, a PDF reader that cannot give word boxes) it says so with an INFO or a WARN and
leaves the comparison to the agent (references/steps/6-verify.md); it never FAILs because a language is unknown.

The helpers live in sibling modules, which verify.py imports by name: verify_lang (language data and detection),
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
import contextlib
import functools
import glob
import hashlib
import html
import importlib
import importlib.metadata
import importlib.util
import json
import math
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from collections.abc import Callable, Iterator, Sequence
from typing import Any, Literal, NoReturn, TypedDict, cast, overload

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure_fill  # noqa: E402
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
from verify_lang import (  # noqa: E402 -- language data: edit verify_lang.py to add a language
    _ACTION_VERB_SRC,
    _ELISION_RE,
    _ENTRY_STOP,
    _EXPERIENCE_TITLES,
    _HEADING_WORDS,
    _LANG_NAMES,
    _LINKS,
    _LOC_GENERIC_SRC,
    _LOC_JOIN_SRC,
    _MONTH_ENFR,
    _MONTH_EXTRA_RE,
    _MONTH_WORDS,
    _MONTHS,
    _PROJECT_TITLES,
    _RANGE_WORDS,
    _SEASONS_OTHER,
    _SUMMARY_TITLES,
    DEGREE_RE,
    INCOMPLETE_RE,
    _is_latin,
    _strip_latin_marks,
)
from verify_lang import (
    _detect_lang as _detect_lang,
)
from verify_level import Level  # noqa: E402
from verify_page import (  # noqa: E402 -- page geometry and pixel measurement: pixels and boxes in, numbers out
    BOUNDARY_RATIO,
    CROP_CAP,
    CROP_PAD_IN,
    CROP_PPI,
    CROP_SCAN_PPI,
    INK_DELTA,
    INK_DPI,
    RULE_PT,
    _lum,
    _row_stats,
    boundary_ink,
    crop_candidates,
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
from verify_typst import (  # noqa: E402 -- cv.typ parsing: pure text in, values out
    _DATE_ARG_RE,
    _ENTRY_CALL_RE,
    _call_strings,
    _doc_body_size,
    _doc_par_list,
    _entries,
    _mask_non_markup,
    _section_bodies,
    _typst_prose,
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

# ---------- shapes passed around ----------
# Geometry, in PDF points unless said otherwise (pdftotext -bbox).
Box = tuple[float, float, float, float]            # x0, y0, x1, y1
WordBox = tuple[Box, str]                          # a word and its box
Word = tuple[float, float, float, float, str]      # x0, y0, x1, y1, text
Band = tuple[int, int]                             # first, last pixel row of a run
LineBox = list[float]                              # [x0, x1, y0, y1] of one text line
GapFn = Callable[[int, LineBox, LineBox], float]   # optical gap (pt) between two lines
Finding = tuple[Level, str]                        # one gate line: level, message
# One extracted word of the hidden-text gate: page, word, box, box height (pt),
# contrast against its own background (None: no raster), off the page.
HiddenStat = tuple[int, str, Box, float, float | None, bool]


class Mark(TypedDict, total=False):
    """One value of lib.typ's invisible markers, read back by `typst query`
    (<vitae-head> / <vitae-part> / <vitae-sec>). Every key is optional: an old
    lib omits some, and the different mark kinds carry different subsets.
    kind: "entry" / "skill" (heads) or "date" / "org" / "date-col" (parts)."""
    kind: str
    text: str
    org: str
    page: int
    x: float
    y: float
    w: float            # measured cell width (parts)
    h: float            # measured cell height (parts)
    dated: bool         # entry heads: given a date?
    anchor: bool        # entry heads: lib's date anchor present
    inline: bool        # date parts: set inline after the role


class _EntryRecord(TypedDict):
    """_entry_records(): an entry head with the part marks that follow it."""
    head: Mark
    date: Mark | None
    org: Mark | None
    date_first: bool | None


class _Line(TypedDict):
    """_lines(): the words of one text line, clustered by y-centre."""
    y0: float
    y1: float
    c: float
    x0: float
    words: list[Word]


class GroupRow(TypedDict):
    """measure_groups() / DETAIL row of an entry or skill group."""
    kind: Literal["group"]
    text: str
    page: int
    n: int                          # lines in the group, less one
    gaps: list[float]               # gaps between consecutive lines inside it
    internal: float                 # the largest of them
    between: float                  # last line -> next block's first line
    ratio: float                    # between / internal
    ls: list[LineBox]
    pair_in: tuple[str, str]        # the line pair behind `internal`
    pair_btw: tuple[str, str]       # the line pair behind `between`


class SecRow(TypedDict):
    """measure_groups() / DETAIL row of a section title."""
    kind: Literal["sec"]
    text: str
    page: int
    before: float                   # previous block -> title (its bar)
    after: float                    # title -> first line of its section
    ratio: float


DetailRow = GroupRow | SecRow


# ---------- dependency preflight ("doctor") ----------

def check_pillow() -> bool:
    """Doctor line for Pillow, which the fill, text-clip, hidden-text and crop measurements read rasters through:
    without it the doctor fails."""
    try:
        import PIL  # noqa: F401
        print(f"OK    Pillow {PIL.__version__}")
        return True
    except ImportError:
        print("MISSING  Pillow -- needed for the page-fill measurement:")
        print("  sudo dnf install python3-pillow | sudo apt install python3-pil   # distro Python: official repos first (PEP 668)")
        print("  uv pip install Pillow | pip3 install --user Pillow               # venvs / pip-only environments")
        return False


def _linux_arch() -> str | None:
    """'x86_64' / 'aarch64' on Linux, else None (no-root binary routes are Linux-only)."""
    if platform.system() != "Linux":
        return None
    m = platform.machine().lower()
    return {"x86_64": "x86_64", "amd64": "x86_64", "aarch64": "aarch64", "arm64": "aarch64"}.get(m)


def _py_fetch(url: str, mode: str, member: str, exact: bool) -> str:
    """One python3 -c line: download `url` with urllib, extract only the tar member
    (`member` is the exact name, or a suffix) into ~/.local/bin as its basename.
    For sandboxes where shell curl/wget are refused but Python can fetch."""
    test = "m.name==" + repr(member) if exact else "m.name.endswith(" + repr("/" + member) + ")"
    base = member.rsplit("/", 1)[-1]
    return ("python3 -c \"import urllib.request as u,tarfile,os;d=os.path.expanduser('~/.local/bin');"
            "os.makedirs(d,exist_ok=True);f=tarfile.open(fileobj=u.urlopen('" + url + "'),mode='r|" + mode + "');"
            "[(setattr(m,'name','" + base + "'),f.extract(m,d)) for m in f if " + test + "]\"")


def _typst_noroot_lines(arch: str) -> list[str]:
    """Install lines for typst without root: the release tarball, by curl and by python."""
    tgt = f"typst-{arch}-unknown-linux-musl"
    url = f"https://github.com/typst/typst/releases/latest/download/{tgt}.tar.xz"
    return [
        f"  no root, curl:   mkdir -p ~/.local/bin && curl -fsSL {url} | tar -xJf - -C ~/.local/bin --strip-components=1 {tgt}/typst",
        "  no root, python (when shell curl/wget are refused): " + _py_fetch(url, "xz", "typst", False),
        "  (then make sure ~/.local/bin is on PATH)",
    ]


def _poppler_noroot_lines(arch: str) -> list[str]:
    """Install lines for poppler without root, through micromamba from conda-forge."""
    plat = "linux-64" if arch == "x86_64" else "linux-aarch64"
    url = f"https://micro.mamba.pm/api/micromamba/{plat}/latest"
    return [
        "  no root (micromamba from conda-forge), step 1, get micromamba:",
        f"    curl:   mkdir -p ~/.local/bin && curl -fsSL {url} | tar -xj -C ~/.local/bin --strip-components=1 bin/micromamba",
        "    python: " + _py_fetch(url, "bz2", "bin/micromamba", True),
        "  step 2: ~/.local/bin/micromamba create -y -p ~/poppler -c conda-forge poppler   # then put ~/poppler/bin on PATH",
    ]


# Oldest typst the fill targets were calibrated on; an older one still works and is reported DEGRADED, not refused.
TYPST_MIN = (0, 15)
_OLD_TYPST = ("fill targets are calibrated on typst 0.15; older versions measure lower "
              "(0.13/0.14 miss 2 templates at 91% against 93-96%)")


def check_typst() -> tuple[bool, bool]:
    """Doctor lines for typst; returns (available, use_cli). The CLI is preferred, the Python API is the fallback and
    is judged by running it, not by its attributes. Older than TYPST_MIN, or a Python API without query/fonts, is
    DEGRADED (still available); a broken or missing install is not."""
    if shutil.which("typst"):
        try:
            ver = subprocess.run(["typst", "--version"], capture_output=True, text=True).stdout.split()[1]
        except Exception:
            ver = "?"
        if ver != "?" and _ver_tuple(ver) < TYPST_MIN:
            print(f"DEGRADED  typst {ver} (CLI): {_OLD_TYPST}.")
            print("  Upgrade the CLI with ONE of:")
            arch = _linux_arch()
            if arch:
                for ln in _typst_noroot_lines(arch):
                    print(ln)
            print("  brew upgrade typst | cargo install typst-cli --force | winget upgrade Typst.Typst")
            print("  distro packages (dnf, apt, pacman) may be older: check `typst --version` after")
            return True, True
        print(f"OK    typst {ver} (CLI)")
        return True, True
    mod, ver, why, full = _typst_py_probe()
    if mod is None and why.startswith("TOOLOLD"):
        print(f"BROKEN  typst: the Python package `typst` is too old ({why[len('TOOLOLD '):]}).")
        print("  Upgrade it: pip install -U typst   # or install the CLI (brew install typst | cargo install typst-cli)")
        return False, False
    if mod is None and why:
        print(f"BROKEN  typst: the Python package `typst` is installed but does not work ({why}).")
        print("  Reinstall it: pip install --force-reinstall typst   # or install the CLI (brew install typst | cargo install typst-cli)")
        return False, False
    if mod is not None and not full:
        print("DEGRADED  typst: Python API only, no typst CLI. Compiling and fill measurement work, but these checks are SKIPPED (WARN):")
        print("  - date adjacency (needs `typst query`, and pdftotext)")
        print("  - group proximity (needs `typst query` and pdftotext)")
        print("  - the design font-availability check of pick_design.py (needs `typst fonts`)")
        print("  Install the CLI with ONE of:")
        arch = _linux_arch()
        if arch:
            for ln in _typst_noroot_lines(arch):
                print(ln)
        print("  brew install typst | cargo install typst-cli | pip install -U typst   # newer typst-py: query, eval and fonts")
        print("  winget install --id Typst.Typst | choco install typst | scoop install typst   # Windows")
        return True, False
    if mod is not None:
        if _ver_tuple(ver) < TYPST_MIN:
            print(f"DEGRADED  typst {ver} (Python API): {_OLD_TYPST}.")
            print("  pip install -U typst")
            return True, False
        print(f"OK    typst {ver} (Python API: compile, query, fonts)")
        return True, False
    print("MISSING  typst -- install with ONE of:")
    print("  pip install typst                            # no CLI needed: compiles, queries and lists fonts via the Python API")
    print("  brew install typst                          # macOS")
    print("  winget install --id Typst.Typst             # Windows")
    print("  choco install typst | scoop install typst   # Windows, if you already use them")
    print("  cargo install typst-cli                      # any, via Rust")
    print("  (distro packages — dnf, apt, pacman — may be older than 0.15, the version the fill targets are calibrated on)")
    arch = _linux_arch()
    if arch:
        for ln in _typst_noroot_lines(arch):
            print(ln)
    print("  OFFLINE sandbox (no DNS / pip index)? On the user's own machine run:")
    _wa = "aarch64" if platform.machine().lower() in ("aarch64", "arm64") else "x86_64"
    print(f"    pip download typst==0.15.0 --no-deps --only-binary=:all: --platform manylinux2014_{_wa} --python-version 3.11")
    print(f"    (or take the cp38-abi3-manylinux_2_17_{_wa} wheel from https://pypi.org/project/typst/#files), upload the .whl, then:")
    print("    pip install --no-index <path-to-wheel>")
    return False, False


PdfBackend = Literal["poppler", "pdfium", "pypdf"] | None


@functools.lru_cache(maxsize=None)
def _importable(name: str) -> bool:
    """True when `name` really imports (find_spec says only that a file exists: a broken
    wheel or a missing shared library passes it and then fails on first use)."""
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False


def pdf_backend() -> PdfBackend:
    """The PDF reader every check uses: poppler when pdfinfo and pdftotext are on PATH
    (the reference), else pypdfium2 (text, word boxes, raster, metadata and attachments in
    Python: close to poppler, not identical, see the CHANGELOG for where it differs), else
    pypdf (page count and indicative text only: it splits words), else None. A module that
    does not import is not selected, the doctor tests it the same way."""
    if shutil.which("pdfinfo") and shutil.which("pdftotext"):
        return "poppler"
    for name, backend in (("pypdfium2", "pdfium"), ("pypdf", "pypdf")):
        if _importable(name):
            return cast(PdfBackend, backend)
    return None


def pdf_tool(name: str) -> bool:
    """True when `name` (pdftotext, pdftoppm, pdfdetach) can be served: on PATH, or by pypdfium2."""
    return bool(shutil.which(name)) or pdf_backend() == "pdfium"


def check_pdf_tools() -> tuple[bool, PdfBackend]:
    """Doctor lines for the PDF reader; returns (available, backend), the backend being the one pdf_backend() would
    pick. A missing pdftoppm, or pypdf standing in for poppler, only degrades: the checks it cannot serve are named
    in the output."""
    arch = _linux_arch()
    if shutil.which("pdfinfo") and shutil.which("pdftotext"):
        if not shutil.which("pdftoppm"):
            print("DEGRADED  poppler-utils: pdftotext and pdfinfo found, pdftoppm missing. SKIPPED (WARN):")
            print("  - hidden-text ink check (also used by verify_letter.py / verify_academic.py)")
            print("  Weaker without a WARN: group proximity falls back to the pdftotext box gap instead of the ink gap")
            print("  Install pdftoppm (part of poppler) with ONE of:")
            if arch:
                for ln in _poppler_noroot_lines(arch):
                    print(ln)
            print("  sudo dnf install poppler-utils | sudo apt install poppler-utils | brew install poppler")
            return True, "poppler"
        print("OK    poppler-utils (pdftotext, pdfinfo, pdftoppm)")
        return True, "poppler"
    if _importable("pypdfium2"):
        try:
            ver = importlib.metadata.version("pypdfium2")
        except importlib.metadata.PackageNotFoundError:
            ver = "?"
        print(f"OK    pdf: pypdfium2 {ver} (Python: text, word boxes, raster, metadata, attachments)")
        print("  - academic mode still needs poppler (verify_academic.py reads `pdftotext -layout`)")
        return True, "pdfium"
    if _importable("pypdf"):
        print("DEGRADED  pypdf: Python fallback, no poppler. Page count is exact, but:")
        print("  - ATS text extraction is indicative only (spurious spaces, e.g. \"FORMA TION\")")
        print("  - SKIPPED (WARN): hidden-text gate and text-clip gate (need pdftotext and pdftoppm)")
        print("  - SKIPPED (WARN): group proximity and date adjacency (need pdftotext)")
        print("  - academic mode cannot run (verify_academic.py requires pdftotext)")
        print("  Install poppler with ONE of:")
        if arch:
            for ln in _poppler_noroot_lines(arch):
                print(ln)
        print("  - or `pip install pypdfium2`: text, word boxes, raster and metadata then run in Python close to poppler's (see the CHANGELOG)")
        print("  brew install poppler | sudo dnf install poppler-utils | sudo apt install poppler-utils")
        print("  choco install poppler | scoop install poppler          # Windows")
        return True, "pypdf"
    else:
        print("MISSING  poppler-utils -- needed for page-count and ATS extraction checks:")
        print("  brew install poppler | sudo dnf install poppler-utils | sudo apt install poppler-utils")
        print("  choco install poppler | scoop install poppler          # Windows")
        print("  pip install pypdfium2                                  # fallback: text, boxes, raster and metadata in Python, close to poppler's (used automatically if present)")
        print("  pip install pypdf                                      # last resort: exact page count, indicative extraction only (used automatically if present)")
        return False, None


def check_fonts() -> None:
    """Doctor line for fonts (typst CLI or typst-py; local, no network, 20 s cap).

    Reuses pick_design's own logic: a design family is usable when every role of
    its pool has at least one installed member (`_installed`). pick_design
    draws from at least MIN_POOL families, so fewer usable ones means it will
    substitute."""
    import pick_design as pd
    have = pd._fonts_available()
    if have is None:
        print("WARN  fonts not checked (`typst fonts` failed or timed out)")
        return
    pools = pd.FONTS
    usable = sum(1 for fp in pools.values()
                 if all(any(pd._installed(f[0], have) for f in cast(Any, fp)[role])
                        for role in ("display", "body", "mono") if role in fp))
    if usable < pd.MIN_POOL:
        print(f"DEGRADED  fonts: only {usable} of {len(pools)} design families have their fonts installed "
              f"(pick_design draws from at least {pd.MIN_POOL}), so it will substitute.")
        print("  Fetch only the fonts the draw asks for (references/fonts.md, \"Downloading from Google Fonts\"):")
        r2 = ("typst --font-path <dir> (no install)" if shutil.which("typst")
              else "export TYPST_FONT_PATHS=<dir> (no install; the Python API reads it here)")
        print(f"  Route 1: install into ~/.local/share/fonts/vitae (persistent, recommended); Route 2: {r2}")
    else:
        print(f"OK    fonts ({usable} of {len(pools)} design families fully installed, {len(have)} families)")


class _CountDegraded:
    """stdout wrapper: counts the doctor lines that start with DEGRADED, so no path can print one and still end on an
    OK summary, whichever check wrote it."""
    def __init__(self, inner: Any) -> None:
        self.inner, self.n, self._bol = inner, 0, True

    def write(self, text: str) -> int:
        for part in text.splitlines(keepends=True):
            if self._bol and part.startswith("DEGRADED"):
                self.n += 1
            self._bol = part.endswith("\n")
        return int(self.inner.write(text))

    def flush(self) -> None:
        self.inner.flush()

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)


def preflight() -> tuple[bool, bool, PdfBackend]:
    """Print the doctor output; returns (all_ok, use_cli_typst, pdf_backend). all_ok is False only when something
    has no fallback (Pillow, typst, a PDF reader); DEGRADED lines leave it True."""
    counter = _CountDegraded(sys.stdout)
    with contextlib.redirect_stdout(cast(Any, counter)):
        pillow_ok = check_pillow()
        typst_ok, use_cli = check_typst()
        if use_cli or typst_py() is not None:
            check_fonts()
        pdf_ok, backend = check_pdf_tools()
        all_ok = pillow_ok and typst_ok and pdf_ok
        pypdf_missing = backend in ("poppler", "pdfium") and not _importable("pypdf")
        if pypdf_missing:
            # the WARN check_hidden_text prints for this backend, quoted so the doctor and the gate agree
            skipped = ("the tiny-text check of the hidden-text gate will NOT run "
                       "(WARN \"tiny-text check not run (pypdf missing)\")" if backend == "pdfium" else
                       "the off-page check of the hidden-text gate will NOT run "
                       "(WARN \"hidden text: off-page check not run (pypdf missing)\")")
            print(f"DEGRADED  pypdf: not installed. {skipped}. Fix: pip install pypdf")
        if (all_ok and not counter.n and not use_cli and backend == "pdfium" and typst_py() is not None
                and _ver_tuple(_typst_py_probe()[1]) >= TYPST_MIN):
            print("OK (Python)  no typst CLI, no poppler: compile, query, fonts, text, boxes and raster all run in Python "
                  "(typst-py + pypdfium2 + pypdf + Pillow); academic mode still needs poppler")
    return all_ok, use_cli, backend


# ---------- compile / page-count / extraction, native or fallback ----------

def auto_root(typ: str) -> str | None:
    """Typst project root a file needs, or None for the default (its own folder).

    The reference family files import the shared mechanics by relative path
    (`#import "../../lib.typ"`), which Typst refuses unless `--root` is an ancestor
    holding both. Climb as many levels as the deepest leading `../` of a
    non-comment import; a CV folder (`#import "lib.typ"`) needs nothing."""
    try:
        with open(typ, encoding="utf-8-sig", errors="replace") as fh:
            src = _strip_typst_comments(fh.read())
    except OSError:
        return None
    ups = max((len(m.group(1)) // 3 for m in re.finditer(r'\bimport\s*\(?\s*"((?:\.\./)+)[^"]*\.typ"', src)), default=0)
    root = os.path.dirname(os.path.abspath(typ))
    for _ in range(ups):
        root = os.path.dirname(root)
    return root if ups else None


# auto_root as a typst-py keyword and as CLI flags; empty when the default root (the file's own folder) is right.
def _root_kw(typ: str) -> dict[str, str]:
    r = auto_root(typ)
    return {"root": r} if r else {}


def _root_cli(typ: str) -> list[str]:
    r = auto_root(typ)
    return ["--root", r] if r else []


def ensure_icons(typ: str) -> None:
    """Guarantee an `icons.typ` beside the file being compiled.

    `lib.typ` does `#import "icons.typ": *`, and Typst resolves that against
    the importing file, so the deliverable folder needs one. Step 4 of
    SKILL.md copies the repo's EMPTY fallback there along with `lib.typ`, and
    `harvest_icons.py <folder>` overwrites it with the fetched path data. This
    covers the one case those two miss: a folder where the copy was forgotten
    — copy the empty fallback instead of failing the compile with a Typst
    import error. No network here; fetching stays harvest_icons.py's job.
    """
    if auto_root(typ):                 # reference family file: lib.typ/icons.typ live in templates/
        return
    d = os.path.dirname(os.path.abspath(typ))
    dst = os.path.join(d, "icons.typ")
    if os.path.islink(dst):            # never write through a symlink
        if not os.path.exists(dst):
            print(f"WARN  {dst} is a dangling symlink — not writing through it; "
                  f"replace it with a regular file")
        return
    if not os.path.exists(dst):
        src = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "templates", "icons.typ")
        if not os.path.exists(src):    # no repo fallback (nothing to copy)
            return
        fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                     | getattr(os, "O_NOFOLLOW", 0), 0o644)
        with os.fdopen(fd, "wb") as fh, open(src, "rb") as sf:
            fh.write(sf.read())
        print(f"NOTE  copied the empty fallback icons.typ into {d} — run "
              f"scripts/harvest_icons.py there for the real marks")


def typst_font_kw() -> dict[str, list[str]]:
    """typst-py keyword for the font route of references/fonts.md: TYPST_FONT_PATHS (what the
    CLI reads on its own) as `font_paths`; typst-py ignores the variable, so pass it by hand."""
    fp = [p for p in os.environ.get("TYPST_FONT_PATHS", "").split(os.pathsep) if p]
    return {"font_paths": fp} if fp else {}


def _ver_tuple(v: str) -> tuple[int, int]:
    """(major, minor) of the first `X.Y` in `v`; (0, 0) when there is none, which reads as older than TYPST_MIN."""
    m = re.search(r"(\d+)\.(\d+)", v)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


@functools.lru_cache(maxsize=None)
def _typst_py_probe() -> tuple[Any | None, str, str, bool]:
    """(module, version, problem, full) for the `typst` Python package, by running it: a tiny
    document is compiled and an expression evaluated, so a broken wheel is reported broken
    (an attribute check passes it). module None + problem "" = not installed; module None +
    problem = installed but unusable; full = also query, eval and Fonts."""
    try:
        mod: Any = importlib.import_module("typst")
    except ImportError:
        return None, "", "", False
    except Exception as e:
        return None, "", f"import failed: {e}", False
    comp_cls = getattr(mod, "Compiler", None)
    if comp_cls is not None and not hasattr(comp_cls, "compile_with_warnings"):
        # a working but old wheel (typst-py 0.11.x): the API this script drives is newer
        return None, "", f"TOOLOLD typst {getattr(mod, '__version__', '?')}: its Compiler has no compile_with_warnings", False
    try:
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "probe.typ")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write("#set page(width: 50pt, height: 50pt)\nprobe\n")
            comp = mod.Compiler(src, **typst_font_kw())
            res = comp.compile_with_warnings()
            doc = res[0] if isinstance(res, tuple) else res      # (pdf bytes, warnings)
            if not isinstance(doc, bytes | bytearray) or not doc.startswith(b"%PDF"):
                return None, "", "compiling a one-line document returned no PDF", False
        try:
            ver = str(json.loads(mod.Compiler().eval("str(sys.version)", format="json")))
        except Exception:
            ver = str(getattr(mod, "__version__", "?"))
        full = False
        try:
            full = (hasattr(comp, "query") and hasattr(comp, "eval")
                    and bool(mod.Fonts(include_system_fonts=True, **typst_font_kw()).families()))
        except Exception:
            pass
        return mod, ver, "", full
    except Exception as e:
        return None, "", f"{type(e).__name__}: {e}", False


def typst_py() -> Any | None:
    """The `typst` Python module if it works and can run query/eval/fonts too (a working
    install, proven by `_typst_py_probe`), else None. A broken, old or compile-only module
    does not qualify."""
    mod, _, _, full = _typst_py_probe()
    return mod if full else None


def typst_can_query() -> bool:
    """True when `typst query`/`eval`/`fonts` can run: the CLI, or typst-py."""
    return bool(shutil.which("typst")) or typst_py() is not None


def typst_compile(src: str, pdf: str | None = None) -> tuple[bool, str]:
    """(ok, stderr) for `typst compile src [pdf]` via the CLI, else typst-py
    (the selftests' compile step; warnings are included in the text)."""
    if shutil.which("typst"):
        r = subprocess.run(["typst", "compile", src] + ([pdf] if pdf else []) + _root_cli(src), capture_output=True, text=True)
        return r.returncode == 0, r.stderr
    mod = typst_py() or importlib.import_module("typst")
    try:
        res = mod.Compiler(src, **_root_kw(src), **typst_font_kw()).compile_with_warnings(output=pdf or os.path.splitext(src)[0] + ".pdf")
        warns = res[1] if isinstance(res, tuple) and len(res) > 1 else []
        return True, "\n".join(str(w) for w in warns or [])
    except Exception as e:
        return False, str(e)


def typst_fonts() -> list[str] | None:
    """Family names `typst fonts` reports (CLI, else typst-py), or None."""
    if shutil.which("typst"):
        try:
            r = subprocess.run(["typst", "fonts"], capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            return None
        return [l.strip() for l in r.stdout.splitlines() if l.strip()] if r.returncode == 0 else None
    mod = typst_py()
    try:
        return list(mod.Fonts(include_system_fonts=True, **typst_font_kw()).families()) if mod else None
    except Exception:
        return None


def compile_pdf(typ: str, pdf: str, use_cli: bool) -> tuple[bool, str]:
    """Returns (ok, stderr_text)."""
    if use_cli:
        r = subprocess.run(["typst", "compile", os.path.abspath(typ), os.path.abspath(pdf)] + _root_cli(typ), capture_output=True, text=True)
        return r.returncode == 0, (r.stdout + r.stderr)
    try:
        typst: Any = importlib.import_module("typst")
        typst.compile(typ, output=pdf, **_root_kw(typ), **typst_font_kw())
        return True, ""
    except Exception as e:
        return False, str(e)


def render_pngs(typ: str, tmp_dir: str, use_cli: bool) -> list[str]:
    """One 90 ppi PNG per page, the raster the fill scan reads (the hidden-text gate renders its own, at HIDDEN_PPI).
    The second typst-py call is for a version whose compile() does not take `ppi`."""
    pattern = os.path.join(tmp_dir, "p{p}.png")
    if use_cli:
        subprocess.run(["typst", "compile", os.path.abspath(typ), os.path.abspath(pattern), "--format", "png", "--ppi", "90"] + _root_cli(typ),
                        capture_output=True, text=True)
    else:
        typst: Any = importlib.import_module("typst")
        try:
            typst.compile(typ, output=pattern, format="png", ppi=90, **_root_kw(typ), **typst_font_kw())
        except TypeError:
            typst.compile(typ, output=pattern, format="png", **_root_kw(typ), **typst_font_kw())
    return sorted(glob.glob(os.path.join(tmp_dir, "p*.png")))


def _pdfium_doc(pdf: str) -> Any:
    return importlib.import_module("pypdfium2").PdfDocument(pdf)


def count_pages(pdf: str, backend: PdfBackend) -> str | None:
    """The page count as text, compared with EXPECTED_PAGES as text; None when pdfinfo prints no Pages line."""
    if backend == "pdfium":
        return str(len(_pdfium_doc(pdf)))
    if backend == "poppler":
        out = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if line.startswith("Pages:"):
                return line.split()[1]
        return None
    pypdf: Any = importlib.import_module("pypdf")
    return str(len(pypdf.PdfReader(pdf).pages))


LINE_GAP = 1.0


def _pdfium_page_text(pg: Any) -> str:
    """pypdfium2's page text with its lines cut like pdftotext's. pdfium joins cells that
    share a baseline (a contact row, a left-flushed role and its right-flushed date) into one
    line; a new line starts where the gap to the previous character exceeds LINE_GAP (1.0) x the box height. That
    value was picked by search against pdftotext's line counts: poppler's own cut is not purely geometric, and
    `_reading_order` cuts its pieces at 1.5 x for a different purpose (reading order). A gap with whitespace in it
    becomes the newline; a gap without any gets one inserted. Trailing blanks are dropped."""
    tp = pg.get_textpage()
    if not tp.count_chars():
        return ""
    text = tp.get_text_range()
    out: list[str] = []
    prev: tuple[float, float, float, float] | None = None
    idx = 0
    pending = ""                                   # whitespace seen since the last glyph
    for ch in text:
        i, idx = idx, idx + (2 if ord(ch) > 0xFFFF else 1)
        if ch.isspace() or ord(ch) < 0x20:
            if ch in "\r\n":
                prev = None
            pending += ch
            continue
        box = tp.get_charbox(i, loose=True)
        if box[2] <= box[0] or box[3] <= box[1]:
            out.append(pending + ch)
            pending = ""
            continue
        if prev is not None and "\n" not in pending:
            height = min(prev[3] - prev[1], box[3] - box[1])
            same_row = abs((prev[1] + prev[3]) / 2 - (box[1] + box[3]) / 2) <= 0.4 * height
            if same_row and box[0] - prev[2] > LINE_GAP * height:
                pending = "\n"
        out.append(pending.rstrip(" \t") if "\n" in pending else pending)
        out.append(ch)
        pending = ""
        prev = (box[0], box[1], box[2], box[3])
    out.append(pending)
    return "".join(out)


def extract_text(pdf: str, backend: PdfBackend) -> str:
    """The PDF text the ATS checks read, in pdftotext's shape whatever the backend. pypdf's is indicative only."""
    if backend == "poppler":
        return subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True).stdout
    if backend == "pdfium":
        # pdftotext's shape: pages end with \f (a blank line before it), lines with \n
        return "".join(t.replace("\r\n", "\n").rstrip("\n") + "\n\n\f"
                       for t in (_pdfium_page_text(pg) for pg in _pdfium_doc(pdf)))
    pypdf: Any = importlib.import_module("pypdf")
    reader = pypdf.PdfReader(pdf)
    return "\n".join(page.extract_text() or "" for page in reader.pages)



# ---------- no section split across a page break (SKILL.md rule 5) ----------

# The headings come from the SOURCE, not from a guess at what a heading looks
# like in the extraction: every family defines its own `#section(t, body)` and
# calls it `#section("Title")[...]`, so the call sites ARE the declared list.
# No font-size heuristic survives the family roster; a grep does.
SECTION_CALL_RE = re.compile(r'#section\(\s*"([^"]*)"')

# lib.typ's `runhead` emits `name #h(1fr) n / total` (design.md § the device
# table: placed IN THE FLOW, because a page `header:` field is dropped by many
# parsers). pdftotext may put the name and the `n / total` on one line or two,
# in either order, so the pagination token is what identifies the band — and a
# section heading never carries one.
PAGINATION_RE = re.compile(r"\b\d+\s*/\s*\d+\b|\bpage\s+\d+\b", re.I)


def _norm_heading(s: str) -> str:
    """Compare headings on letters and digits only: the extraction upper-cases
    them, and a family's device may add or drop punctuation around one. Any
    script: case-folded, accents dropped from Latin letters only, everything
    that is not a letter, digit or mark is a separator."""
    s = _strip_latin_marks(s.casefold())
    return " ".join("".join(c if c.isalnum() or unicodedata.category(c)[0] == "M" else " " for c in s).split())


def _heading_words(s: str) -> frozenset[str]:
    """Loose key of a NON-Latin heading: its words with every combining mark, joiner and
    format character removed, as a set. Extraction may reorder the marks of Devanagari or Thai,
    reshape Arabic, return right-to-left words in another order, or upper-case Greek without its
    accents (ΕΜΠΕΙΡΙΑ for εμπειρία); none of that is a section split, so a heading that matches on this
    key is accepted. Latin headings: empty (exact only)."""
    h = _norm_heading(s)
    if all(_is_latin(c) for c in h if c.isalpha()):
        return frozenset()
    bare = "".join(c for c in unicodedata.normalize("NFKD", h)
                   if not unicodedata.combining(c) and unicodedata.category(c) not in ("Cf", "Mn"))
    return frozenset(bare.split())


def check_no_split(source: str, pages: list[str]) -> list[tuple[bool, str]]:
    """SKILL.md rule 5 -- "no section may split across a page break".

    Reduced to one measurable statement: a section that starts on page P and
    is not finished there leaves content at the TOP of page P+1. So every page
    after the first must OPEN on a section heading. Contrapositive of the rule,
    not an approximation of it -- if every break lands exactly on a boundary,
    nothing straddles; if one does not, whatever section preceded it is split.

    Returns (is_fail, message) pairs; "no #section call" and "single page" come back as non-failures, which the
    caller prints. The caller turns a FAIL into a WARN on the pypdf fallback, whose extraction is indicative only.

    Pure function of (source text, extracted pages) so the selftest can feed it
    synthetic text and needs no Typst. The academic gate checks the same
    property one level down (verify_academic.check_no_straddle: the atom is the
    ENTRY there, and its heading list comes from the declared JSON spec).
    """
    headings = {_norm_heading(t) for t in SECTION_CALL_RE.findall(source)}
    headings.discard("")
    loose = [hw for hw in (_heading_words(t) for t in SECTION_CALL_RE.findall(source)) if hw]
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
        fw = _heading_words(first)
        ok = ok or bool(fw) and any(fw <= hw for hw in loose)   # non-Latin: marks and word order not trusted
        out.append((not ok,
                    f'no-split: page {pageno} opens on "{first[:60]}"'
                    + ("" if ok else " -- not a section heading, so the "
                                     "section before the break is SPLIT "
                                     "across it (SKILL.md rule 5)")))
    return out

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
# 5.14 (a deliberately device-less family, which design.md says legitimately
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
# Internal white runs are judged as fractions of page height, never pixels (references/design.md, "Internal-gap
# scan"): a run over BOUNDARY_CEILING is a canyon wherever it sits; a run over CANYON is a hole unless it is a section
# boundary (a run of at least BOUNDARY_RATIO x the median run).
CANYON = 0.035          # a hole this tall (fraction of page height) is a defect
BOUNDARY_CEILING = 0.05  # …unless it is a section boundary, which may run this tall

# Families whose boundary device is real but of a KIND no row scan can see: they are exempt from the DEVICE_QUORUM
# FAIL only (check_whitespace looks the family up with family_from_path). Measured 2026-09-13; each is a device
# nature, not a tuning miss:
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
_MONTH = r"(?:%s|%s)" % (_MONTH_ENFR, _MONTH_EXTRA_RE)      # + German, Spanish, Italian, Portuguese, Dutch
_SEASON = (r"(?:fall|autumn|summer|winter|spring|automne|[ée]t[ée]|hiver|printemps|%s)"
           % "|".join(re.escape(w) for w in _SEASONS_OTHER))
_DATED = r"(?:%s|%s)\.?\s+" % (_MONTH, _SEASON)
# Both ends of a range need a month (or season): `Aug 2019 – 2021` and
# `2019 – Aug 2021` WARN as well as `2019 – 2021`. Present/now as the end is fine.
YEAR_RANGE_RE = re.compile(
    r"(?<!\d)((?:19|20)\d{2})(?:\s*[–—-]\s*|\s+(?:%s)\s+)"
    r"(%s)?"
    r"((?:19|20)\d{2}(?!\d)|present|now|aujourd.hui|pr[ée]sent)" % ("|".join(_RANGE_WORDS), _DATED), re.I)
MONTH_BEFORE_RE = re.compile(r"(?<![^\W\d_])" + _DATED.replace(r"\s+", r"\s*") + r"$", re.I)


def _month_before(prefix: str, lenient: bool) -> bool:
    """A month or season sits just before the range start. Neutral on what it cannot read: a word with no Latin
    letter (Cyrillic, Greek, CJK, Arabic, Devanagari, Thai...) may be a month, and so may ANY word when the text is in a
    language this file has no month names for (`lenient`). A Latin-script word of a known language must be a month."""
    if MONTH_BEFORE_RE.search(prefix):
        return True
    w = re.search(r"([^\W\d_]+)\.?\s*$", prefix)
    return w is not None and (lenient or not any(_is_latin(c) for c in w.group(1)))


def check_year_only_dates(txt: str) -> list[str]:
    """Lines carrying a range where either end lacks a month (or season). The caller WARNs, never FAILs (see above).
    A word it cannot read as a month, in a script or language it has no month names for, is given the benefit of
    the doubt (_month_before)."""
    out = []
    lenient = _detect_lang(txt)[0] == "other"
    for line in txt.split("\n"):
        for m in YEAR_RANGE_RE.finditer(line):
            end_ok = (m.group(2) is not None
                      or not m.group(3)[0].isdigit())
            if not (_month_before(line[:m.start()], lenient) and end_ok):
                out.append(line.strip())
                break
    return out


def _year_only_msg(line: str) -> str:
    return (f'year-only date range ("{line}") — if the facts file has no month for it, '
            'KEEP it year-only and report the gap; NEVER invent or estimate months '
            '(SKILL.md rule 1)')


# Date, number and name patterns of check_facts_coverage, matched on folded text (`_fold`, `_fold1`).
_MONTH_YEAR_RE = re.compile(
    r"(?<![^\W\d_])(%s)\.?\s+((?:19|20)\d{2})(?!\d)" % "|".join(sorted(_MONTHS, key=len, reverse=True)))
# "juillet – août 2019": the year closes the range and applies to the month before the dash too
# (the month before the dash is the earlier year when it is the later one in the calendar: "déc. – janv. 2020")
_RANGE_FOLDED = "|".join(dict.fromkeys(_strip_latin_marks(w) for w in _RANGE_WORDS))   # applied to folded text
_RANGE_MY_RE = re.compile(
    r"(?<![^\W\d_])(%s)\.?(?:\s*-\s*|\s+(?:to|au|through|%s)\s+)(%s)\.?\s+((?:19|20)\d{2})(?!\d)"
    % ("|".join(sorted(_MONTHS, key=len, reverse=True)), _RANGE_FOLDED,
       "|".join(sorted(_MONTHS, key=len, reverse=True))))
_NUM_MY_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})[-/.](0?[1-9]|1[0-2])(?!\d)|(?<!\d)(0?[1-9]|1[0-2])[-/.]((?:19|20)\d{2})(?!\d)")
_YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_NUM_RE = re.compile(r"[$€£]?(\d+(?:[.,]\d+)*)\s?(%|[kKmM](?![^\W\d_])|)")
def _upper_letters() -> str:
    """Regex class body of every capital letter (category Lu) of the Latin, Greek and Cyrillic
    blocks (Latin Extended-A/B and Additional included): `À-Ö Ø-Þ` missed Ł, Š, Ž, Ő, Ǎ, Ț, Ạ, Greek and Cyrillic."""
    spans = ((0xC0, 0x24F), (0x370, 0x3FF), (0x400, 0x52F), (0x1E00, 0x1FFF))
    return "A-Z" + "".join(re.escape(chr(c)) for a, b in spans for c in range(a, b + 1)
                           if unicodedata.category(chr(c)) == "Lu")


_CAP = r"[%s][\w'’&-]*(?:\.[\w'’&-]+)*" % _upper_letters()     # a dot only INSIDE a word (B.Sc, Node.js)
_WORD_RE = re.compile(r"(?<![^\W\d_])%s" % _CAP)
_CAPSEQ_RE = re.compile(r"(?<![^\W\d_])%s(?:[ \t]+(?:(?:of|de|du|des|la|le|for|the|and|et|au|aux|à|&)[ \t]+)?%s)+" % (_CAP, _CAP))






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


_ACTION_VERBS = frozenset(_fold(_v) for _v in _ACTION_VERB_SRC.split())

# A phone number is a contact detail, not a claim: its digit groups are neither years nor numbers.
_PHONE_RE = re.compile(
    r"(?<![\w])(?:\+?\d{1,2}[ .\-\u00a0]?)?(?:\(\d{3}\)|\d{3})[ .\-\u00a0]?\d{3}[ .\-\u00a0]?\d{4}(?!\d)")
# The same outside North America: "06 12 34 56 78", "+49 30 1234567", "0151-2345678". A leading + or 0, then digit groups
# split by space/dot/hyphen. Only 8+ digits in 2+ groups (or a + prefix) count as a number, so "300 staff", "840 ms",
# "1 500 000" (no leading 0) and "2019 - 2021" are never read as one.
_PHONE_GEN_RE = re.compile(r"(?<![\w.,])(?:\+\d{1,3}|0)(?:[ .\-\u00a0]?\(?\d{1,8}\)?)+(?!\d)")


def _blank_phones(line: str) -> str:
    """`line` with every phone number replaced by spaces (same length: spans carry over)."""
    line = _PHONE_RE.sub(lambda m: " " * len(m.group(0)), line)

    def generic(m: re.Match[str]) -> str:
        t = m.group(0)
        digits = len(re.sub(r"\D", "", t))
        groups = len(re.findall(r"\d+", t))
        return " " * len(t) if digits >= 8 and (t.startswith("+") or groups >= 2) else t
    return _PHONE_GEN_RE.sub(generic, line)
_NAME_SUFFIX_RE = re.compile(r"\b(?:inc|ltee|ltd|corp|llc|sa|sas|gmbh)\b")


def _name_norm(s: str) -> str:
    """Name comparison form: folded, punctuation dropped, company suffixes
    (Inc., Ltée, Corp., LLC, SA, SAS, GmbH ...) removed, single spaces, padded."""
    s = re.sub(r"[^\w&' ]", " ", _fold(s))
    s = _NAME_SUFFIX_RE.sub(" ", s)
    return " " + re.sub(r"\s+", " ", s).strip() + " "


def _clean_word(w: str) -> str:
    """Drop a possessive ('s), an elision (French J’, L’; Italian dell’, all’) and trailing punctuation."""
    w = re.sub(r"['’]s$", "", w.rstrip(".,'’&-"))
    return _ELISION_RE.sub("", w)


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


def _month_years(text: str) -> set[tuple[int, int]]:
    f = _fold(text)
    out = {(_MONTHS[m.group(1)], int(m.group(2))) for m in _MONTH_YEAR_RE.finditer(f)}
    for m in _RANGE_MY_RE.finditer(f):
        m1, m2, yr = _MONTHS[m.group(1)], _MONTHS[m.group(2)], int(m.group(3))
        out.add((m1, yr - 1 if m1 > m2 else yr))
    for m in _NUM_MY_RE.finditer(f):
        y, mo = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
        out.add((int(mo), int(y)))
    return out


_ALNUM_TOKEN_RE = re.compile(r"(?<![\w.])(?=[^\W\d_]*\d)(?=\d*[^\W\d_])[\w]{2,}(?![\w.])")


def _guess_lang(text: str) -> str | None:
    """'en' or 'fr' by stopword counts; None when unclear, too short, or another language (see _detect_lang)."""
    code = _detect_lang(text)[0]
    return code if code in ("en", "fr") else None


def _not_checked_text(label: str, check: str) -> str:
    """What follows `INFO  ` on the one line a language-dependent check prints instead of guessing."""
    return f"not checked for {label}: {check} — the agent compares this by hand (see step 6 list)"


def _not_checked(label: str, check: str) -> str:
    """The INFO line itself (references/steps/6-verify.md lists what the agent then compares)."""
    return "INFO  " + _not_checked_text(label, check)


def check_facts_coverage(pdf_text: str, facts_text: str) -> list[str]:
    """Rule 1, mechanically. WARN, never FAIL: a figure or name absent from the facts file is a prompt to confirm it
    with the candidate, and the facts file may be written in prose the patterns cannot read. When the CV and the
    facts file are in different languages, or in one this file has no word lists for, the name check is replaced
    by an INFO line saying what was not checked (the agent compares by hand), not by guesses.

    WARN lines for every year, month+year, number,
    capitalized name (multi-word, single mid-sentence word, acronym) in the CV
    text that the facts file does not contain. Case, accents, whitespace, number
    formats and company suffixes are normalized; phone numbers are ignored; a
    sentence-start ACTION VERB is the only word dropped from a name's head."""
    facts = _fold(facts_text)
    facts_n = _name_norm(facts_text)
    facts_years = set(_YEAR_RE.findall(facts))
    facts_years |= {str(int(m.group(3)) - 1) for m in _RANGE_MY_RE.finditer(facts)
                    if _MONTHS[m.group(1)] > _MONTHS[m.group(2)]}      # "déc. – janv. 2020" opens in 2019
    facts_my = _month_years(facts_text)
    facts_nums = _num_values(facts_text)
    found: dict[str, None] = {}
    (cf, nf), (cc, nc) = _detect_lang(facts_text), _detect_lang(pdf_text)
    lf, lc = (cf if cf in ("en", "fr") else None), (cc if cc in ("en", "fr") else None)
    foreign = [n for c, n in ((cc, nc), (cf, nf)) if c not in (None, "en", "fr")]
    cross = (lf is not None and lc is not None and lf != lc) or bool(foreign)
    facts_w = " " + re.sub(r"[\W_]+", " ", facts) + " "    # words only: "d'IP" holds "ip"
    info = ([f"INFO  facts file is {_LANG_NAMES[lf]}, CV is {_LANG_NAMES[lc]}: coverage limited to dates, "
             "numbers and acronyms — names and titles are not cross-checked across languages"]
            if cross and lf and lc else [])
    if foreign:     # German, Spanish, Cyrillic...: no verb or heading lists, so capitalised names cannot be judged
        info = [_not_checked(" and ".join(dict.fromkeys(foreign)), "capitalised names and titles against the facts file")]
    for raw in pdf_text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        line = _blank_phones(line)
        if not line.strip():
            continue
        fl = _fold1(line)                   # same length as `line`: spans carry over
        blank: list[tuple[int, int]] = []
        for m in _MONTH_YEAR_RE.finditer(fl):
            blank.append(m.span())
            if (_MONTHS[m.group(1)], int(m.group(2))) not in facts_my:
                found[line[m.start():m.end()]] = None
        for m in _NUM_MY_RE.finditer(fl):
            blank.append(m.span())
            y, mo = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
            if (int(mo), int(y)) not in facts_my:
                found[m.group(0)] = None
        for m in _YEAR_RE.finditer(fl):
            blank.append(m.span())
            if m.group(0) not in facts_years:
                found[m.group(0)] = None
        # dates feed neither the number nor the name scan
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
        if line.isupper():
            continue                        # section headings
        if cross:
            # language-independent tokens only: acronyms and letter+digit tokens (S3, EC2)
            for m in _WORD_RE.finditer(rest):
                w = _clean_word(m.group(0))
                if (w.isupper() and len(w) >= 2 and w.isalpha() and _fold(w) not in _HEADING_WORDS
                        and _name_norm(w) not in facts_n
                        and f" {_fold(w)} " not in facts_w):
                    found[w] = None
            for m in _ALNUM_TOKEN_RE.finditer(rest):
                if f" {_fold(m.group(0))} " not in facts_w:
                    found[m.group(0)] = None
            continue

        def at_start(pos: int, rest: str = rest) -> bool:
            before = rest[:pos].strip()
            return not before or before[-1] in ".:;!?•·▪–—-|"

        def known(name: str) -> bool:
            parts = re.split(r"\s+(?:and|et|&|à|au|aux)\s+", name.strip())   # "Python and SQL": each side
            if all(_name_norm(x).strip() == "" or _name_norm(x) in facts_n for x in parts):
                return True
            # every word is a known word ("API NestJS" vs facts "NestJS ... API"): no new name
            ws = [x for x in re.split(r"[ \t]+", name) if x]
            return len(ws) > 1 and all(_name_norm(x).strip() == "" or _name_norm(x) in facts_n
                                       or _fold(x) in _LINKS for x in ws)

        covered: list[tuple[int, int]] = []
        for m in _CAPSEQ_RE.finditer(rest):
            covered.append(m.span())
            words = [_clean_word(x) for x in re.split(r"[ \t]+", m.group(0))]
            tok = " ".join(words)
            if all(_fold(w) in _HEADING_WORDS for w in words):
                continue
            if known(tok):                  # the WHOLE sequence first
                continue
            if at_start(m.start()) and _fold(words[0]) in _ACTION_VERBS:
                tail = words[1:]            # "Built Python services": drop the verb only
                while tail and _fold(tail[0]) in _LINKS:
                    tail = tail[1:]
                tok = " ".join(tail)
                if not tok or known(tok) or _fold(tok) in _HEADING_WORDS:
                    continue
            found[tok] = None
        for m in _WORD_RE.finditer(rest):
            if any(i <= m.start() < j for i, j in covered):
                continue
            w = _clean_word(m.group(0))
            if not w or not w[0].isupper():
                continue
            f = _fold(w)
            if f in _HEADING_WORDS or known(w):
                continue
            if w.isupper() and len(w) >= 2 and w.isalpha():
                found[w] = None             # acronym: UQAM, AWS — anywhere in the line
            elif (len(w) >= 3 and not w.isupper() and not at_start(m.start())
                  and f not in _ACTION_VERBS):
                found[w] = None             # single name mid-sentence
    return info + [f'WARN  not in facts file: "{t}" — remove it or confirm it with the candidate (rule 1)'
                   for t in found]


_BANNER_RE = re.compile(r"^\s*//\s*FAMILY:\s*([\w-]+)", re.M)
_HEADER1_RE = re.compile(r"//\s*vitae:\s*pages=(\d+)(?:\s+fill=(\d+)-(\d+))?")


def _drawn_fill(typ: str) -> tuple[tuple[int, int] | None, list[str]]:
    """The fill target pick_design.py drew, and WARN lines about the header.

    The `// vitae:` header is editable, so it is NOT the authority when the family
    is known (banner `// FAMILY:` or families/ directory): the target is that
    family's `page.fill` in pick_design.FAMILIES, whatever the header says. The
    header is used only when no family is known, and only on line 1."""
    try:
        with open(typ, encoding="utf-8") as fh:
            first = fh.readline()
            head = first + "".join(fh.readline() for _ in range(2))
    except OSError:
        return None, []
    hm = _HEADER1_RE.match(first.strip())
    header = (int(hm.group(2)), int(hm.group(3))) if hm and hm.group(2) else None
    family = family_from_path(typ)
    table: tuple[int, int] | None = None
    if family:
        import pick_design as pd
        fam = pd.FAMILIES.get(family)
        if fam:
            lo, hi = fam["page"]["fill"].split("-")
            table = (int(lo), int(hi))
    if table is None:
        return header, []
    warns = []
    if _BANNER_RE.search(head) and header != table:
        got = (f"{header[0]}-{header[1]}" if header
               else "no `// vitae: pages=N fill=A-B` header on line 1")
        warns.append(f"WARN  cv.typ header disagrees with family {family}: {got}; the drawn fill "
                     f"target is {table[0]}-{table[1]} (pick_design.FAMILIES) and is what is "
                     "enforced — restore the header, do not edit the target")
    return table, warns


def _fill_args_ok(*vals: str | None) -> bool:
    """FAIL line + False when a fill/page argument is not a plain integer."""
    for v in vals:
        if v is not None and not re.fullmatch(r"\d+", v):
            print(f"FAIL  fill args must be integers (got {v!r}) — e.g. verify.py cv.typ 1 94 96")
            return False
    return True


# Adjacent, not merely on the same line: prose such as "coursework at Polytechnique Exemple, I am
# completing a bachelor's degree" says what it is and must not trip the check.
DEGREE_NEAR_RE = re.compile(
    "(?:%s)[^,;]{0,30}?(?:%s)|(?:%s)[^,;]{0,30}?(?:%s)"
    % (DEGREE_RE.pattern, INCOMPLETE_RE.pattern,
       INCOMPLETE_RE.pattern, DEGREE_RE.pattern), re.I)


def check_degree_tokens(txt: str) -> list[str]:
    """Lines pairing a degree token with a non-completion marker within 30 chars. The caller WARNs: an ATS
    (Eightfold) read "B.Eng. program" as a degree held (references/ats.md)."""
    return [l.strip() for l in txt.split("\n") if DEGREE_NEAR_RE.search(l)]


# A bullet marker set as a CHARACTER survives into the ATS's text (measured:
# Banque Nationale showed it alone on a line above the bullet; Eightfold printed
# it literally). Markers must be drawn (references/ats.md). Private-use code
# points are what icon fonts (Font Awesome etc.) emit. Leading position only:
# an inline separator or a prose dash is not what this catches.
BULLET_CHAR_RE = re.compile("^[\u25c6\u25c7\u2022\u25aa\u25ab\u25ba\u25cf\u25a0\u25e6\u2023\u2219\u27a2\ue000-\uf8ff]")


SUMMARY_REPEAT_MIN = 2   # distinct repeated figures from which the WARN fires (one is a headline metric)
_FIG_MASK = re.compile(
    r"\b\d\.\d{1,2}\s*/\s*\d\.\d{1,2}\b"                              # GPA 3.6/4.3
    r"|\b" + _MONTH_WORDS + r"\s+\d{4}\b"                                     # May 2025
    r"|\b\d{1,2}[/.-]\d{4}\b|\b\d{4}[/.-]\d{1,2}(?:[/.-]\d{1,2})?\b"    # 05/2025, 2025-05-01
    r"|\+?\d?[ .-]?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b", re.I)               # phone
_FIG_RE = re.compile(
    r"(?<![\w.])([$€£]?)(\d+(?:[,. \u00a0]\d{3})*(?:[.,]\d+)?)\s?"
    r"(%|\+|[kKmM]\b|x\b|ms\b|sec\w*|min\w*|h\b|hours?\b|days?\b|GB\b|MB\b|TB\b|"
    r"users?\b|people\b|stars?\b|clients?\b|requests?\b)?", re.I)


def _figures(text: str) -> set[float]:
    """Distinct qualifying figures of a text: numbers of 2+ digits, or with a unit/%/k/+/currency. Years
    1950-2100, GPAs, dates and phone numbers do not count; "40 minutes" and "40 min" are both 40."""
    text = _FIG_MASK.sub(" ", text)
    out: set[float] = set()
    for m in _FIG_RE.finditer(text):
        cur, raw, unit = m.group(1), m.group(2), (m.group(3) or "").lower()
        raw = re.sub(r"(?<=\d)[ \u00a0](?=\d{3}(?!\d))", "", raw)
        raw = re.sub(r",(?=\d{3}(?!\d))", "", raw).replace(",", ".")
        try:
            v = float(raw)
        except ValueError:
            continue
        if not unit and not cur and v == int(v) and 1950 <= v <= 2100:
            continue
        digits = len(re.sub(r"\D", "", raw.split(".")[0]))
        if digits < 2 and not unit and not cur:
            continue
        out.add(v * (1000 if unit == "k" else 1_000_000 if unit == "m" else 1))
    return out


_SUMMARY_TITLE_RE = re.compile(_SUMMARY_TITLES, re.I)
_EXPERIENCE_TITLE_RE = re.compile(_EXPERIENCE_TITLES, re.I)
def check_summary_repeats(src: str) -> list[str]:
    """WARN line when the summary/profile section repeats SUMMARY_REPEAT_MIN+ figures that the experience /
    project sections already state (padding by repetition). A WARN because one repeated figure can be a deliberate
    headline metric. No summary or no experience section: silent."""
    secs = [(t, _typst_prose(b)) for t, b in _section_bodies(_strip_typst_comments(src))]
    summ = [b for t, b in secs if _SUMMARY_TITLE_RE.search(t) and not _EXPERIENCE_TITLE_RE.search(t)]
    rest = [b for t, b in secs if _EXPERIENCE_TITLE_RE.search(t)]
    if not summ or not rest:
        return []
    shared = sorted(_figures(" ".join(summ)) & _figures(" ".join(rest)))
    if len(shared) < SUMMARY_REPEAT_MIN:
        return []
    lst = ", ".join(f"{v:g}" for v in shared)
    return [f"WARN  the summary repeats {len(shared)} figures already in the bullets ({lst}) — repeating facts to fill the "
            "page is padding (SKILL.md anti-filler clause). State the positioning in the summary instead of the "
            "metrics, or cut the summary and add a real fact"]


ENTRY_REPEAT_MIN = 2        # content words a bullet must share with a descriptor segment ...
ENTRY_REPEAT_RATIO = 0.5    # ... and the share of that segment's content words it covers
_PROJECT_TITLE_RE = re.compile(_PROJECT_TITLES, re.I)


def _entry_words(text: str) -> set[str]:
    """Content words of a line: lowercased, markup and stop words dropped, plural -s folded."""
    text = re.sub(r"\b[dlqnsjmtc]['\u2019]", " ", re.sub(r"[*_`]", " ", text).lower())
    words = re.findall(r"[^\W\d_][\w+#.-]*", text)
    return {w.rstrip(".-").removesuffix("s") if len(w) > 3 else w for w in words if w not in _ENTRY_STOP and len(w) > 1}


def entry_repeat_hits(src: str) -> list[tuple[str, str, str, float]]:
    """(entry, descriptor, bullet, share) for each bullet that restates a descriptor segment of its own entry."""
    hits = []
    for t, b in _section_bodies(_strip_typst_comments(src)):
        if not _EXPERIENCE_TITLE_RE.search(t):
            continue
        for title, segs, bullets in _entries(b, bool(_PROJECT_TITLE_RE.search(t))):
            bws = [(bl, _entry_words(_typst_prose(bl))) for bl in bullets]
            for seg in segs:
                dw = _entry_words(_typst_prose(seg))
                if len(dw) < ENTRY_REPEAT_MIN:
                    continue
                for bl, bw in bws:
                    n = len(dw & bw)
                    if n >= ENTRY_REPEAT_MIN and n / len(dw) >= ENTRY_REPEAT_RATIO:
                        hits.append((title, seg, bl, n / len(dw)))
    return hits


def check_entry_repeats(src: str) -> list[str]:
    """WARN lines for a bullet that restates its own entry's descriptor / subtitle line (padding by repetition);
    one line per bullet, naming the descriptor it restates most."""
    best: dict[tuple[str, str], tuple[str, float]] = {}
    for t, seg, bl, share in entry_repeat_hits(src):
        if share > best.get((t, bl), ("", 0.0))[1]:
            best[(t, bl)] = (seg, share)
    return [f'WARN  entry "{t}": the bullet "{bl[:70]}" restates the descriptor "{seg}" — each fact once per entry '
            "(SKILL.md anti-filler clause); give the bullet a new fact (scope, outcome, figure) or cut it"
            for (t, bl), (seg, _) in best.items()]


# Entry-location WARN: a place name in an entry's descriptor segments that is sourced on ANOTHER facts.md item but
# not on the item describing this entry (run 24: "Laval", from the cashier job, on the DEC).
_LOC_GENERIC = frozenset(_fold(w) for w in _LOC_GENERIC_SRC.split())
_LOC_JOIN = frozenset(_LOC_JOIN_SRC.split())
_LOC_SKIP = _LOC_GENERIC | _LOC_JOIN
_HEADING_RE = re.compile(r"^(#{1,6})\s")
_BULLET0_RE = re.compile(r"^[-*+]\s")


def _facts_items(facts_text: str) -> list[tuple[int, int, str]]:
    """facts.md items as (first line, end line, text): a heading with everything under it up to the next heading of the
    same or a higher level, and a top-level bullet with its indented lines. Each item's text also carries the heading
    lines above it (its parent titles), so a place given in a parent title counts for the items under it."""
    lines = facts_text.splitlines()
    heads: list[tuple[int, int]] = []     # (level, line) of the headings open at the current line
    out: list[tuple[int, int, str]] = []
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m:
            lvl = len(m.group(1))
            heads = [h for h in heads if h[0] < lvl]
            end = next((j for j in range(i + 1, len(lines))
                        if (hm := _HEADING_RE.match(lines[j])) and len(hm.group(1)) <= lvl), len(lines))
            parents = [lines[h[1]] for h in heads]
            out.append((i, end, "\n".join(parents + lines[i:end])))
            heads.append((lvl, i))
        elif _BULLET0_RE.match(line):
            end = next((j for j in range(i + 1, len(lines)) if _HEADING_RE.match(lines[j]) or _BULLET0_RE.match(lines[j])), len(lines))
            out.append((i, end, "\n".join([lines[h[1]] for h in heads] + lines[i:end])))
    return out


def _padded_words(s: str) -> str:
    """Folded words joined by single spaces, with one at each end, so `" a b " in text` matches whole words only."""
    return " " + " ".join(re.findall(r"\w+", _fold(s).replace("-", " "))) + " "


def check_entry_locations(src: str, facts_text: str) -> list[str]:
    """WARN lines for an entry whose descriptor (location) segments name a proper noun that the facts.md item
    describing that entry never mentions although ANOTHER part of facts.md does (a place borrowed from another entry;
    a word absent from facts.md altogether is check_facts_coverage's). The item is the smallest heading or top-level
    bullet found by the entry's title and org (title + org, else title, else a single org item), with its parent
    titles; no identifiable item, silent, and a facts.md in prose or a table has no items, so silent too. Only short
    Title Case segments count (not descriptions); generic and job-status words, provinces, countries and short
    acronyms are never flagged; accents and case are ignored. Date-bearing segments are dropped, the rest of the
    argument is checked. Project sections are skipped (their second argument is a description)."""
    items = [(i, e, _padded_words(t)) for i, e, t in _facts_items(facts_text)]
    whole = _padded_words(facts_text)
    out: list[str] = []
    for sec, body in _section_bodies(_strip_typst_comments(src)):
        if _PROJECT_TITLE_RE.search(sec):
            continue
        for m in _ENTRY_CALL_RE.finditer(body):
            strs, _ = _call_strings(body, m.end())
            if len(strs) < 3:
                continue
            title, org = _padded_words(strs[0]), _padded_words(strs[1])
            found = [x for x in items if title.strip() and title in x[2] and org in x[2]]
            found = found or [x for x in items if title.strip() and title in x[2]]
            if not found:
                found = [x for x in items if org.strip() and org in x[2]]
                found = found if len({(x[0], x[1]) for x in found}) == 1 else []
            # keep the most specific items: drop one that encloses another match
            found = [x for x in found if not any(y is not x and x[0] <= y[0] and y[1] <= x[1] and (y[0], y[1]) != (x[0], x[1]) for y in found)]
            if not found:
                continue
            item = [x[2] for x in found]
            own = title + org
            missing: list[str] = []
            for a in strs[2:]:
                for seg in re.split(r"\s[·|]\s|,\s*", a):
                    if _DATE_ARG_RE.search(seg):
                        continue
                    words = re.findall(r"[^\W\d_][\w'\u2019-]*", seg)
                    if len(words) > 4 or any(not x[0].isupper() and _fold(x) not in _LOC_SKIP for x in words):
                        continue    # a place name is short and Title Case; "Back-end API development" is a description
                    for word in words:
                        if not word[0].isupper() or (len(word) <= 3 and word.isupper()) or _fold(word) in _LOC_SKIP:
                            continue
                        pw = _padded_words(word)
                        if word not in missing and pw in whole and pw not in own and not any(pw in w for w in item):
                            missing.append(word)
            out.extend(f'WARN  entry "{strs[0]}": the place "{w}" is not in the facts file item for this entry but is in another one — source this '
                       "place on this entry in facts.md or remove it; do not borrow it from another entry (rule 1)" for w in missing)
    return out


def check_bullet_chars(txt: str) -> list[str]:
    """Extracted lines that start with a bullet or private-use character (the caller WARNs; see BULLET_CHAR_RE)."""
    return [l.strip() for l in txt.split("\n") if BULLET_CHAR_RE.match(l.strip())]


def family_from_path(path: str) -> str | None:
    """The family this CV is built from, for the DEVICELESS exemption and the drawn fill target (_drawn_fill).

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
            head = "".join(fh.readline() for _ in range(3))   # line 1 may be the `// vitae:` header
        m = re.search(r"^\s*//\s*FAMILY:\s*([\w-]+)", head, re.M)
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


@overload
def word_boxes(pdf: str, with_text: Literal[False] = ...) -> list[list[Box]] | None: ...
@overload
def word_boxes(pdf: str, with_text: Literal[True]) -> list[list[WordBox]] | None: ...
@overload
def word_boxes(pdf: str, with_text: bool) -> list[list[Box]] | list[list[WordBox]] | None: ...
def word_boxes(pdf: str, with_text: bool = False) -> list[list[Box]] | list[list[WordBox]] | None:
    """Per-page list of pdftotext word boxes (x0, y0, x1, y1) in PDF points.

    With `with_text` each item is ((x0, y0, x1, y1), word) instead.

    Returns None (not a list of empties) when pdftotext is missing or fails,
    so callers can tell "no text found" from "couldn't check" and degrade to
    the ink-only detector rather than treating every row as furniture.
    """
    pages = _bbox_pages(pdf)
    if pages is None:
        return None
    if with_text:
        return [items for _, _, items in pages]
    return [[b for b, _ in items] for _, _, items in pages]


def _bbox_pages(pdf: str) -> list[tuple[float, float, list[WordBox]]] | None:
    """[(page_w, page_h, [((x0, y0, x1, y1), word), ...]), ...] from
    `pdftotext -bbox` (PDF points), or None when pdftotext is missing/fails.
    With the pdfium backend the words are built from pypdfium2's character boxes."""
    if pdf_backend() == "pdfium":
        return _pdfium_bbox_pages(pdf)
    try:
        r = subprocess.run(["pdftotext", "-bbox", pdf, "-"],
                            capture_output=True, text=True)
    except (FileNotFoundError, OSError):
        return None
    if r.returncode != 0:
        return None
    pages = []
    for pg in r.stdout.split("<page ")[1:]:
        dim = re.match(r'width="([\d.]+)" height="([\d.]+)"', pg)
        items = [((float(m[1]), float(m[2]), float(m[3]), float(m[4])), html.unescape(m[5]))
                 for m in re.finditer(r'<word xMin="([-\d.]+)" yMin="([-\d.]+)" '
                                      r'xMax="([-\d.]+)" yMax="([-\d.]+)">([^<]*)</word>', pg)]
        pages.append((float(dim[1]) if dim else 0.0, float(dim[2]) if dim else 0.0, items))
    return pages


def _reading_order(words: list[WordBox]) -> list[WordBox]:
    """pdftotext's reading order, approximated: pdfium lists words in content-stream
    order, poppler in layout order. Words on one baseline form a line, cut where the gap
    exceeds 1.5 x the box height (a right-flushed date is another piece); a piece joins
    every piece directly above it that it overlaps in x (one text block); blocks read by
    row then x, lines within a block top to bottom, left to right. A right-flushed date
    joins the first line under it that overlaps its x-range, up to the next dated head, so
    it is read in place only then, which is the behaviour `check_date_adjacency` measures."""
    if not words:
        return words
    rows: list[list[int]] = []
    for i in sorted(range(len(words)), key=lambda k: (words[k][0][1] + words[k][0][3]) / 2):
        wb = words[i][0]
        yc, hh = (wb[1] + wb[3]) / 2, wb[3] - wb[1]
        if rows:
            rb = [words[k][0] for k in rows[-1]]
            ryc = sum((q[1] + q[3]) / 2 for q in rb) / len(rb)
            if abs(yc - ryc) <= 0.4 * min(hh, min(q[3] - q[1] for q in rb)):
                rows[-1].append(i)
                continue
        rows.append([i])
    pieces: list[list[int]] = []                       # word indexes, left to right, one row each
    piece_row: list[int] = []
    for r, row in enumerate(rows):
        cur: list[int] = []
        for i in sorted(row, key=lambda k: words[k][0][0]):
            if cur:
                prev = words[cur[-1]][0]
                if words[i][0][0] - prev[2] > 1.5 * min(prev[3] - prev[1], words[i][0][3] - words[i][0][1]):
                    pieces.append(cur)
                    piece_row.append(r)
                    cur = []
            cur.append(i)
        pieces.append(cur)
        piece_row.append(r)
    geo = [(min(words[k][0][0] for k in pc), max(words[k][0][2] for k in pc),
            min(words[k][0][1] for k in pc), max(words[k][0][3] for k in pc)) for pc in pieces]
    parent = list(range(len(pieces)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for lo in range(len(pieces)):
        for up in range(len(pieces)):
            if piece_row[up] == piece_row[lo] - 1 and geo[up][0] < geo[lo][1] and geo[lo][0] < geo[up][1]:
                parent[find(up)] = find(lo)
    # A piece with another piece to its left on its row (a right-flushed date beside its role) is
    # read after the lines of its entry, at any distance, unless one of them under it overlaps its
    # x-range: then it is read in place. Measured on poppler: role, org, date at every head-to-org
    # gap from 4 to 200 pt and heads of 9 to 18 pt, so there is no distance cutoff. The lines of
    # its entry stop at the next row that holds a right-flushed piece (the next dated head).
    side = [n for n in range(len(pieces)) if any(piece_row[m] == piece_row[n] and geo[m][0] < geo[n][0]
                                                 for m in range(len(pieces)))]
    for n in side:
        stop = min((piece_row[m] for m in side if piece_row[m] > piece_row[n]), default=len(rows))
        under = [m for m in range(len(pieces)) if piece_row[n] < piece_row[m] < stop and m not in side
                 and geo[m][0] < geo[n][1] and geo[n][0] < geo[m][1]]
        if under:
            parent[find(n)] = find(min(under, key=lambda m: (piece_row[m], geo[m][0])))
    blocks: dict[int, list[int]] = {}
    for n in range(len(pieces)):
        blocks.setdefault(find(n), []).append(n)
    # by row (the rows are clustered on the baseline with a tolerance), not by the box top: a bold role
    # and a regular date of one size differ by a point or two of box top
    order = sorted(blocks.values(), key=lambda bl: (min(piece_row[n] for n in bl), min(geo[n][0] for n in bl)))
    return [words[k] for bl in order for n in sorted(bl, key=lambda n: (piece_row[n], geo[n][0])) for k in pieces[n]]


_pdfium_error: str | None = None     # why the last `_pdfium_bbox_pages` returned None


def _boxes_unavailable() -> str:
    """Why `word_boxes` returned None, for the WARN that says a gate was skipped."""
    if pdf_backend() == "pdfium":
        return f"pypdfium2 could not read the PDF ({_pdfium_error or 'unknown error'})"
    return "pdftotext not found (install poppler-utils)"


def _pdfium_bbox_pages(pdf: str) -> list[tuple[float, float, list[WordBox]]] | None:
    """`_bbox_pages` on pypdfium2: words are runs of non-space characters, each box the union of its loose character
    boxes (top-down, like pdftotext). LOOSE boxes, because pdfium's tight ones are ink extents and vary with the
    letters (a word without descenders is shorter), while the loose ones follow the font's ascent and descent like
    poppler's word boxes. Measured on the shipped templates against `pdftotext -bbox`: x within 0.8 pt, y within ~1
    pt for most fonts; tight boxes padded by 2.5 pt per side were off by up to 10 pt and cut one hard-edge line out
    of its band, a FAIL poppler does not give."""
    try:
        doc = _pdfium_doc(pdf)
        pdfium_raw: Any = importlib.import_module("pypdfium2.raw")
        pages: list[tuple[float, float, list[WordBox]]] = []
        for pg in doc:
            pw, ph = pg.get_size()
            tp = pg.get_textpage()
            text = tp.get_text_range() if tp.count_chars() else ""
            items: list[WordBox] = []
            chars: list[str] = []
            box: list[float] = []
            size: list[float] = [0.0]

            def flush(chars: list[str] = chars, box: list[float] = box, items: list[WordBox] = items,
                      size: list[float] = size, ph: float = ph) -> None:
                if chars and box:
                    # a mark pdfium splits off a word (Arabic dots, accents) has a sliver of a box:
                    # never under the font size, like the line it belongs to in poppler's boxes
                    grow = max(0.0, size[0] - (box[3] - box[1])) / 2
                    items.append(((box[0], ph - box[3] - grow, box[2], ph - box[1] + grow), "".join(chars)))
                chars.clear()
                box.clear()
                size[0] = 0.0
            idx = 0
            for ch in text:
                i, idx = idx, idx + (2 if ord(ch) > 0xFFFF else 1)   # pdfium counts UTF-16 units
                if ch.isspace() or ord(ch) < 0x20:
                    flush()
                    continue
                l, b, r, t = tp.get_charbox(i, loose=True)
                if r <= l or t <= b:
                    continue
                chars.append(ch)
                size[0] = max(size[0], float(pdfium_raw.FPDFText_GetFontSize(tp, i)))
                if box:
                    box[:] = [min(box[0], l), min(box[1], b), max(box[2], r), max(box[3], t)]
                else:
                    box[:] = [l, b, r, t]
            flush()
            pages.append((float(pw), float(ph), _reading_order(items)))
        return pages
    except Exception as e:
        global _pdfium_error
        _pdfium_error = f"{type(e).__name__}: {e}"[:120]
        return None


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


# ---------- hidden text: every extracted word must be visible ----------

# Calibrated on the 29 templates and 294 palette renders (CHANGELOG): weakest legitimate contrast 4.55:1, smallest
# legitimate box 5.49 pt (a superscript).
HIDDEN_PPI = 150          # own raster: tiny legit text needs more than the 90 ppi fill scan
HIDDEN_MIN_BOX_PT = 4.0   # word-box height floor (pt). Legit: 7.98 for 8.5pt text, 5.49 for a
                          # superscript in 7.5-9pt body. Hidden-text intent is invisibility, not
                          # small print: between 4.0 and the smallest legit box only the ink counts.
HIDDEN_FAIL_RATIO = 1.5   # WCAG contrast ratio of the strongest pixel in a word's box against the
HIDDEN_WARN_RATIO = 3.0   # box background: below 1.5 unreadable (FAIL), below 3 barely visible (WARN)
HIDDEN_PAD_PX = 1         # px added around each box (single-stem words like "i", "l", "二")
# Metadata gate (check_pdf_metadata): a Keywords field over KEYWORD_MAX_TERMS terms, or any other field over
# META_MAX_CHARS characters, is WARNed as stuffing.
KEYWORD_MAX_TERMS = 15
META_MAX_CHARS = 200


def _pdfium_render(pdf: str, ppi: int, gray: bool = False, pages: Sequence[int] | None = None) -> list[Image.Image]:
    """One PIL image per page (1-based `pages`, default all) rendered by pypdfium2, cropped to
    the size pdftoppm gives (pdfium rounds a page's pixel size up one row more often)."""
    doc = _pdfium_doc(pdf)
    scale = ppi / 72.0
    out: list[Image.Image] = []
    for n in (pages if pages is not None else range(1, len(doc) + 1)):
        pg = doc[n - 1]
        pw, ph = pg.get_size()
        im = pg.render(scale=scale, grayscale=gray).to_pil()
        want = (math.ceil(pw * scale - 1e-3), math.ceil(ph * scale - 1e-3))
        if im.size[0] > want[0] or im.size[1] > want[1]:
            im = im.crop((0, 0, min(im.size[0], want[0]), min(im.size[1], want[1])))
        out.append(im.convert("L" if gray else "RGB"))
    return out


def _render_pages_png(pdf: str, tmp: str, ppi: int = HIDDEN_PPI) -> list[str]:
    """PNG per page via pdftoppm (poppler) or pypdfium2, or [] when neither is there."""
    if pdf_backend() == "pdfium":
        paths = []
        for n, im in enumerate(_pdfium_render(pdf, ppi), 1):
            paths.append(os.path.join(tmp, f"h-{n}.png"))
            im.save(paths[-1])
        return paths
    if not shutil.which("pdftoppm"):
        return []
    subprocess.run(["pdftoppm", "-r", str(ppi), "-png", pdf, os.path.join(tmp, "h")],
                   capture_output=True, text=True)
    return sorted(glob.glob(os.path.join(tmp, "h*.png")),
                  key=lambda f: int(cast(re.Match[str], re.search(r"(\d+)\.png$", f)).group(1)))


def pdf_unreadable(pdf: str) -> bool:
    """True when the PDF backend cannot open `pdf` (not a PDF, corrupt): header, then a page count."""
    try:
        with open(pdf, "rb") as fh:
            if b"%PDF" not in fh.read(1024):
                return True
        backend = pdf_backend()
        return backend is not None and not count_pages(pdf, backend)
    except Exception:
        return True


def render_pages(pdf: str, out_dir: str, ppi: int) -> list[str]:
    """`<stem>-p<N>.png` per page in out_dir: pypdfium2 when it imports, else pdftoppm.
    Returns the paths, or [] when neither is there."""
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(pdf))[0]
    stale = re.compile(r"%s-p\d+(?:-(?:fill|icon)\d+)?\.png" % re.escape(stem))

    def drop_stale() -> None:        # a longer previous render, or one with --crops, must not leave its pages or crops behind
        for f in os.listdir(out_dir):
            if stale.fullmatch(f):
                os.remove(os.path.join(out_dir, f))
    if _importable("pypdfium2"):
        paths = []
        ims = _pdfium_render(pdf, ppi)
        drop_stale()
        for n, im in enumerate(ims, 1):
            paths.append(os.path.join(out_dir, f"{stem}-p{n}.png"))
            im.save(paths[-1])
        return paths
    if not shutil.which("pdftoppm"):
        return []
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", str(ppi), "-png", pdf, os.path.join(tmp, "p")],
                       capture_output=True, text=True)
        paths = []
        drop_stale()
        for f in sorted(glob.glob(os.path.join(tmp, "p*.png")),
                        key=lambda f: int(cast(re.Match[str], re.search(r"(\d+)\.png$", f)).group(1))):
            n = int(cast(re.Match[str], re.search(r"(\d+)\.png$", f)).group(1))
            paths.append(os.path.join(out_dir, f"{stem}-p{n}.png"))
            shutil.move(f, paths[-1])
    return paths


def _page_rasters(pdf: str, ppi: int) -> list[Image.Image]:
    """One RGB PIL image per page, the way render_pages picks its backend; [] when neither is there."""
    if _importable("pypdfium2"):
        return _pdfium_render(pdf, ppi)
    if not shutil.which("pdftoppm"):
        return []
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", str(ppi), "-png", pdf, os.path.join(tmp, "c")],
                       capture_output=True, text=True)
        files = sorted(glob.glob(os.path.join(tmp, "c*.png")),
                       key=lambda f: int(cast(re.Match[str], re.search(r"(\d+)\.png$", f)).group(1)))
        out = []
        for f in files:
            with Image.open(f) as fh:
                out.append(fh.convert("RGB"))
        return out


def render_crops(pdf: str, out_dir: str) -> tuple[list[str], list[str]]:
    """`<stem>-p<N>-<band>.png` at CROP_PPI for the bands at visual risk (solid fills, icons),
    band = fill1, icon2, ... counted per kind in reading order. At most CROP_CAP per page, fills
    first, then the icons with the most ink. Crops of this stem from an earlier run are removed
    first. Returns (paths, notes naming the bands dropped by the cap)."""
    stem = os.path.splitext(os.path.basename(pdf))[0]
    scan = _page_rasters(pdf, CROP_SCAN_PPI)
    if not scan:
        return [], []
    boxes = word_boxes(pdf)
    big = _page_rasters(pdf, CROP_PPI)
    old_crops = re.compile(r"%s-p\d+-(?:fill|icon)\d+\.png" % re.escape(stem))
    if os.path.isdir(out_dir):
        for f in os.listdir(out_dir):        # a run with fewer bands must not leave the old ones beside it
            if old_crops.fullmatch(f):
                os.remove(os.path.join(out_dir, f))
    paths: list[str] = []
    notes: list[str] = []
    r = CROP_PPI / CROP_SCAN_PPI
    pad = CROP_PAD_IN * CROP_PPI
    for n, (sm, lg) in enumerate(zip(scan, big), 1):
        bands = crop_candidates(sm, boxes[n - 1] if boxes and n <= len(boxes) else None)
        count = {"fill": 0, "icon": 0}
        named = []
        score = {}
        for kind, box, sc in bands:
            count[kind] += 1
            named.append((f"{kind}{count[kind]}", kind, box))
            score[count[kind], kind] = sc
        ranked = [b for b in named if b[1] == "icon"]
        ranked.sort(key=lambda b: -score[int(b[0][4:]), "icon"])
        keep = ([b for b in named if b[1] == "fill"] + ranked)[:CROP_CAP]
        if len(named) > len(keep):
            notes.append(f"NOTE  crops: p.{n} capped at {CROP_CAP}, dropped "
                         + ", ".join(b[0] for b in named if b not in keep))
        for name, _, (x0, y0, x1, y1) in sorted(keep, key=lambda b: (b[2][1], b[2][0])):
            crop = lg.crop((max(0, int(x0 * r - pad)), max(0, int(y0 * r - pad)),
                            min(lg.size[0], int(x1 * r + pad)), min(lg.size[1], int(y1 * r + pad))))
            paths.append(os.path.join(out_dir, f"{stem}-p{n}-{name}.png"))
            crop.save(paths[-1])
    return paths, notes


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
    doc: Any = None
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
                pypdf: Any = importlib.import_module("pypdf")
                md: Any = pypdf.PdfReader(pdf).metadata or {}
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
            pypdf: Any = importlib.import_module("pypdf")
            reader = pypdf.PdfReader(pdf)
            off: list[tuple[int, str]] = []
            tiny: list[tuple[int, str, float, int]] = []
            for pno, pg in enumerate(reader.pages, 1):
                box = pg.cropbox
                x0, y0, x1, y1 = float(box.left), float(box.bottom), float(box.right), float(box.top)
                runs: list[tuple[str, float, float, float]] = []   # (text, x, y, real size)

                def visit(text: str, cm: Any, tm: Any, fd: Any, fs: Any,
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
        return [(Level.WARN, f"hidden-text gate skipped: {_boxes_unavailable()}")]
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
    # INK by default (design.md, "Boundaries carry ink by default"). With no device AT A
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
               "hairline above each section (design.md § Boundaries carry ink "
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


# A list item opens with `-`, `+` or `1.`; its indentation marks where its continuation lines end.
LIST_ITEM_RE = re.compile(r"^(\s*)(?:[-+]|\d+\.)\s")
FORCED_BREAK_RE = re.compile(r"(?<!\\)\\(?:\s|$)|#linebreak\s*\(")


def check_forced_linebreak(src: str) -> list[str]:
    """FAIL messages: a forced line break (`\\ ` or `#linebreak()`) inside a
    bullet / list item. A bullet is one sentence that wraps on its own; a hard
    break mid-bullet leaves a ragged half-line and, in the extraction, splits
    the bullet in two. Source-text check: it needs no PDF, so it runs in every mode.
    A FAIL because the construct is unambiguous in the source, whatever the language."""
    out, indent = [], None
    for n, raw in enumerate(src.split("\n"), 1):
        line = re.sub(r"(?:^|(?<=\s))//.*$", "", raw)   # drop `//` comments, but not a `//` inside a URL
        m = LIST_ITEM_RE.match(line)
        if m:
            indent = len(m.group(1))
        elif indent is not None:
            # the item ends at a blank line or a line indented no deeper than its marker
            if not line.strip() or len(line) - len(line.lstrip()) <= indent:
                indent = None
        if indent is not None and FORCED_BREAK_RE.search(line):
            out.append(f"line {n}: forced line break inside a bullet "
                       f'("{raw.strip()[:50]}") — let the bullet wrap itself; '
                       "split it into two bullets or shorten it")
    return out


TILDE_RE = re.compile(r"(?:^|(?<=[\s\[(*_]))~(?=[0-9A-Za-z])", re.M)


def check_literal_tilde(src: str) -> list[str]:
    """FAIL messages: an unescaped `~` that starts a word in content text
    (`~25 users`, `*~25 users*`). Typst reads it as a non-breaking space, so the
    PDF shows ` 25 users` and the tilde is gone, silently. Comments (line and
    block), "strings", `raw` spans (multi-line too), $math$ and `\\~` are masked
    over the whole file first; the intentional uses (`#cat~:`, `[~#sc]`) sit
    after an identifier or before `#`, so they never match."""
    out = []
    raws = src.split("\n")
    for n, line in enumerate(_mask_non_markup(src).split("\n"), 1):
        if TILDE_RE.search(line):
            out.append(f"line {n}: unescaped `~` in text "
                       f'("{raws[n - 1].strip()[:50]}") — Typst turns it into a non-breaking space; '
                       "write \\~ for a literal tilde")
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


# ---------- auto-tuner: the fill loop, run by bisection instead of by hand ----------

# Why a bisection is valid: raising `leading` pushes every line further down, so the last ink
# row rises monotonically with it, until the last unbreakable section no longer fits and the
# page count jumps. The leading values that keep the expected page count therefore form an
# interval [lo, L*], and the best fill is at its top end. So: bisect for L*, then check the
# fill it produces.
#
# `spacing` moves WITH `leading`, keeping the family's own delta between the two: that delta
# is part of the recipe (a family with a wide paragraph spacing relative to its leading has a
# different rhythm, not just a different density), and tuning them independently would
# silently redesign the family.
#
# If the fill at L* is still under the target, no leading value reaches it: that is the
# anti-filler clause (SKILL.md rule 5) speaking, the content does not honestly fill that
# pagination. The tuner says so instead of inventing a value; the fix is the section gap,
# real content, or a different page count.


def _probe(typ: str, text: str, leading: float, spacing: float, expected: int,
           use_cli: bool, backend: PdfBackend) -> tuple[bool, int | None]:
    """Compile at (leading, spacing); return (pages_ok, fill_pct or None).

    Rewrites `typ` in place on every call: the caller restores the original text."""
    open(typ, "w", encoding="utf-8").write(_write_par(text, leading, spacing))
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "t.pdf")
        ok, _ = compile_pdf(typ, pdf, use_cli)
        if not ok:
            return False, None
        if count_pages(pdf, backend) != str(expected):
            return False, None
        pngs = render_pngs(typ, tmp, use_cli)
        if not pngs:
            return False, None
        m = re.search(r"to (\d+)%", measure_fill.measure(pngs[-1]))
        return True, (int(m.group(1)) if m else None)


# UPWARD CAP. An under-filled page means a fact is missing, not whitespace to inflate. The
# shipped templates use body leading up to 0.96em and paragraph spacing up to 1.075em; the tuner
# never goes above LEADING_CAP or SPACING_CAP (each the shipped maximum plus 15%, CHANGELOG)
# whatever range the caller passes. The downward (over-full) search is not capped.
LEADING_CAP = 1.10     # em; largest shipped body leading 0.96 x 1.15
SPACING_CAP = 1.24     # em; largest shipped paragraph spacing 1.075 x 1.15


def tune(typ: str, expected: int, fmin: int, fmax: int, lo: float | None = None,
         hi: float | None = None, step: float = 0.005) -> int:
    """--tune: bisect `#set par(leading:, spacing:)` in `typ` to the largest rhythm that holds
    `expected` pages, and keep it only if the fill lands in fmin-fmax. Returns the exit code
    (0 won, 1 no value in range, 2 no par line). Any failure restores the original file: a
    value that misses the target is worse than the rhythm the family was designed with."""
    deps_ok, use_cli, backend = preflight()
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
    lo_arg = lo   # kept to tell, on failure, whether the caller already passed a wide range
    lo = l0 * 0.80 if lo is None else lo
    # The default ceiling is relative, but a family with an already-tight
    # leading gets a range too narrow to ever reach the fill target, so the
    # ceiling never sits below 1.10em.
    hi = max(l0 * 1.30, 1.10) if hi is None else hi
    hi_arg = hi
    # the cap on leading is the tighter of the two caps once the family's delta is added to
    # the spacing; never below the current leading, so a family already above it is not forced down
    cap = max(min(LEADING_CAP, SPACING_CAP - delta), l0)
    clamped = hi > cap + 1e-9
    if clamped:
        hi = cap
    lo = min(lo, hi)
    print("tuning %s: leading %.3fem (spacing %+.3fem), searching [%.3f, %.3f], "
          "target %s pages / fill %s-%s%%"
          % (typ, l0, delta, lo, hi, expected, fmin, fmax))
    if clamped:
        print("NOTE  upper bound clamped to %.3fem: the shipped templates never exceed "
              "%.2fem leading (cap %.2f); an under-filled page needs a real fact, "
              "not more air" % (cap, 0.96, LEADING_CAP))
    try:
        ok_lo, fill_lo = _probe(typ, original, lo, lo + delta, expected,
                                use_cli, backend)
        if not ok_lo:
            open(typ, "w", encoding="utf-8").write(original)   # undo the probe
            # the floor failed, so no larger leading can hold the page count either
            print("FAIL  even the floor leading %.3fem does not give %s page(s) "
                  "— either the content is too long for %s page(s), or the search range starts "
                  "too high: try an explicit lower range, e.g. `--tune %s %s %s %s 0.45 1.0` "
                  "(FILL_MIN FILL_MAX LEAD_LO LEAD_HI)"
                  % (lo, expected, expected, typ, expected, fmin, fmax))
            return 1
        best, best_fill = lo, fill_lo
        # The top of the feasible interval is not always the ANSWER: the last value before the
        # page breaks can overshoot fmax (the fill target has a ceiling too: ink must not reach
        # into the bottom margin). So remember the largest probe that landed INSIDE the target
        # and prefer it over the interval's top end.
        in_target = None
        while hi - lo > step:             # bisect for the top of the interval
            mid = (lo + hi) / 2
            ok, fill = _probe(typ, original, mid, mid + delta, expected,
                              use_cli, backend)
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
            # A losing value is worse than no value: it silently replaces a rhythm the family was
            # designed with. Put the original back and let the caller decide.
            open(typ, "w", encoding="utf-8").write(original)
            under = best_fill is not None and best_fill < fmin
            print("FAIL  best leading %.3fem / spacing %.3fem -> fill %s%% "
                  "(target %s-%s%%); restored the original %.3fem/%.3fem"
                  % (best, best + delta, best_fill, fmin, fmax, l0, s0))
            if under:
                _footer = _FOOTER_TUNE_UNDER
                print("      the page is UNDER-FILLED: a fact is missing, not whitespace. "
                      "Leading is capped at %.2fem (never widen the range). Add a real fact "
                      "from the candidate's facts (a bullet with a measurable result, a "
                      "project, a certification) — never pad. If the facts are not in "
                      "hand, ASK the user for them; never invent. Alternative, only if the "
                      "facts are exhausted: drop to fewer pages or accept a lower fill "
                      "target, and say so to the user." % cap)
            else:
                if lo_arg is not None and lo_arg <= 0.40 and hi_arg >= 1.40:
                    _footer = _FOOTER_TUNE_WIDE
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
        # BaseException, not Exception: Ctrl-C mid-probe must not leave a half-tuned file behind
        open(typ, "w", encoding="utf-8").write(original)   # never leave a probe
        raise


# ---------- main gate ----------

HEADER_RE = re.compile(r"^//\s*vitae:\s*pages=(\d+)(?:\s+fill=(\d+)-(\d+))?",
                       re.M)


def pages_from_name(typ: str) -> str:
    """The page count a headerless deliverable declares in its own file name."""
    return "2" if re.search(r"[-_]2\s*p(?:ages?)?(?![a-z])",
                            os.path.basename(typ), re.I) else "1"


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


# Both markers are looked for in the first 4096 bytes: they are line-1 comments of the templates.
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


# sha256 of every templates/lib.typ ever committed (past releases). A CV whose
# lib.typ matches one of these is a stale-but-honest copy (WARN: recopy for the fixes);
# anything else was rewritten or edited (FAIL: the gates assume lib.typ's behaviour). The
# CURRENT lib is not listed: it is compared by content against the skill's own file.
# Regenerate after each release commit:
#   for c in $(git log --format=%H -- templates/lib.typ); do
#     git show $c:templates/lib.typ | sha256sum | cut -c1-64; done | sort -u
# (a model once rewrote lib.typ from memory, dropped `derive()`, and looped.)
KNOWN_LIB_SHA256 = {
    "5f550c000b6b21f1b48e7e564ef223a76e7b34eb444cad4e1dada8054d1d7ae7",
    "6676cfb4239ba0da1647df675731920570190a56a9a2480821e3ad3a350f37df",
    "e83601b082f068fd3ded679358d3aeaab28ac59af812815077b95e58dab80aee",
    "fd5a2ed352e234f476dfc6cfdb4d20bda011dae8ebb2f32f8553137cdf2ac6f1",
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
    "817c4ec76e6e55e5767ecb402b2c2ff44ae167f91416ca40f573b42d87e2d76e",
}


def digest_of(f: str) -> str:
    """sha256 of a lib file, BOM and CRLF normalised, so a copy re-saved on Windows still matches."""
    with open(f, "rb") as fh:
        data = fh.read()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def check_lib_integrity(typ_path: str, skill_dir: str | None = None,
                        known: set[str] | None = None) -> list[Finding]:
    """Return [(level, msg)] for the lib.typ the CV imports (Level.FAIL/Level.WARN);
    empty when it is the skill's own lib or the CV imports none. Runs before
    compilation so the message survives a Typst error.

    FAIL for a lib that is not a byte copy (rewritten or edited: a model once rewrote it from
    memory, dropped `derive()` and looped); WARN for a known older release; WARN, not FAIL,
    when a lib.typ sits beside the CV but no import resolves to it (integrity unchecked)."""
    skill_dir = skill_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    known = KNOWN_LIB_SHA256 if known is None else known
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
    h = digest_of(lib)
    if h == digest_of(ref):
        return []
    if h in known:
        return [(Level.WARN, f"lib.typ is from an older vitae release; recopy to get fixes: {cp}")]
    return [(Level.FAIL, "lib.typ is not a copy of the skill's lib (rewritten or edited) "
                     f"— recopy it byte-for-byte: {cp}")]


# The last lines printed when a run ends on a non-zero exit (see `_run`). A reader (human or
# model) acts on what it sees LAST, so the instruction is here, not only in the header.
# Armed (set non-None) only after preflight succeeded, per mode, so a missing
# dependency or a usage error never gets a footer that blames cv.typ.
_NO_READ = ("      Do not open verify.py or lib.typ: their code is not the fix, and "
            "reading them costs your context.")
_FOOTER_GATE = ("NEXT  Apply the fix each FAIL above names, then re-run the same command. "
                "Edit cv.typ only; a lib.typ FAIL is fixed by the printed `cp` command "
                "(recopy it, never edit it).\n" + _NO_READ)
_FOOTER_TUNE = ("NEXT  Run the command printed above (wider range), or add real content / "
                "change the page count in cv.typ; do not edit leading by hand.\n" + _NO_READ)
_FOOTER_TUNE_UNDER = ("NEXT  The page is under-filled: do not re-run --tune or widen the range "
                      "(leading is capped). Add a real fact from the candidate's facts (a bullet "
                      "with a measurable result, a project, a certification); raising the body type size "
                      "is the same padding, not an alternative; never pad or invent "
                      "— if the facts are not in hand, ask the user. Only if the facts are "
                      "exhausted: fewer pages or a lower fill target, and tell the user.\n" + _NO_READ)
_FOOTER_TUNE_NOPAR = ("NEXT  Add the `#set par(leading: Xem, spacing: Yem)` line to cv.typ "
                      "(copy it from the template), then re-run the same command.\n" + _NO_READ)
_FOOTER_TUNE_WIDE = ("NEXT  The range was already wide: do not re-run --tune. Add real content "
                     "or change the page count in cv.typ.\n" + _NO_READ)
_footer: str | None = None


_LOWERED_WARN = ("WARN  fill target lowered below drawn target {a} — allowed ONLY if "
                 "the facts are exhausted; tell the user the page is under-filled and which "
                 "facts would fill it; never pad or invent to reach it (rule 1)")


# The shipped templates top out at 0.96em body leading; the tuner may go to LEADING_CAP
# (1.10em). Above 1.00em multi-line text (profile summary, wrapped bullets) reads as
# double-spaced while every mechanical check still passes.
LEADING_WARN = 1.00    # em; strictly above it the WARN fires (largest shipped 0.96)
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
    global _footer
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
        elif int(fmin) < drawn[0]:
            lowered = f"{drawn[0]}-{drawn[1]} → {fmin}-{fmax}"
            print(_LOWERED_WARN.format(a=f"{drawn[0]}-{drawn[1]}"))

    deps_ok, use_cli, backend = preflight()
    if not deps_ok:
        sys.exit(1)
    _footer = _FOOTER_GATE     # armed only now: before this, a FAIL is not about cv.typ

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

    # Clone markers: the template's own accent and its "Category: items" skills block, left in
    # place, make every CV from the skill look alike (references/design.md, three clone markers).
    typ_text = open(typ, encoding="utf-8").read()
    if "7d2231" in typ_text.lower():
        print("WARN  template default accent (#7d2231) — run scripts/pick_design.py and apply the family it draws (references/design.md § Design families)")
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

    for line in check_year_only_dates(txt):
        print(f'WARN  {_year_only_msg(line)}')
    for line in check_degree_tokens(txt):
        print(f'WARN  degree token beside a non-completion marker ("{line}") — ATS (Eightfold) read "B.Eng. program" as a degree held; say "coursework" (references/ats.md)')

    if facts:
        try:
            facts_text = open(facts, encoding="utf-8").read()
        except OSError as e:
            print(f"FAIL  --facts: cannot read {facts} ({e.strerror})")
            fail = 1
        else:
            for w in check_facts_coverage(txt, facts_text):
                print(w)
            foreign = [n for c, n in (_detect_lang(txt), _detect_lang(facts_text)) if c == "other"]
            if foreign:     # no status or country words for this language or script: INFO, never a guess (design principle)
                print(_not_checked(" and ".join(dict.fromkeys(foreign)), "a place on an entry against its facts-file item"))
            else:
                for w in check_entry_locations(typ_text, facts_text):
                    print(w)

    for w in check_summary_repeats(typ_text):
        print(w)
    for w in check_entry_repeats(typ_text):
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
    global _footer
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
        _footer = _FOOTER_GATE
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
                 f"         --facts: WARN on every year / month+year / number / proper name in the CV absent from the facts file\n"
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
        if _footer and isinstance(e.code, int) and e.code != 0:
            print(_footer, flush=True)
        raise


if __name__ == "__main__":
    _run()
