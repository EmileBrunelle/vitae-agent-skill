"""verify.py --selftest: Rule 1 gate: the facts check flags a number the facts do not say"""

from __future__ import annotations

from vitae.verify.text import check_facts_coverage


def facts_coverage() -> None:
    """Rule 1 gate: the facts check flags a number the facts do not say."""
    # Rule 1 gate: the facts check flags a year, numeric month+year or number the facts do not say, and reads no word.
    # `_good` re-spells the facts ($50k for $50,000) and must stay silent: a faithful paraphrase is not an invention.
    _facts = ("Jane Roe\nAnalyst, Acme Corp, 2020–2022 (year only, no months known)\n"
              "- Cut reporting time by 40%, saving $50,000 across 12 teams. Python, SQL.\n"
              "Education: B.Sc. Université de Montréal, 2018\n")
    _good = ("Jane Roe\nPROFESSIONAL EXPERIENCE\nAnalyst, Acme Corp  2020 – 2022\n"
             "Cut reporting time by 40%, saving $50k across 12 teams\n"
             "Built Python and SQL pipelines\nUniversite de Montreal  2018\n")
    assert check_facts_coverage(_good, _facts) == [], check_facts_coverage(_good, _facts)
    _w = check_facts_coverage("Analyst, Acme Corp  2020 – 2023\nGrew revenue 75% in 1999\n", _facts)
    assert len(_w) == 3 and all(x.startswith("WARN  not in facts file:") for x in _w), _w
    assert '"2023"' in _w[0] and '"1999"' in _w[1] and '"75%"' in _w[2], _w
    assert "remove it or confirm it with the candidate (rule 1)" in _w[0], _w
    assert len(check_facts_coverage("1999\n1999\n", _facts)) == 1
    assert check_facts_coverage("Globex Industries, AWS, Sep 2020\n", _facts) == []     # no word is read: names are the agent's
    assert check_facts_coverage("03/2020", "2020-03") == [] and check_facts_coverage("2020-03", "03.2020") == []
    _w = check_facts_coverage("04/2020", "2020-03")
    assert len(_w) == 1 and '"04/2020"' in _w[0], _w
    _f2 = "Analyst, 2020-2022\nPython 3.11, 75 percent\n"
    for _ph in ("(514) 555-1234", "1 800 555 1234", "+1 514 555 1234", "514-555-1234"):
        assert check_facts_coverage("Contact " + _ph + "\n", _f2) == [], _ph
    assert check_facts_coverage("Grew by 75%\nGrew 75 percent\nCroissance de 75 pour cent\n", _f2) == []
    assert any('"3.12"' in x for x in check_facts_coverage("Python 3.12\n", _f2))
    assert check_facts_coverage("Python 3.11\n", _f2) == []
