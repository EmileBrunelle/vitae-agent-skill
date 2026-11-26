"""Reads of non-ASCII files by the verify gates, run in-process and in a subprocess whose locale encoding is ASCII.

test_verify_locale.py compares both runs: a read that drops its explicit `encoding="utf-8"` still works under the
UTF-8 locale of a normal test run but fails (or silently misreads) under `LC_ALL=C -X utf8=0`.
"""
import contextlib
import io
import json
import os
import sys
from types import SimpleNamespace
from unittest import mock

NON_ASCII = "// café — naïve résumé, 日本語\n"


def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def _check_cv_output(cv, typ):
    stubs = dict(
        preflight=lambda: (True, False, "pdftotext"), check_lib_integrity=lambda t: [], ensure_icons=lambda t: None,
        compile_pdf=lambda t, p, use_cli: (True, ""), count_pages=lambda pdf, backend: "1",
        word_boxes=lambda pdf, with_text=False: None, render_pngs=lambda t, tmp, use_cli: [],
        extract_text=lambda pdf, backend: "", make_context=lambda *a, **k: object(), GATES=(),
        run_gates=lambda gates, ctx: 0, check_review_record=lambda t: [], layout_report_line=lambda t: None,
        typst_can_query=lambda: False)
    out = io.StringIO()
    with mock.patch.multiple(cv, **stubs), contextlib.redirect_stdout(out):
        cv._check_cv(typ, "1", None, None)
    return out.getvalue()


def _check_all_output(cv, directory):
    out = io.StringIO()
    with mock.patch.object(cv.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0)), \
            contextlib.redirect_stdout(out):
        rc = cv.check_all(directory)
    return rc, out.getvalue()


def run(workdir):
    """Everything is computed from files under `workdir`; the result is JSON-serialisable and encoding independent."""
    from vitae.verify import cv, jsonout, review_record
    w = str(workdir)
    os.makedirs(w, exist_ok=True)

    def p(name):
        return os.path.join(w, name)

    res = {}
    _write(p("guide.typ"), NON_ASCII + "// vitae: pages=1\n")
    res["gated"] = cv.is_gated(p("guide.typ"))
    _write(p("academic.typ"), NON_ASCII + cv.ACADEMIC_MARKER + "\n")
    res["academic"] = cv.is_academic(p("academic.typ"))
    _write(p("letter.typ"), NON_ASCII + cv.LETTER_MARKER + "\n")
    res["letter"] = cv.is_letter(p("letter.typ"))

    _write(p("loose.typ"), NON_ASCII + "#set par(leading: 1.5em)\n#set text(size: 12pt)\n")
    res["leading_warn"] = cv._leading_warn(p("loose.typ")).startswith("WARN  leading 1.500em")
    res["size_warn"] = cv._body_size_warn(p("loose.typ")).startswith("WARN  body text 12pt")
    res["family_default"] = [round(x, 3) for x in cv._family_default("color-band", 1) or ()]

    # `éimport` is one identifier, not an import: decoding the é as two replacement characters would split it
    skill = os.path.join(w, "skill")
    os.makedirs(os.path.join(skill, "templates"))
    _write(os.path.join(skill, "templates", "lib.typ"), "#let derive() = 1\n")
    cvdir = os.path.join(w, "lib-cv")
    os.makedirs(cvdir)
    _write(os.path.join(cvdir, "lib.typ"), "#let derive() = 1\n")
    _write(os.path.join(cvdir, "cv.typ"), NON_ASCII + 'Voir éimport "lib.typ" ici\n')
    res["lib"] = [str(lvl) for lvl, _ in cv.check_lib_integrity(os.path.join(cvdir, "cv.typ"), skill)]

    _write(p("clone.typ"), NON_ASCII + '#let accent = rgb("#7d2231")\n')
    res["check_cv_accent_warn"] = "WARN  template default accent" in _check_cv_output(cv, p("clone.typ"))

    sweep = os.path.join(w, "sweep")
    os.makedirs(sweep)
    _write(os.path.join(sweep, "cv-2page.typ"), NON_ASCII + "// vitae: pages=2 fill=90-99\n")
    rc, out = _check_all_output(cv, sweep)
    res["sweep"] = [rc, "expects 2 90 99" in out]

    _write(p("review.md"), "runtime: sub-agents\ncv: cv.typ\npersonas: recruiter, hiring manager, ATS, "
           "nurse-recruiter segment\nlayout: subagent haiku — café\n## Findings\n"
           "- recruiter: le résumé enterre le titre → applied\n- ATS: mot-clé absent → rejected: aucun fait\n")
    os.utime(p("review.md"), (2_000, 2_000))
    _write(p("cv.typ"), "#lorem(5)\n")
    os.utime(p("cv.typ"), (1_000, 1_000))
    record = review_record.check_review_record(p("cv.typ"))
    res["record"] = [str(lvl) for lvl, _ in record][-1:] + [str(not any(m.startswith("review record unreadable") for _, m in record))]
    res["layout"] = review_record.layout_report_line(p("cv.typ"))

    res["version"] = jsonout.skill_version()
    return res


if __name__ == "__main__":      # python -X utf8=0 _locale_probe.py '<sys.path as JSON>' <workdir>
    sys.path[:0] = json.loads(sys.argv[1])
    print(json.dumps(run(sys.argv[2])))
