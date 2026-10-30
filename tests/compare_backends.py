#!/usr/bin/env python3
"""Poppler vs pypdfium2, line by line, on rendered PDFs (the fixtures).

verify.py reads every PDF through one backend (pdf_backend()); the line-start gates
(check_bullet_chars and friends) only see the same items if pdfium's text is cut into
lines the way pdftotext cuts it. Prints, per PDF, the non-blank line counts of both and
whether the lines are identical (whitespace collapsed); exits 1 when a PDF's counts differ
by more than MAX_DELTA lines. Needs pdftotext AND pypdfium2: SKIPs (exit 0) otherwise.
Usage: tests/compare_backends.py <pdf>...   (run_all.sh passes the rendered fixtures)"""
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import verify  # noqa: E402

MAX_DELTA = 6    # measured on the 14 fixtures: 0 to 5 lines apart, 24 of 43 PDFs identical


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
        delta = abs(len(a) - len(b))
        flag = "identical" if a == b else f"differ by {delta}"
        print(f"{os.path.basename(pdf)[:-4]:<20} poppler {len(a):>3} pdfium {len(b):>3} {flag}")
        bad += delta > MAX_DELTA
    print(f"{'FAIL' if bad else 'ok'} {bad} PDF(s) over {MAX_DELTA} lines apart")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
