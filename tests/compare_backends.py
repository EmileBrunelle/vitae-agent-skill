#!/usr/bin/env python3
"""Poppler vs pypdfium2, line by line, on rendered PDFs (the fixtures).

verify.py reads every PDF through one backend (pdf_backend()); the line-start gates
(check_bullet_chars and friends) only see the same items if pdfium's text is cut into
lines the way pdftotext cuts it. Per PDF this prints the non-blank line counts of both, how
many of poppler's lines (whitespace collapsed) pdfium also has verbatim, and whether the
sequence and the line set are identical. Exits 1 when counts differ by more than MAX_DELTA,
fewer than MIN_MATCH of poppler's lines are found in pdfium's, or the words differ at all.
Measured on the 14 fixtures (the one source for the figures in the CHANGELOG): line sequence
identical on 8, same set of lines on 10, 630 of poppler's 642 lines found verbatim in
pdfium's, at most 5 lines apart, the same words everywhere.
Needs pdftotext AND pypdfium2: SKIPs (exit 0) otherwise.
Usage: tests/compare_backends.py <pdf>...   (run_all.sh passes the rendered fixtures)"""
import collections
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import verify  # noqa: E402

MAX_DELTA = 6      # lines apart
MIN_MATCH = 0.85   # share of poppler's lines that pdfium has verbatim (measured 0.89 to 1.00)


def lines(pdf: str, backend: verify.PdfBackend) -> list[str]:
    return [" ".join(ln.split()) for ln in verify.extract_text(pdf, backend).split("\n") if ln.strip()]


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
        ok = delta <= MAX_DELTA and found >= MIN_MATCH * len(a) and same_words
        print(f"{os.path.basename(pdf)[:-4]:<20} poppler {len(a):>3} pdfium {len(b):>3} "
              f"matched {found:>3}/{len(a):<3} {kind}{'' if same_words else ', WORDS DIFFER'}{'' if ok else '  <-- FAIL'}")
        bad += not ok
    print(f"{'FAIL' if bad else 'ok'} {bad} PDF(s) failed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
