#!/usr/bin/env python3
"""Two binary gates for a cover letter — nothing else. A letter is prose, not
a CV: verify.py's fill/separation/ink thresholds are calibrated for a
data-dense résumé page and mean nothing on a paragraph of text, so this
script reuses only verify.py's compile/extract plumbing, never its constants
(the task that created this file forbids it explicitly).

Gates:
  1. the letter compiles to exactly ONE page.
  2. the employer AND the exact job title both appear in the extracted text.

Usage:
    verify_letter.py letter.typ EMPLOYER "EXACT JOB TITLE"
    verify_letter.py --selftest

Exit codes: 0 PASS, 1 FAIL, 2 usage error.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify  # noqa: E402 — reuse compile_pdf/count_pages/extract_text only


def check_letter(typ, employer, job_title):
    """Returns (ok, messages) — messages are (is_fail, text) pairs."""
    ok, use_cli, use_poppler = verify.preflight()
    if not ok:
        return False, [(True, "missing dependency — see --doctor output above")]

    verify.ensure_icons(typ)
    msgs = []
    fail = False
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "letter.pdf")
        compiled, err = verify.compile_pdf(typ, pdf, use_cli)
        if not compiled:
            return False, [(True, f"compile failed: {err}")]

        pages = verify.count_pages(pdf, use_poppler)
        if pages != "1":
            fail = True
            msgs.append((True, f"letter is {pages} page(s), must be exactly 1"))
        else:
            msgs.append((False, "1 page"))

        txt = verify.extract_text(pdf, use_poppler)
        for label, needle in (("employer", employer), ("job title", job_title)):
            if needle.lower() not in txt.lower():
                fail = True
                msgs.append((True, f'{label} "{needle}" not found in the letter text'))
            else:
                msgs.append((False, f'{label} "{needle}" found'))

    return not fail, msgs


def main():
    argv = sys.argv[1:]

    if argv and argv[0] == "--selftest":
        # Build a tiny one-page letter mentioning "Acme Corp" and "Data
        # Analyst", then check the gate passes on the right pair and FAILS
        # on a wrong employer — proves the needle search actually bites
        # rather than always reporting PASS.
        src = (
            '#set page(paper: "us-letter")\n'
            '#set text(size: 11pt)\n'
            'Dear Hiring Manager,\n\n'
            'I am writing to apply for the Data Analyst role at Acme Corp.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            typ = os.path.join(tmp, "letter.typ")
            with open(typ, "w", encoding="utf-8") as f:
                f.write(src)
            ok, msgs = check_letter(typ, "Acme Corp", "Data Analyst")
            assert ok, f"expected PASS on the matching pair: {msgs}"
            ok, msgs = check_letter(typ, "Widgets Inc", "Data Analyst")
            assert not ok, "a wrong employer must FAIL the gate"
            assert any("employer" in m and "not found" in m for _, m in msgs)

            # a 2-page letter must fail the page gate
            two_page = src + "#pagebreak()\nSincerely,\n"
            typ2 = os.path.join(tmp, "letter2.typ")
            with open(typ2, "w", encoding="utf-8") as f:
                f.write(two_page)
            ok, msgs = check_letter(typ2, "Acme Corp", "Data Analyst")
            assert not ok, "a 2-page letter must FAIL the page gate"
            assert any("page" in m and "must be exactly 1" in m for _, m in msgs)

        print("selftest OK — matching employer/title PASSes, a wrong employer "
              "FAILs the text gate, and a 2-page letter FAILs the page gate")
        sys.exit(0)

    if len(argv) != 3:
        print(f"usage: {os.path.basename(sys.argv[0])} letter.typ EMPLOYER \"EXACT JOB TITLE\"\n"
              f"       {os.path.basename(sys.argv[0])} --selftest", file=sys.stderr)
        sys.exit(2)

    typ, employer, job_title = argv
    ok, msgs = check_letter(typ, employer, job_title)
    for is_fail, msg in msgs:
        print(f"{'FAIL' if is_fail else 'OK  '}  {msg}")
    if ok:
        print("PASS  both gates hold")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
