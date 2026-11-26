#!/usr/bin/env python3
"""Two binary gates for a cover letter — nothing else. A letter is prose, not
a CV: verify.py's fill/separation/ink thresholds are calibrated for a
data-dense résumé page and mean nothing on a paragraph of text, so this
script reuses only verify.py's compile/extract plumbing, never its constants
(the task that created this file forbids it explicitly).

Gates:
  1. the letter compiles to exactly ONE page.
  2. the employer AND the exact job title both appear in the extracted text.
  (+ no template sample left in the text — the CV gate's placeholder check;
  --allow-placeholders skips it, for the shipped templates/letter.typ only.)

Usage:
    verify_letter.py letter.typ EMPLOYER "EXACT JOB TITLE" [--allow-placeholders]

Exit codes: 0 PASS, 1 FAIL, 2 usage error.

Run as a CLI step of the skill's letter workflow (references/companion-guide.md), never imported: verify.py only
points at it (is_letter() makes verify.py's own CV gate step aside for a
letter, since that gate would misjudge one). The hidden-text check is the one
shared gate that applies to a letter too, because an ATS reads a letter's text
as readily as a CV's. Deliberately NOT checked: layout quality, fill, section
separation, tone or length of the prose.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from typing import NoReturn

from vitae.core.env import preflight
from vitae.core.level import Level  # noqa: E402
from vitae.verify.cv import _ALLOW_REFUSED, placeholders_allowed
from vitae.verify.gates import _placeholders, make_context
from vitae.verify.pdf import compile_pdf, count_pages, ensure_icons, extract_text
from vitae.verify.text import check_hidden_text


def check_letter(typ: str, employer: str, job_title: str,
                 allow_placeholders: bool = False) -> tuple[bool, list[tuple[bool | None, str]]]:
    """Returns (ok, messages) — messages are (is_fail, text) pairs.

    is_fail is True for a FAIL, False for an informational OK line, and None
    for a WARN that is printed but never fails the gate (hidden-text warnings).
    A template sample left in the text (the CV gate's placeholder check) FAILs; `allow_placeholders` skips it,
    for the shipped templates/letter.typ only.
    """
    if allow_placeholders and not placeholders_allowed(typ):
        return False, [(True, _ALLOW_REFUSED.removeprefix("FAIL  "))]
    ok, use_cli, backend = preflight()
    if not ok:
        return False, [(True, "missing dependency — see --doctor output above")]

    ensure_icons(typ)
    msgs: list[tuple[bool | None, str]] = []
    fail = False
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "letter.pdf")
        compiled, err = compile_pdf(typ, pdf, use_cli)
        if not compiled:
            return False, [(True, f"compile failed: {err}")]

        pages = count_pages(pdf, backend)
        if pages != "1":
            fail = True
            msgs.append((True, f"letter is {pages} page(s), must be exactly 1"))
        else:
            msgs.append((False, "1 page"))

        txt = extract_text(pdf, backend)
        for label, needle in (("employer", employer), ("job title", job_title)):
            if needle.casefold() not in txt.casefold():     # casefold, not lower: "Straße" meets "STRASSE"
                fail = True
                msgs.append((True, f'{label} "{needle}" not found in the letter text'))
            else:
                msgs.append((False, f'{label} "{needle}" found'))

        if allow_placeholders:
            msgs.append((None, "placeholder gate skipped (--allow-placeholders): only for the shipped templates, never a real letter"))
        else:
            with open(typ, encoding="utf-8") as f:
                ctx = make_context(typ, pdf, txt, f.read(), backend, can_query=False)
            for lvl, msg in _placeholders(ctx):
                msgs.append((True if lvl == Level.FAIL else None, msg))
                fail = fail or lvl == Level.FAIL

        # shared with verify.py and verify_academic.py: a letter can hide text too
        # is_fail None = WARN (printed, never fails)
        for lvl, msg in check_hidden_text(pdf):
            msgs.append((True if lvl == Level.FAIL else None, msg))
            fail = fail or lvl == Level.FAIL

    return not fail, msgs


class _UsageParser(argparse.ArgumentParser):
    """Any usage error prints the old hand-written usage text and exits 2."""

    def error(self, message: str) -> NoReturn:
        print(_usage(), file=sys.stderr)
        sys.exit(2)


def _usage() -> str:
    prog = os.path.basename(sys.argv[0])
    return (f"usage: {prog} letter.typ EMPLOYER \"EXACT JOB TITLE\" [--allow-placeholders]")


def main() -> None:
    ap = _UsageParser(add_help=False, allow_abbrev=False)
    ap.add_argument("args", nargs="*")
    argv = sys.argv[1:]
    if argv[:1] in (["-h"], ["--help"]):
        print(_usage())
        sys.exit(0)
    allow_placeholders = "--allow-placeholders" in argv
    argv = [a for a in argv if a != "--allow-placeholders"]
    # as the old manual argv: only argv[0] is a mode flag (the rest is
    # ignored then); otherwise every argument is a positional, even "-x"
    argv = ["--"] + argv
    parsed = ap.parse_args(argv)

    if len(parsed.args) != 3:
        ap.error("expected letter.typ EMPLOYER JOB_TITLE")

    typ, employer, job_title = parsed.args
    ok, msgs = check_letter(typ, employer, job_title, allow_placeholders)
    for is_fail, msg in msgs:
        print(f"{'FAIL' if is_fail else 'WARN' if is_fail is None else 'OK  '}  {msg}")
    if ok:
        print("PASS  all gates hold")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
