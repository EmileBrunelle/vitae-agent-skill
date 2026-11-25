"""vitae.verify.groups: word matching, text-line clustering, whole-group proximity (measure_groups and its
FAIL/WARN thresholds), entry records, date adjacency in reading order, duplicate section/skill names.

Everything runs on small synthetic word lists and marks (the shapes lib.typ's markers and the PDF word
extraction give), so no PDF or Typst is needed."""
import math
from collections.abc import Sequence

import pytest
from vitae.core.base import DetailRow, GroupRow, Mark, SecRow, _Line
from vitae.core.level import Level
from vitae.verify import groups
from vitae.verify.groups import dates, proximity, query

PROX_THRESHOLDS = (groups.PROX_FAIL, groups.PROX_WARN)


def W(x0, y0, x1, y1, t):
    return (float(x0), float(y0), float(x1), float(y1), t)


def line(text, y, x=10.0, h=10.0, w=40.0):
    """One word of `text` on its own text line starting at y."""
    return W(x, y, x + w, y + h, text)


def text_line(*words) -> _Line:
    """A text line holding `words` (only its words matter to the tests that use it)."""
    return _Line(y0=0.0, y1=10.0, c=5.0, x0=0.0, words=list(words))


# ---------------------------------------------------------------- _gnorm

class TestGnorm:
    @pytest.mark.parametrize("raw, key", [
        ("Hello,", "hello"), ("  A-B_c ", "abc"), ("R&D 2020", "rd2020"), ("...", ""), ("", ""),
        ("ÉCOLE", "école"),
    ])
    def test_letters_and_digits_casefolded(self, raw, key):
        assert groups._gnorm(raw) == key


# ---------------------------------------------------------------- _lines

class TestLines:
    def test_empty(self):
        assert groups._lines([], 0) == []

    def test_words_left_of_x_min_are_dropped_and_x_min_is_inclusive(self):
        ls = groups._lines([W(5, 0, 9, 10, "a"), W(10, 0, 20, 10, "b")], 10)
        assert [[w[4] for w in ln["words"]] for ln in ls] == [["b"]]

    def test_same_line_tolerance_is_three_points_of_centre(self):
        # centres 5 and 8 (3.0 apart): one line; 5 and 8.1: two
        assert len(groups._lines([W(0, 0, 5, 10, "a"), W(6, 3, 9, 13, "b")], 0)) == 1
        assert len(groups._lines([W(0, 0, 5, 10, "a"), W(6, 3.1, 9, 13.1, "b")], 0)) == 2

    def test_line_geometry_and_order(self):
        ls = groups._lines([W(30, 21, 40, 31, "c"), W(10, 0, 20, 10, "a"), W(22, 1, 28, 12, "b")], 0)
        assert [ln["x0"] for ln in ls] == [10, 30]
        first = ls[0]
        assert (first["y0"], first["y1"], first["c"]) == (0, 12, 6.0)
        assert [w[4] for w in first["words"]] == ["a", "b"]


# ---------------------------------------------------------------- _find_run / _line_index

class TestFindRun:
    def _words(self, *texts, y=0.0):
        return [W(i * 20, y, i * 20 + 15, y + 10, t) for i, t in enumerate(texts)]

    def test_run_of_the_first_four_tokens(self):
        words = self._words("Senior", "Software", "Engineer", "Acme", "Corp", "2020")
        run = groups._find_run(words, "Senior Software Engineer Acme Corp Ltd", 5)
        assert run is not None
        assert [w[4] for w in run] == ["Senior", "Software", "Engineer", "Acme"]

    def test_tokens_after_the_fourth_are_not_compared(self):
        words = self._words("a", "b", "c", "d", "zzz")
        assert groups._find_run(words, "a b c d e f", 5) is not None

    def test_matching_ignores_case_and_punctuation(self):
        words = self._words("Dev,", "Ops")
        run = groups._find_run(words, "DEV OPS", 5)
        assert run is not None
        assert [w[4] for w in run] == ["Dev,", "Ops"]

    def test_pure_punctuation_words_are_skipped_inside_the_run(self):
        words = self._words("Dev", "|", "Ops")
        run = groups._find_run(words, "Dev Ops", 5)
        assert run is not None
        assert [w[4] for w in run] == ["Dev", "Ops"]

    def test_a_mismatch_in_the_run_is_not_a_match(self):
        assert groups._find_run(self._words("Dev", "Lead"), "Dev Ops", 5) is None

    def test_single_token_text_matches(self):
        assert groups._find_run(self._words("Dev"), "Dev", 5) is not None

    @pytest.mark.parametrize("text", ["", "   ", "--- ..."])
    def test_text_without_tokens_is_none(self, text):
        assert groups._find_run(self._words("Dev"), text, 0) is None

    def test_nearest_occurrence_to_the_marker_wins(self):
        words = self._words("Dev", y=0) + self._words("Dev", y=100)
        run = groups._find_run(words, "Dev", 98)
        assert run is not None
        assert run[0][1] == 100

    def test_thirty_points_from_the_marker_is_still_found_beyond_is_not(self):
        words = self._words("Dev", y=0)          # centre y = 5
        assert groups._find_run(words, "Dev", 35) is not None     # 30.0 away
        assert groups._find_run(words, "Dev", 35.5) is None       # 30.5 away

    def test_no_words(self):
        assert groups._find_run([], "Dev", 0) is None


class TestLineIndex:
    def test_matches_by_identity_not_equality(self):
        a, b = W(0, 0, 5, 5, "x"), W(0, 0, 5, 5, "x")           # equal values, distinct objects
        lines = [text_line(a), text_line(b)]
        assert groups._line_index(lines, [b]) == 1
        assert groups._line_index(lines, [a]) == 0

    def test_absent_word_is_none(self):
        assert groups._line_index([text_line(W(0, 0, 1, 1, "x"))], [W(0, 0, 1, 1, "x")]) is None


# ---------------------------------------------------------------- measure_groups

def head(text: str, y: float, page: int = 1, x: float = 10.0) -> Mark:
    return Mark(kind="entry", text=text, page=page, x=x, y=y)


def sec(text: str, y: float, page: int = 1, x: float = 10.0) -> Mark:
    return Mark(text=text, page=page, x=x, y=y)


def only_group(rows: Sequence[DetailRow]) -> GroupRow:
    """The single row of `rows`, which must be an entry/skill group."""
    (r,) = rows
    assert r["kind"] == "group"
    return r


def only_sec(rows: Sequence[DetailRow]) -> SecRow:
    """The single section-title row among `rows`."""
    (r,) = [r for r in rows if r["kind"] == "sec"]
    assert r["kind"] == "sec"
    return r


class TestMeasureGroups:
    def test_internal_between_and_ratio(self):
        words = [line("Role", 0), line("Org", 12), line("Bullet", 24), line("Next", 50)]
        rows, skipped = groups.measure_groups([head("Role", 0), head("Next", 50)], [], [words])
        assert skipped == 0
        r = only_group(rows)
        assert (r["kind"], r["text"], r["page"], r["n"]) == ("group", "Role", 1, 3)
        assert r["gaps"] == [2.0, 2.0]
        assert (r["internal"], r["between"], r["ratio"]) == (2.0, 16.0, 8.0)
        assert r["pair_in"] == ("Role", "Org") and r["pair_btw"] == ("Bullet", "Next")

    def test_the_largest_internal_gap_names_its_pair(self):
        words = [line("A", 0), line("B", 12), line("C", 40), line("Next", 80)]
        r = only_group(groups.measure_groups([head("A", 0), head("Next", 80)], [], [words])[0])
        assert r["internal"] == 18.0 and r["pair_in"] == ("B", "C")

    def test_custom_gap_function_is_used(self):
        words = [line("A", 0), line("B", 12), line("Next", 50)]
        calls = []

        def gap(page, up, lo):
            calls.append((page, up[2], lo[2]))
            return 4.0
        r = only_group(groups.measure_groups([head("A", 0), head("Next", 50)], [], [words], gap)[0])
        assert r["internal"] == 4.0 and r["between"] == 4.0 and r["ratio"] == 1.0
        assert calls == [(1, 0.0, 12.0), (1, 12.0, 50.0)]

    def test_zero_internal_gap_is_an_infinite_ratio(self):
        words = [line("A", 0), line("B", 10), line("Next", 40)]            # B touches A
        r = only_group(groups.measure_groups([head("A", 0), head("Next", 40)], [], [words])[0])
        assert r["internal"] == 0 and math.isinf(r["ratio"])

    def test_single_line_group_is_not_a_row_and_not_skipped(self):
        words = [line("A", 0), line("Next", 30)]
        assert groups.measure_groups([head("A", 0), head("Next", 30)], [], [words]) == ([], 0)

    def test_last_block_on_the_page_has_no_next_head(self):
        words = [line("A", 0), line("B", 12), line("C", 24)]
        assert groups.measure_groups([head("A", 0)], [], [words]) == ([], 0)

    def test_head_on_a_page_the_pdf_does_not_have_is_skipped(self):
        assert groups.measure_groups([head("A", 0, page=2)], [], [[line("A", 0)]]) == ([], 1)

    def test_head_not_found_in_the_words_is_skipped(self):
        assert groups.measure_groups([head("Ghost", 0)], [], [[line("A", 0)]]) == ([], 1)

    def test_next_block_not_found_in_the_words_is_skipped(self):
        words = [line("A", 0), line("B", 12)]
        # A's next block is not located (1), and the Ghost head itself is not located either (1)
        assert groups.measure_groups([head("A", 0), head("Ghost", 50)], [], [words]) == ([], 2)

    def test_next_head_in_another_column_is_not_the_next_block(self):
        # a head 100pt to the right belongs to another column's flow: A's next block is Next
        # (Side shares B's text line: were it taken as the next block, A would read as a two-line group)
        words = [line("A", 0), line("B", 12), line("Side", 12, x=110), line("Next", 50)]
        rows, _ = groups.measure_groups([head("A", 0), head("Side", 12, x=110), head("Next", 50)], [], [words])
        r = only_group([r for r in rows if r["text"] == "A"])
        assert r["pair_btw"][1] == "Next" and r["between"] == 28.0

    def test_next_head_exactly_sixty_points_right_still_counts_as_same_column(self):
        words = [line("A", 0), line("B", 12), line("Next", 50, x=70)]
        # Next is the nearest block below, 60 pt right of A: kept in the flow (> 60 would be another column)
        rows, _ = groups.measure_groups([head("A", 0), head("Next", 50, x=70)], [], [words])
        assert [r["text"] for r in rows] == ["A"]

    def test_marks_must_be_more_than_two_points_below_the_head(self):
        # a mark 2pt lower is the head's own marker, not a next block
        words = [line("A", 0), line("B", 12), line("C", 24)]
        assert groups.measure_groups([head("A", 0), head("A", 2)], [], [words]) == ([], 0)

    def test_a_mark_two_and_a_half_points_below_the_head_is_a_next_block(self):
        # the cut is "more than 2 pt below"; a mark that close but past it opens the next block
        words = [line("A", 0), line("B", 12), line("C", 24)]
        rows, _ = groups.measure_groups([head("A", 0), head("C", 2.5)], [], [words])
        got = [r for r in rows if r["text"] == "A"]
        assert [(r["kind"], r["text"], r["pair_btw"]) for r in got if r["kind"] == "group"] == [
            ("group", "A", ("B", "C"))]
        assert all(r["kind"] == "group" for r in got)

    def test_in_flow_title_starting_left_of_an_indented_head_is_read_in_the_flow(self):
        # gutter-rail style: the head is indented (x=30) and its next block, a title, starts just left of it
        # (27.9 < 30 - 2) yet extends past the body edge, so it is not a rail title
        words = [line("A", 0, x=30), line("B", 12, x=30), line("TITLE", 40, x=27.9, w=60)]
        rows, _ = groups.measure_groups([head("A", 0, x=30)], [sec("TITLE", 40, x=27.9)], [words])
        r = only_group([r for r in rows if r["kind"] == "group"])
        assert r["pair_btw"] == ("B", "TITLE")

    def test_section_title_is_a_next_block_of_the_group_above(self):
        words = [line("A", 0), line("B", 12), line("EDU", 40)]
        r = only_group(groups.measure_groups([head("A", 0)], [sec("EDU", 40)], [words])[0])
        assert r["pair_btw"] == ("B", "EDU")

    def test_rail_title_left_of_the_body_reads_the_head_in_its_window(self):
        # section title wholly left of the body column (margin index): the next block is the in-column
        # head opening within a few points of it, not the title
        words = [line("A", 0, x=100), line("B", 12, x=100), line("RAIL", 40, x=10, w=30),
                 line("Next", 42, x=100)]
        rows, _ = groups.measure_groups([head("A", 0, x=100), head("Next", 42, x=100)], [sec("RAIL", 40, x=10)],
                                        [words])
        r = only_group([r for r in rows if r["kind"] == "group"])
        assert r["pair_btw"][1] == "Next"

    def test_rail_title_whose_in_column_head_is_not_located_is_skipped(self):
        # the in-column head opening in the rail title's window has no words at its position: the group is
        # skipped (counted), not measured against the title
        words = [line("A", 0, x=100), line("B", 12, x=100), line("RAIL", 40, x=10, w=30),
                 line("Next", 80, x=100)]
        rows, skipped = groups.measure_groups([head("A", 0, x=100), head("Next", 42, x=100)],
                                              [sec("RAIL", 40, x=10)], [words])
        assert [r for r in rows if r["kind"] == "group"] == []
        assert skipped == 2      # A (its next block is not located) and Next (not located itself)

    def test_section_rows_measure_gap_above_and_below_the_title(self):
        words = [line("A", 0), line("B", 12), line("EDU", 40), line("Item", 62)]
        rows, _ = groups.measure_groups([head("A", 0)], [sec("EDU", 40)], [words])
        s = only_sec(rows)
        assert (s["before"], s["after"], s["ratio"]) == (18.0, 12.0, 1.5)

    def test_section_without_a_line_above_or_below_is_not_measured(self):
        heads = [head("A", 0)]
        first = [line("EDU", 0), line("Item", 12)]
        last = [line("A", 0), line("EDU", 12)]
        assert [r for r in groups.measure_groups(heads, [sec("EDU", 0)], [first])[0] if r["kind"] == "sec"] == []
        assert [r for r in groups.measure_groups(heads, [sec("EDU", 12)], [last])[0] if r["kind"] == "sec"] == []

    def test_section_mark_beyond_the_pdf_is_ignored(self):
        words = [line("A", 0), line("B", 12), line("EDU", 40), line("Item", 62)]
        rows, _ = groups.measure_groups([head("A", 0)], [sec("EDU", 40, page=3)], [words])
        assert [r for r in rows if r["kind"] == "sec"] == []

    @pytest.mark.parametrize("partial", [
        ("head", Mark(kind="entry", text="Ghost", page=1, y=20)),                   # no x
        ("head", Mark(kind="entry", text="Ghost", page=1, x=10.0)),                 # no y
        ("head", Mark(kind="entry", text="Ghost", y=20, x=10.0)),                   # no page
        ("sec", Mark(text="EDU", page=1)),                                          # no y
        ("sec", Mark(text="EDU", y=40)),                                            # no page
    ], ids=["head-no-x", "head-no-y", "head-no-page", "sec-no-y", "sec-no-page"])
    def test_a_partial_mark_is_skipped_and_the_well_formed_head_is_measured_as_before(self, partial):
        words = [line("A", 0), line("B", 12), line("Next", 50)]
        heads, secs = [head("A", 0), head("Next", 50)], list[Mark]()
        (heads if partial[0] == "head" else secs).append(partial[1])
        rows, _ = groups.measure_groups(heads, secs, [words])
        r = only_group(rows)
        assert (r["text"], r["internal"], r["between"], r["ratio"]) == ("A", 2.0, 28.0, 14.0)

    def test_section_title_beside_the_body_is_skipped(self):
        # starts more than 5pt left of the leftmost head of the page: a rail title
        words = [line("A", 0), line("B", 12), line("EDU", 40, x=2, w=5), line("Item", 62)]
        assert [r for r in groups.measure_groups([head("A", 0)], [sec("EDU", 40, x=2)], [words])[0]
                if r["kind"] == "sec"] == []


# ---------------------------------------------------------------- check_group_proximity

def _two_lines_then_next(between, internal=10.0):
    """Head "Role", one detail line `internal` below it, then the next head `between` below that."""
    words = [line("Role", 0), line("Detail", 10 + internal), line("Next", 20 + internal + between)]
    heads = [head("Role", 0), head("Next", 20 + internal + between)]
    return heads, words


def _prox(between, internal=10.0, **kw):
    heads, words = _two_lines_then_next(between, internal)
    detail: list[DetailRow] = []
    out = groups.check_group_proximity("", "", heads=heads, secs=kw.pop("secs", []),
                                       pages=[kw.pop("words", words)], detail=detail)
    return out, detail


class TestCheckGroupProximity:
    @pytest.mark.parametrize("between, level", [
        (6.9, Level.FAIL), (7.0, Level.WARN),       # exactly PROX_FAIL (0.7) is not a failure
        (8.4, Level.WARN),
        (12, Level.OK),                             # >= PROX_WARN and >= PROX_HIER (1.2); 0.85-1.2 is the hierarchy WARN
        (20, Level.OK),
    ])
    def test_thresholds_on_the_between_over_internal_ratio(self, between, level):
        out, _ = _prox(between)
        assert [lv for lv, _ in out] == [level]

    def test_threshold_constants(self):
        assert PROX_THRESHOLDS == (0.7, 0.85)

    def test_fail_message_names_the_worst_group_and_the_fix(self):
        (lv, msg), = _prox(5)[0]
        assert lv is Level.FAIL
        assert '1/1 groups sit closer to the next block' in msg
        assert 'worst "Role"' in msg and "ratio 0.50" in msg
        assert '"Role" -> "Detail"' in msg and '"Detail" -> "Next"' in msg
        assert "never edit lib.typ" in msg

    def test_warn_message_counts_weak_groups(self):
        (lv, msg), = _prox(8)[0]
        assert lv is Level.WARN and "1/1 groups barely separated" in msg and "aim for >= 0.85" in msg

    def test_ok_message_names_the_tightest_group(self):
        (lv, msg), = _prox(12)[0]
        assert lv is Level.OK and '(tightest "Role": ratio 1.20, 12.0pt vs 10.0pt)' in msg

    def test_zero_internal_gap_cannot_fail(self):
        out, _ = _prox(7, internal=0.0)
        assert [lv for lv, _ in out] == [Level.OK]

    def test_nan_ratio_counts_as_failing(self, monkeypatch):
        # `not ratio >= PROX_FAIL`, not `ratio < PROX_FAIL`: a NaN must never pass as fine
        heads, words = _two_lines_then_next(7)
        rows: list[DetailRow] = [GroupRow(
            kind="group", text="t", page=1, n=2, gaps=[1.0], internal=1.0, between=float("nan"),
            ratio=float("nan"), hkind=None, ls=[], pair_in=("a", "b"), pair_btw=("c", "d"), next_sec=False,
            head_gap=None, pitch=None)]
        monkeypatch.setattr(proximity, "measure_groups", lambda *a, **k: (rows, 0))
        out = groups.check_group_proximity("", "", heads=heads, secs=[], pages=[words])
        assert out[-1][0] is Level.FAIL

    def test_detail_rows_are_appended_and_printed(self, capsys):
        out, detail = _prox(7)
        assert [d["kind"] for d in detail] == ["group"]
        assert capsys.readouterr().out == 'DETAIL group "Role" p1 lines=2 internal=10.00pt between=7.00pt ratio=0.70\n'

    def test_unlocated_heads_add_a_warning_besides_the_verdict(self):
        heads, words = _two_lines_then_next(20)
        heads.append(head("Ghost", 0))
        out = groups.check_group_proximity("", "", heads=heads, secs=[], pages=[words])
        assert [lv for lv, _ in out] == [Level.WARN, Level.OK]
        assert "not measured for 1 head(s)" in out[0][1]

    def test_nothing_checkable_is_a_warning_with_the_skip_count(self):
        out = groups.check_group_proximity("", "", heads=[head("Ghost", 0)], secs=[], pages=[[line("A", 0)]])
        assert len(out) == 1 and out[0][0] is Level.WARN and "1 head(s) not located" in out[0][1]

    def test_no_heads_is_a_warning_not_a_failure(self):
        out = groups.check_group_proximity("", "", heads=[], secs=[], pages=[[line("A", 0)]])
        assert out[0][0] is Level.WARN and "no lib entry()/srow() heads" in out[0][1]

    def test_unavailable_typst_query_is_not_checked(self, monkeypatch):
        monkeypatch.setattr(proximity, "_typst_query", lambda *a, **k: None)
        monkeypatch.setattr(proximity, "pdf_backend", lambda: "poppler")
        out = groups.check_group_proximity("cv.typ", "cv.pdf", pages=[[]])
        assert out == [(Level.WARN, "group proximity NOT checked (typst query or pdftotext unavailable)")]

    def test_unavailable_pdfium_words_name_the_reason(self, monkeypatch):
        monkeypatch.setattr(proximity, "pdf_backend", lambda: "pdfium")
        monkeypatch.setattr(proximity, "_boxes_unavailable", lambda pdf: "WHY")
        monkeypatch.setattr(proximity, "word_boxes", lambda pdf, with_text=False: None)
        out = groups.check_group_proximity("", "x.pdf", heads=[head("A", 0)], secs=[])
        assert len(out) == 1 and "WHY" in out[0][1] and out[0][0] is Level.WARN

    def test_word_boxes_are_flattened_when_pages_are_not_given(self, monkeypatch):
        heads, words = _two_lines_then_next(20)
        wb = [[((w[0], w[1], w[2], w[3]), w[4]) for w in words]]
        monkeypatch.setattr(proximity, "word_boxes", lambda pdf, with_text=False: wb)
        out = groups.check_group_proximity("", "", heads=heads, secs=[])
        assert [lv for lv, _ in out] == [Level.OK]


class TestSectionProximity:
    def _run(self, before, after):
        """Group "A" (kept OK by a wide internal gap) then a section title `before` below its last line and a
        first line `after` below the title."""
        words = [line("A", 0), line("B", 100), line("EDU", 110 + before), line("Item", 120 + before + after)]
        return groups.check_group_proximity("", "", heads=[head("A", 0)], secs=[sec("EDU", 110 + before)],
                                            pages=[words])

    @pytest.mark.parametrize("before, level", [(13.9, Level.FAIL), (14.0, Level.WARN), (16.9, Level.WARN),
                                               (17.0, Level.OK)])
    def test_thresholds_on_gap_above_over_gap_below(self, before, level):
        out = self._run(before, 20)                  # ratios 0.695, 0.7, 0.845, 0.85
        sec_level = out[0][0]
        assert sec_level is level

    def test_messages(self):
        fail = self._run(5, 20)[0][1]
        assert fail.startswith("section proximity: 1/1 titles sit closer to the block above")
        assert 'worst "EDU": gap above 5.0pt, gap below 20.0pt, ratio 0.25' in fail
        ok = self._run(30, 20)[0][1]
        assert ok.startswith("section proximity: 1 titles") and 'tightest "EDU": ratio 1.50' in ok

    def test_section_findings_come_before_the_group_verdict(self):
        out = self._run(5, 20)
        assert [lv for lv, _ in out][0] is Level.FAIL and out[-1][1].startswith("group proximity")

    def test_section_detail_row_is_printed(self, capsys):
        self._run(30, 20)
        assert 'DETAIL section "EDU" p1 before-bar=30.00pt bar-to-first=20.00pt ratio=1.50' in capsys.readouterr().out


# ---------------------------------------------------------------- _entry_records

def mk(kind: str, text: str = "") -> Mark:
    return Mark(kind=kind, text=text, page=1, x=0.0, y=0.0)


class TestEntryRecords:
    def test_none_and_empty(self):
        assert groups._entry_records(None) == []
        assert groups._entry_records([]) == []

    def test_parts_attach_to_the_preceding_head_with_emission_order(self):
        e, d, o = mk("entry", text="a"), mk("date"), mk("org")
        (r,) = groups._entry_records([e, d, o])
        assert r == {"head": e, "date": d, "org": o, "date_first": True}
        (r,) = groups._entry_records([e, o, d])
        assert r["date_first"] is False

    def test_first_part_of_a_kind_wins_and_date_first_is_set_once(self):
        e, o1, o2, d = mk("entry"), mk("org", "1"), mk("org", "2"), mk("date")
        (r,) = groups._entry_records([e, o1, o2, d])
        assert r["org"] is o1 and r["date"] is d and r["date_first"] is False

    def test_entry_without_parts(self):
        (r,) = groups._entry_records([mk("entry")])
        assert (r["date"], r["org"], r["date_first"]) == (None, None, None)

    def test_parts_before_any_entry_are_ignored(self):
        assert groups._entry_records([mk("date"), mk("org")]) == []

    def test_a_skill_row_ends_the_entry_so_later_parts_are_orphans(self):
        e, d = mk("entry"), mk("date")
        (r,) = groups._entry_records([e, mk("skill"), d])
        assert r["date"] is None

    def test_other_part_kinds_are_ignored_and_do_not_reset(self):
        e, d = mk("entry"), mk("date")
        (r,) = groups._entry_records([e, mk("date-col"), d])
        assert r["date"] is d

    def test_one_record_per_entry(self):
        recs = groups._entry_records([mk("entry"), mk("date"), mk("entry"), mk("org")])
        assert [(r["date"] is not None, r["org"] is not None) for r in recs] == [(True, False), (False, True)]


# ---------------------------------------------------------------- _first_word

def WB(x0, y0, x1, y1, t):
    return ((float(x0), float(y0), float(x1), float(y1)), t)


class TestFirstWord:
    words = [WB(50, 0, 60, 10, "right"), WB(10, 1, 20, 11, "left"), WB(10, 30, 20, 40, "below")]

    def test_top_line_then_leftmost(self):
        assert groups._first_word(self.words, 10, 0, 20) == 1

    def test_x_is_inclusive_within_one_and_a_half_points(self):
        assert groups._first_word(self.words, 11.5, 0, 20) == 1      # 10 >= 11.5 - 1.5
        assert groups._first_word(self.words, 11.6, 0, 20) == 0      # left is now too far left

    def test_x_end_is_exclusive(self):
        assert groups._first_word(self.words, 0, 0, 20, x_end=10) is None
        assert groups._first_word(self.words, 0, 0, 20, x_end=10.5) == 1

    def test_y_window_starts_two_points_above_and_ends_before_y_end(self):
        assert groups._first_word(self.words, 10, 8, 20) == 1         # centre 6 >= 8 - 2
        assert groups._first_word(self.words, 10, 8.5, 20) is None    # centre 6 < 6.5
        assert groups._first_word(self.words, 10, 0, 5) is None       # centre 6 is not < 5

    def test_words_within_three_points_of_the_top_line_count_as_it(self):
        ws = [WB(40, 0, 50, 10, "a"), WB(5, 3, 15, 13, "b")]          # centres 5 and 8: same line
        assert groups._first_word(ws, 0, 0, 30) == 1
        ws = [WB(40, 0, 50, 10, "a"), WB(5, 3.5, 15, 13.5, "b")]      # 8.5: a lower line
        assert groups._first_word(ws, 0, 0, 30) == 0

    def test_nothing_in_the_window(self):
        assert groups._first_word([], 0, 0, 10) is None


# ---------------------------------------------------------------- check_date_adjacency

H = Mark(kind="entry", text="Dev", page=1, x=10.0, y=0.0, dated=True, anchor=True)
D = Mark(kind="date", text="", page=1, x=200.0, y=0.0, w=30.0, h=10.0)
O = Mark(kind="org", text="", page=1, x=10.0, y=14.0, w=40.0, h=10.0)
DEV = WB(10, 0, 30, 10, "Dev")
DATE = WB(200, 0, 230, 10, "2020")
ACME = WB(10, 14, 50, 24, "Acme")


def adj(marks, page_words, **kw):
    warns = []
    stats = {}
    fails = groups.check_date_adjacency("", "", marks=marks, words=[page_words] if page_words is not None
                                        and page_words and not isinstance(page_words[0], list) else page_words,
                                        warns=warns, stats=stats, **kw)
    return fails, warns, stats


class TestCheckDateAdjacency:
    def test_date_read_before_the_org_line_passes(self):
        fails, warns, stats = adj([H, D, O], [DEV, DATE, ACME])
        assert (fails, warns) == ([], [])
        assert stats == {"measured": 1, "undated": 0, "unmeasured": 0}

    def test_org_line_read_before_the_date_fails(self):
        fails, _, _ = adj([H, D, O], [DEV, ACME, DATE])
        (msg,) = fails
        assert 'employer line BEFORE its date' in msg and 'entry "Dev"' in msg
        assert msg.startswith("lengthen the org/descriptor line of")

    def test_date_read_in_the_middle_of_the_role_fails(self):
        h = H.copy()
        h["text"] = "Senior Dev"
        words = [WB(10, 0, 40, 10, "Senior"), DATE, WB(45, 0, 70, 10, "Dev"), ACME]
        fails, _, _ = adj([h, D, O], words)
        (msg,) = fails
        assert "read in the middle of its role" in msg and 'before "Dev"' in msg

    def test_date_read_after_the_next_entry_starts_fails(self):
        h2 = H.copy()
        h2["text"] = "Ops"
        h2["y"] = 50.0
        words = [DEV, ACME, WB(10, 50, 30, 60, "Ops"), DATE]
        # no org mark so the org-order check cannot be the one that fires
        fails, _, _ = adj([H, D, h2], words)
        (msg,) = fails
        assert "emitted AFTER the next entry starts" in msg

    def test_date_read_after_text_set_below_the_head_fails(self):
        words = [DEV, WB(10, 14, 50, 24, "Bullet"), DATE]
        fails, _, _ = adj([H, D], words)
        (msg,) = fails
        assert 'AFTER text set below the entry head (read first: "Bullet")' in msg

    def test_org_emitted_before_the_date_fails_without_reading_positions(self):
        fails, warns, stats = adj([H, O, D], [DEV, DATE, ACME])
        (msg,) = fails
        assert "EMITTED before its date" in msg
        assert stats["unmeasured"] == 1 and stats["measured"] == 0

    def test_date_on_another_page_fails(self):
        d = D.copy()
        d["page"] = 2
        fails, _, _ = adj([H, d, O], [DEV, DATE, ACME])
        assert "its date is set on page 2, its head on page 1" in fails[0]

    def test_head_page_beyond_the_pdf_is_only_a_note(self):
        h = H.copy()
        h["page"] = 3
        d = D.copy()
        d["page"] = 3
        fails, warns, _ = adj([h, d, O], [DEV, DATE, ACME])
        assert fails == [] and 'page 3 not in the PDF' in warns[0]

    def test_undated_entry_is_counted_and_never_fails(self):
        undated = H.copy()
        undated["dated"] = False
        fails, warns, stats = adj([undated], [DEV])
        assert (fails, warns) == ([], [])
        assert stats == {"measured": 0, "undated": 1, "unmeasured": 0}

    def test_dated_entry_without_a_date_marker_is_unmeasured(self):
        fails, warns, stats = adj([H], [DEV])
        assert fails == [] and "dated but no date marker" in warns[0]
        assert stats["unmeasured"] == 1

    def test_head_without_lib_markers_is_noted_when_others_have_them(self):
        old = Mark(kind="entry", text="Old", page=1, x=10.0, y=80.0)
        fails, warns, _ = adj([H, D, O, old], [DEV, DATE, ACME])
        assert fails == [] and any('entry "Old": no lib markers' in w for w in warns)

    def test_no_entry_carries_markers_is_one_note(self):
        old = Mark(kind="entry", text="Old", page=1, x=10.0, y=0.0)
        fails, warns, stats = adj([old], [DEV])
        assert fails == [] and len(warns) == 1 and "no lib markers" in warns[0]

    def test_no_entries_at_all(self):
        assert adj([], [DEV]) == ([], [], {"measured": 0, "undated": 0, "unmeasured": 0})
        assert adj([mk("skill")], [DEV])[0] == []

    def test_words_not_found_at_the_marker_position_is_a_note(self):
        fails, warns, stats = adj([H, D, O], [WB(150, 70, 160, 80, "far")])
        assert fails == [] and "words not found at the marker position" in warns[0]
        assert stats["unmeasured"] == 1

    def test_org_line_twelve_points_from_its_marker_is_still_matched(self):
        # the org words are looked up within max(h, 6) + 10 pt of the marker's y
        o = O.copy()
        o["x"] = 20.0
        o["y"] = 14.0
        o["h"] = 6.0
        acme = WB(20, 21, 60, 31, "Acme")                      # centre 26: 12 pt below the marker
        fails, warns, stats = adj([H, D, o], [DEV, DATE, acme])
        assert (fails, warns) == ([], []) and stats["measured"] == 1

    def test_org_line_not_found_is_a_note_not_a_failure(self):
        o = O.copy()
        o["x"] = 20.0
        fails, warns, stats = adj([H, D, o], [DEV, DATE])
        assert fails == [] and any("employer line words not found" in w for w in warns)
        assert stats["measured"] == 1

    def test_unavailable_word_positions_are_a_note(self, monkeypatch):
        monkeypatch.setattr(dates, "word_boxes", lambda pdf, with_text=False: None)
        monkeypatch.setattr(dates, "pdf_backend", lambda: "poppler")
        warns = []
        assert groups.check_date_adjacency("", "x.pdf", marks=[H, D, O], warns=warns) == []
        assert warns == ["pdftotext unavailable (word positions needed)"]

    def test_inline_date_after_the_role_is_measured_on_the_head_line(self):
        d = D.copy()
        d["x"] = 35.0
        d["inline"] = True
        d["w"] = 25.0
        words = [DEV, WB(35, 0, 60, 10, "2020"), ACME]
        fails, warns, stats = adj([H, d, O], words)
        assert (fails, stats["measured"]) == ([], 1)

    def test_inline_date_read_after_the_org_line_fails_with_the_rebuild_advice(self):
        d = D.copy()
        d["x"] = 35.0
        d["inline"] = True
        d["w"] = 25.0
        words = [DEV, ACME, WB(35, 0, 60, 10, "2020")]
        (msg,), _, _ = adj([H, d, O], words)
        assert msg.startswith("rebuild entry \"Dev\" with the family's unmodified job()")
        assert "already set its date inline after the role" in msg

    def test_old_lib_head_without_anchor_gets_the_recopy_advice(self):
        h = H.copy()
        del h["anchor"]
        (msg,), _, _ = adj([h, D, O], [DEV, ACME, DATE])
        assert "recopy the skill's lib.typ" in msg

    def test_short_org_line_advice_gives_the_missing_length(self):
        # org starts at x=10 and is 40 wide: the date at 200 is 150 + 3 = 153 pt further right
        (msg,), _, _ = adj([H, D, O], [DEV, ACME, DATE])
        assert "by at least 153pt" in msg

    def test_org_line_that_already_reaches_the_date_gets_the_rebuild_advice(self):
        o = O.copy()
        o["w"] = 200.0
        (msg,), _, _ = adj([H, D, o], [DEV, WB(10, 14, 230, 24, "Acme"), DATE])
        assert "already runs its org line under the date" in msg

    def test_words_are_read_from_the_pdf_when_not_given(self, monkeypatch):
        monkeypatch.setattr(dates, "word_boxes", lambda pdf, with_text=False: [[DEV, DATE, ACME]])
        assert groups.check_date_adjacency("", "x.pdf", marks=[H, D, O]) == []

    def test_marks_come_from_typst_query_when_not_given(self, monkeypatch):
        seen = []
        monkeypatch.setattr(dates, "_typst_query", lambda typ, sel, root=None: seen.append(sel) or [H, D, O])
        groups.check_date_adjacency("cv.typ", "", words=[[DEV, DATE, ACME]])
        assert seen == [groups.ENTRY_MARKS]


# ---------------------------------------------------------------- check_duplicate_names

class TestDuplicateNames:
    def test_skill_label_equal_to_a_section_title_fails(self):
        out = groups.check_duplicate_names([{"text": "LANGUAGES"}], [{"kind": "skill", "text": "Languages"}])
        assert out == ['"Languages" is both a skill row label and the section title "LANGUAGES" — '
                       'rename one (e.g. "Programming languages")']

    def test_punctuation_and_case_do_not_hide_a_clash(self):
        out = groups.check_duplicate_names([{"text": "Skills:"}], [{"kind": "skill", "text": " SKILLS "}])
        assert len(out) == 1 and out[0].startswith('"SKILLS" is both')

    def test_entry_heads_are_not_row_labels(self):
        assert groups.check_duplicate_names([{"text": "Education"}], [{"kind": "entry", "text": "Education"}]) == []

    def test_distinct_names_pass(self):
        assert groups.check_duplicate_names([{"text": "Skills"}], [{"kind": "skill", "text": "Tools"}]) == []

    @pytest.mark.parametrize("secs, heads", [(None, None), ([], []), (None, [{"kind": "skill", "text": "A"}]),
                                             ([{"text": "A"}], None)])
    def test_missing_or_empty_inputs(self, secs, heads):
        assert groups.check_duplicate_names(secs, heads) == []

    def test_empty_normalised_names_never_clash(self):
        assert groups.check_duplicate_names([{"text": "---"}], [{"kind": "skill", "text": "..."}]) == []

    def test_first_title_with_a_key_names_the_clash(self):
        secs: list[Mark] = [{"text": "Skills"}, {"text": "SKILLS"}]
        out = groups.check_duplicate_names(secs, [{"kind": "skill", "text": "skills"}])
        assert 'section title "Skills"' in out[0]

    def test_each_clashing_row_is_reported(self):
        heads: list[Mark] = [{"kind": "skill", "text": "A"}, {"kind": "skill", "text": "B"}]
        assert len(groups.check_duplicate_names([{"text": "a"}, {"text": "b"}], heads)) == 2


# ---------------------------------------------------------------- mark validation at the typst boundary

class TestMarkValidation:
    def test_valid_marks_pass_through_unchanged(self, monkeypatch):
        vals = [{"text": "Dev", "kind": "entry", "org": "X", "page": 1, "x": 10, "y": 20.5,
                 "dated": True, "anchor": True},
                {"text": "EDU"},
                {"kind": "date", "text": "", "page": 2, "x": 1.0, "y": 2.0, "w": 3, "h": 4.5, "inline": False}]
        monkeypatch.setattr(query, "_typst_values", lambda *a, **k: vals)
        assert query._typst_query("cv.typ", "sel") == vals

    def test_malformed_entries_are_dropped_and_valid_ones_kept(self, monkeypatch):
        good = {"text": "ok", "page": 1, "x": 1.0, "y": 2.0}
        bad = [{"kind": "entry"},                     # no text
               {"text": 3},                           # text not a str
               {"text": "a", "x": "10"},              # x a str
               {"text": "a", "page": 1.5},            # page not an int
               {"text": "a", "page": True},           # a bool is not a number
               {"text": "a", "dated": 1},             # dated not a bool
               "entry", 7, None, ["text"]]            # not objects
        monkeypatch.setattr(query, "_typst_values", lambda *a, **k: [*bad, good])
        assert query._typst_query("cv.typ", "sel") == [good]

    def test_none_stays_none(self, monkeypatch):
        monkeypatch.setattr(query, "_typst_values", lambda *a, **k: None)
        assert query._typst_query("cv.typ", "sel") is None

    def test_json_list_accepts_only_arrays(self):
        assert query._json_list('[1, {"a": 2}]') == [1, {"a": 2}]
        assert query._json_list('{"a": 1}') is None
        with pytest.raises(ValueError):
            query._json_list("[1,")

    def test_unplaced_marks_are_ignored_by_entry_records(self):
        unplaced = Mark(kind="entry", text="a")
        placed = Mark(kind="entry", text="b", page=1, x=0.0, y=0.0)
        recs = groups._entry_records([unplaced, placed])
        assert [r["head"]["text"] for r in recs] == ["b"]
