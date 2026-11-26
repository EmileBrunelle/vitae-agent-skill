"""check_facts_coverage: figures the facts do not state are flagged; faithful re-spellings stay quiet."""
import pytest
from vitae.verify.text import check_facts_coverage

FACTS = ("Jane Roe\nAnalyst, Acme Corp, 2020–2022 (year only, no months known)\n"
         "- Cut reporting time by 40%, saving $50,000 across 12 teams. Python 3.11, 75 percent, SQL.\n"
         "Education: B.Sc. Université de Montréal, 2018\nStage, 2020-03\n")


def test_faithful_respelling_is_silent():
    cv = ("Jane Roe\nAnalyst, Acme Corp  2020 – 2022\nCut reporting time by 40%, saving $50k across 12 teams\n"
          "Built Python and SQL pipelines\nUniversite de Montreal  2018\n")
    assert check_facts_coverage(cv, FACTS) == []


def test_invented_figures_are_flagged_in_order_with_the_remedy():
    w = check_facts_coverage("Analyst, Acme Corp  2020 – 2023\nGrew revenue 75% in 1999\n", "Analyst 2020–2022\n")
    assert len(w) == 3 and all(x.startswith("WARN  not in facts file:") for x in w)
    assert ['"2023"' in w[0], '"1999"' in w[1], '"75%"' in w[2]] == [True] * 3
    assert "remove it or confirm it with the candidate (rule 1)" in w[0]


def test_a_repeated_figure_is_reported_once():
    assert len(check_facts_coverage("1999\n1999\n", FACTS)) == 1


@pytest.mark.parametrize("cv, facts, fires", [
    ("03/2020", "2020-03", False), ("2020-03", "03.2020", False), ("04/2020", "2020-03", True),
    ("Python 3.11\n", FACTS, False), ("Python 3.12\n", FACTS, True),
    ("Grew by 75%\nGrew 75 percent\nCroissance de 75 pour cent\n", FACTS, False),
    ("Globex Industries, AWS, Sep 2020\n", FACTS, False),                    # no word is read
])
def test_equivalent_spellings(cv, facts, fires):
    assert bool(check_facts_coverage(cv, facts)) == fires
