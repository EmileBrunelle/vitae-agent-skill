"""The validators that replaced `cast`: a valid value passes unchanged, a malformed one has a stated outcome."""
import io

import pytest
from _raster_ref import RgbPixels
from PIL import Image
from vitae import palette as P
from vitae.core import env
from vitae.core.base import is_placed, is_sec_placed
from vitae.core.pdfium import PdfiumDoc
from vitae.core.pixels import colour_counts, gray_pixels
from vitae.design.tables import is_audacity
from vitae.verify import pdf
from vitae.verify.groups.query import _is_mark


class TestPixels:
    def _gray(self):
        im = Image.new("L", (3, 2))
        im.putdata([0, 10, 20, 30, 40, 255])
        return im

    def test_gray_reads_the_same_as_pillow(self):
        im = self._gray()
        px, ref = gray_pixels(im), im.load()
        assert ref is not None
        assert [px[x, y] for y in range(2) for x in range(3)] == [ref[x, y] for y in range(2) for x in range(3)]

    def test_rgb_reads_the_same_as_pillow(self):
        im = Image.new("RGB", (2, 2))
        im.putdata([(1, 2, 3), (4, 5, 6), (7, 8, 9), (250, 251, 252)])
        px, ref = RgbPixels(im), im.load()
        assert ref is not None
        assert [px[x, y] for y in range(2) for x in range(2)] == [ref[x, y] for y in range(2) for x in range(2)]

    @pytest.mark.parametrize("xy", [(3, 0), (0, 2), (-1, 0), (0, -1)])
    def test_out_of_range_is_an_index_error_not_a_wrapped_pixel(self, xy):
        with pytest.raises(IndexError):
            gray_pixels(self._gray())[xy]
        with pytest.raises(IndexError):
            RgbPixels(Image.new("RGB", (3, 2)))[xy]

    def test_wrong_mode_is_a_value_error(self):
        with pytest.raises(ValueError, match="L"):
            gray_pixels(Image.new("RGB", (1, 1)))
        with pytest.raises(ValueError, match="RGB"):
            RgbPixels(Image.new("L", (1, 1)))


class TestColourCounts:
    def test_rgb_pairs(self):
        im = Image.new("RGB", (2, 1), (1, 2, 3))
        im.putpixel((1, 0), (9, 9, 9))
        assert sorted(colour_counts(im, 4)) == [(1, (1, 2, 3)), (1, (9, 9, 9))]

    def test_more_colours_than_allowed_is_empty(self):
        im = Image.new("RGB", (2, 1), (1, 2, 3))
        im.putpixel((1, 0), (9, 9, 9))
        assert colour_counts(im, 1) == []

    def test_single_band_is_a_value_error(self):
        with pytest.raises(ValueError, match="multi-band"):
            colour_counts(Image.new("L", (2, 2)), 4)


class TestMarkNarrowing:
    def test_placed_head_passes(self):
        assert is_placed({"text": "x", "page": 1, "x": 1.0, "y": 2.0})

    @pytest.mark.parametrize("missing", ["page", "x", "y"])
    def test_head_missing_a_coordinate_is_not_placed(self, missing):
        m = {"text": "x", "page": 1, "x": 1.0, "y": 2.0}
        del m[missing]
        assert not is_placed(m)   # type: ignore[arg-type]  # a plain dict built to drop one key

    def test_section_needs_page_and_y_only(self):
        assert is_sec_placed({"text": "x", "page": 1, "y": 2.0})
        assert not is_sec_placed({"text": "x", "page": 1})
        assert not is_sec_placed({"text": "x", "y": 2.0})

    def test_json_mark_validator_rejects_wrong_field_types(self):
        assert _is_mark({"text": "x", "page": 1, "x": 1.5})
        assert not _is_mark({"text": "x", "page": True})
        assert not _is_mark({"text": 3})
        assert not _is_mark(["text"])


class TestAudacity:
    @pytest.mark.parametrize("v", ["sober", "expressive", "bold"])
    def test_levels_pass(self, v):
        assert is_audacity(v)

    @pytest.mark.parametrize("v", ["loud", "", "Sober"])
    def test_anything_else_fails(self, v):
        assert not is_audacity(v)


class TestPaletteSecondHue:
    def test_single_hue_palette_has_none(self):
        assert P._second(P.build("swiss-grid", "s")) is None

    def test_duotone_palette_returns_its_three_fields(self):
        p = P.build("color-band", "s")
        second = P._second(p)
        assert second is not None and second[0] == p["accent2"] and second[1] == p["hsl2"] and second[2] == p["roles"]

    def test_colour_without_hsl_or_roles_is_a_bug_and_asserts(self):
        p = P.build("color-band", "s")
        broken: P.Palette = {**p, "hsl2": None}
        with pytest.raises(AssertionError):
            P._second(broken)


class TestPdfiumBoundary:
    def test_png_number(self):
        assert pdf._png_number("/t/p-03.png") == 3
        assert pdf._png_number("h12.png") == 12

    def test_png_name_without_a_number_is_a_value_error(self):
        with pytest.raises(ValueError, match="numbered page image"):
            pdf._png_number("/t/p-x.png")

    def test_document_with_the_methods_is_accepted(self, monkeypatch):
        class Doc:
            def __init__(self, path):
                self.path = path

            def __len__(self): return 0
            def __iter__(self): return iter(())
            def __getitem__(self, i): raise IndexError
            def get_metadata_dict(self): return {}
            def count_attachments(self): return 0

        mod = type("M", (), {"PdfDocument": Doc})
        monkeypatch.setattr(pdf.importlib, "import_module", lambda name: mod)
        assert isinstance(pdf._pdfium_doc("x.pdf"), Doc)

    def test_object_without_them_is_a_type_error(self, monkeypatch):
        mod = type("M", (), {"PdfDocument": lambda path: object()})
        monkeypatch.setattr(pdf.importlib, "import_module", lambda name: mod)
        assert not isinstance(object(), PdfiumDoc)
        with pytest.raises(TypeError, match="not the document"):
            pdf._pdfium_doc("x.pdf")


class TestCountDegraded:
    def test_counts_degraded_lines_and_forwards_everything(self):
        out = io.StringIO()
        c = env._CountDegraded(out)
        c.write("OK  a\nDEGRADED b\nnot DEGRADED\nOK ")
        c.write("DEGRADED mid-line\n")   # DEGRADED, but not at the start of a line
        assert c.n == 1 and out.getvalue() == "OK  a\nDEGRADED b\nnot DEGRADED\nOK DEGRADED mid-line\n"
        assert c.getvalue() == ""


class TestMalformedMarksAreReported:
    GOOD = {"text": "ok", "page": 1, "x": 1.0, "y": 2.0}
    NOTE = "1 lib marks ignored: malformed (first: w = None)"

    def _q(self, monkeypatch, vals):
        from vitae.verify.groups import query
        monkeypatch.setattr(query, "_typst_values", lambda *a, **k: vals)
        return query._typst_query_checked("cv.typ", "sel")

    def test_valid_marks_give_no_note(self, monkeypatch):
        assert self._q(monkeypatch, [self.GOOD, {"text": "EDU"}]) == ([self.GOOD, {"text": "EDU"}], None)

    def test_dropped_marks_are_counted_with_the_first_offender(self, monkeypatch):
        marks, note = self._q(monkeypatch, [self.GOOD, {"text": "a", "dated": None}, {"text": "b", "w": None}])
        assert marks == [self.GOOD]
        assert note == "2 lib marks ignored: malformed (first: dated = None)"

    @pytest.mark.parametrize("bad, field", [({"kind": "entry"}, "text = None"), ({"text": 3}, "text = 3"),
                                             ({"text": "a", "x": "10"}, "x = '10'"), ("entry", "<mark> = 'entry'")])
    def test_first_offender_names_the_field(self, monkeypatch, bad, field):
        assert self._q(monkeypatch, [bad])[1] == f"1 lib marks ignored: malformed (first: {field})"

    def test_unavailable_query_has_no_note(self, monkeypatch):
        assert self._q(monkeypatch, None) == (None, None)

    def test_the_gate_run_turns_the_note_into_a_warn(self, monkeypatch):
        from vitae.core.level import Level
        from vitae.verify import gates
        monkeypatch.setattr(gates, "_typst_marks_and_contact", lambda *a, **k: ([self.GOOD], self.NOTE, None))
        ctx = gates.make_context("cv.typ", "cv.pdf", "", "", "poppler")
        assert gates._mark_notes(ctx) == [(Level.WARN, "lib marks: " + self.NOTE)]
        monkeypatch.setattr(gates, "_typst_marks_and_contact", lambda *a, **k: ([self.GOOD], None, None))
        assert gates._mark_notes(gates.make_context("cv.typ", "cv.pdf", "", "", "poppler")) == []

    def test_duplicate_names_gate_warns_on_dropped_sections(self, monkeypatch):
        from vitae.core.level import Level
        from vitae.verify import gates
        monkeypatch.setattr(gates, "_typst_query_checked", lambda *a, **k: ([{"text": "A"}], self.NOTE))
        ctx = gates.make_context("cv.typ", "cv.pdf", "", "", "poppler", can_query=False)
        assert (Level.WARN, "duplicate names: " + self.NOTE) in gates._duplicate_names(ctx)
