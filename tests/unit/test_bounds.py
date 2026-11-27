"""vitae.verify.bounds: the declared page size past which the position gates refuse instead of measuring."""
import pytest
from vitae.core.base import Mark
from vitae.core.level import Level
from vitae.core.limits import PAGES_MAX
from vitae.verify.bounds import MAX_PAGE_WORK, density_guard, page_at, too_dense, too_many_pages


def _marks(n: int, page: int = 1) -> list[Mark]:
    return [Mark(text="m", page=page, x=0.0, y=float(i)) for i in range(n)]


def _page(words: int) -> list[int]:
    return list(range(words))


def test_a_page_at_the_limit_is_measured() -> None:
    assert too_dense("g", [_page(2000)], _marks(MAX_PAGE_WORK // 2000)) is None


def test_a_page_one_mark_past_the_limit_is_refused_with_its_numbers() -> None:
    msg = too_dense("g", [_page(2000)], _marks(MAX_PAGE_WORK // 2000 + 1))

    assert msg is not None
    assert msg.startswith("g not measured: page 1 has 1001 marks over 2000 words")
    assert "limit 2,000,000" in msg


def test_the_lowest_oversized_page_is_named_and_other_pages_do_not_add_up() -> None:
    pages = [_page(10), _page(3000), _page(3000)]
    marks = _marks(5, page=1) + _marks(700, page=3) + _marks(700, page=2)

    msg = too_dense("g", pages, marks)

    assert msg is not None and "page 2" in msg


def test_marks_without_a_position_or_on_a_missing_page_are_not_counted() -> None:
    unplaced: list[Mark] = [Mark(text="m")] * 5000

    assert too_dense("g", [_page(3000)], unplaced) is None
    assert too_dense("g", [_page(3000)], _marks(5000, page=2)) is None
    assert too_dense("g", [_page(3000)], _marks(5000, page=0)) is None
    assert too_dense("g", [_page(3000)], _marks(5000, page=-1)) is None


@pytest.mark.parametrize(("number", "expected"), [(1, "a"), (2, "b"), (0, None), (-1, None), (3, None), (4, None)])
def test_page_at_takes_a_one_based_page_number_and_nothing_outside_the_pages(number: int, expected: str | None) -> None:
    assert page_at(["a", "b"], number) == expected


def test_density_guard_returns_the_gates_failure_for_a_dense_page_and_none_otherwise() -> None:
    dense = density_guard("g", [_page(2000)], _marks(MAX_PAGE_WORK // 2000 + 1), lambda m: (Level.FAIL, m))

    assert dense is not None and [lvl for lvl, _ in dense] == [Level.FAIL] and dense[0][1].startswith("g not measured")
    assert density_guard("g", [_page(2000)], _marks(MAX_PAGE_WORK // 2000), lambda m: (Level.FAIL, m)) is None



def test_page_count_bound_is_inclusive() -> None:
    assert too_many_pages("a.pdf", str(PAGES_MAX)) is None
    assert too_many_pages("a.pdf", str(PAGES_MAX + 1)) == "a.pdf: 101 pages exceeds the 100-page bound"


def test_unreadable_page_count_is_not_a_bound_failure() -> None:
    assert too_many_pages("a.pdf", None) is None
    assert too_many_pages("a.pdf", "") is None
