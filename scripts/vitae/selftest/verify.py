"""verify.py --selftest: the checks that can break silently, kept shipped so a user
can verify their install (lib.typ integrity, tuner regex round-trips, poppler and
typst present, the hidden-text / raster / date-adjacency measurements, ...).

What it covers: verify.py's own gates and readers. Each gate module of vitae/selftest/gates/ builds a
synthetic case (a PIL-drawn page, a typst snippet compiled to a PDF, a source string,
a temp directory) and asserts that one gate FAILs or WARNs on the defect and stays
silent on the legitimate shape next to it. A gate whose self-test case is deleted can
turn into a no-op or a false alarm with nothing else in the suite noticing, which is
why the cases come in pairs (fires / stays quiet) and why most assertions carry a
message naming what would break. The blocks that need typst, pdftoppm or pdftotext
print `SKIPPED` when they are missing instead of failing; the tuner block runs only
when `preflight()` finds a PDF backend.

How it is invoked: only through `python -I scripts/verify.py --selftest` (the
`selftest-verify` case of tests/run_all.sh runs exactly that). There is no CLI of
its own, and the entry point is `run()`, which ends in `sys.exit(0)` or raises
AssertionError. verify.py imports this module lazily inside its `--selftest` branch,
so a normal run never loads it (the self-test is a large share of what
verify.py once was, and none of it runs during a real verification).

`VERIFY_FILE` (gates/fixtures.py) is the façade scripts/verify.py: the self-test spawns it as a subprocess and feeds it to
is_letter / is_academic.

What it does not cover: verify_letter.py, verify_academic.py and pick_design.py each
have their own `--selftest`; the end-to-end fixtures, the per-template gates and the
backend comparisons live in tests/run_all.sh, not here.

Not printed by --help (verify.py's usage text is separate)."""

from __future__ import annotations

import sys
from typing import NoReturn

from vitae.selftest.gates import (
    dates,
    facts,
    fonts,
    header,
    hidden,
    libint,
    nosplit,
    proximity,
    source,
    textclip,
    tuner,
    warns,
    whitespace,
)

# The blocks run in this order (it fixes the order of the SKIPPED lines).
GATES = (
    tuner.par_regex, fonts.font_fallback, tuner.par_reader, warns.document_warns, facts.facts_coverage,
    header.cv_header, whitespace.whitespace, nosplit.no_split, textclip.text_clip, hidden.hidden_text,
    proximity.group_proximity, dates.date_adjacency, source.source_gates, libint.lib_integrity,
    tuner.tuner_cap, warns.leading_warn,
)


def run() -> NoReturn:
    """--selftest: the checks that can break silently. Exits 0 or raises."""
    for gate in GATES:
        gate()
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
