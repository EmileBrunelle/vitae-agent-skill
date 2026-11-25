"""verify_academic: headings are declared in [headings], never guessed from a language."""
import pytest
import vitae.verify.academic.checks as va_checks
import vitae.verify.academic.parse as va_parse
import vitae.verify.academic.spec as va_spec
from _academic_samples import ACADEMIC, SECTIONS

FR_HEADINGS = {"education": "Formation", "publications": {"journal": "Articles de revues"}}


def failures(results):
    return [m for _, ok, m in results if not ok]


def _full_data(data):
    counts = {k: 0 for k in ("education", "appointments", "honours", "funding", "supervision", "teaching", "service",
                             "knowledge_mobilization", "references")}
    counts["publications"] = {"journal": 0, "conference": 0, "preprint": 0}
    counts["talks"] = {k: 0 for k in ("plenary", "invited", "conference", "seminar", "poster")}
    counts.update({k: v for k, v in data["counts"].items() if k != "publications"})
    counts["publications"].update(data["counts"].get("publications", {}))
    return {**data, "counts": counts}


def test_missing_declared_heading_is_reported_plainly():
    text = ACADEMIC.replace("EDUCATION", "FORMATION").replace("PUBLICATIONS: JOURNAL ARTICLES", "ARTICLES DE REVUE")
    results, _ = va_checks.analyze(text, SECTIONS, "Dupont", (), ["Sous presse"])
    assert any("EDUCATION: declared 1 but this heading was not found" in m for m in failures(results))


def test_missing_heading_report_makes_no_language_guess():
    text = ACADEMIC.replace("EDUCATION", "FORMATION")
    results, _ = va_checks.analyze(text, SECTIONS, "Dupont", (), ["Sous presse"])
    assert not any("not checked for" in m for m in failures(results))


def test_undeclared_french_heading_fails_with_the_hint():
    text = ACADEMIC.replace("EDUCATION", "FORMATION")
    results, _ = va_checks.analyze(text, SECTIONS, "Dupont", (), ["Sous presse"])
    assert any("EDUCATION" in m and "declare it under [headings]" in m for m in failures(results))


def test_declared_french_headings_are_built_into_the_section_spec():
    data = _full_data({"counts": {"education": 1, "publications": {"journal": 2}}, "headings": FR_HEADINGS})
    secs = va_spec.build_sections_spec(data)
    assert [s["heading"] for s in secs if s["heading"] in ("Formation", "Articles de revues")] == ["Formation", "Articles de revues"]


def test_declared_french_headings_make_the_counts_pass_case_insensitively():
    text = ACADEMIC.replace("EDUCATION", "FORMATION").replace("PUBLICATIONS: JOURNAL ARTICLES", "Articles de revues")
    secs: list[va_spec.Section] = [{"heading": "Formation", "count": 1, "undated_prefix": 0, "numbered": False},
                                   {"heading": "Articles de revues", "count": 2, "undated_prefix": 1, "numbered": False}]
    results, _ = va_checks.analyze(text, secs, "Dupont", (), ["Sous presse"], ["Formation", "Articles de revues"])
    assert failures(results) == []


def test_unknown_headings_key_fails_naming_it():
    res = va_spec.check_headings_table({"headings": {"educaton": "Formation"}})
    msgs = failures(res)
    assert len(msgs) == 1 and "educaton" in msgs[0]


def test_unknown_publications_subkey_fails_naming_it():
    res = va_spec.check_headings_table({"headings": {"publications": {"jurnal": "X", "journal": "Y"}}})
    msgs = failures(res)
    assert len(msgs) == 1 and "publications.jurnal" in msgs[0]


@pytest.mark.parametrize("data", [{"headings": FR_HEADINGS}, {}], ids=["valid-table", "no-table"])
def test_valid_or_absent_headings_table_gives_no_failure(data):
    assert va_spec.check_headings_table(data) == []


def test_headings_table_that_is_not_a_table_fails():
    assert failures(va_spec.check_headings_table({"headings": "Formation"})) == ["[headings] must be a table"]


def test_subsection_heading_given_as_a_string_fails():
    msgs = failures(va_spec.check_headings_table({"headings": {"publications": "Pubs"}}))
    assert len(msgs) == 1 and "publications" in msgs[0] and "expects a table of subsections" in msgs[0]


def test_english_body_line_equal_to_a_heading_up_to_case_is_not_a_heading():
    secs: list[va_spec.Section] = [{"heading": "EDUCATION", "count": 2, "undated_prefix": 0, "numbered": False},
                                   {"heading": "TEACHING", "count": 0, "undated_prefix": 0, "numbered": False}]
    text = ("Dupont\nEDUCATION\n2015  PhD, Université de Montréal, thesis on graph colouring and its applications.\n"
            "Teaching\n2012  MSc, McGill University, thesis on planar graphs and their colourings in general.\n")
    results, _ = va_checks.analyze(text, secs, "Dupont", ())
    assert failures(results) == []


def test_canonical_headings_leaves_text_alone_without_declared_headings():
    text = "Dupont\nTeaching\n2012 MSc"
    assert va_parse._canonical_headings(text, set()) == text


def test_canonical_headings_rewrites_a_declared_heading_to_its_declared_case():
    assert va_parse._canonical_headings("formation", {"Formation"}) == "Formation"


def test_affiliations_heading_can_be_declared():
    assert va_spec.check_headings_table({"headings": {"affiliations": "Affiliations et langues"}}) == []


def test_declared_affiliations_heading_is_printed_but_is_not_a_counts_key():
    extra, declared = va_spec.printed_headings({"headings": {"affiliations": "Affiliations et langues"}})
    assert extra == ("Affiliations et langues",) and declared == ["Affiliations et langues"]


def test_printed_headings_default_to_the_built_in_extras():
    assert va_spec.printed_headings({})[0] == va_spec.EXTRA_HEADINGS
