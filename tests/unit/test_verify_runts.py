"""vitae.verify.runts: a wrapped bullet whose last line is a few glyphs alone is a FAIL; everything else passes.

The CVs are tiny Typst documents that draw their list through lib.typ's marker, compiled with the `typst` package."""
import dataclasses
import shutil

import pypdfium2
import pytest
import typst
from _paths import ROOT
from vitae.core.base import Mark, WordBox
from vitae.core.level import Level
from vitae.verify import pdf, runts
from vitae.verify.bounds import MAX_PAGE_WORK
from vitae.verify.gates import LAYOUT_GATES, _bullet_runts, make_context
from vitae.verify.runts import BulletLine, Extent, check_runts, is_runt

PAGE_330 = "width: 330pt, height: 200pt, margin: 20pt"

# (script, font, full filler line, long closing text, runt, rtl)
SCRIPTS = {
    "latin": ("Libertinus Serif", "Reduced the nightly billing report time after profiling slow queries and",
              "adding indexes so the whole report now finishes well inside the maintenance window each night.",
              "ms.", False),
    # Non-Latin: forced line breaks (a backslash), every line well under the measure (at most about 60 % of it, so no plausible
    # font wraps one on its own); the Noto script faces are fetched by tests/fetch_fonts.sh (CJK is not: that case skips on CI), the test skips where Typst lacks them.
    "arabic": ("Noto Naskh Arabic", "قمت بتقليل زمن التقرير بعد تحليل الاستعلامات البطيئة",
               "وأضفت الفهارس اللازمة للتقرير الليلي", "ثانية.", True),
    "cjk": ("Noto Sans CJK JP", "遅いクエリを分析してインデックス \\ を追加し処理時間を短縮しました",
            "その結果レポートが夜間に完了します", "分。", False),
    "thai": ("Noto Sans Thai", "ลดเวลาการสร้างรายงานประจำคืน \\ หลังจากวิเคราะห์คิวรีที่ช้า",
             "ทำให้รายงานเสร็จสิ้นทุกคืน", "ที", False),
}


def _compile(tmp_path, name, font, bullet, rtl):
    for f in ("lib.typ", "icons.typ"):
        shutil.copy(ROOT / "templates" / f, tmp_path / f)
    src = ('#import "lib.typ": drawn-marker, list-marker\n#set page(width: 330pt, height: 200pt, margin: 20pt)\n'
           f'#set text(font: "{font}", size: 10pt{", dir: rtl" if rtl else ""})\n'
           '#set par(justify: false)\n'
           '#set list(marker: list-marker("dot", black), indent: 0pt, spacing: 1em, body-indent: 6pt)\n'
           f"{bullet}\n")
    typ = tmp_path / f"{name}.typ"
    typ.write_text(src, encoding="utf-8")
    out = tmp_path / f"{name}.pdf"
    typst.compile(str(typ), output=str(out))
    return make_context(str(typ), str(out), pdf.extract_text(str(out), "pdfium"), src, "pdfium", can_query=True)


def _fonts():
    return {f.lower() for f in typst.Fonts(include_system_fonts=True).families()} if hasattr(typst, "Fonts") else set()


def _bullets(first, rest):
    return f"- {first}{rest}\n- Second bullet, one line.\n"


@pytest.mark.parametrize("script", sorted(SCRIPTS))
def test_runt_fails_full_last_line_and_one_line_pass(tmp_path, script):
    font, first, closing, runt, rtl = SCRIPTS[script]
    if font.lower() not in _fonts():
        pytest.skip(f"{font} is not visible to typst-py: the test would measure a fallback face")
    runt_cv = _compile(tmp_path, "runt", font, _bullets(first, f" \\ {runt}"), rtl)
    out = _bullet_runts(runt_cv)
    assert [lvl for lvl, _ in out] == [Level.FAIL], out
    assert rtl or runt in out[0][1]   # the Arabic extraction reorders glyphs: only its verdict is asserted
    full = _compile(tmp_path, "full", font, _bullets(first, f" \\ {closing}"), rtl)
    assert _bullet_runts(full) == []
    one = _compile(tmp_path, "one", font, _bullets(runt, ""), rtl)
    assert _bullet_runts(one) == []


def test_runt_after_natural_wrap_fails(tmp_path):
    """No forced break: the text itself wraps and leaves one short word on the second line."""
    first = SCRIPTS["latin"][1]
    for n in range(1, 60):   # widen the body one letter at a time until the wrap leaves a lone word
        typ, out_pdf, src = _write_doc(tmp_path, "nat", PAGE_330, f"- {first} {'x' * n} ms.\n")
        if "ms." in pdf.extract_text(out_pdf, "pdfium").splitlines():     # the lone last word: the gate is run on this one
            out = _bullet_runts(_context(typ, out_pdf, src))
            assert [lvl for lvl, _ in out] == [Level.FAIL] and "ms." in out[0][1]
            return
    pytest.fail("no width produced a lone last word")


def test_no_lib_marker_is_not_measured_never_a_fail(tmp_path):
    src = "#set page(width: 330pt, height: 200pt)\n- Plain list item that wraps onto the next line because it is long \\ ms.\n"
    typ = tmp_path / "plain.typ"
    typ.write_text(src, encoding="utf-8")
    out_pdf = tmp_path / "plain.pdf"
    typst.compile(str(typ), output=str(out_pdf))
    ctx = make_context(str(typ), str(out_pdf), pdf.extract_text(str(out_pdf), "pdfium"), src, "pdfium")
    out = _bullet_runts(ctx)
    assert [lvl for lvl, _ in out] == [Level.WARN]
    assert "not measured" in out[0][1]


def test_gate_is_registered_and_needs_the_query():
    assert "bullet-runts" in [g.name for g in LAYOUT_GATES]


def test_pypdf_fallback_downgrades_to_warn(tmp_path):
    font, first, _, runt, rtl = SCRIPTS["latin"]
    ctx = _compile(tmp_path, "pp", font, _bullets(first, f" \\ {runt}"), rtl)
    ctx = dataclasses.replace(ctx, backend="pypdf")
    assert [lvl for lvl, _ in _bullet_runts(ctx)] == [Level.WARN]


# ---- the threshold, on synthetic lines (width in line heights of 10pt; widest line 400pt)
def _lines(last_w):
    full = BulletLine(1, Extent(0, 400), 10, "x")
    return [full, BulletLine(1, Extent(0, last_w), 10, "y")]


@pytest.mark.parametrize(("width", "expected"), [(15, True), (25, True), (26, False), (60, False), (200, False)])
def test_threshold_edge(width, expected):
    assert is_runt(_lines(width)) is expected


def test_wide_type_is_judged_against_the_bullet_too():
    """A last line short in line heights but not against a narrow column's widest line is not a runt."""
    narrow = [BulletLine(1, Extent(0, 100), 40, "x"), BulletLine(1, Extent(0, 50), 40, "y")]
    assert is_runt(narrow) is False


def test_single_line_is_never_a_runt():
    assert is_runt([BulletLine(1, Extent(0, 5), 10, "ms.")]) is False


def test_check_runts_without_query_warns():
    assert check_runts(None, None, fail=lambda m: (Level.FAIL, m))[0][0] == Level.WARN


# ---- layouts: small type, columns, edge side, page breaks
LATIN_FIRST = SCRIPTS["latin"][1]
LATIN_FULL = SCRIPTS["latin"][2]


def _write_doc(tmp_path, name, page, body):
    """Compile a CV drawn through lib.typ's marker with a free page setup and body: (typ path, pdf path, source)."""
    for f in ("lib.typ", "icons.typ"):
        shutil.copy(ROOT / "templates" / f, tmp_path / f)
    src = (f'#import "lib.typ": list-marker\n#set page({page})\n'
           '#set text(font: "Libertinus Serif", size: 10pt)\n#set par(justify: false)\n'
           '#set list(marker: list-marker("dot", black), indent: 0pt, spacing: 1em, body-indent: 6pt)\n'
           f"{body}\n")
    typ = tmp_path / f"{name}.typ"
    typ.write_text(src, encoding="utf-8")
    out = tmp_path / f"{name}.pdf"
    typst.compile(str(typ), output=str(out))
    return str(typ), str(out), src


def _context(typ, out, src):
    """The gates' context of a compiled document (reads its marks and words: the costly part of a test)."""
    return make_context(typ, out, pdf.extract_text(out, "pdfium"), src, "pdfium", can_query=True)


def _compile_doc(tmp_path, name, page, body):
    return _context(*_write_doc(tmp_path, name, page, body))


def test_small_type_measures_each_bullet_from_its_own_line(tmp_path):
    """Tight 6pt type: the previous bullet's line sits within 8pt of the next marker. A real runt must still
    be found, and a bullet next to one-line bullets is not judged on their lines."""
    tight = '#set text(size: 6pt)\n#set par(leading: 0.2em)\n#set list(spacing: 0pt)\n'
    page = "width: 330pt, height: 200pt, margin: 20pt"
    real = _compile_doc(tmp_path, "s1", page, tight + f"- {LATIN_FIRST} \\ ms.\n- Another.\n")
    out = _bullet_runts(real)
    assert [lvl for lvl, _ in out] == [Level.FAIL], out
    assert "ms." in out[0][1]
    full = _compile_doc(tmp_path, "s2", page, tight + f"- {LATIN_FIRST} \\ {LATIN_FULL}\n- Git.\n- Ok.\n")
    assert _bullet_runts(full) == []


@pytest.mark.parametrize("sidebar_left", [True, False])
def test_runt_next_to_a_sidebar_is_found(tmp_path, sidebar_left):
    side = "[" + " \\ ".join(f"Sidebar line {i} of words" for i in range(14)) + "]"
    main = f"[\n- {LATIN_FIRST} \\ ms.\n- Another bullet, one line.\n]"
    cells = f"{side}, {main}" if sidebar_left else f"{main}, {side}"
    cols = "110pt, 1fr" if sidebar_left else "1fr, 110pt"
    ctx = _compile_doc(tmp_path, "cols", "width: 400pt, height: 200pt, margin: 20pt",
                       f"#grid(columns: ({cols}), column-gutter: 16pt, {cells})")
    out = _bullet_runts(ctx)
    assert [lvl for lvl, _ in out] == [Level.FAIL], out
    assert "ms." in out[0][1]


def test_right_flushed_line_after_a_ltr_bullet_is_not_its_continuation(tmp_path):
    """The bullet's text ends at the column's right edge; a right-aligned paragraph right below shares that
    edge but is not the bullet's second line (left-to-right text continues on the LEFT edge)."""
    body = ("#set block(spacing: 0.3em)\n"
            f"- #box(width: 100%, align(right)[{LATIN_FIRST}])\n#align(right)[ms.]\n")
    ctx = _compile_doc(tmp_path, "edge", "width: 330pt, height: 200pt, margin: 20pt", body)
    assert _bullet_runts(ctx) == []


def _ms_on_page(out_pdf, count, page):
    """True when the PDF has `count` pages and "ms." is on the 1-based `page`."""
    doc = pypdfium2.PdfDocument(out_pdf)
    return len(doc) == count and "ms." in doc[page - 1].get_textpage().get_text_range()


def _split_across_pages(tmp_path, body_for):
    """Scan the room left on page 1 until the bullet's last line lands alone at the top of page 2; the gates' context
    is read for that one document only."""
    for room in range(20, 90):
        typ, out_pdf, src = _write_doc(tmp_path, f"pb{room}", "width: 330pt, height: 100pt, margin: 20pt", body_for(room))
        if _ms_on_page(out_pdf, 2, 2):
            return _context(typ, out_pdf, src)
    pytest.fail("no room made the bullet break across pages")


@pytest.fixture(scope="module")
def split_ctx(tmp_path_factory):
    """The bullet whose last line ("ms.") is alone at the top of page 2: built once for the tests that read it."""
    return _split_across_pages(tmp_path_factory.mktemp("split"),
                               lambda room: f"#v({room}pt)\n- {LATIN_FIRST} \\ {LATIN_FIRST} \\ ms.\n")


def test_runt_at_the_top_of_the_next_page_is_found(split_ctx):
    out = _bullet_runts(split_ctx)
    assert [lvl for lvl, _ in out] == [Level.FAIL], out
    assert "ms." in out[0][1]

def test_inline_separator_is_not_a_bullet(tmp_path):
    """drawn-marker used as an inline separator dot must not be tagged <vitae-bullet>; list-marker is."""
    from vitae.verify.groups.query import typst_values
    for f in ("lib.typ", "icons.typ"):
        shutil.copy(ROOT / "templates" / f, tmp_path / f)
    typ = tmp_path / "sep.typ"
    typ.write_text('#import "lib.typ": drawn-marker, list-marker\n#set page(width: 300pt, height: 100pt)\n'
                   '#set list(marker: list-marker("dot", black))\n'
                   'Nî #drawn-marker("dot", auto) Nî #drawn-marker("mid", auto) Nî\n\n- one\n- two\n', encoding="utf-8")
    vals = typst_values(str(typ), "<vitae-bullet>", str(tmp_path))
    assert vals is not None and len(vals) == 2


def test_next_page_runt_is_reported_on_its_own_page(split_ctx):
    assert "page 2" in _bullet_runts(split_ctx)[0][1]


def test_complete_bullet_then_aligned_line_on_next_page_is_not_a_runt(tmp_path):
    """The bullet ended on page 1 above the bottom; page 2 starts with a short line at the same left edge."""
    for room in range(10, 30, 4):   # beyond that the bullet is within ~2 line pitches of the bottom: a continuation cannot be excluded
        body = (f"#v({room}pt)\n- {LATIN_FIRST} more words to wrap the line here ok.\n"
                "#pagebreak()\n#pad(left: 9.6pt)[2021]\n")
        ctx = _compile_doc(tmp_path, f"np{room}", "width: 330pt, height: 120pt, margin: 20pt", body)
        assert _bullet_runts(ctx) == [], room


def test_runt_is_found_whatever_the_room_left_widow_orphan_control(tmp_path):
    """Typst moves the last two lines together, so page 1 can end two line pitches above the content bottom:
    every split of a 5-line bullet whose last word lands alone on page 2 is found."""
    body_for = f"#v({{room}}pt)\n- {LATIN_FIRST} \\ {LATIN_FIRST} \\ {LATIN_FIRST} \\ ms.\n"
    split = 0
    for room in range(40):
        typ, out_pdf, src = _write_doc(tmp_path, f"wo{room}", "width: 330pt, height: 160pt, margin: 20pt",
                                       body_for.format(room=room))
        if _ms_on_page(out_pdf, 2, 2):
            split += 1
            out = _bullet_runts(_context(typ, out_pdf, src))
            assert [lvl for lvl, _ in out] == [Level.FAIL], (room, out)
    assert split >= 3   # the sweep must reach splits, widow/orphan ones included


@pytest.mark.parametrize(("top", "bottom"), [(20, 60), (60, 20)])
def test_runt_is_found_with_unequal_margins(tmp_path, top, bottom):
    page = f"width: 330pt, height: 160pt, margin: (top: {top}pt, bottom: {bottom}pt, x: 20pt)"
    # a full first page tells the document where its content ends
    fill = "#block(height: 100%, align(bottom)[Filled.])\n#pagebreak()\n"
    for room in range(90):
        typ, out_pdf, src = _write_doc(tmp_path, f"um{room}", page,
                                       f"{fill}#v({room}pt)\n- {LATIN_FIRST} \\ {LATIN_FIRST} \\ ms.\n")
        if _ms_on_page(out_pdf, 3, 3):
            out = _bullet_runts(_context(typ, out_pdf, src))
            assert [lvl for lvl, _ in out] == [Level.FAIL], (room, out)
            return
    pytest.fail("no room made the bullet break across pages")


def test_complete_bullet_far_above_the_bottom_with_a_small_bottom_margin_is_not_a_runt(tmp_path):
    """Top margin 60, bottom 20: the bullet ends 50pt above the content bottom, which page 1's text shows."""
    page = "width: 330pt, height: 160pt, margin: (top: 60pt, bottom: 20pt, x: 20pt)"
    for room in range(0, 16, 4):
        body = ("#block(height: 100%, align(bottom)[Filled.])\n#pagebreak()\n"
                f"#v({room}pt)\n- {LATIN_FIRST} more words to wrap the line ok.\n"
                "#pagebreak()\n#pad(left: 9.6pt)[2021]\n")
        ctx = _compile_doc(tmp_path, f"fp{room}", page, body)
        assert _bullet_runts(ctx) == [], room


def test_next_bullet_with_a_lowered_inline_element_does_not_hide_the_runt(tmp_path):
    body = f"- {LATIN_FIRST} \\ ms.\n- Cut floor area by #box(baseline: 4pt)[30] m2 across sites.\n"
    ctx = _compile_doc(tmp_path, "low", "width: 330pt, height: 200pt, margin: 20pt", body)
    out = _bullet_runts(ctx)
    assert [lvl for lvl, _ in out] == [Level.FAIL], out
    assert "ms." in out[0][1]


@pytest.mark.parametrize("sidebar_left", [True, False])
def test_runt_next_to_a_justified_sidebar_with_a_narrow_gutter_is_found(tmp_path, sidebar_left):
    side = "[" + " ".join(f"Sidebar words {i} of a justified paragraph text" for i in range(14)) + "]"
    main = (f"[\n- {LATIN_FIRST} adding indexes so the report now finishes \\ ms.\n"
            "- Another bullet, one line.\n]")
    cells = f"{side}, {main}" if sidebar_left else f"{main}, {side}"
    cols = "110pt, 1fr" if sidebar_left else "1fr, 110pt"
    ctx = _compile_doc(tmp_path, "just", "width: 400pt, height: 300pt, margin: 20pt",
                       "#set par(justify: true)\n"
                       f"#grid(columns: ({cols}), column-gutter: 12pt, {cells})")
    out = _bullet_runts(ctx)
    assert [lvl for lvl, _ in out] == [Level.FAIL], out
    assert "ms." in out[0][1]


def test_not_measured_notice_names_the_tagging_markers():
    out = check_runts([], None, fail=lambda m: (Level.FAIL, m))
    assert "list-marker" in out[0][1] and "bullet-marked" in out[0][1]


def test_a_page_denser_than_the_work_limit_is_not_located(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("located_bullets called on a dense page")

    monkeypatch.setattr(runts, "located_bullets", refuse)
    words: list[WordBox] = [((0.0, 0.0, 1.0, 1.0), "w")] * 2000
    marks = [Mark(text="m", page=1, x=0.0, y=float(i)) for i in range(MAX_PAGE_WORK // 2000 + 1)]

    layout = runts.bullet_layout(marks, [(600.0, 800.0, words)])

    assert layout.located == []
    assert layout.pages == [words]
