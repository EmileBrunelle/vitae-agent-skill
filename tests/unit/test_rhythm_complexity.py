"""LOG320 worst-case sweep of rhythm.py: the head index answers `separated` exactly as the old filter of every mark did
(Hypothesis, on integer grids so that the strict and inclusive bounds are hit), and its work, counted in line events (no
wall clock), stays linear with thousands of bullet pairs over thousands of heads."""
from collections.abc import Callable

from _complexity import assert_linear, line_events
from _rhythm_ref import separated_filtering
from hypothesis import given, settings
from hypothesis import strategies as st
from vitae.core.base import Mark, Pos
from vitae.verify.rhythm import _HeadIndex

_coord = st.integers(0, 12).map(float)


@st.composite
def _mark(draw: st.DrawFn) -> Mark:
    kind = draw(st.sampled_from(["bullet", "entry", "skill", "part", None]))
    page, x, y = draw(st.integers(1, 2)), draw(_coord), draw(_coord)
    if draw(st.booleans()) and draw(st.integers(0, 4)) == 0:     # a partial mark carries no position
        return Mark(text="t", page=page, y=y) if kind is None else Mark(text="t", page=page, y=y, kind=kind)
    return Mark(text="t", page=page, x=x, y=y) if kind is None else Mark(text="t", page=page, x=x, y=y, kind=kind)


@settings(max_examples=800, deadline=None)
@given(st.lists(_mark(), max_size=14), st.integers(1, 2), _coord, _coord, st.integers(-2, 12).map(float),
       st.integers(-2, 12).map(float))
def test_head_index_matches_the_old_filter(marks: list[Mark], page: int, ya: float, yb: float, lo: float,
                                           hi: float) -> None:
    a, b = Pos(page, 3.0, ya), Pos(page, 3.0, yb)

    assert _HeadIndex(marks).separated(a, b, lo, hi) == separated_filtering(marks, a, b, lo, hi)


def test_head_index_equivalence_is_not_vacuous() -> None:
    marks = [Mark(text="h", page=1, x=10.0, y=5.0, kind="entry"), Mark(text="b", page=1, x=10.0, y=6.0, kind="bullet"),
             Mark(text="s", page=1, x=200.0, y=7.0, kind="entry"), Mark(text="o", page=2, x=10.0, y=5.0, kind="part")]
    index = _HeadIndex(marks)

    assert index.separated(Pos(1, 10.0, 4.0), Pos(1, 10.0, 8.0), 10.0, 100.0)           # a head between, in the column
    assert not index.separated(Pos(1, 10.0, 5.0), Pos(1, 10.0, 7.0), 10.0, 100.0)     # bounds are strict
    assert not index.separated(Pos(1, 10.0, 6.0), Pos(1, 10.0, 8.0), 10.0, 100.0)     # only a sidebar head, a bullet
    assert not index.separated(Pos(1, 10.0, 4.0), Pos(1, 10.0, 8.0), 300.0, 400.0)
    assert not index.separated(Pos(3, 10.0, 4.0), Pos(3, 10.0, 8.0), 10.0, 100.0)     # no mark on page 3


_RHYTHM_FILES = frozenset({_HeadIndex.__init__.__code__.co_filename, separated_filtering.__code__.co_filename})


def _separated_events(separated: Callable[[list[Mark], list[tuple[Pos, Pos]]], list[bool]], n: int) -> int:
    marks = [Mark(text="h", page=1, x=500.0 + i % 7, y=float(i), kind="entry") for i in range(n)]
    pairs = [(Pos(1, 10.0, float(i)), Pos(1, 10.0, float(i + 1))) for i in range(0, n, 2)]
    events, found = line_events(_RHYTHM_FILES, lambda: separated(marks, pairs))
    assert len(found) == len(pairs) and not any(found)     # every pair was asked, none is separated (heads are in a sidebar)
    return events


def _indexed(marks: list[Mark], pairs: list[tuple[Pos, Pos]]) -> list[bool]:
    index = _HeadIndex(marks)
    return [index.separated(a, b, 10.0, 100.0) for a, b in pairs]


def _filtering(marks: list[Mark], pairs: list[tuple[Pos, Pos]]) -> list[bool]:
    return [separated_filtering(marks, a, b, 10.0, 100.0) for a, b in pairs]


def test_head_index_work_grows_linearly_with_thousands_of_pairs_over_thousands_of_heads() -> None:
    assert_linear(lambda n: _separated_events(_indexed, n), 375)      # measured 2.0 x per doubling


def test_the_work_count_tells_the_filtering_version_from_the_head_index() -> None:
    # control: the same counter shows the old filter quadratic (4.0 x per doubling at 375, 750, 1500 marks)
    w1, w2, w4 = (_separated_events(_filtering, 375 * k) for k in (1, 2, 4))

    assert w2 / w1 > 3.5 and w4 / w2 > 3.5
