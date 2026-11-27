"""LOG320 worst-case sweep of the bullet gates: `located_bullets` returns exactly what the version that rebuilt every
page for every bullet returned (the old code is kept verbatim in _runts_ref.py; Hypothesis builds one- and two-page
documents on a grid, with lines that share baselines, a sidebar and a left-hand marker (right-to-left), heads between
bullets, bullets that run on to the next page, and pages that do not exist), the layout is built once and shared by the
runts and rhythm gates, and a page of hundreds of bullets stays fast (`slow`)."""
import time
from collections.abc import Callable

import pytest
from _pages import bullet, cv_page, head_mark
from _runts_ref import located_bullets_rebuilding
from hypothesis import given, settings
from hypothesis import strategies as st
from vitae.core.base import BulletLayout, Mark, WordBox
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
    marks.extend(bullet(40.0 + 12.0 * draw(st.integers(0, rows)) + draw(st.sampled_from([0.0, 0.0, 1.0, -1.0, -2.0])),
                        x=draw(st.sampled_from([22.0, 22.0, 22.0, 22.5, 23.5, 24.0, 190.0, 300.0])),
                        page=draw(st.integers(1, n_pages + 1)))
                 for _ in range(draw(st.integers(0, 7))))
    marks.extend(head_mark(40.0 + 12.0 * draw(st.integers(0, rows)), x=draw(st.sampled_from([10.0, 30.0, 200.0])),
                           page=draw(st.integers(1, n_pages)), text="Head",
                           kind=draw(st.sampled_from(["entry", "part"])))
                 for _ in range(draw(st.integers(0, 3))))
    heights = draw(st.sampled_from([None, [_BOTTOM] * n_pages, [_BOTTOM + 70.0] * n_pages]))
    return draw(st.permutations(marks)), pages, heights


@settings(max_examples=600, deadline=None)
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
    marks = [bullet(118.0)]
    return marks, [page1, page2], [150.0, 150.0]


def _two_columns_doc() -> tuple[list[Mark], list[list[WordBox]], None]:
    """Two lists end their text on page 1, each with the content bottom of its own x band: the left one is the lowest
    text of its band and page 2 does not reach as low (it runs on); the right one has a page 2 whose band goes
    far lower than its last line (its bullet is not at the bottom, so it stays on page 1)."""
    page1: list[WordBox] = [((30.0, 40.0, 120.0, 49.0), "left full"), ((30.0, 52.0, 60.0, 61.0), "ms."),
                            ((200.0, 70.0, 290.0, 79.0), "right full"), ((200.0, 82.0, 230.0, 91.0), "ms.")]
    page2: list[WordBox] = [((30.0, 40.0, 60.0, 49.0), "top"), ((200.0, 40.0, 260.0, 49.0), "top"),
                            ((200.0, 130.0, 290.0, 139.0), "bottom")]
    marks = [bullet(40.0), bullet(70.0, x=190.0)]
    return marks, [page1, page2], None


def test_the_content_bottom_is_read_per_column() -> None:
    marks, pages, heights = _two_columns_doc()

    got = runts.located_bullets(marks, pages, heights)

    assert got == located_bullets_rebuilding(marks, pages, heights)
    assert [[ln.page for ln in lines] for _, lines in got] == [[1, 1, 2], [1, 1]]


def test_the_page_is_clustered_per_distinct_column_not_per_bullet(monkeypatch: pytest.MonkeyPatch) -> None:
    clusters: list[int] = []
    real_cluster = runts.cluster
    monkeypatch.setattr(runts, "cluster", lambda ws: clusters.append(1) or real_cluster(ws))
    bottoms: list[int] = []
    real_bottoms = runts._Document._lowest_per_page
    monkeypatch.setattr(runts._Document, "_lowest_per_page", lambda self, col: bottoms.append(1) or real_bottoms(self, col))
    heads, bullet_marks, words = cv_page(60)

    out = runts.located_bullets(heads + bullet_marks, [words], [10000.0])

    # 180 bullets of one list: a few distinct columns (the column narrows where the words below run out), not one per bullet
    assert len(out) == 180 and 1 <= len(clusters) <= 5 and len(bottoms) <= len(clusters)


def test_equivalence_is_not_vacuous() -> None:
    # control: bullets are located, a bullet runs on across the page break, and a right-to-left marker is read
    marks, pages, heights = _two_page_doc()
    [(pos, lines)] = runts.located_bullets(marks, pages, heights)
    rtl_page: list[WordBox] = [((100.0, 40.0, 150.0, 49.0), "abc"), ((60.0, 52.0, 150.0, 61.0), "def")]
    rtl = runts.located_bullets([bullet(40.0, x=160.0)], [rtl_page], None)

    assert pos.page == 1 and [ln.page for ln in lines] == [1, 1, 2]
    assert lines == located_bullets_rebuilding(marks, pages, heights)[0][1]
    assert len(rtl) == 1 and runts.located_bullets([], [rtl_page]) == []


def test_a_bullet_at_the_bottom_with_a_blank_next_page_is_measured_not_a_crash() -> None:
    # the old code took min() of the next page's words for its top margin: ValueError when that page has none
    page1: list[WordBox] = [((30.0, 118.0, 200.0, 127.0), "last line of page one")]
    marks = [bullet(118.0)]

    [(_, lines)] = runts.located_bullets(marks, [page1, []], [150.0, 150.0])

    assert [ln.page for ln in lines] == [1]


# ------------------------------------------------------------------ the layout shared by the gates


def _sized(words: list[WordBox], height: float = 800.0) -> list[tuple[float, float, list[WordBox]]]:
    return [(600.0, height, words)]


def _boom(*_a: object) -> None:
    raise AssertionError("the bullets were located again")


def test_the_layout_holds_the_located_bullets_and_both_gates_read_it_without_locating(monkeypatch: pytest.MonkeyPatch) -> None:
    heads, bullet_marks, words = cv_page(3)
    marks = heads + bullet_marks
    layout = runts.bullet_layout(marks, _sized(words))
    monkeypatch.setattr(runts, "located_bullets", _boom)

    runts.check_runts(marks, layout, fail=_fail)
    rhythm.check_rhythm(marks, layout, fail=_fail)

    assert layout.located == located_bullets_rebuilding(marks, [words], [800.0])
    assert layout.pages == [words] and layout.heights == [800.0]


def test_the_layout_of_a_document_without_bullets_is_empty() -> None:
    heads, _, words = cv_page(2)

    assert runts.bullet_layout(heads, _sized(words)).located == []


@pytest.mark.parametrize("page", [0, -1, 2], ids=["page-0", "negative-page", "beyond-last"])
def test_a_bullet_on_a_page_outside_the_document_is_dropped_not_read_from_another_page(page: int) -> None:
    heads, bullet_marks, words = cv_page(2)
    assert runts.located_bullets(heads + bullet_marks, [words])          # the same bullets on page 1 are located
    moved = [bullet(m["y"], m["x"], page) for m in bullet_marks if "x" in m and "y" in m]

    assert runts.located_bullets(moved, [words], [800.0]) == []


def test_the_content_bottom_of_a_column_is_read_once_for_all_its_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    bottoms: list[int] = []
    real_bottoms = runts._Document._lowest_per_page
    monkeypatch.setattr(runts._Document, "_lowest_per_page", lambda self, col: bottoms.append(1) or real_bottoms(self, col))
    pages: list[list[WordBox]] = [[((30.0, 118.0, 200.0, 127.0), "last line")] for _ in range(3)]
    marks = [bullet(118.0, page=n) for n in (1, 2, 3)]

    got = runts.located_bullets(marks, pages, [150.0] * 3)

    assert got == located_bullets_rebuilding(marks, pages, [150.0] * 3) and len(got) == 3
    assert len(bottoms) == 1


@pytest.mark.parametrize("check", [runts.check_runts, rhythm.check_rhythm], ids=["runts", "rhythm"])
def test_gates_warn_when_the_word_positions_are_unavailable(check: Callable[..., list[Finding]]) -> None:
    out = check([bullet(10.0)], None, fail=_fail)

    assert [lvl for lvl, _ in out] == [Level.WARN] and "word positions unavailable" in out[0][1]


# ------------------------------------------------------------------ the declared size and the time


def _fail(msg: str) -> Finding:
    return (Level.FAIL, msg)


def _dense_page() -> tuple[list[Mark], list[WordBox]]:
    n_words = 2001
    page: list[WordBox] = [((10.0, float(i), 40.0, i + 9.0), "w") for i in range(n_words)]
    return [bullet(float(i), x=18.0) for i in range(MAX_PAGE_WORK // n_words + 1)], page


def test_a_page_beyond_the_declared_size_is_not_located(monkeypatch: pytest.MonkeyPatch) -> None:
    marks, page = _dense_page()
    monkeypatch.setattr(runts, "located_bullets", _boom)

    assert runts.bullet_layout(marks, _sized(page)).located == []


def test_check_runts_fails_a_page_beyond_the_declared_size_without_measuring_it() -> None:
    marks, page = _dense_page()

    out = runts.check_runts(marks, BulletLayout([page], [800.0], []), fail=_fail)

    assert [lvl for lvl, _ in out] == [Level.FAIL] and "bullet runts not measured: page 1" in out[0][1]


def test_check_rhythm_fails_a_page_beyond_the_declared_size_without_measuring_it() -> None:
    marks, page = _dense_page()

    out = rhythm.check_rhythm(marks, BulletLayout([page], [800.0], []), fail=_fail)

    assert [lvl for lvl, _ in out] == [Level.FAIL] and "spacing rhythm not measured: page 1" in out[0][1]


@pytest.mark.slow
def test_located_bullets_bound_time_on_a_page_of_hundreds_of_bullets() -> None:
    heads, bullet_marks, words = cv_page(160)       # 7 200 words, 480 bullets, 160 heads
    start = time.perf_counter()

    out = runts.located_bullets(heads + bullet_marks, [words], [10000.0])

    assert time.perf_counter() - start < 3.0     # idle ~0.13 s (10x margin); rebuilding the page for every bullet took ~1.5 s
    assert len(out) == 480


@pytest.mark.slow
def test_located_bullets_bound_time_at_the_declared_size_with_a_new_column_per_bullet() -> None:
    # no growth-ratio test for the runts: reading a bullet's column walks the words below its marker, so a page of
    # bullets is O(bullets x words) by design, as the rebuilding version was; the declared size (bounds.py) bounds it,
    # and the count of clusterings (test above) is what separates the two versions
    n_words = 2000
    page: list[WordBox] = [((10.0 + 0.5 * i, 12.0 * (i % 100), 14.0 + 0.5 * i, 12.0 * (i % 100) + 9.0), "w")
                           for i in range(n_words)]
    marks = [bullet(12.0 * (i % 100), x=9.0 + 0.5 * i) for i in range(MAX_PAGE_WORK // n_words)]
    start = time.perf_counter()

    runts.located_bullets(marks, [page], None)

    assert time.perf_counter() - start < 5.0     # idle ~0.4 s: 12x margin, a loaded runner does not trip it
