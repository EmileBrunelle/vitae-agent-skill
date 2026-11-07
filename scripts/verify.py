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
import glob
import hashlib
import json
import os
import re
import shlex
import shutil  # noqa: F401 -- tests patch v.shutil.which (the stdlib module object, shared by every verify_* module)
import subprocess
import sys
import tempfile
from typing import NoReturn

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
    classify_font_fallback as classify_font_fallback,
)
from verify_fonts import (
    requested_families as requested_families,
)
from verify_groups import ENTRY_MARKS as ENTRY_MARKS
from verify_groups import PROX_FAIL as PROX_FAIL
from verify_groups import PROX_WARN as PROX_WARN
from verify_groups import _entry_records as _entry_records
from verify_groups import _find_run as _find_run
from verify_groups import _first_word as _first_word
from verify_groups import _gnorm as _gnorm
from verify_groups import _line_index as _line_index
from verify_groups import _lines as _lines
from verify_groups import _page_ink_gap as _page_ink_gap
from verify_groups import _typst_query as _typst_query
from verify_groups import _yc as _yc
from verify_groups import check_date_adjacency as check_date_adjacency
from verify_groups import check_duplicate_names as check_duplicate_names
from verify_groups import check_group_proximity as check_group_proximity
from verify_groups import measure_groups as measure_groups
from verify_layout import BOUNDARY_CEILING as BOUNDARY_CEILING
from verify_layout import CANYON as CANYON
from verify_layout import DEVICE_QUORUM as DEVICE_QUORUM
from verify_layout import DEVICELESS as DEVICELESS
from verify_layout import SEPARATION_CEILING as SEPARATION_CEILING
from verify_layout import check_font_fallback as check_font_fallback
from verify_layout import check_text_clip as check_text_clip
from verify_layout import check_whitespace as check_whitespace
from verify_layout import pdf_char_fonts as pdf_char_fonts
from verify_level import Finding, Level  # noqa: E402
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
