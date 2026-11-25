"""verify_academic: declared entry statuses, no built-in word list."""
import pytest
import vitae.verify.academic.checks as va_checks
import vitae.verify.academic.parse as va_parse
import vitae.verify.academic.spec as va_spec
from _academic_samples import ACADEMIC, SECTIONS


def failures(results):
    return [m for _, ok, m in results if not ok]


def test_entry_start_recognises_years_by_default():
    rx = va_parse.entry_start_re()
    assert rx.match("2019-2024  Entry") and rx.match("2021 Entry")


@pytest.mark.parametrize("word", ["In press", "submitted", "Sous presse", "Accepted somewhere"])
def test_entry_start_does_not_recognise_a_status_word_unless_declared(word):
    assert not va_parse.entry_start_re().match(f"{word}  Doe, J. A paper")


@pytest.mark.parametrize("status", ["Sous presse", "soumis", "In press", "eingereicht", "投稿中"])
def test_declared_status_is_a_case_insensitive_whole_word(status):
    rx = va_parse.entry_start_re([status])
    assert rx.match(f"{status}  Doe, J. A paper") and rx.match(f"{status.upper()}  Doe, J. A paper")


def test_declared_status_does_not_match_another_word():
    assert not va_parse.entry_start_re(["Sous presse"]).match("Accepted somewhere")


def test_declared_status_is_escaped_not_a_regex():
    rx = va_parse.entry_start_re(["(a.c)"])
    assert rx.match("(a.c) Entry")
    assert not rx.match("(abc) Entry")


@pytest.mark.parametrize("line, want", [
    ("In  press  Doe, J.", True),         # extra spaces in the line
    ("In pressing Doe", False),          # whole word only
])
def test_status_matches_across_whitespace_runs(line, want):
    assert bool(va_parse.entry_start_re(["in press"]).match(line)) is want


def test_status_declared_with_extra_spaces_matches_single_spaced_line():
    assert va_parse.entry_start_re(["in  press"]).match("in press Doe")


def test_declared_status_entry_is_counted():
    results, _ = va_checks.analyze(ACADEMIC, SECTIONS, "Dupont", (), ["Sous presse"])
    assert failures(results) == []


def test_undeclared_status_fails_with_the_declaration_hint():
    results, _ = va_checks.analyze(ACADEMIC, SECTIONS, "Dupont", ())
    assert any("entry_status is not declared" in m for m in failures(results))


def test_undeclared_status_fails_instead_of_passing_a_wrong_count():
    results, _ = va_checks.analyze(ACADEMIC, SECTIONS, "Dupont", ())
    assert any("declared 2, extracted 1" in m for m in failures(results))


def test_declared_statuses_are_read_from_meta():
    assert va_spec.declared_statuses({"meta": {"entry_status": ["Soumis"]}}) == ["Soumis"]


@pytest.mark.parametrize("data", [{"meta": {}}, {}], ids=["empty-meta", "no-meta"])
def test_no_declared_status_reads_as_an_empty_list(data):
    assert va_spec.declared_statuses(data) == []


def test_declared_status_that_is_not_a_list_is_rejected():
    with pytest.raises(ValueError):
        va_spec.declared_statuses({"meta": {"entry_status": "Soumis"}})
