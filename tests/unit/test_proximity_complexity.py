"""LOG320 worst-case sweep of the proximity gate: the page index answers `find_run`, `lines` (with its `line_index`) and the whole
`measure_groups` exactly as the code it replaced did (the old code is kept verbatim in _proximity_ref.py; Hypothesis builds
pages from a tiny vocabulary so words repeat, lines share baselines and overlap, heads sit in several columns, rails and
missing pages come up), and its work, counted in line events (no wall clock), stays linear."""
import sys
from collections.abc import Callable

import _proximity_ref
import pytest
from _complexity import assert_linear, line_events
from _pages import cv_page, head_mark
from _proximity_ref import (
    find_run_scanning,
    line_index_scanning,
    lines_rebuilt,
    measure_groups_rebuilding,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from vitae.core.base import HeadMark, Mark, SecMark, Word
from vitae.core.level import Level
from vitae.verify.bounds import MAX_PAGE_WORK
from vitae.verify.groups import proximity
from vitae.verify.groups.query import PageIndex

_VOCAB = ["Alpha", "Beta", "alpha,", "BETA.", "Gamma", "2020", "—", "x", "Alpha-Beta"]


@st.composite
def _pages(draw: st.DrawFn) -> list[list[Word]]:
    pages = []
    for _ in range(draw(st.integers(1, 2))):
        words: list[Word] = []
        for r in range(draw(st.integers(1, 8))):
            y = 10.0 * r + draw(st.sampled_from([0.0, 0.0, 1.0, 2.5, 3.0, 4.0]))      # shared baselines and near ones
            x = draw(st.sampled_from([5.0, 10.0, 10.0, 40.0, 100.0]))
            for _ in range(draw(st.integers(0, 4))):
                w = draw(st.sampled_from([6.0, 20.0, 45.0]))
                words.append((x, y, x + w, y + draw(st.sampled_from([6.0, 9.0, 12.0])), draw(st.sampled_from(_VOCAB))))
                x += draw(st.sampled_from([-3.0, 2.0, 4.0, 30.0])) + w                     # overlaps, gaps
        pages.append(draw(st.permutations(words)))
    return pages


@settings(max_examples=500, deadline=None)
@given(_pages(), st.sampled_from(_VOCAB), st.integers(0, 3), st.sampled_from(_VOCAB), st.integers(-10, 90))
def test_page_index_matches_the_scanning_functions(pages: list[list[Word]], first: str, n: int, second: str,
                                                   y: int) -> None:
    words = pages[0]
    idx = PageIndex(words)
    text = " ".join([first, second][:max(n, 1)] + (["Gamma"] if n == 3 else []))
    got = idx.find_run(text, float(y))

    assert got == find_run_scanning(words, text, float(y))
    for x_min in (-1.0, 4.5, 5.0, 9.5, 10.0, 39.9, 40.0, 100.0, 1e9):
        lines = idx.lines(x_min)
        assert lines.lines == lines_rebuilt(words, x_min)
        assert lines is idx.lines(x_min)                                  # computed once per edge
        if got:
            assert lines.line_index(got) == line_index_scanning(lines.lines, got)


@st.composite
def _heads_and_secs(draw: st.DrawFn, n_pages: int) -> tuple[list[Mark], list[Mark]]:
    heads: list[Mark] = []
    for _ in range(draw(st.integers(0, 6))):
        toks = draw(st.lists(st.sampled_from(_VOCAB), min_size=1, max_size=3))
        page = draw(st.integers(0, n_pages + 1))
        x = draw(st.sampled_from([5.0, 10.0, 40.0, 100.0, 140.0]))
        y = draw(st.sampled_from([0.0, 1.0, 10.0, 11.0, 20.0, 30.0, 33.0, 50.0, 70.0]))
        kind = draw(st.sampled_from(["entry", "skill"]))
        if draw(st.booleans()):
            org = " ".join(draw(st.lists(st.sampled_from(_VOCAB), min_size=1, max_size=2)))
            heads.append(HeadMark(text=" ".join(toks), page=page, x=x, y=y, kind=kind, org=org))
        else:
            heads.append(HeadMark(text=" ".join(toks), page=page, x=x, y=y, kind=kind))
    secs: list[Mark] = []
    for _ in range(draw(st.integers(0, 3))):
        text = draw(st.sampled_from(_VOCAB))
        page = draw(st.integers(0, n_pages + 1))
        y = draw(st.sampled_from([0.0, 10.0, 20.0, 40.0, 60.0]))
        if draw(st.booleans()):
            secs.append(SecMark(text=text, page=page, y=y, x=draw(st.sampled_from([5.0, 10.0, 100.0]))))
        else:
            secs.append(SecMark(text=text, page=page, y=y))
    return heads, secs


@settings(max_examples=700, deadline=None)
@given(st.data())
def test_measure_groups_matches_the_rebuilding_version(data: st.DataObject) -> None:
    pages = data.draw(_pages())
    heads, secs = data.draw(_heads_and_secs(len(pages)))

    assert proximity.measure_groups(heads, secs, pages) == measure_groups_rebuilding(heads, secs, pages)


def _cv_words(entries: int) -> tuple[list[Mark], list[list[Word]]]:
    heads, _, items = cv_page(entries)
    return heads, [[(b[0], b[1], b[2], b[3], t) for b, t in items]]


@settings(max_examples=60, deadline=None)
@given(st.integers(1, 12), st.integers(1, 4), st.integers(1, 14))
def test_measure_groups_matches_on_cv_pages(entries: int, bullets: int, per_line: int) -> None:
    heads, _bullet_marks, items = cv_page(entries, bullets, per_line)
    pages = [[(b[0], b[1], b[2], b[3], t) for b, t in items]]

    assert proximity.measure_groups(heads, [], pages) == measure_groups_rebuilding(heads, [], pages)


def test_measure_groups_equivalence_is_not_vacuous() -> None:
    # control: rows are produced (not just empty == empty), and unlocated heads are counted as skipped
    heads, pages = _cv_words(5)
    rows, skipped = proximity.measure_groups(heads, [], pages)
    ghost = [*heads, head_mark(5.0, text="Nowhere")]

    assert len(rows) == 4 and skipped == 0
    assert proximity.measure_groups(ghost, [], pages)[1] == 1


_PROXIMITY_FILES = frozenset({proximity.__file__, sys.modules[PageIndex.__module__].__file__ or "", _proximity_ref.__file__ or ""})


def _grouping_events(measure: Callable[[list[Mark], list[Mark], list[list[Word]]], object], entries: int) -> int:
    heads, pages = _cv_words(entries)
    events, rows = line_events(_PROXIMITY_FILES, lambda: measure(heads, [], pages))
    assert rows                                          # the code path ran: a swap for another algorithm cannot blind the counter
    return events


def test_measure_groups_work_grows_linearly_with_the_heads_of_a_page() -> None:
    # bound 3: a small superlinear term shows (2.1 x per doubling at 30 heads, 2.7 x at 480), where the quadratic code makes 4 x
    assert_linear(lambda n: _grouping_events(proximity.measure_groups, n), 30, bound=3.0)


def test_the_work_count_tells_the_rebuilding_version_from_the_indexed_one() -> None:
    # control: the same counter shows the old code superlinear (a quadruple per doubling is a quadratic)
    w1, w2, w4 = (_grouping_events(measure_groups_rebuilding, 15 * k) for k in (1, 2, 4))

    assert w1 > 0 and w2 / w1 > 3.0 and w4 / w2 > 3.0


def test_measure_groups_does_far_less_work_than_rebuilding_on_a_page_of_dozens_of_heads() -> None:
    indexed = _grouping_events(proximity.measure_groups, 60)        # 2 700 words, 60 heads
    rebuilding = _grouping_events(measure_groups_rebuilding, 60)

    assert indexed * 20 < rebuilding


def _find_run_events(n_words: int, queries: int = 250) -> int:
    words: list[Word] = [(10.0, 12.0 * i, 40.0, 12.0 * i + 9.0, "same") for i in range(n_words)]
    idx = PageIndex(words)
    events, runs = line_events(_PROXIMITY_FILES, lambda: [idx.find_run("same", 12.0 * i) for i in range(0, 4 * queries, 4)])
    assert all(r is not None for r in runs)
    return events


def test_find_run_work_grows_linearly_with_a_word_repeated_across_the_page() -> None:
    # a fixed number of queries on a page of n identical words: each start is tried, none is checked beyond its token
    assert_linear(_find_run_events, 1000)


def test_find_run_does_less_work_than_the_scanning_version_on_a_repeated_word() -> None:
    words: list[Word] = [(10.0, 12.0 * i, 40.0, 12.0 * i + 9.0, "same") for i in range(4000)]
    idx = PageIndex(words)
    ys = [12.0 * i for i in range(0, 1000, 4)]
    indexed, _ = line_events(_PROXIMITY_FILES, lambda: [idx.find_run("same", y) for y in ys])
    scanning, runs = line_events(_PROXIMITY_FILES, lambda: [find_run_scanning(words, "same", y) for y in ys])

    assert all(r is not None for r in runs)
    assert indexed > 0 and indexed * 2 < scanning


def test_check_group_proximity_fails_a_page_beyond_the_declared_size() -> None:
    n_words = 2001
    pages = [[(10.0, float(i), 40.0, i + 9.0, "w") for i in range(n_words)]]
    heads: list[Mark] = [head_mark(float(i), text="w") for i in range(MAX_PAGE_WORK // n_words + 1)]

    out = proximity.check_group_proximity("", "x.pdf", heads=heads, secs=[], pages=pages)

    assert [lvl for lvl, _ in out] == [Level.FAIL]
    assert "page 1" in out[0][1] and "limit 2,000,000" in out[0][1]


def test_check_group_proximity_measures_a_page_at_the_declared_size() -> None:
    n_words = 2000
    pages = [[(10.0, float(i), 40.0, i + 9.0, "w") for i in range(n_words)]]
    heads: list[Mark] = [head_mark(float(i), text="w") for i in range(MAX_PAGE_WORK // n_words)]

    out = proximity.check_group_proximity("", "x.pdf", heads=heads, secs=[], pages=pages)

    assert all("not measured: page" not in msg for _, msg in out)


@pytest.mark.parametrize("page", [0, -1, 2], ids=["page-0", "negative-page", "beyond-last"])
def test_a_head_on_a_page_outside_the_document_is_skipped_not_read_from_the_last_page(page: int) -> None:
    heads, pages = _cv_words(3)
    assert proximity.measure_groups(heads, [], pages)[0]         # the same heads on page 1 do measure (not vacuous)
    moved: list[Mark] = [head_mark(y, x, page, h["text"]) for h in heads if (y := h.get("y")) is not None and (x := h.get("x")) is not None]

    rows, skipped = proximity.measure_groups(moved, [], pages)

    assert rows == [] and skipped == len(moved)
