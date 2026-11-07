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
import json
import os
import shutil  # noqa: F401 -- tests patch v.shutil.which (the stdlib module object, shared by every verify_* module)
import subprocess  # noqa: F401 -- tests patch v.subprocess.run (the stdlib module object, shared by every verify_* module)
import sys
import tempfile
from typing import NoReturn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
from verify_cv import _BODY_SIZE_WARN as _BODY_SIZE_WARN
from verify_cv import _LEADING_RATIO_WARN as _LEADING_RATIO_WARN
from verify_cv import _LEADING_WARN as _LEADING_WARN
from verify_cv import _LOWERED_FAIL as _LOWERED_FAIL
from verify_cv import _LOWERED_WARN as _LOWERED_WARN
from verify_cv import ACADEMIC_MARKER as ACADEMIC_MARKER
from verify_cv import BODY_SIZE_WARN as BODY_SIZE_WARN
from verify_cv import HEADER_RE as HEADER_RE
from verify_cv import LEADING_RATIO_WARN as LEADING_RATIO_WARN
from verify_cv import LETTER_MARKER as LETTER_MARKER
from verify_cv import NON_CV_RE as NON_CV_RE
from verify_cv import _body_size_warn as _body_size_warn
from verify_cv import _check_cv as _check_cv
from verify_cv import _leading_warn as _leading_warn
from verify_cv import check_all as check_all
from verify_cv import check_lib_integrity as check_lib_integrity
from verify_cv import digest_of as digest_of
from verify_cv import is_academic as is_academic
from verify_cv import is_gated as is_gated
from verify_cv import is_letter as is_letter
from verify_cv import pages_from_name as pages_from_name
from verify_cv import run_hidden_gate as run_hidden_gate
from verify_cv import run_new_gates as run_new_gates
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
from verify_typst import _doc_body_size as _doc_body_size
from verify_typst import _doc_par_list as _doc_par_list
from verify_typst import (
    _read_par as _read_par,
)
from verify_typst import (
    _strip_typst_comments as _strip_typst_comments,
)
from verify_typst import (
    _write_par as _write_par,
)


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
