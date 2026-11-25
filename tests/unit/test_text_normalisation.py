"""verify.text: _fold and _fold1 strip accents from Latin letters only; _num_values extracts numbers. Private helpers."""
import pytest
from vitae.verify.text import _fold, _fold1, _num_values


def test_fold_strips_latin_accents_and_lowercases():
    assert _fold("Expérience Çà") == "experience ca"


@pytest.mark.parametrize("text", ["कार्य अनुभव", "การศึกษา"], ids=["devanagari", "thai"])
def test_fold_keeps_vowel_and_tone_marks_of_other_scripts(text):
    assert _fold(text) == text


def test_fold_normalises_typographic_apostrophe_and_dash():
    assert _fold("Éléphant — Ça’va") == "elephant - ca'va"


def test_fold_strips_surrounding_whitespace_to_single_spaces():
    assert _fold("  A\n\tB ") == " a b "


def test_fold_of_empty_is_empty():
    assert _fold("") == ""


def test_fold_unifies_every_dash_variant():
    assert _fold("a–b‒c−d") == "a-b-c-d"


def test_fold_unifies_dashes_and_collapses_whitespace():
    assert _fold("2019 – 2020— x") == "2019 - 2020- x"
    assert _fold("a   \n b") == "a b"


@pytest.mark.parametrize("text", ["Évry İstanbul", "कार्य अनुभव", "การศึกษา", "Йога", "ÉCOLE Ωmega"],
                         ids=["latin", "devanagari", "thai", "cyrillic", "latin-greek"])
def test_fold1_is_length_preserving(text):
    assert len(_fold1(text)) == len(text)


def test_fold1_lowercases_and_strips_latin_accents():
    assert _fold1("Évry") == "evry"


def test_fold1_leaves_devanagari_untouched():
    assert _fold1("कार्य अनुभव") == "कार्य अनुभव"


@pytest.mark.parametrize("text", ["й", "क़"], ids=["cyrillic-short-i-breve", "devanagari-precomposed-nukta"])
def test_fold1_keeps_precomposed_letters_of_other_scripts(text):
    """These letters decompose under NFKD: folding them as Latin would drop their mark."""
    assert _fold1(text) == text


@pytest.mark.parametrize("text, expected", [
    ("1,200", {1200.0}),
    ("1 200", {1200.0}),
    ("1.5k", {1500.0}),
    ("2M", {2_000_000.0}),
    ("3,5", {3.5}),                         # decimal comma
    ("10 000 000", {10_000_000.0}),
    ("", set()),
    ("abc", set()),
    ("1,2,3", set()),                       # malformed: "1.2.3" is not a float and is skipped, not raised
])
def test_num_values_extracts_numbers_in_every_notation(text, expected):
    assert _num_values(text) == expected
