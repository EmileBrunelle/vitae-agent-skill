"""_blank_phones: a phone number is a contact detail, not a claim; a date or a result never is a phone."""
import pytest
from vitae.verify.text import _blank_phones, check_facts_coverage

FACTS = "# Experience\nDeveloper at Acme, 2015 to 2016."


def warns(cv: str, facts: str) -> list[str]:
    return [x for x in check_facts_coverage(cv, facts) if x.startswith("WARN")]


PHONES = ["06 12 34 56 78", "+49 30 1234567", "0151-2345678", "+33 6 12 34 56 78", "01.23.45.67.89",
          "+34 612 345 678", "(514) 555-0123", "+1 514 555 0123", "+49 170 1234567", "0170 1234567"]


@pytest.mark.parametrize("phone", PHONES)
def test_phone_is_blanked_to_spaces_of_the_same_length(phone):
    assert _blank_phones(phone) == " " * len(phone)


@pytest.mark.parametrize("phone", PHONES)
def test_phone_never_reaches_the_warnings(phone):
    assert warns(f"Contact: {phone}\nDeveloper at Acme.", FACTS) == []


def test_the_phone_gate_can_fire_on_the_same_line_without_the_phone():
    """Control: the line is not exempt, only the phone is."""
    assert any('"2019' in x for x in warns("Contact: 06 12 34 56 78, since 2019", FACTS))


@pytest.mark.parametrize("claim", ["300 staff", "840 ms", "1 500 000 users", "2019 - 2021 staff of 120",
                                   "0.5 s to 120 000 rows"])
def test_real_results_are_not_swallowed_as_phones(claim):
    assert _blank_phones(claim) == claim


# --- boundary: how many digits make a phone ------------------------------------------------------------------------

@pytest.mark.parametrize("text, blanked", [
    ("0151 2345", True),       # 8 digits, 2 groups: smallest phone
    ("0151 234", False),       # 7 digits: one short
    ("01234567", False),       # 8 digits but a single group
    ("+12345678", True),       # 8 digits with a +
    ("+1234567", False),       # 7 digits with a +: one short
], ids=str)
def test_phone_length_boundary(text, blanked):
    assert (_blank_phones(text).strip() == "") is blanked


# --- numeric dates ------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("dates", [
    "01.03.2019 – 05.06.2021", "01.03.2019 - 05.06.2021", "01.03.2019-05.06.2021", "01-03-2019 – 05-06-2021",
    "01/03/2019 – 05/06/2021", "1.3.2019 – 5.6.2021", "10.03.2019 – 30.06.2021"])
def test_numeric_date_range_is_not_blanked(dates):
    assert _blank_phones(dates) == dates


@pytest.mark.parametrize("dates", ["01.03.2019 – 05.06.2021", "10.03.2019 – 30.06.2021"])
def test_years_of_a_numeric_date_are_warned_when_the_facts_lack_them(dates):
    out = warns(f"Developer, {dates}", FACTS)
    assert any("2019" in x for x in out) and any("2021" in x for x in out)


@pytest.mark.parametrize("date, kept", [
    ("01.12.2019", True),      # month 12: last valid month
    ("01.13.2019", False),     # month 13: not a date, blanked as a phone
    ("31.12.2019", True),      # day 31 with a leading digit 3
    ("01.12.1999", True),      # year 19xx lower edge
    ("01.12.1899", False),     # year 18xx: not a date
    ("01.12.2099", True),      # year 20xx upper edge
    ("01.12.2100", False),     # year 21xx: not a date
], ids=str)
def test_date_validity_boundary(date, kept):
    assert (_blank_phones(date) == date) is kept


@pytest.mark.parametrize("line", [
    "(05.06.2021)", "(01.03.2019 – 05.06.2021)", "Developer (05.06.2021)", "05.06.2021 12.07.2022 13.08.2023",
    "01.03.2019 1500 staff", "01.03.2019 2024 award"])
def test_dates_survive_parentheses_and_neighbouring_numbers(line):
    assert _blank_phones(line) == line


@pytest.mark.parametrize("cv, facts, token", [
    ("Developer (05.06.2021)", FACTS, "2021"),
    ("01.03.2019 2024 award", "Award, 2019.", "2024"),
    ("01.03.2019 – 05.06.2021 12.07.2022", FACTS, "2022"),
], ids=["parenthesised", "beside-number", "third-date-of-a-run"])
def test_invented_year_in_a_date_still_warns(cv, facts, token):
    assert any(token in x for x in warns(cv, facts))


def test_a_number_beside_a_date_is_not_warned_when_the_facts_state_it():
    out = warns("Developer, 01.03.2019 1500 staff", "Developer, 2019. 1500 staff.")
    assert not any("1500" in x for x in out)


def test_a_number_beside_a_date_is_warned_when_the_facts_lack_it():
    """Control for the test above."""
    assert any("1500" in x for x in warns("Developer, 01.03.2019 1500 staff", "Developer, 2019."))


# --- date-shaped phones ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("phone", ["04-12-3456-7890", "05-06-2021-1234 5678", "03-12-2012-3456"])
def test_date_shaped_phone_is_blanked(phone):
    assert _blank_phones(phone).strip() == ""


def test_date_shaped_phone_after_a_label_leaves_only_the_label():
    assert _blank_phones("Tel 04-12-3456-7890").strip() == "Tel"


def test_phone_next_to_a_date_is_blanked_and_the_date_kept():
    assert _blank_phones("01.03.2019 - 06 12 34 56 78") == "01.03.2019 -" + " " * 15
