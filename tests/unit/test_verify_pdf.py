"""vitae.verify.pdf: project-root detection, family banner, page count / text / word boxes across the PDF
backends, the reading-order approximation, PDF readability, rendering and compile helpers.

The PDFs are tiny Typst documents compiled once per module with the `typst` package."""
import os
import shutil
from pathlib import Path

import pytest
import typst
from _paths import ROOT
from PIL import Image
from vitae.verify import pdf

DOC = """#set document(title: "Test CV")
#set page(width: 200pt, height: 100pt)
Hello world

Second line
#pagebreak()
Page two
"""
ROW = """#set page(width: 300pt, height: 60pt)
Left #h({gap}pt) Right
"""

BACKENDS = [
    pytest.param("pdfium", id="pdfium"),
    pytest.param("poppler", id="poppler", marks=pytest.mark.skipif(
        not (shutil.which("pdfinfo") and shutil.which("pdftotext")), reason="poppler missing")),
    pytest.param("pypdf", id="pypdf"),
]


def _compile(tmp_path, name, src):
    typ = tmp_path / f"{name}.typ"
    typ.write_text(src, encoding="utf-8")
    out = tmp_path / f"{name}.pdf"
    typst.compile(str(typ), output=str(out))
    return str(out)


@pytest.fixture(scope="module")
def two_page(tmp_path_factory):
    return _compile(tmp_path_factory.mktemp("pdf"), "two", DOC)


# ---------------------------------------------------------------- auto_root

class TestAutoRoot:
    def _typ(self, tmp_path, src, depth=0):
        d = tmp_path
        for i in range(depth):
            d = d / f"d{i}"
        d.mkdir(parents=True, exist_ok=True)
        f = d / "cv.typ"
        f.write_text(src, encoding="utf-8")
        return str(f), d

    def test_no_import_means_default_root(self, tmp_path):
        typ, _ = self._typ(tmp_path, "Hello")
        assert pdf.auto_root(typ) is None

    def test_sibling_import_needs_no_root(self, tmp_path):
        typ, _ = self._typ(tmp_path, '#import "lib.typ": *')
        assert pdf.auto_root(typ) is None

    @pytest.mark.parametrize("ups", [1, 2, 3])
    def test_root_climbs_one_level_per_dotdot(self, tmp_path, ups):
        typ, d = self._typ(tmp_path, '#import "' + "../" * ups + 'lib.typ": *', depth=4)
        want = d
        for _ in range(ups):
            want = want.parent
        assert pdf.auto_root(typ) == str(want)

    def test_deepest_import_wins(self, tmp_path):
        src = '#import "../a.typ"\n#import "../../b.typ"\n'
        typ, d = self._typ(tmp_path, src, depth=3)
        assert pdf.auto_root(typ) == str(d.parent.parent)

    def test_parenthesised_import_counts(self, tmp_path):
        typ, d = self._typ(tmp_path, '#import("../lib.typ")', depth=2)
        assert pdf.auto_root(typ) == str(d.parent)

    def test_commented_import_is_ignored(self, tmp_path):
        typ, _ = self._typ(tmp_path, '// #import "../../lib.typ"\n/* #import "../lib.typ" */\n', depth=3)
        assert pdf.auto_root(typ) is None

    def test_non_typ_import_is_ignored(self, tmp_path):
        typ, _ = self._typ(tmp_path, '#import "../data.json"', depth=2)
        assert pdf.auto_root(typ) is None

    def test_unreadable_file_is_none(self, tmp_path):
        assert pdf.auto_root(str(tmp_path / "missing.typ")) is None


# ---------------------------------------------------------------- family_from_path

class TestFamilyFromPath:
    def _f(self, tmp_path, text, rel="cv.typ"):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return str(p)

    def test_banner_on_line_one(self, tmp_path):
        assert pdf.family_from_path(self._f(tmp_path, "// FAMILY: humanist-quiet\nx")) == "humanist-quiet"

    def test_banner_on_line_three_is_read(self, tmp_path):
        assert pdf.family_from_path(self._f(tmp_path, "// vitae: 1\n\n// FAMILY: a-b\nx")) == "a-b"

    def test_banner_on_line_four_is_not_read(self, tmp_path):
        assert pdf.family_from_path(self._f(tmp_path, "a\nb\nc\n// FAMILY: late\n")) is None

    def test_banner_beats_directory(self, tmp_path):
        p = self._f(tmp_path, "// FAMILY: real\n", "families/dirname/cv.typ")
        assert pdf.family_from_path(p) == "real"

    def test_directory_is_the_fallback(self, tmp_path):
        p = self._f(tmp_path, "no banner", "families/dirname/cv.typ")
        assert pdf.family_from_path(p) == "dirname"

    def test_families_as_last_component_gives_none(self, tmp_path):
        assert pdf.family_from_path(str(tmp_path / "x" / "families")) is None

    def test_no_banner_no_families_dir(self, tmp_path):
        assert pdf.family_from_path(self._f(tmp_path, "plain")) is None

    def test_unreadable_file_still_uses_the_path(self):
        assert pdf.family_from_path("/nonexistent/families/fam/cv.typ") == "fam"


# ---------------------------------------------------------------- page count / text / boxes

class TestCountPages:
    @pytest.mark.parametrize("backend", BACKENDS)
    def test_two_pages(self, two_page, backend):
        assert pdf.count_pages(two_page, backend) == "2"

    def test_poppler_without_pages_line_is_none(self, monkeypatch):
        class R:
            stdout = "Title: x\nProducer: y\n"
        monkeypatch.setattr(pdf.subprocess, "run", lambda *a, **k: R())
        assert pdf.count_pages("x.pdf", "poppler") is None

    def test_poppler_reads_the_pages_line(self, monkeypatch):
        class R:
            stdout = "Pages:          7\nPage size: 1 x 1\n"
        monkeypatch.setattr(pdf.subprocess, "run", lambda *a, **k: R())
        assert pdf.count_pages("x.pdf", "poppler") == "7"


class TestExtractText:
    @pytest.mark.parametrize("backend", BACKENDS)
    def test_every_backend_reads_the_words_in_order(self, two_page, backend):
        t = pdf.extract_text(two_page, backend)
        assert t.index("Hello world") < t.index("Second line") < t.index("Page two")

    def test_pdfium_matches_pdftotext_shape(self, two_page):
        # pages end with a blank line then \f
        assert pdf.extract_text(two_page, "pdfium") == "Hello world\nSecond line\n\n\x0cPage two\n\n\x0c"

    @pytest.mark.parametrize("gap, newline", [(2, False), (5, False), (14, True), (200, True)],
                             ids=["tight", "word-space", "past-one-box-height", "wide-gap"])
    def test_pdfium_cuts_a_line_at_a_wide_same_row_gap(self, tmp_path, gap, newline):
        # a right-flushed cell sharing a baseline is a line of its own, as in pdftotext
        p = _compile(tmp_path, "row", ROW.format(gap=gap))
        text = pdf.extract_text(p, "pdfium")
        assert ("Left\nRight" in text) is newline
        assert ("Left Right" in text) is (not newline)

    @pytest.mark.parametrize("backend", [b for b in BACKENDS if b.values[0] != "pypdf"])
    def test_overlapping_line_boxes_stay_separate_lines(self, tmp_path, backend):
        # hard-edge's header at its tightened leading: the 25 pt name's box reaches over the title's below it
        # (a pulled-up `#v(-5pt)`); pdfium's own text range joined them into one line, poppler cuts them
        out = tmp_path / "hard-edge.pdf"
        typst.compile(str(ROOT / "tests" / "fixtures" / "hard-edge.typ"), output=str(out), root=str(ROOT))
        lines = [" ".join(ln.split()) for ln in pdf.extract_text(str(out), backend).split("\n")]
        assert "Firstname Lastname" in lines
        assert any(ln.startswith("[Target title") for ln in lines)

    def test_pdfium_empty_page_gives_blank_page(self, tmp_path):
        p = _compile(tmp_path, "empty", "#set page(width: 50pt, height: 50pt)\n#rect(width: 10pt, height: 10pt)")
        assert pdf.extract_text(p, "pdfium") == "\n\n\f"


class TestWordBoxes:
    @pytest.fixture(params=["pdfium", "poppler"])
    def backend(self, request, monkeypatch):
        if request.param == "poppler" and not shutil.which("pdftotext"):
            pytest.skip("poppler missing")
        monkeypatch.setattr(pdf, "pdf_backend", lambda: request.param)
        return request.param

    def test_words_per_page(self, two_page, backend):
        pages = pdf.word_boxes(two_page, with_text=True)
        assert pages is not None
        assert [[w for _, w in pg] for pg in pages] == [["Hello", "world", "Second", "line"], ["Page", "two"]]

    def test_boxes_are_in_points_top_down(self, two_page, backend):
        pages = pdf.word_boxes(two_page)
        assert pages is not None
        (hello, world, second, _), _ = pages
        assert hello[0] < world[0] and hello[2] <= world[0] + 1        # same row, left to right
        assert second[1] > hello[3] - 3                                # next line is lower
        assert all(0 <= b[0] < b[2] <= 200 and 0 <= b[1] < b[3] <= 100 for b in (hello, world, second))

    def test_without_text_returns_only_boxes(self, two_page, backend):
        pages = pdf.word_boxes(two_page)
        assert pages is not None
        assert all(len(b) == 4 for pg in pages for b in pg)

    def test_unreadable_pdf_is_none_not_empty(self, tmp_path, backend):
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"not a pdf")
        assert pdf.word_boxes(str(bad)) is None

    def test_boxes_unavailable_names_the_reason(self, tmp_path, backend):
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"not a pdf")
        msg = pdf._boxes_unavailable(str(bad))
        assert (backend == "pdfium") == ("pypdfium2 could not read the PDF" in msg)


class TestBboxPagesPoppler:
    def test_parses_poppler_markup_and_unescapes(self, monkeypatch):
        out = ('<doc><page width="100.00" height="50.5">'
               '<word xMin="1.5" yMin="2" xMax="10" yMax="12">A&amp;B</word>'
               '<word xMin="-3" yMin="2" xMax="4" yMax="12">x</word></page>'
               '<page width="10" height="10"></page></doc>')

        class R:
            returncode = 0
            stdout = out
        monkeypatch.setattr(pdf, "pdf_backend", lambda: "poppler")
        monkeypatch.setattr(pdf.subprocess, "run", lambda *a, **k: R())
        assert pdf._bbox_pages("x.pdf") == [
            (100.0, 50.5, [((1.5, 2.0, 10.0, 12.0), "A&B"), ((-3.0, 2.0, 4.0, 12.0), "x")]),
            (10.0, 10.0, [])]

    def test_nonzero_exit_and_missing_tool_are_none(self, monkeypatch):
        class R:
            returncode = 1
            stdout = ""
        monkeypatch.setattr(pdf, "pdf_backend", lambda: "poppler")
        monkeypatch.setattr(pdf.subprocess, "run", lambda *a, **k: R())
        assert pdf._bbox_pages("x.pdf") is None

        def boom(*a, **k):
            raise FileNotFoundError("pdftotext")
        monkeypatch.setattr(pdf.subprocess, "run", boom)
        assert pdf._bbox_pages("x.pdf") is None


# ---------------------------------------------------------------- reading order

def _w(x0, y0, x1, y1, t):
    return ((float(x0), float(y0), float(x1), float(y1)), t)


def _order(words):
    return [t for _, t in pdf._reading_order(words)]


class TestReadingOrder:
    def test_empty(self):
        assert pdf._reading_order([]) == []

    def test_content_stream_order_is_replaced_by_layout_order(self):
        words = [_w(0, 40, 10, 50, "c"), _w(0, 0, 10, 10, "a"), _w(0, 20, 10, 30, "b")]
        assert _order(words) == ["a", "b", "c"]

    def test_row_tolerance_is_four_tenths_of_the_box_height(self):
        # B sits left of A: when the two share a row, B is read first (left to right);
        # when B's centre is just past 0.4 x height lower, it is the next row, read after A
        a, c = _w(0, 0, 10, 10, "A"), _w(0, 40, 10, 50, "C")
        same = _order([a, _w(-100, 4, -90, 14, "B"), c])      # centre offset 4.0 = 0.4 x 10
        other = _order([a, _w(-100, 4.5, -90, 14.5, "B"), c])  # centre offset 4.5
        assert same == ["B", "A", "C"]
        assert other == ["A", "B", "C"]

    def test_piece_cut_is_one_and_a_half_box_heights(self):
        # "Co" beside "Dev" with "Acme" under Dev only: a gap over 15 pt makes Co a right-flushed cell,
        # read after the entry's lines; at 15 pt it is part of the head
        dev, acme = _w(0, 0, 10, 10, "Dev"), _w(0, 14, 10, 24, "Acme")
        joined = _order([dev, _w(25, 0, 35, 10, "Co"), acme])       # gap 15.0
        split = _order([dev, _w(25.5, 0, 35.5, 10, "Co"), acme])    # gap 15.5
        assert joined == ["Dev", "Co", "Acme"]
        assert split == ["Dev", "Acme", "Co"]

    def test_right_flushed_date_is_read_after_the_entry_lines(self):
        words = [_w(0, 0, 20, 10, "Dev"), _w(200, 0, 230, 10, "2020"), _w(0, 14, 30, 24, "Acme")]
        assert _order(words) == ["Dev", "Acme", "2020"]

    def test_date_with_a_line_under_it_is_read_in_place(self):
        words = [_w(0, 0, 20, 10, "Dev"), _w(200, 0, 230, 10, "2020"), _w(0, 14, 230, 24, "Acme")]
        assert _order(words) == ["Dev", "2020", "Acme"]


# ---------------------------------------------------------------- unreadable PDFs

class TestPdfUnreadable:
    def test_valid_pdf(self, two_page):
        assert pdf.pdf_unreadable(two_page) is False

    def test_not_a_pdf(self, tmp_path):
        p = tmp_path / "x.pdf"
        p.write_bytes(b"hello, this is text")
        assert pdf.pdf_unreadable(str(p)) is True

    def test_empty_file(self, tmp_path):
        p = tmp_path / "x.pdf"
        p.write_bytes(b"")
        assert pdf.pdf_unreadable(str(p)) is True

    def test_header_only_is_unreadable(self, tmp_path):
        p = tmp_path / "x.pdf"
        p.write_bytes(b"%PDF-1.7\n%%EOF\n")
        assert pdf.pdf_unreadable(str(p)) is True

    def test_missing_file(self, tmp_path):
        assert pdf.pdf_unreadable(str(tmp_path / "nope.pdf")) is True

    def test_header_after_the_first_kilobyte_does_not_count(self, tmp_path, two_page):
        p = tmp_path / "x.pdf"
        p.write_bytes(b"x" * 1024 + Path(two_page).read_bytes())
        assert pdf.pdf_unreadable(str(p)) is True

    def test_no_backend_means_only_the_header_is_checked(self, two_page, monkeypatch):
        monkeypatch.setattr(pdf, "pdf_backend", lambda: None)
        assert pdf.pdf_unreadable(two_page) is False


# ---------------------------------------------------------------- rendering

class TestRender:
    def test_pdfium_render_size_matches_page_at_ppi(self, two_page):
        ims = pdf._pdfium_render(two_page, 144)
        assert [im.size for im in ims] == [(400, 200)] * 2
        assert all(im.mode == "RGB" for im in ims)

    def test_pdfium_render_gray_and_page_selection(self, two_page):
        ims = pdf._pdfium_render(two_page, 72, gray=True, pages=[2])
        assert len(ims) == 1 and ims[0].mode == "L" and ims[0].size == (200, 100)

    def test_render_pages_writes_one_png_per_page(self, two_page, tmp_path):
        out = tmp_path / "out"
        paths = pdf.render_pages(two_page, str(out), 72)
        assert [os.path.basename(p) for p in paths] == ["two-p1.png", "two-p2.png"]
        with Image.open(paths[1]) as im:
            assert im.size == (200, 100)

    def test_render_pages_drops_stale_pages_and_crops_of_the_same_stem_only(self, two_page, tmp_path):
        out = tmp_path / "out"
        out.mkdir()
        stale = ["two-p9.png", "two-p1-fill1.png", "two-p3-icon12.png"]
        keep = ["other-p1.png", "two-p1-note.png", "notes.txt", "two2-p1.png"]
        for n in stale + keep:
            (out / n).write_bytes(b"x")
        pdf.render_pages(two_page, str(out), 72)
        left = set(os.listdir(out))
        assert not left & set(stale)
        assert set(keep) <= left

    @pytest.mark.usefixtures("typst_api_only")
    def test_render_pngs_typstpy_makes_pages_in_order(self, tmp_path):
        typ = tmp_path / "d.typ"
        typ.write_text(DOC, encoding="utf-8")
        out = tmp_path / "png"
        out.mkdir()
        paths = pdf.render_pngs(str(typ), str(out))
        assert [os.path.basename(p) for p in paths] == ["p1.png", "p2.png"]
        with Image.open(paths[0]) as im:
            assert im.size == (250, 125)               # 90 ppi of 200 x 100 pt

    def test_render_crops_cuts_a_solid_band_and_removes_old_crops(self, tmp_path):
        p = _compile(tmp_path, "band", '#set page(width: 300pt, height: 200pt, margin: 20pt)\n'
                     '#rect(width: 100%, height: 50pt, fill: black)[#text(fill: white)[Title]]\nBody text')
        out = tmp_path / "crops"
        out.mkdir()
        (out / "band-p1-fill7.png").write_bytes(b"old")
        (out / "other-p1-fill1.png").write_bytes(b"keep")
        paths, notes = pdf.render_crops(p, str(out))
        names = [os.path.basename(x) for x in paths]
        assert names == ["band-p1-fill1.png"]
        assert notes == []
        assert not (out / "band-p1-fill7.png").exists()
        assert (out / "other-p1-fill1.png").exists()
        with Image.open(paths[0]) as im:
            assert im.size[0] > 100 * 300 / 72 * 0.8            # a band at least ~100 pt wide at 300 ppi

    def test_render_crops_of_a_plain_page_is_empty(self, two_page, tmp_path):
        assert pdf.render_crops(two_page, str(tmp_path / "c")) == ([], [])


# ---------------------------------------------------------------- compile

class TestCompile:
    @pytest.mark.usefixtures("typst_api_only")
    def test_ok_writes_the_pdf(self, tmp_path):
        typ = tmp_path / "a.typ"
        typ.write_text(DOC, encoding="utf-8")
        ok, err = pdf.compile_pdf(str(typ), str(tmp_path / "a.pdf"))
        assert (ok, err) == (True, "")
        assert (tmp_path / "a.pdf").read_bytes().startswith(b"%PDF")

    @pytest.mark.usefixtures("typst_api_only")
    def test_a_syntax_error_is_reported_not_raised(self, tmp_path):
        typ = tmp_path / "a.typ"
        typ.write_text("#let x = (", encoding="utf-8")
        ok, err = pdf.compile_pdf(str(typ), str(tmp_path / "a.pdf"))
        assert ok is False and err
        assert not (tmp_path / "a.pdf").exists()

    @pytest.mark.skipif(not shutil.which("typst"), reason="typst CLI missing")
    @pytest.mark.parametrize("src, ok", [(DOC, True), ("#let x = (", False)], ids=["valid", "broken"])
    def test_cli_return_code_decides(self, tmp_path, src, ok):
        typ = tmp_path / "a.typ"
        typ.write_text(src, encoding="utf-8")
        got, text = pdf.compile_pdf(str(typ), str(tmp_path / "a.pdf"))
        assert got is ok
        assert bool(text) is (not ok)

    @pytest.mark.skipif(not shutil.which("typst"), reason="typst CLI missing")
    def test_typst_compile_reports_the_error(self, tmp_path):
        typ = tmp_path / "a.typ"
        typ.write_text("#let x = (", encoding="utf-8")
        ok, err = pdf.typst_compile(str(typ), str(tmp_path / "a.pdf"))
        assert ok is False and "error" in err

    @pytest.mark.skipif(not shutil.which("typst"), reason="typst CLI missing")
    def test_typst_compile_ok(self, tmp_path):
        typ = tmp_path / "a.typ"
        typ.write_text(DOC, encoding="utf-8")
        ok, _ = pdf.typst_compile(str(typ), str(tmp_path / "a.pdf"))
        assert ok is True and (tmp_path / "a.pdf").exists()


# ---------------------------------------------------------------- ensure_icons

class TestEnsureIcons:
    def test_never_writes_into_the_skill_tree(self):
        skill = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        d = os.path.join(skill, "templates", "academic")
        stray = os.path.join(d, "icons.typ")
        existed = os.path.exists(stray)
        try:
            pdf.ensure_icons(os.path.join(d, "cv.typ"))
            assert existed or not os.path.exists(stray)
        finally:
            if not existed and os.path.exists(stray):
                os.remove(stray)

    def test_a_symlinked_dir_into_the_skill_is_still_the_skill_tree(self, tmp_path):
        skill = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        d = os.path.join(skill, "templates", "academic")
        stray = os.path.join(d, "icons.typ")
        existed = os.path.exists(stray)
        link = tmp_path / "link"
        link.symlink_to(d)
        try:
            pdf.ensure_icons(str(link / "cv.typ"))
            assert existed or not os.path.exists(stray)
        finally:
            if not existed and os.path.exists(stray):
                os.remove(stray)

    def test_copies_the_fallback_when_missing(self, tmp_path):
        typ = tmp_path / "cv.typ"
        typ.write_text("x", encoding="utf-8")
        pdf.ensure_icons(str(typ))
        src = os.path.join(os.path.dirname(__file__), "..", "..", "templates", "icons.typ")
        with open(src, "rb") as fh:
            assert (tmp_path / "icons.typ").read_bytes() == fh.read()

    def test_never_overwrites_harvested_icons(self, tmp_path):
        typ = tmp_path / "cv.typ"
        typ.write_text("x", encoding="utf-8")
        (tmp_path / "icons.typ").write_text("REAL", encoding="utf-8")
        pdf.ensure_icons(str(typ))
        assert (tmp_path / "icons.typ").read_text(encoding="utf-8") == "REAL"

    def test_does_not_write_through_a_dangling_symlink(self, tmp_path, capsys):
        typ = tmp_path / "cv.typ"
        typ.write_text("x", encoding="utf-8")
        target = tmp_path / "elsewhere.typ"
        (tmp_path / "icons.typ").symlink_to(target)
        pdf.ensure_icons(str(typ))
        assert not target.exists()
        assert "dangling symlink" in capsys.readouterr().out

    def test_a_live_symlink_is_left_alone(self, tmp_path, capsys):
        typ = tmp_path / "cv.typ"
        typ.write_text("x", encoding="utf-8")
        target = tmp_path / "real.typ"
        target.write_text("REAL", encoding="utf-8")
        (tmp_path / "icons.typ").symlink_to(target)
        pdf.ensure_icons(str(typ))
        assert target.read_text(encoding="utf-8") == "REAL"
        assert capsys.readouterr().out == ""

    def test_reference_family_file_gets_nothing(self, tmp_path):
        d = tmp_path / "a" / "b"
        d.mkdir(parents=True)
        typ = d / "cv.typ"
        typ.write_text('#import "../lib.typ"', encoding="utf-8")
        pdf.ensure_icons(str(typ))
        assert not (d / "icons.typ").exists()
