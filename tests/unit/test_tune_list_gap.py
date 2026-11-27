"""--tune keeps the list-item gap (list spacing less leading) at the core.md floor when the rhythm shrinks."""
import pytest
from vitae.verify import tune as T
from vitae.verify.typst import doc_par_list_size, read_par

SRC = ("#let rhythm = 0.972\n#set par(justify: false, leading: 0.528em, spacing: 0.601em)\n"
       "#set list(indent: 10pt, spacing: 0.688em)\nbody\n")


def gap(text: str) -> float:
    lead, lsp, _ = doc_par_list_size(text)
    assert lead is not None and lsp is not None
    return lsp - lead


@pytest.mark.parametrize("rhythm", [0.972, 0.959, 0.95, 0.91])
def test_shrinking_rhythm_keeps_the_gap(rhythm: float) -> None:
    out = T._with_gap_scale(SRC, rhythm)
    assert gap(out) >= T.LIST_GAP_FLOOR - 1e-9
    par = read_par(out)
    assert par is not None and par[0] == 0.528     # leading untouched


def test_growing_rhythm_scales_the_list_spacing() -> None:
    out = T._with_gap_scale(SRC, 1.1)
    assert doc_par_list_size(out)[1] == pytest.approx(0.688 * 1.1 / 0.972, abs=1e-3)


def test_gap_already_under_the_floor_is_not_made_worse() -> None:
    src = SRC.replace("0.688em", "0.600em")           # gap 0.072 < floor
    assert gap(T._with_gap_scale(src, 0.95)) >= gap(src) - 1e-9


def test_leading_bisection_below_one_keeps_the_floor() -> None:
    """Leading lowered by k<1 scales the list spacing by k too: 0.16 x 0.9 = 0.144 em would break the floor."""
    out = T._with_rhythm(SRC, 0.528 * 0.9, 0.601 * 0.9)
    assert gap(out) >= T.LIST_GAP_FLOOR - 1e-9


def test_leading_bisection_leaves_a_file_under_the_floor_alone() -> None:
    src = SRC.replace("0.688em", "0.600em")
    out = T._with_rhythm(src, 0.528, 0.601)
    assert gap(out) == pytest.approx(gap(src), abs=1e-3)


TWO = ("#let rhythm = 1\n#set par(leading: 0.5em, spacing: 0.6em)\n#set list(spacing: 0.66em)\n"
       "#set list(spacing: 0.9em)\nbody\n")


def test_each_list_rule_is_floored_not_only_the_last() -> None:
    from vitae.verify.typst import list_rules
    out = T._with_gap_scale(TWO, 0.9)
    rules = list_rules(out)
    assert len(rules) == 2
    for r in rules:
        assert r.leading is not None and r.spacing_em - r.leading >= T.LIST_GAP_FLOOR - 1e-9
