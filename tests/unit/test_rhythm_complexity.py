"""LOG320 worst-case sweep of rhythm.py: the head index answers `separated` exactly as the old filter of every mark did
(Hypothesis, on integer grids so that the strict and inclusive bounds are hit), and stays fast with thousands of
bullet pairs over thousands of heads (`slow`)."""
import time

import pytest
from _rhythm_ref import separated_filtering
from hypothesis import given, settings
from hypothesis import strategies as st
from vitae.core.base import Mark
from vitae.verify.rhythm import _HeadIndex
from vitae.verify.runts import Pos

_coord = st.integers(0, 12).map(float)


@st.composite
def _mark(draw: st.DrawFn) -> Mark:
    kind = draw(st.sampled_from(["bullet", "entry", "skill", "part", None]))
    mark = Mark(text="t", page=draw(st.integers(1, 2)), x=draw(_coord), y=draw(_coord))
    if kind is not None:
        mark["kind"] = kind
    if draw(st.booleans()) and draw(st.integers(0, 4)) == 0:
        del mark["x"]          # a partial mark carries no position
    return mark


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


@pytest.mark.slow
def test_head_index_bounds_time_with_thousands_of_pairs_over_thousands_of_heads() -> None:
    n = 6000
    marks = [Mark(text="h", page=1, x=500.0 + i % 7, y=float(i), kind="entry") for i in range(n)]
    pairs = [(Pos(1, 10.0, float(i)), Pos(1, 10.0, float(i + 1))) for i in range(0, n, 2)]
    start = time.perf_counter()

    index = _HeadIndex(marks)
    found = [index.separated(a, b, 10.0, 100.0) for a, b in pairs]

    assert time.perf_counter() - start < 1.0     # measured ~0.01 s; filtering every mark per pair took ~3 s
    assert not any(found)
