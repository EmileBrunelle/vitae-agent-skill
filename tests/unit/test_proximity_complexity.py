"""LOG320 worst-case sweep of the proximity gate: the page index answers `find_run`, `lines` (with its `line_index`) and the whole
`measure_groups` exactly as the code it replaced did (the old code is kept verbatim in _proximity_ref.py; Hypothesis builds
pages from a tiny vocabulary so words repeat, lines share baselines and overlap, heads sit in several columns, rails and
missing pages come up), and a page of thousands of heads stays fast (`slow`)."""
import time
from collections.abc import Callable

import pytest
from _growth import GROWTH_BOUND, growth_ratio
from _pages import cv_page, head_mark
from _proximity_ref import (
    find_run_scanning,
    line_index_scanning,
    lines_rebuilt,
    measure_groups_rebuilding,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from vitae.core.base import HeadMark, Mark, SecMark, Word, is_placed
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
        h = HeadMark(text=" ".join(toks), page=draw(st.integers(0, n_pages + 1)), x=draw(st.sampled_from([5.0, 10.0, 40.0, 100.0, 140.0])),
                     y=draw(st.sampled_from([0.0, 1.0, 10.0, 11.0, 20.0, 30.0, 33.0, 50.0, 70.0])))
        h["kind"] = draw(st.sampled_from(["entry", "skill"]))
        if draw(st.booleans()):
            h["org"] = " ".join(draw(st.lists(st.sampled_from(_VOCAB), min_size=1, max_size=2)))
        heads.append(h)
    secs: list[Mark] = []
    for _ in range(draw(st.integers(0, 3))):
        s = SecMark(text=draw(st.sampled_from(_VOCAB)), page=draw(st.integers(0, n_pages + 1)),
                    y=draw(st.sampled_from([0.0, 10.0, 20.0, 40.0, 60.0])))
        if draw(st.booleans()):
            s["x"] = draw(st.sampled_from([5.0, 10.0, 100.0]))
        secs.append(s)
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
    heads, bullet_marks, items = cv_page(entries, bullets, per_line)
    pages = [[(b[0], b[1], b[2], b[3], t) for b, t in items]]

    assert proximity.measure_groups(heads, [], pages) == measure_groups_rebuilding(heads, [], pages)


def test_measure_groups_equivalence_is_not_vacuous() -> None:
    # control: rows are produced (not just empty == empty), and unlocated heads are counted as skipped
    heads, pages = _cv_words(5)
    rows, skipped = proximity.measure_groups(heads, [], pages)
    ghost = [*heads, head_mark(5.0, text="Nowhere")]

    assert len(rows) == 4 and skipped == 0
    assert proximity.measure_groups(ghost, [], pages)[1] == 1


def _measured(entries: int) -> Callable[[], object]:
    heads, pages = _cv_words(entries)
    return lambda: proximity.measure_groups(heads, [], pages)


def _measured_rebuilding(entries: int) -> Callable[[], object]:
    heads, pages = _cv_words(entries)
    return lambda: measure_groups_rebuilding(heads, [], pages)


@pytest.mark.slow
def test_measure_groups_time_grows_linearly_with_the_heads_of_a_page() -> None:
    assert growth_ratio(_measured, 60) < GROWTH_BOUND


@pytest.mark.slow
def test_the_growth_ratio_tells_the_rebuilding_version_from_the_indexed_one() -> None:
    assert growth_ratio(_measured_rebuilding, 60, repeats=2) > GROWTH_BOUND     # control: the old code is quadratic


@pytest.mark.slow
def test_measure_groups_bounds_time_on_a_page_of_hundreds_of_heads() -> None:
    heads, pages = _cv_words(240)       # 10 800 words, 240 heads
    start = time.perf_counter()

    rows, _ = proximity.measure_groups(heads, [], pages)

    assert time.perf_counter() - start < 1.0     # measured ~0.05 s; rebuilding the page for every head took ~3 s
    assert len(rows) == 239


@pytest.mark.slow
def test_find_run_bounds_time_on_a_word_repeated_across_the_page() -> None:
    words: list[Word] = [(10.0, 12.0 * i, 40.0, 12.0 * i + 9.0, "same") for i in range(4000)]
    idx = PageIndex(words)
    start = time.perf_counter()

    runs = [idx.find_run("same", 12.0 * i) for i in range(0, 4000, 4)]

    assert time.perf_counter() - start < 1.0     # measured ~0.1 s (every start is tried, none is checked beyond its token)
    assert all(r is not None for r in runs)


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
    moved: list[Mark] = [head_mark(h["y"], h["x"], page, h["text"]) for h in heads if is_placed(h)]

    rows, skipped = proximity.measure_groups(moved, [], pages)

    assert rows == [] and skipped == len(moved)
