"""vitae.verify.groups on real Typst output: the `typst query` mark reader (CLI and typst-py routes) and the
optical line-gap measure that group proximity is judged on (page_ink_gap, on a raster of a compiled PDF)."""
import shutil

import pytest
import typst
from vitae.verify import groups, pdf
from vitae.verify.groups.query import PageIndex


@pytest.fixture(params=["cli", "typst-py"])
def route(request, fake_typst):
    """The mark reader through the CLI, then forced through the typst package."""
    if request.param == "cli":
        if not shutil.which("typst"):
            pytest.skip("typst CLI missing")
    else:
        fake_typst(api=pytest.importorskip("typst"))
    return request.param


def _typ(tmp_path, src, name="m.typ"):
    f = tmp_path / name
    f.write_text(src, encoding="utf-8")
    return str(f)


MARKS = """#metadata((kind: "entry", text: "Dev", page: 1, x: 10.5, y: 20)) <vitae-head>
#metadata((kind: "skill", text: "Tools", page: 1, x: 10, y: 40)) <vitae-head>
#metadata("not a dict") <vitae-head>
#metadata((text: "EDU")) <vitae-sec>
Body
"""


class TestTypstQuery:
    def test_values_of_every_labelled_element(self, tmp_path, route):
        vals = groups.typst_values(_typ(tmp_path, MARKS), "<vitae-head>")
        assert vals == [{"kind": "entry", "text": "Dev", "page": 1, "x": 10.5, "y": 20},
                        {"kind": "skill", "text": "Tools", "page": 1, "x": 10, "y": 40}, "not a dict"]

    def test_marks_drop_everything_that_is_not_an_object(self, tmp_path, route):
        marks = groups.typst_query(_typ(tmp_path, MARKS), "<vitae-head>")
        assert marks is not None
        assert [m["text"] for m in marks] == ["Dev", "Tools"]

    def test_no_match_is_an_empty_list_not_none(self, tmp_path, route):
        assert groups.typst_query(_typ(tmp_path, MARKS), "<vitae-part>") == []

    def test_a_document_that_does_not_compile_is_none(self, tmp_path, route):
        assert groups.typst_values(_typ(tmp_path, "#let x = ("), "<vitae-head>") is None

    def test_a_sibling_import_of_the_folder_is_resolved(self, tmp_path, route):
        (tmp_path / "lib.typ").write_text('#let m() = [#metadata((text: "L")) <vitae-sec>]', encoding="utf-8")
        typ = _typ(tmp_path, '#import "lib.typ": m\n#m()')
        assert groups.typst_query(typ, "<vitae-sec>") == [{"text": "L"}]

    def test_an_import_above_the_file_needs_the_auto_root(self, tmp_path, route):
        (tmp_path / "lib.typ").write_text('#let m() = [#metadata((text: "UP")) <vitae-sec>]', encoding="utf-8")
        sub = tmp_path / "fam"
        sub.mkdir()
        typ = _typ(sub, '#import "../lib.typ": m\n#m()', "cv.typ")
        assert groups.typst_query(typ, "<vitae-sec>") == [{"text": "UP"}]

    def test_without_cli_or_package_it_is_none(self, tmp_path, fake_typst):
        fake_typst()
        assert groups.typst_values(_typ(tmp_path, MARKS), "<vitae-head>") is None


# ---------------------------------------------------------------- optical gap

def _pdf(tmp_path, name, body):
    typ = tmp_path / f"{name}.typ"
    typ.write_text('#set page(width: 300pt, height: 300pt, margin: 20pt)\n'
                   '#set text(size: 10pt)\n' + body, encoding="utf-8")
    out = tmp_path / f"{name}.pdf"
    typst.compile(str(typ), output=str(out))
    return str(out)


def _line_boxes(path):
    """[x0, x1, y0, y1] per text line, the way measure_groups hands them to the gap function."""
    wb = pdf.word_boxes(path, with_text=True)
    assert wb is not None
    lines = PageIndex([(b[0], b[1], b[2], b[3], t) for b, t in wb[0]]).lines(0).lines
    return [[ln["x0"], max(w[2] for w in ln["words"]), ln["y0"], ln["y1"]] for ln in lines]


class TestPageInkGap:
    def _gap(self, path, i=0):
        ls = _line_boxes(path)
        return groups.page_ink_gap(path)(1, ls[i], ls[i + 1]), ls

    def test_the_gap_follows_the_layout_one_for_one(self, tmp_path):
        small, _ = self._gap(_pdf(tmp_path, "s", "Hello world foo\n#v(4pt)\nHello world foo"))
        large, _ = self._gap(_pdf(tmp_path, "l", "Hello world foo\n#v(24pt)\nHello world foo"))
        assert large - small == pytest.approx(20, abs=1.0)

    def test_the_gap_skips_the_descender_and_stays_under_the_line_pitch(self, tmp_path):
        # baseline of the upper line to the x-height top of the lower one: more than the box gap (the
        # upper box's descender and the lower box's ascender room are not counted) yet less than the
        # box-top to box-top pitch; bounds come from the measured boxes, not from a font's metrics
        gap, ls = self._gap(_pdf(tmp_path, "a", "Hello world foo\n#v(8pt)\nHello world foo"))
        box_gap, pitch = ls[1][2] - ls[0][3], ls[1][2] - ls[0][2]
        assert box_gap + 2 < gap < pitch

    def test_the_gap_is_baseline_to_x_height_top_not_box_to_box(self, tmp_path):
        # descenders, ascenders and caps in the upper line must not move it: same layout, other words
        # (running text: a line of one repeated letter has no dense x-height band to find)
        plain, _ = self._gap(_pdf(tmp_path, "p", "Hello world foo\n#v(8pt)\nHello world foo"))
        tall, _ = self._gap(_pdf(tmp_path, "t", "gag Hxg pop\n#v(8pt)\nHello world foo"))
        assert tall == pytest.approx(plain, abs=1.0)

    def test_a_rule_between_the_lines_splits_the_gap(self, tmp_path):
        plain, _ = self._gap(_pdf(tmp_path, "p", "Hello world foo\n#v(30pt)\nHello world foo"))
        ruled, _ = self._gap(_pdf(tmp_path, "r", "Hello world foo\n#v(14pt)\n#line(length: 100%)\n#v(14pt)\nHello world foo"))
        assert ruled < plain - 5                         # the longest blank stretch, not the whole gap

    def test_a_line_on_a_filled_band_counts_as_the_band(self, tmp_path):
        # white title on a black bar: the gap below the bar starts at the bar's edge, whatever sits in it
        body = ('#rect(width: 100%, height: 30pt, fill: black, inset: 10pt)[#text(fill: white)[TITLE]]\n'
                '#v({s}pt)\nHello world foo')
        near, _ = self._gap(_pdf(tmp_path, "n", body.format(s=4)))
        far, _ = self._gap(_pdf(tmp_path, "f", body.format(s=24)))
        assert far - near == pytest.approx(20, abs=1.0)

    def test_without_a_raster_it_falls_back_to_the_box_gap(self, tmp_path):
        gap = groups.page_ink_gap(str(tmp_path / "missing.pdf"))
        assert gap(1, [10, 50, 0, 10], [10, 50, 25.5, 35]) == 15.5

    def test_an_empty_pdf_path_means_box_gaps(self):
        assert groups.page_ink_gap("")(1, [0, 10, 0, 10], [0, 10, 30, 40]) == 20

    def test_lines_overlapping_in_the_raster_have_no_gap(self, tmp_path):
        path = _pdf(tmp_path, "o", "Hello world foo\n#v(4pt)\nHello world foo")
        ls = _line_boxes(path)
        assert groups.page_ink_gap(path)(1, ls[1], ls[0]) == 0.0      # lower line given above the upper one

    def test_a_text_line_with_no_ink_falls_back_to_the_box_gap(self, tmp_path):
        path = _pdf(tmp_path, "e", "Hello world foo\n#v(40pt)\nHello world foo")
        blank = [[20.0, 80.0, 120.0, 130.0]]                           # empty paper where no text was set
        gap = groups.page_ink_gap(path)
        up = _line_boxes(path)[0]
        assert gap(1, up, blank[0]) == blank[0][2] - up[3]
