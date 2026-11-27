"""verify.source: _norm_heading (heading normalisation) and check_no_split work on headings in any script."""
import pytest
from vitae.verify.source import _norm_heading, check_no_split

HEADINGS = {"cyrillic": "Досвід роботи", "greek": "Επαγγελματική εμπειρία", "cjk": "工作经历", "devanagari": "कार्य अनुभव",
            "thai": "ประสบการณ์ทำงาน", "arabic": "الخبرة المهنية", "german": "Berufserfahrung"}


@pytest.mark.parametrize("heading", HEADINGS.values(), ids=HEADINGS.keys())
def test_norm_heading_keeps_letters_of_every_script(heading):
    assert _norm_heading(heading) != ""


@pytest.mark.parametrize("heading", ["", "&", " - ", "!!!"], ids=["empty", "ampersand", "dash", "exclamations"])
def test_norm_heading_of_no_letters_is_empty(heading):
    """Control for the test above: the check can return an empty key."""
    assert _norm_heading(heading) == ""


def test_norm_heading_latin_case_and_accents_fold():
    assert _norm_heading("EXPÉRIENCE") == _norm_heading("Expérience") == _norm_heading("EXPERIENCE") == "experience"


@pytest.mark.parametrize("heading, expected", [
    ("Work Experience!", "work experience"),
    ("  A  B ", "a b"),                 # surrounding and repeated spaces collapse
    ("A/B", "a b"),                     # a separator becomes a space
], ids=["trailing-punctuation", "whitespace", "slash"])
def test_norm_heading_lowercases_and_collapses_separators(heading, expected):
    assert _norm_heading(heading) == expected


def test_norm_heading_drops_punctuation():
    assert _norm_heading("Ausbildung & Studium") == "ausbildung studium"


def test_norm_heading_case_folds_cyrillic():
    assert _norm_heading("Досвід роботи") == _norm_heading("ДОСВІД РОБОТИ")


def test_norm_heading_keeps_greek_accents_in_the_exact_key():
    assert _norm_heading("Επαγγελματική εμπειρία") != _norm_heading("ΕΠΑΓΓΕΛΜΑΤΙΚΗ ΕΜΠΕΙΡΙΑ")


def is_fail(src: str, page2: str) -> bool:
    """check_no_split returns (is_fail, message) pairs; page 1 is a placeholder, page 2 is the page under test."""
    return check_no_split(src, ["a", page2])[0][0]


def test_no_split_accepts_greek_uppercase_page_opening_without_accents():
    assert not is_fail('#section("Επαγγελματική εμπειρία")[x]', "ΕΠΑΓΓΕΛΜΑΤΙΚΗ ΕΜΠΕΙΡΙΑ\nx")


def test_no_split_accepts_a_page_opening_on_a_non_latin_heading():
    src = '#section("Досвід роботи")[x]\n#section("Освіта")[y]'
    assert check_no_split(src, ["a", "ОСВІТА\nx"]) == [(False, 'no-split: page 2 opens on "ОСВІТА"')]


def test_no_split_fails_a_page_opening_mid_section():
    """Positive control of the two tests above: the check can fail."""
    src = '#section("Досвід роботи")[x]\n#section("Освіта")[y]'
    assert is_fail(src, "і тоді\nx")


@pytest.mark.parametrize("src, page2", [
    ('#section("الخبرة المهنية")[x]', "المهنية الخبرة\nx"),      # words returned in the other order
    ('#section("कार्य अनुभव")[x]', "कार्य अनुभव\nx"),
], ids=["arabic-reordered", "devanagari"])
def test_no_split_accepts_right_to_left_and_reordered_headings(src, page2):
    assert not is_fail(src, page2)


def test_no_split_is_not_checked_when_the_source_has_no_section_call():
    assert check_no_split("#let x = 1", ["a", "b"]) == [(False, 'no-split: no #section("...") call in the source -- not checked')]
