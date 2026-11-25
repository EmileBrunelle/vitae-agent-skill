"""check_facts_coverage reads digits only, in any script (development only).

The scripts know no language: a gate reads digits, geometry and fonts, never a word.
"""
import pytest
from _samples import FAMILIES, INVENTED_LINE, INVENTED_TOKENS
from vitae.verify.text import check_facts_coverage


def warns(cv: str, facts: str) -> list[str]:
    return [x for x in check_facts_coverage(cv, facts) if x.startswith("WARN")]


def quoted(out: list[str]) -> set[str]:
    return {x.split('"')[1].strip() for x in out}


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_clean_run_gives_no_finding(family):
    cv, facts = FAMILIES[family]
    assert check_facts_coverage(cv, facts) == []


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_invented_years_and_number_are_warned_in_every_script(family):
    """Positive control of the clean run above: the same pair with figures the facts never state."""
    cv, facts = FAMILIES[family]
    assert quoted(warns(cv + "\n" + INVENTED_LINE, facts)) == INVENTED_TOKENS


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_figure_stated_in_the_facts_is_not_warned_in_every_script(family):
    """Same injection, but the facts state it too: the warning is driven by the facts, not by the line itself."""
    cv, facts = FAMILIES[family]
    assert warns(cv + "\n" + INVENTED_LINE, facts + "\n" + INVENTED_LINE) == []


def test_a_name_never_warns_because_no_word_is_read():
    facts = "# Experience\nAcme Software, Boston. Built web applications and led five developers."
    assert warns("Summer intern at Globex Corporation, AWS and Škoda.", facts) == []


def test_a_year_beside_names_is_still_warned():
    """Control for the test above: the same sentence with a year added does warn."""
    facts = "# Experience\nAcme Software, Boston. Built web applications and led five developers."
    assert quoted(warns("Summer intern at Globex Corporation, 2019.", facts)) == {"2019"}


# --- thousands separators: "1.500" is 1500 or 1.5 ---------------------------------------------------------------------

@pytest.mark.parametrize("cv, facts", [
    ("Umsatz von 1.500 Kunden.", "Kunden: 1500"),
    ("Facturación de 1.500.000 euros.", "Facturación: 1500000 euros"),
    ("Revenue of 1,500 clients.", "Clients: 1500"),
], ids=["dot-thousands", "dot-thousands-millions", "comma-thousands"])
def test_thousands_separator_matches_a_facts_file_written_with_plain_digits(cv, facts):
    assert warns(cv, facts) == []


def test_a_different_number_is_warned_despite_the_separator():
    out = warns("Revenue of 1,600 clients.", "Clients: 1500")
    assert len(out) == 1 and '"1,600' in out[0]
