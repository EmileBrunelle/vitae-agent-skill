"""verify.py / pick_design behaviour checks on the scratch copy, ported from run_all.sh (drawn header, --all, lowered fill,
placeholders, review record, facts, --text/--render/--crops, font fallback).

Every assertion is run_all's, with its strictness: where the bash read stdout alone (`$(...)` without 2>&1, `>"$log"`) the test
reads `.stdout`; where it merged stderr it reads `.output`.
"""
from __future__ import annotations

import os
import re
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
from harness import CheckResult, Template, discover_templates, grep, importable_isolated, typst_compile

Check = Callable[..., CheckResult]


def _first_template_target() -> tuple[str, int, int]:
    t = discover_templates()[0]
    return t.family, t.fill_min, t.fill_max


def _compile(src: Path, pdf: Path, cwd: Path) -> None:
    r = typst_compile(src, pdf, cwd)
    assert r.rc == 0, f"typst could not compile {src.name}\n{r.output}"


def test_drawn_header(check: Check, py: str, scratch: Path) -> None:
    """pick_design --init writes the drawn fill target as line 1 of cv.typ."""
    r = check("drawn-header", [py, "-I", "scripts/pick_design.py", "--name", "Jane Roe", "--field", "accounting", "--market", "ca",
                               "--init", scratch / "drawn", "--no-font-check"])
    assert r.rc == 0, r.output
    first = (scratch / "drawn" / "cv.typ").read_text(encoding="utf-8").splitlines()[0]
    assert re.fullmatch(r"// vitae: pages=1 fill=[0-9]+-[0-9]+", first), f"no header on line 1: {first!r}"


def test_all_broken(check: Check, py: str, scratch: Path) -> None:
    """--all re-runs verify.py once per deliverable; a broken child must make the sweep FAIL."""
    d = scratch / "all-broken"
    d.mkdir()
    (d / "cv.typ").write_text("#this is not valid typst (\n")
    r = check("all-broken", [py, "-I", "scripts/verify.py", "--all", d])
    assert r.rc != 0, "--all exited 0 on a broken cv.typ"
    assert "FAIL" in r.output, "--all printed no FAIL"


def test_lowered_fill_warns(check: Check, py: str, scratch: Path) -> None:
    """A lowered FILL_MIN argument is a loud WARN (exit 0), never silent; below the floor it FAILs."""
    f, a, b = _first_template_target()
    d = scratch / "templates" / "families" / f
    drawn = d / "_drawn.typ"
    rel = drawn.relative_to(scratch)
    drawn.write_text(f"// vitae: pages=1 fill={a}-{b}\n" + (d / "resume.typ").read_text(encoding="utf-8"), encoding="utf-8")
    try:
        r = check("lowered-fill-warns/header", [py, "-I", "scripts/verify.py", rel, 1, a, b, "--allow-placeholders"])
        assert grep(r.stdout, r"^PASS "), f"header target did not pass\n{r.output}"
        r = check("lowered-fill-warns/lowered", [py, "-I", "scripts/verify.py", rel, 1, a - 6, 100, "--allow-placeholders"])
        assert r.rc == 0, f"exit non-zero\n{r.output}"
        assert grep(r.stdout, r"^WARN  fill target lowered below drawn target"), "no WARN"
        assert grep(r.stdout, r"^PASS \(fill target lowered: "), "no PASS summary"
        r = check("lowered-fill-warns/65", [py, "-I", "scripts/verify.py", rel, 1, 65, 100, "--allow-placeholders"])
        assert r.rc == 0, f"65-100 lowered target refused\n{r.output}"
        assert grep(r.output, r"^PASS \(fill target lowered: "), f"65 no PASS-lowered\n{r.output}"
        r = check("lowered-fill-warns/50", [py, "-I", "scripts/verify.py", rel, 1, 50, 100, "--allow-placeholders"])
        assert r.rc != 0, f"below-floor lowered target exited 0\n{r.output}"
        assert grep(r.output, r"^FAIL  fill target lowered to 50-100% is below the lowered-target floor"), f"no floor FAIL\n{r.output}"
    finally:
        drawn.unlink(missing_ok=True)
        drawn.with_suffix(".pdf").unlink(missing_ok=True)


def test_raw_template_fails_placeholders(check: Check, py: str, scratch: Path) -> None:
    """Without --allow-placeholders a raw template must FAIL on that gate (the opt-out must never become the default)."""
    f, a, b = _first_template_target()
    d = scratch / "templates" / "families" / f
    raw = d / "_raw.typ"
    raw.write_text((d / "resume.typ").read_text(encoding="utf-8"), encoding="utf-8")
    try:
        r = check("raw-template-fails-placeholders", [py, "-I", "scripts/verify.py", raw.relative_to(scratch), 1, a, b])
        assert r.rc != 0, "a raw template passed without --allow-placeholders"
        assert grep(r.output, r"^FAIL  template placeholder left in the text"), f"no placeholder FAIL\n{r.output}"
    finally:
        raw.unlink(missing_ok=True)
        raw.with_suffix(".pdf").unlink(missing_ok=True)


def _fill_samples(src: str) -> str:
    """The template's samples filled with plain text, so the placeholder gate does not decide (written for swiss-grid)."""
    from vitae.verify import placeholders
    for ph in sorted(placeholders.placeholders_in(src), key=len, reverse=True):
        if ph.startswith("["):
            src = re.sub(r"\\?\[" + re.escape(ph[1:-1]) + r"\\?\]", "Sample text", src)
    src = src.replace("Firstname Lastname", "Jane Roe").replace("(555) 555-0100", "(613) 555-0142")
    src = re.sub(r"me\\?@example\.com", r"jane\\@roe.test", src)
    return src


def test_review_record_required(check: Check, py: str, scratch: Path) -> None:
    """Delivery needs the step-7 review record: all mechanical gates passing still exits 1 without review.md (the output
    ends on FAIL, never on a PASS) and passes once a valid record newer than the .typ sits beside it."""
    tpl = next(t for t in discover_templates() if t.family == "swiss-grid" and t.name == "resume")
    a, b = tpl.fill_min, tpl.fill_max
    d = scratch / "templates" / "families" / "swiss-grid"
    typ = d / "_drawn_rr.typ"
    typ.write_text(_fill_samples((d / "resume.typ").read_text(encoding="utf-8")), encoding="utf-8")
    rel = typ.relative_to(scratch)
    verify = [py, "-I", "scripts/verify.py", rel, 1, a, b]
    r = check("review-record-required/missing", verify)
    assert r.rc == 1, f"a passing CV without review.md exited {r.rc}\n{r.output}"
    assert grep(r.output, r"^mechanical gates: PASS"), f"mechanical gates did not pass\n{r.output}"
    assert grep(r.output, r"^FAIL  review record missing"), f"no review record FAIL\n{r.output}"
    assert r.output.rstrip("\n").splitlines()[-1][:4] == "FAIL", f"last line is not FAIL\n{r.tail(3)}"
    assert not grep(r.output, r"^PASS "), "PASS printed without a record"
    review = d / "review.md"
    review.write_text("runtime: sub-agents\ncv: _drawn_rr.typ\npersonas: recruiter, hiring manager, ATS\nlayout: subagent haiku\n"
                      "## Findings\n- ATS: sample finding -> applied\n")
    try:
        r = check("review-record-required/valid", verify)
        assert r.rc == 0, f"valid record: exit {r.rc}\n{r.output}"
        assert grep(r.output, r"^INFO  review record: runtime sub-agents"), f"no INFO summary\n{r.output}"
        assert grep(r.output, r"^PASS "), f"no PASS with a valid record\n{r.output}"
        # --rebuild skips only the record check, loudly: a stale record (fixed in 2000) still passes with the flag.
        os.utime(review, (946684800, 946684800))
        r = check("review-record-required/stale", verify)
        assert r.rc == 1, f"stale record without --rebuild exited {r.rc}\n{r.output}"
        assert "review record older than" in r.output, f"stale record: no 'older than' message\n{r.output}"
        r = check("review-record-required/rebuild", [*verify, "--rebuild"])
        assert r.rc == 0, f"--rebuild: exit {r.rc}\n{r.output}"
        assert grep(r.output, r"^PASS \(review record skipped: --rebuild, candidate rebuild\)"), \
            f"--rebuild not loud on the verdict\n{r.output}"
    finally:
        review.unlink(missing_ok=True)
        typ.unlink(missing_ok=True)
        typ.with_suffix(".pdf").unlink(missing_ok=True)


def test_facts_years_and_dates() -> None:
    from vitae.verify.text import check_facts_coverage
    f = "Stage, Acme, 2020-03 to 2021\n"
    for ok in ("Intern  03/2020\n", "Intern  2021\n", "Intern  Mars 2020\n"):
        w = check_facts_coverage(ok, f)
        assert w == [], f"{ok!r}: false positive {w}"
    for bad, token in (("Intern  04/2020\n", "04/2020"), ("Intern  2019\n", "2019"), ("Intern  Dec 2022\n", "2022")):
        w = check_facts_coverage(bad, f)
        assert len(w) == 1 and f'"{token}"' in w[0], f"{bad!r} not flagged: {w}"


@pytest.mark.parametrize("lang", ["de", "uk"])
def test_language_facts(lang: str, check: Check, py: str, scratch: Path) -> None:
    """A CV and its facts file in German and Ukrainian: `--facts` reads digits only, so no `not in facts file` WARN when the
    numbers agree. tests/language/*.typ are bare Typst without lib.typ, so verify.py legitimately prints `FAIL boundaries carry
    no ink` and a `not measured` WARN on them; this test deliberately rejects only the no-split|hidden|font fallback FAILs."""
    d = scratch / "tests" / "language"
    r = check(f"language-facts/{lang}", [py, "-I", "scripts/verify.py", d / f"{lang}.typ", 1, "--facts", d / f"{lang}-facts.md"])
    assert not grep(r.output, r"^FAIL  compile"), f"{lang}.typ did not compile\n{r.output}"
    assert not grep(r.output, r"^WARN  not in facts file"), f"{lang}: false facts WARN\n{r.output}"
    assert not grep(r.output, r"^FAIL  (no-split|hidden|font fallback)"), f"{lang}: unexpected FAIL\n{r.output}"


@pytest.fixture
def a_template_pdf(run_template: Callable[[Template], CheckResult], scratch: Path) -> Path:
    """The PDF of the first template (its run also keeps it in <out>/pdf)."""
    t = discover_templates()[0]
    run_template(t)
    pdf = scratch / "templates" / "families" / t.family / f"{t.name}.pdf"
    assert pdf.is_file(), "no PDF from the template run"
    return pdf


def test_text_render(a_template_pdf: Path, check: Check, py: str, scratch: Path) -> None:
    """--text / --render: the interface the step docs promise, whatever backend is installed."""
    r = check("text-render/text", [py, "-I", "scripts/verify.py", "--text", a_template_pdf])
    assert r.rc == 0 and re.search(r"[A-Za-z]", r.stdout), "--text printed nothing"
    r = check("text-render/render", [py, "-I", "scripts/verify.py", "--render", a_template_pdf, "--out", scratch / "render", "--ppi", 72])
    assert r.rc == 0, r.output
    first = r.stdout.splitlines()[0]
    assert os.path.basename(first) == f"{a_template_pdf.stem}-p1.png" and os.path.getsize(scratch / first) > 0, \
        f"bad --render output: {r.stdout}"


def test_text_render_bad(a_template_pdf: Path, check: Check, py: str, scratch: Path) -> None:
    """Corrupt or non-PDF input: one FAIL line and exit 1, never silence or a traceback; a re-render drops its stale pages."""
    d = scratch / "bad"
    d.mkdir()
    (d / "bad.pdf").write_text("this is not a pdf\n")
    for m in ("--text", "--render"):
        r = check(f"text-render-bad/{m.strip('-')}", [py, "-I", "scripts/verify.py", m, d / "bad.pdf", "--out", d / "o"])
        txt = r.output.rstrip("\n")
        assert r.rc == 1, f"{m} exit {r.rc}, expected 1: {txt}"
        assert len(txt.splitlines()) == 1 and grep(txt, r"^FAIL  .*not a readable PDF"), f"{m}: bad message: {txt}"
    o = d / "o"
    o.mkdir(exist_ok=True)
    stem = a_template_pdf.stem
    for n in (f"{stem}-p9.png", "keep.png", f"{stem}x-p9.png"):
        (o / n).touch()
    r = check("text-render-bad/stale", [py, "-I", "scripts/verify.py", "--render", a_template_pdf, "--out", o, "--ppi", 40])
    assert r.rc == 0, r.output
    assert not (o / f"{stem}-p9.png").exists(), "stale page kept"
    assert (o / "keep.png").exists() and (o / f"{stem}x-p9.png").exists(), "removed an unrelated file"


def _typ(d: Path, name: str, body: str) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.typ"
    p.write_text(body)
    _compile(p, d / f"{name}.pdf", d.parent)
    return p


def _icons(r: CheckResult) -> int:
    return sum(1 for ln in r.stdout.splitlines() if re.search(r"-icon[0-9]*\.png$", ln))


def test_render_crops(check: Check, py: str, scratch: Path) -> None:
    """--render --crops: a solid band and a vector mark each get a <stem>-p<N>-<band>.png; plain --render is unchanged."""
    d = scratch / "crops"
    _typ(d, "c", '#set page(width: 21cm, height: 29.7cm, margin: 2cm)\n#set text(size: 11pt)\n'
                 '#block(fill: rgb("#1b4965"), width: 100%, inset: 12pt)[#text(fill: white)[Band title]]\n#v(1cm)\n'
                 '#grid(columns: 2, gutter: 8pt, circle(radius: 5pt, fill: black), [mail\\@example.org])\n')
    r = check("render-crops/plain", [py, "-I", "scripts/verify.py", "--render", d / "c.pdf", "--out", d / "a"])
    assert len(r.stdout.splitlines()) == 1, "plain --render printed more than the page PNG"
    r = check("render-crops/crops", [py, "-I", "scripts/verify.py", "--render", d / "c.pdf", "--out", d / "b", "--crops"])
    assert r.rc == 0, r.output
    lines = r.stdout.splitlines()
    assert os.path.basename(lines[0]) == "c-p1.png", f"page PNG not first: {r.stdout}"
    assert lines[1].endswith("/c-p1-fill1.png"), f"no fill1 crop: {r.stdout}"
    assert any(ln.endswith("/c-p1-icon1.png") for ln in lines), f"no icon1 crop: {r.stdout}"
    assert all(os.path.getsize(scratch / ln) > 0 for ln in lines), f"empty or missing file in: {r.stdout}"
    # Stale crops: recompile without the band, re-render into the same --out: the old -fill1/-icon1 go, a sibling stem's stay.
    (d / "b" / "cx-p1-fill1.png").touch()
    _typ(d, "c", '#set page(width: 21cm, height: 29.7cm, margin: 2cm)\n#set text(size: 11pt)\nPlain text only.\n')
    r = check("render-crops/stale", [py, "-I", "scripts/verify.py", "--render", d / "c.pdf", "--out", d / "b", "--crops"])
    assert r.rc == 0, r.output
    left = sorted(os.listdir(d / "b"))
    assert not any(re.fullmatch(r"c-p1-(fill|icon)[0-9]+\.png", n) for n in left), f"stale crop kept: {left}"
    assert "cx-p1-fill1.png" in left and "c-p1.png" in left, f"removed too much: {left}"


def test_render_crops_sidebar(check: Check, py: str, scratch: Path) -> None:
    """A sidebar covering 70% of the page must not become the "paper": one fill of the sidebar's own width."""
    from PIL import Image  # a missing Pillow is a FAIL (the bash check failed too), not a skip
    d = scratch / "crops-sb"
    _typ(d, "s", '#set page(width: 21cm, height: 29.7cm, margin: 0pt, fill: white)\n#set text(size: 11pt)\n'
                 '#place(top + left, rect(width: 70%, height: 100%, fill: rgb("#1e5631"), inset: 2cm)[#text(fill: white)[Sidebar text]])\n'
                 '#place(top + right, box(width: 30%, inset: 1cm)[Main column text])\n')
    r = check("render-crops-sidebar", [py, "-I", "scripts/verify.py", "--render", d / "s.pdf", "--out", d / "o", "--crops"])
    assert r.rc == 0, r.output
    with Image.open(d / "o" / "s-p1-fill1.png") as im:
        w = im.size[0]
    # 70% of 21 cm at 300 ppi = 1736 px (+ padding); a whole-page fill is 2480
    assert 1600 <= w <= 2000, f"sidebar fill is {w} px wide"


MARKS = ('#let tel = box(width: 6pt, height: 10pt, fill: rgb("#1b4965"))\n'
         '#let mail = box(width: 11pt, height: 8pt, stroke: 1pt + rgb("#1b4965"))\n'
         '#let pin = circle(radius: 4pt, fill: rgb("#1b4965"))\n#let web = circle(radius: 4.5pt, stroke: 1pt + rgb("#1b4965"))\n'
         '#tel#sym.space.nobreak (555) 555-0100  #h(1em) #mail#sym.space.nobreak me\\@example.com  #h(1em) '
         '#pin#sym.space.nobreak City  #h(1em) #web#sym.space.nobreak example.com\n')


def test_render_crops_marks(check: Check, py: str, scratch: Path) -> None:
    """A solid phone glyph and a mail mark one no-break space from its value are kept (the 4 contact marks), the heading
    squares (same shape 3+ times) are not; a dark page under a white card gives the card and the band, not a whole-page
    fill; a plain --render drops the stem's old crops."""
    from PIL import Image  # a missing Pillow is a FAIL (the bash check failed too), not a skip
    d = scratch / "crops-marks"
    _typ(d, "m", '#set page(width: 21cm, height: 29.7cm, margin: 2cm)\n#set text(size: 11pt)\n'
                 '#let sq = box(width: 5pt, height: 5pt, fill: rgb("#1b4965"))\n' + MARKS +
                 '#for t in ("Skills", "Work", "Study", "Other") [\n  #v(1cm) #sq #sym.space.nobreak *#t*\n]\n')
    r = check("render-crops-marks/icons", [py, "-I", "scripts/verify.py", "--render", d / "m.pdf", "--out", d / "o", "--crops"])
    assert r.rc == 0, r.output
    assert _icons(r) == 4, f"want exactly the 4 contact marks, got: {r.stdout}"
    r = check("render-crops-marks/plain", [py, "-I", "scripts/verify.py", "--render", d / "m.pdf", "--out", d / "o"])
    assert r.rc == 0, r.output
    assert os.listdir(d / "o") == ["m-p1.png"], f"plain --render kept crops: {os.listdir(d / 'o')}"
    _typ(d, "k", '#set page(width: 21cm, height: 29.7cm, margin: 0pt, fill: rgb("#14213d"))\n#set text(size: 11pt, fill: white)\n'
                 '#place(top + left, dx: 2cm, dy: 6cm, rect(width: 17cm, height: 18cm, fill: white, inset: 1cm)[#text(fill: black)[Card text]])\n'
                 '#place(top + left, dx: 2cm, dy: 1cm, rect(width: 17cm, height: 2cm, fill: rgb("#e63946"), inset: 8pt)[Band])\n')
    r = check("render-crops-marks/card", [py, "-I", "scripts/verify.py", "--render", d / "k.pdf", "--out", d / "ko", "--crops"])
    assert r.rc == 0, r.output
    fills = sorted((d / "ko").glob("k-p1-fill*.png"))
    sizes = []
    for f in fills:
        with Image.open(f) as im:
            sizes.append(im.size)
    assert len(fills) == 2 and all(max(s) < 2300 for s in sizes), f"fills: {sizes}"


SVG_LI = ("M0 1.146C0 .513.526 0 1.175 0h13.65C15.474 0 16 .513 16 1.146v13.708c0 .633-.526 1.146-1.175 1.146H1.175C.526 16 0 15.487 0 "
          "14.854zm4.943 12.248V6.169H2.542v7.225zm-1.2-8.212c.837 0 1.358-.554 1.358-1.248c-.015-.709-.52-1.248-1.342-1.248S2.4 3.226 2.4 "
          "3.934c0 .694.521 1.248 1.327 1.248zm4.908 8.212V9.359c0-.216.016-.432.08-.586c.173-.431.568-.878 1.232-.878c.869 0 1.216.662 "
          "1.216 1.634v3.865h2.401V9.25c0-2.22-1.184-3.252-2.764-3.252c-1.274 0-1.845.7-2.165 1.193v.025h-.016l.016-.025V6.169h-2.4c.03.678 "
          "0 7.225 0 7.225z")
SVG_MAIL = ("M22 7.535V17a3 3 0 0 1-2.824 2.995L19 20H5a3 3 0 0 1-2.995-2.824L2 17V7.535l9.445 6.297l.116.066a1 1 0 0 0 .878 0l.116-.066z "
            "M19 4c1.08 0 2.027.57 2.555 1.427L12 11.797l-9.555-6.37a3 3 0 0 1 2.354-1.42L5 4z")


def test_render_crops_solid(check: Check, py: str, scratch: Path) -> None:
    """A filled LinkedIn square and a filled mail beside their values at 7 pt are kept; a frame stroked at the page edge is
    not the paper: the marks inside are found and no whole-page fill comes out."""
    d = scratch / "crops-solid"
    _typ(d, "s", '#set page(width: 21cm, height: 29.7cm, margin: 2cm)\n#set text(size: 10pt)\n'
                 '#let svg(vb, p) = box(image(bytes("<svg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'" + vb + "\'><path fill=\'#1b4965\' d=\'" + p + "\'/></svg>"), format: "svg", height: 7pt))\n'
                 f'#let li = svg("0 0 16 16", "{SVG_LI}")\n#let mail = svg("0 0 24 24", "{SVG_MAIL}")\n'
                 '#align(center)[#li#sym.space.nobreak in/someone #h(14pt) #mail#sym.space.nobreak someone\\@example.org]\n')
    r = check("render-crops-solid/filled", [py, "-I", "scripts/verify.py", "--render", d / "s.pdf", "--out", d / "o", "--crops"])
    assert r.rc == 0, r.output
    assert _icons(r) == 2, f"want the filled LinkedIn and mail kept, got: {r.stdout}"
    _typ(d, "f", '#set page(width: 21cm, height: 29.7cm, margin: 2cm)\n#set text(size: 11pt)\n'
                 '#place(top + left, dx: -2cm, dy: -2cm, rect(width: 21cm, height: 29.7cm, stroke: 0.5cm + rgb("#1b4965")))\n' + MARKS)
    r = check("render-crops-solid/frame", [py, "-I", "scripts/verify.py", "--render", d / "f.pdf", "--out", d / "fo", "--crops"])
    assert r.rc == 0, r.output
    assert _icons(r) == 4, f"frame at the page edge: want the 4 marks, got: {r.stdout}"
    assert not any(re.search(r"-fill[0-9]*\.png$", ln) for ln in r.stdout.splitlines()), f"frame at the page edge became a fill: {r.stdout}"


def test_font_fallback(check: Check, py: str, scratch: Path) -> None:
    """A CV whose requested family draws no Latin FAILs naming requested and drawn families; one symbol the face lacks is at
    most an INFO; CJK text, math and symbols never FAIL. Needs pypdfium2 (the gate says "NOT checked" without it)."""
    if not importable_isolated("pypdfium2"):
        pytest.skip("needs pypdfium2")
    d = scratch / "tests" / "font_fallback"
    for f in ("bad", "near", "cjk", "math", "symbols", "math-libertinus", "ncm", "raw-only"):
        _compile(d / f"{f}.typ", d / f"{f}.pdf", scratch)

    def gates(f: str) -> str:
        return check(f"font-fallback/{f}", [py, "-I", "scripts/verify.py", "--gates", d / f"{f}.typ", d / f"{f}.pdf"]).output

    assert grep(gates("bad"), r"^FAIL  font fallback: .*vitaenonexistentsans.*latin-ext"), "bad.typ: no font-fallback FAIL"
    assert not grep(gates("near"), r"^(FAIL|WARN)  font fallback"), "near.typ: one symbol must not FAIL or WARN"
    for f in ("cjk", "math", "symbols"):
        assert not grep(gates(f), r"^FAIL  font fallback"), f"{f}.typ: must never FAIL (script, math and symbols are not Latin fallback)"
    for f in ("math-libertinus", "ncm", "raw-only"):
        assert not grep(gates(f), r"^(FAIL|WARN)  font fallback"), f"{f}.typ: must print no FAIL and no WARN font-fallback line"


# ---- header contact block: bounded column, honest row count (swiss-grid, editorial-serif, keyline-corporate, clause-index)

_TITLE_WORDS = {"Target", "title,", "as", "in", "the", "facts", "or", "posting]", "—", "[Degree,", "if", "state", "it]"}


def _title_lines(pdf: Path) -> int:
    """Distinct baselines the placeholder title occupies, read from pdftotext -bbox (words above the first section heading)."""
    import subprocess
    xml = subprocess.run(["pdftotext", "-f", "1", "-l", "1", "-bbox", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    words = [(float(m.group(2)), m.group(4)) for m in re.finditer(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="[\d.]+">([^<]*)</word>', xml)]
    heading_y = min(y for y, w in words if w in ("Profile", "Summary", "Professional"))
    return len({round(y) for y, w in words if y < heading_y and w in _TITLE_WORDS})


@pytest.mark.parametrize("family", ["swiss-grid", "editorial-serif", "keyline-corporate", "clause-index"])
def test_header_contact_block_is_bounded(check: Check, py: str, scratch: Path, family: str) -> None:
    """Five extra links after the profile or portfolio item: the contact block wraps INSIDE its column (it is capped at 55% of the measure), so the
    title keeps its width (placeholder title on at most 2 lines, as with the standard contacts), and the contact-line gate FAILs
    loudly (declared 2 rows) instead of letting the layout drift silently."""
    if not all(shutil.which(t) for t in ("typst", "pdftotext")):
        pytest.skip("typst CLI / poppler missing (the title lines are read with pdftotext -bbox)")
    d = scratch / "templates" / "families" / family
    src = (d / "resume.typ").read_text(encoding="utf-8")
    gh = re.search(r'#contact\(mk\.web\)\[\\\[profile or portfolio — only if in the facts\\\]\]', src)
    assert gh, "no profile or portfolio contact item in the header"
    extra = "".join(f' #h(10pt) #contact(none)[#link("https://example.com/p{i}")[example.com/p{i}]]' for i in range(1, 6))
    typ = d / "_five_links.typ"
    typ.write_text(src[:gh.end()] + extra + src[gh.end():], encoding="utf-8")
    pdf, base = typ.with_suffix(".pdf"), d / "_std.pdf"
    for inp, out in ((typ, pdf), (d / "resume.typ", base)):
        r = check(f"header-five-links/typst-{out.stem}", ["typst", "compile", "--root", scratch, inp, out])
        assert r.rc == 0, r.output
    assert _title_lines(pdf) <= max(2, _title_lines(base)), "the title column was crushed by the contact block"
    tpl = next(t for t in discover_templates() if t.family == family and t.name == "resume")
    r = check(f"header-five-links/{family}", [py, "-I", "scripts/verify.py", typ.relative_to(scratch), 1, tpl.fill_min, tpl.fill_max,
                                              "--allow-placeholders"])
    assert r.rc != 0 and grep(r.output, r"^FAIL  contact line wraps"), f"the gate did not FAIL on the wrapped contact block\n{r.output}"
