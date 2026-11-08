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

The helpers live in sibling modules under vitae/verify/ and vitae/core/, imported by name where they are used; the
--selftest code (vitae/selftest/verify.py) is loaded lazily, so a normal run never loads it.

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
import sys
import tempfile
from typing import NoReturn

from vitae.core.base import _FOOTER_GATE, HIDDEN_PPI, DetailRow
from vitae.core.env import pdf_backend, preflight
from vitae.verify.cv import _check_cv, check_all, run_new_gates
from vitae.verify.pdf import extract_text, pdf_unreadable, render_crops, render_pages
from vitae.verify.source import _fill_args_ok
from vitae.verify.tune import tune


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


def main() -> tuple[int, str | None]:
    """Mode dispatch, and the owner of every usage text (what a usage error and --help print).

    The first argument picks the mode, checked in this order: --all, --gates, --render/--text,
    --doctor, --selftest, --tune; anything else is the one-file gate. Modes that need no
    cv.typ (--doctor, --selftest, --render, --text) come before the positional parsing, which
    would otherwise reject them for a missing `typ`. Every mode ends in sys.exit, except the
    gate modes, which return (exit code, footer): the footer is the NEXT line `_run` prints last
    on a non-zero exit, None until the mode's preflight passed."""
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
        rows: list[DetailRow] = []
        rc = run_new_gates(ga.typ, ga.pdf, extract_text(ga.pdf, pdf_backend()),
                           open(ga.typ, encoding="utf-8").read(), root=ga.root, detail=rows)
        print("DETAIL " + json.dumps(rows))
        return rc, _FOOTER_GATE
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
        import vitae.selftest.verify as verify_selftest  # noqa: PLC0415 -- lazy: a normal run never loads the self-test
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
        return tune(ta.typ, int(ta.pages), int(ta.fill_min), int(ta.fill_max),
                    lo=bounds[0], hi=bounds[1])

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
    return _check_cv(ca.typ, ca.expected, ca.fill_min, ca.fill_max, facts_path)


def _run() -> None:
    """Entry point: run main(), and on a non-zero exit print the mode's footer last, so the
    next step is the final thing a reader sees. Exit codes are passed through unchanged."""
    rc, footer = main()
    if footer and rc != 0:
        print(footer, flush=True)
    sys.exit(rc)


if __name__ == "__main__":
    _run()
