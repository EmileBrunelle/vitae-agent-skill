#!/usr/bin/env python3
"""Five binary gates for an academic CV — a round-trip between the declared
TOML data file (source of truth for counts/order) and the rendered PDF
(`pdftotext -layout`). See academic-mode.md for the design rationale; the
five checks and the non-goals below are DECIDED THERE, not here.

PLUMBING REUSED from verify.py (imported, not copied — none of it carries a
calibrated constant): preflight(), compile_pdf(), count_pages(),
render_pngs(). Also measure_fill.measure() for the reported-only last-page
fill line.

NOT REUSED, on purpose (commit c7ca219): check_whitespace(), tune(), or any
of BOUNDARY_RATIO / SEPARATION_CEILING / DEVICE_QUORUM / CANYON /
BOUNDARY_CEILING. Those are curve-fit to one/two-page industry résumés and
are meaningless on a genre with no fill target at all (academic-mode.md "What does not apply here":
"Écarté, pas assoupli" — no fill floor, not even on the last page).

This script also never regexes the .typ source and compares it to a PDF
built from that same source — that round-trip is a tautology, and a
previous attempt at exactly this had to be deleted (commit d7f67da). Every declared count/order/prefix comes from the TOML;
every extracted count/order comes from the rendered PDF.

Usage:
    verify_academic.py cv.typ data.toml
    verify_academic.py --selftest
    verify_academic.py --doctor

Exit codes: 0 PASS, 1 FAIL, 2 usage error.

Run as a CLI step 6 of academic mode (references/academic-mode.md), never imported by another
module: verify.py's is_academic() makes its own gate step aside for an
academic CV and points here instead. The checks, by id: A = declared count
and entry numbering, B = antechronology, C = no orphan heading, D = no entry
straddling a page break, E = running head and pagination (beyond 2 pages).
Hidden-text detection is the shared check_hidden_text gate.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from typing import NoReturn

from vitae.core.env import preflight
from vitae.selftest.academic import selftest
from vitae.verify.academic.gate import run_gate


class _UsageParser(argparse.ArgumentParser):
    """Any usage error prints the old hand-written usage text and exits 2."""

    def error(self, message: str) -> NoReturn:
        prog = os.path.basename(sys.argv[0])
        print(f"usage: {prog} cv.typ data.toml\n"
              f"       {prog} --selftest\n"
              f"       {prog} --doctor", file=sys.stderr)
        sys.exit(2)


def main() -> None:
    ap = _UsageParser(add_help=False, allow_abbrev=False)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--doctor", action="store_true")
    ap.add_argument("paths", nargs="*")
    argv = sys.argv[1:]
    # as the old manual argv: only argv[0] is a mode flag (the rest is
    # ignored then); otherwise every argument is a positional, even "-x"
    argv = argv[:1] if argv and argv[0] in ("--selftest", "--doctor") else ["--"] + argv
    args = ap.parse_args(argv)

    if args.selftest:
        selftest()
        sys.exit(0)

    if args.doctor:
        ok, _, _ = preflight()
        if not shutil.which("pdftotext"):
            print("MISSING  pdftotext (poppler-utils) -- required for the "
                  "-layout extraction these checks depend on")
            ok = False
        sys.exit(0 if ok else 1)

    if len(args.paths) != 2:
        ap.error("expected cv.typ data.toml")

    typ, toml_path = args.paths
    ok, msgs, reported = run_gate(typ, toml_path)
    for is_fail, msg in msgs:
        print(f"{'FAIL' if is_fail else 'WARN' if is_fail is None else 'OK  '}  {msg}")
    for line in reported:
        print(f"INFO  {line}")
    if ok:
        print("PASS  all five checks hold")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
