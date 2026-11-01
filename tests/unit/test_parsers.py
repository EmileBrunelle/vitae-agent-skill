"""Pinned behaviour of verify.py's pure parsing helpers (development only, not shipped logic).

Each test records what the function does TODAY. The two xfail(strict) cases are probable defects: they state the
documented behaviour and flip to a failure (XPASS) the day the function is fixed, at which point drop the marker.
"""
import pytest
import verify as v
import verify_typst

# --- _call_strings ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("body, j, strs, end", [
    ('"a", "b") tail', 0, ["a", "b"], 9),
    ('"a" (nested "x") "y") z', 0, ["a", "x", "y"], 21),   # nested call's strings are collected too
    ('"b\\"c") tail', 0, ['b\\"c'], 7),                     # escaped quote kept raw, not unescaped
    ('")" , "x")', 0, [")", "x"], 10),                      # a paren inside a string does not close the call
    (")", 0, [], 1),
    ("", 0, [], 0),
])
def test_call_strings(body, j, strs, end):
    assert v._call_strings(body, j) == (strs, end)


def test_call_strings_unterminated_string_is_kept():
    assert v._call_strings('"unclosed', 0)[0] == ["unclosed"]


# --- _section_bodies -------------------------------------------------------------------------------------------

def test_section_bodies_balances_brackets_and_escapes():
    src = '#section("Exp")[ a [b] c ]\n#section("Edu", x: 1)[ d \\] e ]'
    assert v._section_bodies(src) == [("Exp", " a [b] c "), ("Edu", " d \\] e ")]


@pytest.mark.parametrize("src", ["", "no section here", '#section("NoBody")'])
def test_section_bodies_none(src):
    assert v._section_bodies(src) == []


@pytest.mark.xfail(strict=True, reason="unclosed bracket: body is cut one char short (src[m.end():i - 1] with i == len)")
def test_section_bodies_unclosed_keeps_whole_tail():
    assert v._section_bodies('#section("Bad")[ open') == [("Bad", " open")]


# --- _entries --------------------------------------------------------------------------------------------------

ENTRY = '''#entry("Dev", "Acme Inc", "Jan 2020 – Mar 2021", "Montréal · QC | Remote, Hybrid")
- Built things
  continued here
- Second
#entry("Solo")
'''


def test_entries_descriptors_bullets_and_separators():
    assert v._entries(ENTRY) == [
        ("Dev", ["Montréal", "QC", "Remote", "Hybrid"], ["Built things continued here", "Second"]),
        ("Solo", [], []),
    ]


def test_entries_org_as_descriptor_keeps_second_argument():
    assert v._entries(ENTRY, True)[0][1] == ["Acme Inc", "Montréal", "QC", "Remote", "Hybrid"]


@pytest.mark.parametrize("body, expected", [
    ("", []),
    ('#entry("Only")', [("Only", [], [])]),
    ("#entry()", [("", [], [])]),
    ('#entry("T", "Org", "2020 – Present")', [("T", [], [])]),        # date-bearing argument is dropped
    ('#entry("T", "Org", "Québec, QC")', [("T", ["Québec", "QC"], [])]),
    ("plain prose, no call", []),
])
def test_entries_edge_cases(body, expected):
    assert v._entries(body) == expected


# --- _facts_items (the brief's `_facts_blocks`; that name does not exist) -------------------------------------------

def test_facts_items_headings_bullets_and_parent_titles():
    text = "# A\n## B\ntext\n- bullet\n  more\n## C\n"
    assert v._facts_items(text) == [
        (0, 6, "# A\n## B\ntext\n- bullet\n  more\n## C"),
        (1, 5, "# A\n## B\ntext\n- bullet\n  more"),
        (3, 5, "# A\n## B\n- bullet\n  more"),
        (5, 6, "# A\n## C"),
    ]


@pytest.mark.parametrize("text", ["", "just prose\nno headings or bullets"])
def test_facts_items_none(text):
    assert v._facts_items(text) == []


# --- _figures --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("Saved 40 minutes, 5k users, $1,200 and 3 things in 2021", {40.0, 5000.0, 1200.0}),
    ("5%", {5.0}),
    ("12 345 requests", {12345.0}),
    ("2M users", {2_000_000.0}),
    ("", set()),
    ("abc", set()),
    ("in 2021", set()),                     # a bare year is not a figure
])
def test_figures(text, expected):
    assert v._figures(text) == expected


# --- _month_years ----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("Jan 2020", {(1, 2020)}),
    ("janvier 2020 à mars 2021", {(1, 2020), (3, 2021)}),
    ("déc. – janv. 2020", {(12, 2019), (1, 2020)}),     # a range wrapping the year opens the year before
    ("03/2020", {(3, 2020)}),
    ("2020-03", {(3, 2020)}),
    ("", set()),
    ("foo bar", set()),
])
def test_month_years(text, expected):
    assert v._month_years(text) == expected


# --- _fold -----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("s, expected", [
    ("Éléphant — Ça’va", "elephant - ca'va"),
    ("  A\n\tB ", " a b "),
    ("", ""),
    ("a–b‒c−d", "a-b-c-d"),
])
def test_fold(s, expected):
    assert v._fold(s) == expected


# --- _name_norm ------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("s, expected", [
    ("Acme Inc.", " acme "),
    ("Café L’Été Ltée", " cafe l'ete "),
    ("Dupont & Fils", " dupont & fils "),
    ("Acme GmbH", " acme "),
    ("", "  "),
    ("Corp", "  "),                         # a bare suffix leaves nothing
])
def test_name_norm(s, expected):
    assert v._name_norm(s) == expected


@pytest.mark.xfail(strict=True, reason="docstring says SA is removed, but the dotted form 'S.A.' folds to 's a' and stays")
def test_name_norm_dotted_suffix_removed():
    assert v._name_norm("Société Générale S.A.") == " societe generale "


# --- _clean_word -----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("w, expected", [
    ("Marie’s", "Marie"),
    ("Marie's", "Marie"),
    ("J’aime", "aime"),
    ("L'Été", "Été"),
    ("word.,", "word"),
    ("R&", "R"),
    ("x", "x"),
    ("", ""),
])
def test_clean_word(w, expected):
    assert v._clean_word(w) == expected


# --- _num_values -----------------------------------------------------------------------------------------------

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
def test_num_values(text, expected):
    assert v._num_values(text) == expected


# --- _norm_heading ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("s, expected", [
    ("Work Experience!", "work experience"),
    ("  A  B ", "a b"),
    ("A/B", "a b"),
    ("", ""),
    ("!!!", ""),
])
def test_norm_heading(s, expected):
    assert v._norm_heading(s) == expected


def test_norm_heading_drops_accents_on_latin_letters():
    # "Expérience" and "EXPÉRIENCE" meet on "experience"; both sides of a real comparison go through it.
    assert v._norm_heading("EXPÉRIENCE") == "experience"
    assert v._norm_heading("Expérience") == v._norm_heading("EXPERIENCE")


# --- _padded_words ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("s, expected", [
    ("Jean-Pierre Côté", " jean pierre cote "),
    ("a_b c", " a_b c "),
    ("", "  "),
    ("  ", "  "),
])
def test_padded_words(s, expected):
    assert v._padded_words(s) == expected


# --- _spacing_arg ----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("args, found, groups", [
    ("spacing: 0.5em", True, ("0.5", "em")),
    ("leading: 1em, spacing: 2pt", True, ("2", "pt")),
    ("spacing:\n 3em", True, ("3", "em")),
    ("spacing: auto", True, None),          # found but non-numeric
    ("box(spacing: 1pt)", False, None),     # nested call's own argument
    ("leading: 1em", False, None),
    ("", False, None),
])
def test_spacing_arg(args, found, groups):
    ok, m = verify_typst._spacing_arg(args)
    assert ok is found
    assert (m.groups() if m else None) == groups


# --- _doc_body_size --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("#set text(size: 10pt)\n#set par(leading: 0.5em)\nBody", 10.0),
    ("#set text(size: 9.5pt)\n#set text(size: 12pt)\nx", 12.0),     # the last one wins
    ("Just body", None),
    ("", None),
])
def test_doc_body_size(text, expected):
    assert v._doc_body_size(text) == expected


# --- _guess_lang -----------------------------------------------------------------------------------------------

EN = "the cat and the dog are in the house with the bird on the mat by the tree"
FR = "le chat et le chien sont dans la maison avec un oiseau sur le tapis par les arbres"


@pytest.mark.parametrize("text, expected", [
    (EN, "en"),
    (FR, "fr"),
    ("hello", None),                        # too short
    ("the cat and the dog", None),          # 4 stopwords < 8: still too short to call
    ("the cat and the dog are in the house with the bird on the mat le", "en"),   # 2x rule: en 12 vs fr 1
    ("", None),
    ("the le and et of de to a b c d e f", None),   # mixed: neither side has 2x the other
])
def test_guess_lang(text, expected):
    assert v._guess_lang(text) == expected
