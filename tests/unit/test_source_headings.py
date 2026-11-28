"""verify.source: _norm_heading (heading normalisation) and check_no_split work on headings in any script."""
import pytest
from vitae.core.base import Mark
from vitae.verify.source import _norm_heading, boundary_headings, check_native_headings, check_no_split

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


def test_no_split_fails_when_there_is_no_boundary_to_measure():
    """No mark, no native heading, no #section call: unmeasurable, so FAIL (never "not checked" and OK)."""
    (fail, msg), = check_no_split("#let x = 1", ["a", "b"])
    assert fail and "no <vitae-sec> mark" in msg and "section()" in msg


def test_no_split_fails_without_boundary_even_on_one_page():
    assert check_no_split("#let x = 1", ["a"])[0][0] is True


def _h(text: str, level: int = 1, page: int = 1) -> Mark:
    return {"text": text, "kind": "heading", "level": level, "page": page}


def test_native_heading_opening_the_next_page_is_a_boundary():
    assert check_no_split("", ["a", "Experience\nx"], native=[_h("Profile"), _h("Experience", page=2)]) == [
        (False, 'no-split: page 2 opens on "Experience"')]


def test_native_heading_section_split_across_pages_fails():
    (fail, msg), = check_no_split("", ["a", "tail of a job\nx"], native=[_h("Profile"), _h("Experience")])
    assert fail and "SPLIT" in msg


def test_marks_and_native_headings_are_both_boundaries_without_double_count():
    secs: list[Mark] = [{"text": "Work", "page": 1, "y": 1.0}]
    native = [_h("Projects", page=2)]
    assert check_no_split("", ["a", "Projects\nx", "Work\ny"], secs=secs, native=native) == [
        (False, 'no-split: page 2 opens on "Projects"'), (False, 'no-split: page 3 opens on "Work"')]
    # the same title as mark and heading is one boundary, not a double
    assert not check_no_split("", ["a", "Work\nx"], secs=secs, native=[_h("Work", page=2)])[0][0]


def test_marks_win_over_the_source_calls():
    """Query available: the #section calls of the source are not consulted."""
    assert check_no_split('#section("Old")[x]', ["a", "Old\nx"], secs=[{"text": "New"}])[0][0] is True


def test_boundary_headings_use_the_shallowest_level():
    assert boundary_headings([_h("A", 1), _h("a1", 2), _h("B", 1)]) == ["A", "B"]


def test_a_lone_top_heading_is_the_document_title():
    assert boundary_headings([_h("Name", 1), _h("Experience", 2), _h("Education", 2), _h("detail", 3)]) == ["Experience", "Education"]


def test_a_lone_heading_with_no_deeper_one_is_a_section():
    assert boundary_headings([_h("Only", 1)]) == ["Only"]
    assert boundary_headings([]) == []


def test_a_page_opening_on_a_sub_heading_is_a_split():
    native = [_h("Experience", 1), _h("Job", 2, page=2), _h("Education", 1)]
    assert check_no_split("", ["a", "Job\nx"], native=native)[0][0] is True


def test_native_headings_next_to_marks_warn_by_position():
    got = check_native_headings([{"text": "A"}, {"text": "B"}], [_h("Projects", page=2)])
    assert len(got) == 1 and "heading #1 (page 2)" in got[0] and "1 native heading(s) of 3" in got[0]
    assert "Projects" not in got[0]


@pytest.mark.parametrize("secs, native", [([], [_h("A")]), ([{"text": "A"}], []), ([], [])],
                         ids=["no-marks", "no-native", "neither"])
def test_no_native_warning_when_nothing_is_mixed(secs: list[Mark], native: list[Mark]) -> None:
    assert check_native_headings(secs, native) == []


def test_a_lone_top_heading_over_a_single_deeper_level_is_the_title():
    assert boundary_headings([_h("Name", 1), _h("A", 2), _h("B", 2)]) == ["A", "B"]


def test_a_heading_record_without_a_level_counts_as_a_top_level_one():
    bare: list[Mark] = [{"text": "A", "kind": "heading"}, {"text": "B", "kind": "heading"}, _h("c", 2)]
    assert boundary_headings(bare) == ["A", "B"]
    assert boundary_headings([{"text": "A", "kind": "heading"}, _h("B", 1)]) == ["A", "B"]


def test_native_warning_lists_every_heading_and_states_the_consequence():
    (msg,) = check_native_headings([{"text": "S"}], [_h("x", page=1), _h("y", page=2), {"text": "z", "kind": "heading"}])
    assert "heading #1 (page 1), #2 (page 2), #3 (page ?)" in msg
    assert msg.endswith("NOT measured for them; build every section with section()")


def test_a_lone_level_less_heading_over_deeper_ones_is_the_title():
    assert boundary_headings([{"text": "Name", "kind": "heading"}, _h("A", 2), _h("B", 2)]) == ["A", "B"]


def test_a_running_heading_is_no_boundary_and_a_real_split_still_fails():
    native = [_at("Running", 1, 20.0), _at("Running", 2, 20.0), _at("Running", 3, 20.5), _at("Work", 1, 90.0)]
    assert boundary_headings(native) == ["Work"]
    pages = ["Running\na", "Running\nmid-section text", "Running\nmore"]
    assert any(fail for fail, _ in check_no_split("", pages, native=native))


def test_a_heading_on_one_page_twice_is_not_running():
    assert boundary_headings([_at("A", 1, 20.0), _at("A", 1, 20.0)]) == ["A", "A"]


def test_a_repeated_section_title_at_other_heights_is_kept():
    native = [_at("Projects", 1, 90.0), _at("Projects", 3, 30.0), _at("Edu", 4, 30.0)]
    assert boundary_headings(native) == ["Projects", "Projects", "Edu"]
    assert not check_no_split("", ["a", "b", "Projects\nx", "Edu\ny"], native=native)[1][0]


def test_all_repeated_titles_at_other_heights_are_not_a_missing_boundary():
    assert boundary_headings([_at("Projects", 1, 90.0), _at("Projects", 3, 30.0)]) == ["Projects", "Projects"]


def test_running_tolerance_edge_and_missing_positions():
    assert boundary_headings([_at("R", 1, 20.0), _at("R", 2, 21.0)]) == []
    assert boundary_headings([_at("R", 1, 20.0), _at("R", 2, 21.1)]) == ["R", "R"]
    assert boundary_headings([_h("R", page=1), _h("R", page=2)]) == ["R", "R"]
    assert boundary_headings([_at("R", 1, 20.0), {"text": "R", "kind": "heading", "level": 1, "page": 2}]) == ["R", "R"]
    assert boundary_headings([_at("R", 1, 20.0), _at("R", 2, 20.0, 2), _at("x", 1, 50.0, 2)]) == ["R", "x"]


def test_running_headings_are_not_reported_as_hand_built():
    secs: list[Mark] = [{"text": "S", "page": 1, "y": 50.0}]
    assert check_native_headings(secs, [_at("Run", 1, 9.0), _at("Run", 2, 9.0)]) == []


def _at(text: str, page: int, y: float, level: int = 1) -> Mark:
    return {"text": text, "kind": "heading", "level": level, "page": page, "y": y}


def test_the_document_title_above_the_first_mark_is_not_a_hand_built_section():
    secs: list[Mark] = [{"text": "S", "page": 1, "y": 80.0}]
    assert check_native_headings(secs, [_at("Name", 1, 20.0)]) == []


def test_a_lone_heading_below_the_first_mark_is_hand_built():
    secs: list[Mark] = [{"text": "S", "page": 1, "y": 80.0}]
    assert len(check_native_headings(secs, [_at("Projects", 1, 120.0)])) == 1
    assert len(check_native_headings(secs, [_at("Projects", 2, 5.0)])) == 1


def test_a_title_followed_by_a_hand_section_counts_only_the_section():
    secs: list[Mark] = [{"text": "S", "page": 1, "y": 80.0}]
    (msg,) = check_native_headings(secs, [_at("Name", 1, 20.0), _at("Projects", 1, 120.0, 2)])
    assert "1 native heading(s) of 2" in msg and "heading #1 (page 1)" in msg


def test_a_second_top_heading_above_the_marks_is_not_a_title():
    secs: list[Mark] = [{"text": "S", "page": 1, "y": 80.0}]
    assert len(check_native_headings(secs, [_at("A", 1, 10.0), _at("B", 1, 20.0)])) == 1


def test_a_title_without_position_is_not_dropped():
    secs: list[Mark] = [{"text": "S", "page": 1, "y": 80.0}]
    assert len(check_native_headings(secs, [_h("Name")])) == 1
    assert len(check_native_headings([{"text": "S"}], [_at("Name", 1, 20.0)])) == 1


def test_no_boundary_fails_on_every_backend_with_its_own_message():
    from vitae.core.context import VerifyContext
    from vitae.core.level import Level
    from vitae.verify.gates import _no_split
    from vitae.verify.source import NO_BOUNDARY_MSG
    for backend in ("poppler", "pypdf"):
        ctx = VerifyContext(typ="x.typ", pdf="x.pdf", txt="a\fb", src="#let x = 1", backend=backend, secs=[], native=[])
        assert _no_split(ctx) == [(Level.FAIL, NO_BOUNDARY_MSG)]


def test_a_failed_heading_read_is_reported_and_not_taken_for_no_headings(monkeypatch):
    from vitae.verify import gates
    calls: list[str] = []

    def fake(typ, selector, root=None):
        calls.append(selector)
        return (None, None, None) if "heading" in selector else ([{"text": "S", "page": 1, "y": 1.0}], None, None)

    monkeypatch.setattr(gates, "typst_marks_and_contact", fake)
    monkeypatch.setattr(gates, "bbox_pages", lambda pdf: None)
    ctx = gates.make_context("x.typ", "x.pdf", "t", "", "poppler")
    assert len(calls) == 2 and "heading" not in calls[1]
    assert ctx.native is None and ctx.secs is not None
    assert len(ctx.mark_notes) == 1 and "native headings could not be read" in ctx.mark_notes[0]


def test_no_heading_note_when_the_heading_read_works(monkeypatch):
    from vitae.verify import gates
    monkeypatch.setattr(gates, "typst_marks_and_contact", lambda *a, **k: ([], None, None))
    monkeypatch.setattr(gates, "bbox_pages", lambda pdf: None)
    ctx = gates.make_context("x.typ", "x.pdf", "t", "", "poppler")
    assert ctx.mark_notes == () and ctx.native == []


def test_title_above_marks_is_dropped_whatever_its_level_or_missing_level():
    secs: list[Mark] = [{"text": "S", "page": 1, "y": 80.0}]
    assert check_native_headings(secs, [_at("Name", 1, 20.0, 2)]) == []
    assert check_native_headings(secs, [{"text": "Name", "kind": "heading", "page": 1, "y": 20.0}]) == []


def test_a_mark_without_a_position_does_not_move_the_first_mark():
    secs: list[Mark] = [{"text": "X", "page": 1}, {"text": "S", "page": 1, "y": 80.0}]
    assert check_native_headings(secs, [_at("Name", 1, 20.0)]) == []


def test_a_heading_at_the_exact_position_of_the_first_mark_is_not_above_it():
    secs: list[Mark] = [{"text": "S", "page": 1, "y": 80.0}]
    assert len(check_native_headings(secs, [_at("Name", 1, 80.0)])) == 1


def test_running_match_is_level_aware_in_both_directions_and_defaults_missing_level_to_top():
    bare: Mark = {"text": "R", "kind": "heading", "page": 2, "y": 20.0}
    assert boundary_headings([_at("R", 1, 20.0), bare]) == []              # a missing level reads as level 1
    assert boundary_headings([bare, _at("R", 1, 20.0)]) == []
    assert boundary_headings([bare, {**bare, "page": 3}]) == []
    assert check_native_headings([{"text": "S", "page": 1, "y": 99.0}], [_at("R", 1, 20.0, 2), _at("R", 2, 20.0, 1)]) != []
    assert check_native_headings([{"text": "S", "page": 1, "y": 99.0}], [_at("R", 1, 20.0, 1), _at("R", 2, 20.0, 2)]) != []
