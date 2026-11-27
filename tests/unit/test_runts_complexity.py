"""LOG320 worst-case sweep of the bullet gates: `located_bullets` returns exactly what the version that rebuilt every
page for every bullet returned (the old code is kept verbatim in _runts_ref.py; Hypothesis builds one- and two-page
documents on a grid, with lines that share baselines, a sidebar and a left-hand marker (right-to-left), heads between
bullets, bullets that run on to the next page, and pages that do not exist), the memo is a pure function of its
arguments, and a page of hundreds of bullets stays fast (`slow`)."""
import time

import pytest
from _pages import cv_page
from _runts_ref import located_bullets_rebuilding
from hypothesis import given, settings
from hypothesis import strategies as st
from vitae.core.base import Mark, WordBox
from vitae.core.level import Finding, Level
from vitae.verify import rhythm, runts
from vitae.verify.bounds import MAX_PAGE_WORK

_TOKENS = ["a", "bb", "ccc", "ms.", "x"]
_BOTTOM = 130.0


@st.composite
def _docs(draw: st.DrawFn) -> tuple[list[Mark], list[list[WordBox]], list[float] | None]:
    n_pages = draw(st.integers(1, 2))
    rows = draw(st.integers(3, 9))
    pages: list[list[WordBox]] = []
    for _ in range(n_pages):
        words: list[WordBox] = []
        for r in range(rows):
            y = 40.0 + 12.0 * r + draw(st.sampled_from([0.0, 0.0, 0.0, 1.0, 3.0]))     # near baselines, shared ones
            x = draw(st.sampled_from([10.0, 30.0, 30.0, 30.0, 200.0, 230.0]))
            for _ in range(draw(st.integers(0, 4))):
                w = draw(st.sampled_from([8.0, 20.0, 30.0, 60.0]))
                words.append(((x, y, x + w, y + draw(st.sampled_from([8.0, 9.0, 9.0]))), draw(st.sampled_from(_TOKENS))))
                x += w + draw(st.sampled_from([2.0, 4.0, 20.0]))
        pages.append(draw(st.permutations(words)))
    marks: list[Mark] = []
    for _ in range(draw(st.integers(0, 7))):
        marks.append(Mark(text="•", page=draw(st.integers(1, n_pages + 1)), kind="bullet",
                          x=draw(st.sampled_from([22.0, 22.0, 22.0, 22.5, 23.5, 24.0, 190.0, 300.0])),
                          y=40.0 + 12.0 * draw(st.integers(0, rows)) + draw(st.sampled_from([0.0, 0.0, 1.0, -1.0, -2.0]))))
    for _ in range(draw(st.integers(0, 3))):
        marks.append(Mark(text="Head", page=draw(st.integers(1, n_pages)), kind=draw(st.sampled_from(["entry", "part"])),
                          x=draw(st.sampled_from([10.0, 30.0, 200.0])), y=40.0 + 12.0 * draw(st.integers(0, rows))))
    heights = draw(st.sampled_from([None, [_BOTTOM] * n_pages, [_BOTTOM + 70.0] * n_pages]))
    return draw(st.permutations(marks)), pages, heights


@settings(max_examples=2000, deadline=None)
@given(_docs())
def test_located_bullets_match_the_rebuilding_version(doc: tuple[list[Mark], list[list[WordBox]], list[float] | None]) -> None:
    marks, pages, heights = doc

    assert runts.located_bullets(marks, pages, heights) == located_bullets_rebuilding(marks, pages, heights)


@settings(max_examples=60, deadline=None)
@given(st.integers(1, 10), st.integers(1, 4), st.integers(1, 14))
def test_located_bullets_match_on_cv_pages(entries: int, bullets: int, per_line: int) -> None:
    heads, marks, words = cv_page(entries, bullets, per_line)

    assert (runts.located_bullets(heads + marks, [words], [10000.0])
            == located_bullets_rebuilding(heads + marks, [words], [10000.0]))


def _two_page_doc() -> tuple[list[Mark], list[list[WordBox]], list[float]]:
    """A bullet whose second line is the last of page 1 and whose third line opens page 2; page 2 reaches as low."""
    page1: list[WordBox] = [((30.0, 40.0, 60.0, 49.0), "head"), ((30.0, 118.0, 200.0, 127.0), "tail of one"),
                            ((30.0, 130.0, 80.0, 139.0), "line two")]
    page2: list[WordBox] = [((30.0, 40.0, 60.0, 49.0), "ms."), ((30.0, 130.0, 200.0, 139.0), "bottom")]
    marks = [Mark(text="•", page=1, x=22.0, y=118.0, kind="bullet")]
    return marks, [page1, page2], [150.0, 150.0]


def _two_columns_doc() -> tuple[list[Mark], list[list[WordBox]], None]:
    """Two lists end their text on page 1, each with the content bottom of its own x band: the left one is the lowest
    text of its band and page 2 does not reach as low (it runs on); the right one has a page 2 whose band goes
    far lower than its last line (its bullet is not at the bottom, so it stays on page 1)."""
    page1: list[WordBox] = [((30.0, 40.0, 120.0, 49.0), "left full"), ((30.0, 52.0, 60.0, 61.0), "ms."),
                            ((200.0, 70.0, 290.0, 79.0), "right full"), ((200.0, 82.0, 230.0, 91.0), "ms.")]
    page2: list[WordBox] = [((30.0, 40.0, 60.0, 49.0), "top"), ((200.0, 40.0, 260.0, 49.0), "top"),
                            ((200.0, 130.0, 290.0, 139.0), "bottom")]
    marks = [Mark(text="•", page=1, x=22.0, y=40.0, kind="bullet"), Mark(text="•", page=1, x=190.0, y=70.0, kind="bullet")]
    return marks, [page1, page2], None


def test_the_content_bottom_is_read_per_column() -> None:
    marks, pages, heights = _two_columns_doc()

    got = runts.located_bullets(marks, pages, heights)

    assert got == located_bullets_rebuilding(marks, pages, heights)
    assert [[ln.page for ln in lines] for _, lines in got] == [[1, 1, 2], [1, 1]]


def test_the_page_is_clustered_per_distinct_column_not_per_bullet(monkeypatch: pytest.MonkeyPatch) -> None:
    clusters: list[int] = []
    real_cluster = runts._cluster
    monkeypatch.setattr(runts, "_cluster", lambda ws: clusters.append(1) or real_cluster(ws))
    bottoms: list[int] = []
    real_bottoms = runts._Document._lowest_per_page
    monkeypatch.setattr(runts._Document, "_lowest_per_page", lambda self, col: bottoms.append(1) or real_bottoms(self, col))
    heads, bullet_marks, words = cv_page(60)
    runts._located.cache_clear()

    out = runts.located_bullets(heads + bullet_marks, [words], [10000.0])

    # 180 bullets of one list: a few distinct columns (the column narrows where the words below run out), not one per bullet
    assert len(out) == 180 and 1 <= len(clusters) <= 5 and len(bottoms) <= len(clusters)


def test_equivalence_is_not_vacuous() -> None:
    # control: bullets are located, a bullet runs on across the page break, and a right-to-left marker is read
    marks, pages, heights = _two_page_doc()
    [(pos, lines)] = runts.located_bullets(marks, pages, heights)
    rtl_page: list[WordBox] = [((100.0, 40.0, 150.0, 49.0), "abc"), ((60.0, 52.0, 150.0, 61.0), "def")]
    rtl = runts.located_bullets([Mark(text="•", page=1, x=160.0, y=40.0, kind="bullet")], [rtl_page], None)

    assert pos.page == 1 and [ln.page for ln in lines] == [1, 1, 2]
    assert lines == located_bullets_rebuilding(marks, pages, heights)[0][1]
    assert len(rtl) == 1 and runts.located_bullets([], [rtl_page]) == []


def test_a_bullet_at_the_bottom_with_a_blank_next_page_is_measured_not_a_crash() -> None:
    # the old code took min() of the next page's words for its top margin: ValueError when that page has none
    page1: list[WordBox] = [((30.0, 118.0, 200.0, 127.0), "last line of page one")]
    marks = [Mark(text="•", page=1, x=22.0, y=118.0, kind="bullet")]

    [(_, lines)] = runts.located_bullets(marks, [page1, []], [150.0, 150.0])

    assert [ln.page for ln in lines] == [1]


# ------------------------------------------------------------------ the memo


def test_located_bullets_is_computed_once_for_equal_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    runts._located.cache_clear()
    calls: list[int] = []
    real = runts._locate
    monkeypatch.setattr(runts, "_locate", lambda *a: calls.append(1) or real(*a))
    heads, bullet_marks, words = cv_page(3)
    marks = heads + bullet_marks

    first = runts.located_bullets(marks, [words], [800.0])
    runts.bullet_lines([dict(m) for m in marks], [list(words)], [800.0])     # equal, not identical, arguments
    rhythm.measure_columns(list(marks), [list(words)], [800.0])

    assert len(calls) == 1
    assert first == located_bullets_rebuilding(marks, [words], [800.0])


def test_located_bullets_recomputes_when_the_arguments_differ(monkeypatch: pytest.MonkeyPatch) -> None:
    runts._located.cache_clear()
    calls: list[int] = []
    real = runts._locate
    monkeypatch.setattr(runts, "_locate", lambda *a: calls.append(1) or real(*a))
    heads, bullet_marks, words = cv_page(3)
    moved = [((b[0] + 1.0, b[1], b[2] + 1.0, b[3]), t) for b, t in words]

    a = runts.located_bullets(heads + bullet_marks, [words], [800.0])
    b = runts.located_bullets(heads + bullet_marks, [moved], [800.0])
    c = runts.located_bullets(heads + bullet_marks, [moved], [900.0])
    d = runts.located_bullets(heads + bullet_marks[:-1], [moved], [900.0])

    assert len(calls) == 4
    assert a != b and len(c) == len(b) and len(d) == len(c) - 1


def test_located_bullets_gives_the_same_result_whatever_ran_before() -> None:
    heads, bullet_marks, words = cv_page(4)
    other_heads, other_bullets, other_words = cv_page(2, 2, 5)
    runts._located.cache_clear()
    alone = runts.located_bullets(heads + bullet_marks, [words], None)

    runts.located_bullets(other_heads + other_bullets, [other_words], None)
    after = runts.located_bullets(heads + bullet_marks, [words], None)

    assert after == alone and after is not alone


def test_the_lists_returned_are_the_callers_own() -> None:
    heads, bullet_marks, words = cv_page(2)
    first = runts.located_bullets(heads + bullet_marks, [words], None)
    first[0][1].clear()
    first.pop()

    again = runts.located_bullets(heads + bullet_marks, [words], None)

    assert len(again) == len(bullet_marks) and all(lines for _, lines in again)


def test_a_mark_that_cannot_be_hashed_is_still_measured() -> None:
    heads, bullet_marks, words = cv_page(2)
    odd = Mark(text="•", page=1, x=18.0, y=40.0, kind="bullet")
    odd["org"] = ["not", "a", "string"]

    assert runts.located_bullets([odd, *heads, *bullet_marks], [words], None) == \
        located_bullets_rebuilding([odd, *heads, *bullet_marks], [words], None)


# ------------------------------------------------------------------ the declared size and the time


def _fail(msg: str) -> Finding:
    return (Level.FAIL, msg)


def _dense(monkeypatch: pytest.MonkeyPatch) -> list[Mark]:
    n_words = 2001
    page: list[WordBox] = [((10.0, float(i), 40.0, i + 9.0), "w") for i in range(n_words)]
    monkeypatch.setattr(runts, "_bbox_pages", lambda pdf: [(600.0, 800.0, page)])
    monkeypatch.setattr(rhythm, "_bbox_pages", lambda pdf: [(600.0, 800.0, page)])

    def boom(*_a: object) -> None:
        raise AssertionError("a page past the declared size was measured")

    monkeypatch.setattr(runts, "_locate", boom)
    return [Mark(text="•", page=1, x=18.0, y=float(i), kind="bullet") for i in range(MAX_PAGE_WORK // n_words + 1)]


def test_check_runts_fails_a_page_beyond_the_declared_size_without_measuring_it(monkeypatch: pytest.MonkeyPatch) -> None:
    marks = _dense(monkeypatch)

    out = runts.check_runts(marks, "x.pdf", fail=_fail)

    assert [lvl for lvl, _ in out] == [Level.FAIL] and "bullet runts not measured: page 1" in out[0][1]


def test_check_rhythm_fails_a_page_beyond_the_declared_size_without_measuring_it(monkeypatch: pytest.MonkeyPatch) -> None:
    marks = _dense(monkeypatch)

    out = rhythm.check_rhythm(marks, "x.pdf", fail=_fail)

    assert [lvl for lvl, _ in out] == [Level.FAIL] and "spacing rhythm not measured: page 1" in out[0][1]


@pytest.mark.slow
def test_located_bullets_bound_time_on_a_page_of_hundreds_of_bullets() -> None:
    heads, bullet_marks, words = cv_page(160)       # 7 200 words, 480 bullets, 160 heads
    runts._located.cache_clear()
    start = time.perf_counter()

    out = runts.located_bullets(heads + bullet_marks, [words], [10000.0])

    assert time.perf_counter() - start < 1.0     # measured ~0.1 s; rebuilding the page for every bullet took ~1.5 s
    assert len(out) == 480


@pytest.mark.slow
def test_located_bullets_bound_time_at_the_declared_size_with_a_new_column_per_bullet() -> None:
    n_words = 2000
    page: list[WordBox] = [((10.0 + 0.5 * i, 12.0 * (i % 100), 14.0 + 0.5 * i, 12.0 * (i % 100) + 9.0), "w")
                           for i in range(n_words)]
    marks = [Mark(text="•", page=1, x=9.0 + 0.5 * i, y=12.0 * (i % 100), kind="bullet")
             for i in range(MAX_PAGE_WORK // n_words)]
    runts._located.cache_clear()
    start = time.perf_counter()

    runts.located_bullets(marks, [page], None)

    assert time.perf_counter() - start < 1.5     # a column per bullet, the page at the limit: measured ~0.3 s
