#!/usr/bin/env python3
"""Poppler vs pypdfium2, line by line, on rendered PDFs (the fixtures).

verify.py reads every PDF through one backend (pdf_backend()); the line-start gates
(check_bullet_chars and friends) only see the same items if pdfium's text is cut into
lines the way pdftotext cuts it. Per PDF this prints the non-blank line counts of both, how
many of poppler's lines (whitespace collapsed) pdfium also has verbatim, and whether the
sequence and the line set are identical. Exits 1 when counts differ by more than MAX_DELTA,
fewer than MIN_MATCH of poppler's lines are found in pdfium's, or the words differ at all.
Measured on the 14 fixtures (the one source for the figures in the CHANGELOG): line sequence
identical on 6 (tightened leading made poppler split the name of 2 more), same set of lines on 8, at most 6 lines apart,
the same words everywhere. IDENTICAL ratchets those 6: any loss of an identical
sequence FAILs; SAME_WORDS requires the identical word sequence; on the others, no word may change its neighbours inside a line.
Needs pdftotext AND pypdfium2: SKIPs (exit 0) otherwise.
Usage: tests/compare_backends.py <pdf>...   (tests/integration passes the rendered fixtures)"""
import collections
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from vitae.core.env import PdfBackend
from vitae.verify.pdf import extract_text

MAX_DELTA = 6      # lines apart
# Ratchet: fixtures whose line sequence is identical today. Losing that is a FAIL.
IDENTICAL = {"avant-poster", "color-band", "engraved-card", "hard-edge", "humanist-quiet", "mono-technical"}
# Fixtures whose word stream must stay identical: none. editorial-serif and keyline-corporate were here while their name and
# title line boxes overlapped; with the contact block below the name they follow the neighbour-pair rule like the rest.
SAME_WORDS: set[str] = set()
MIN_MATCH = 0.85   # share of poppler's lines that pdfium has verbatim (measured 0.89 to 1.00)


def lines(pdf: str, backend: PdfBackend) -> list[str]:
    return [" ".join(ln.split()) for ln in extract_text(pdf, backend).split("\n") if ln.strip()]


def bigrams_ok(a: list[str], b: list[str]) -> bool:
    """Every pair of neighbouring words inside a pdfium line also neighbours in poppler's word
    stream (poppler's lines joined): a word swapped or moved between lines makes a new pair.
    A line pdfium merged or split only makes pairs that exist across poppler's line ends."""
    stream = [w for ln in a for w in ln.split()]
    known = set(zip(stream, stream[1:]))
    return all(pr in known for ln in b for pr in zip(ln.split(), ln.split()[1:]))


def main() -> int:
    try:
        import pypdfium2  # noqa: F401
    except ImportError:
        print("SKIP compare_backends: pypdfium2 not installed")
        return 0
    if not (shutil.which("pdftotext") and shutil.which("pdfinfo")):
        print("SKIP compare_backends: poppler not on PATH")
        return 0
    bad = 0
    for pdf in sys.argv[1:]:
        a, b = lines(pdf, "poppler"), lines(pdf, "pdfium")
        found = sum((collections.Counter(a) & collections.Counter(b)).values())
        same_words = collections.Counter(w for ln in a for w in ln.split()) == collections.Counter(
            w for ln in b for w in ln.split())
        delta = abs(len(a) - len(b))
        kind = "identical" if a == b else "same lines, other order" if sorted(a) == sorted(b) else "differ"
        name = os.path.basename(pdf)[:-4]
        ordered = (a == b if name in IDENTICAL
                   else [w for ln in a for w in ln.split()] == [w for ln in b for w in ln.split()] if name in SAME_WORDS
                   else bigrams_ok(a, b))
        ok = delta <= MAX_DELTA and found >= MIN_MATCH * len(a) and same_words and ordered
        print(f"{os.path.basename(pdf)[:-4]:<20} poppler {len(a):>3} pdfium {len(b):>3} "
              f"matched {found:>3}/{len(a):<3} {kind}{'' if same_words else ', WORDS DIFFER'}{'' if ordered else ', ORDER LOST'}{'' if ok else '  <-- FAIL'}")
        bad += not ok
    print(f"{'FAIL' if bad else 'ok'} {bad} PDF(s) failed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
