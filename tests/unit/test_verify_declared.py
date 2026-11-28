"""Checks on declared lib.typ arguments: a summary figure repeated in a bullet, an `expected` date already past."""
from datetime import date

from vitae.core.base import BulletLayout, BulletLine, Extent, Mark, Pos
from vitae.core.context import VerifyContext
from vitae.core.level import Level
from vitae.verify.declared import bullets_outside, check_expected_past, check_summary_figures, section_text
from vitae.verify.gates import _expected_past, _has_expected, _has_summary, _summary_figures

TODAY = date(2026, 11, 28)


# ---- summary figures repeated in bullets
def test_figure_in_summary_and_in_a_bullet_is_flagged_once_and_named() -> None:
    w = check_summary_figures("Cut costs by 40% across 12 teams", ["Reduced spend 40% in Q3", "Also 40% again"])
    assert len(w) == 1 and '"40%"' in w[0]


def test_figure_only_in_the_summary_is_silent() -> None:
    assert check_summary_figures("Cut costs by 40%", ["Shipped the billing rewrite"]) == []


def test_years_are_not_figures() -> None:
    assert check_summary_figures("Since 2015, 10 years of work", ["Joined in 2015", "Led 2015-03 migration"]) == []


def test_unit_and_separator_variants_read_alike() -> None:
    assert len(check_summary_figures("Managed $1,500 weekly", ["Budget of $1500 per week"])) == 1
    assert len(check_summary_figures("Saved 50k", ["Saved 50,000 yearly"])) == 1
    assert len(check_summary_figures("1.500 clients", ["1500 clients served"])) == 1


def test_a_unit_symbol_makes_a_different_figure() -> None:
    assert check_summary_figures("Raised 40%", ["Led 40 people"]) == []
    assert check_summary_figures("Raised $5", ["Hired 5 more"]) == []
    assert check_summary_figures("Over 40", ["Won 40+ awards"]) == []
    assert len(check_summary_figures("Raised 40%", ["Up 40% again"])) == 1
    assert len(check_summary_figures("Saved \u20ac50", ["Saved \u20ac50 yearly"])) == 1


def test_a_range_is_one_figure_not_two_endpoints() -> None:
    assert check_summary_figures("10-20 clients", ["Closed 20 deals"]) == []
    assert check_summary_figures("10\u201320 clients", ["Closed 10 deals"]) == []
    w = check_summary_figures("10\u201320 clients", ["Served 10-20 accounts"])
    assert len(w) == 1 and '"10\u201320"' in w[0]


def test_ranges_match_only_on_both_endpoints_and_not_a_single_figure() -> None:
    assert check_summary_figures("10-20 clients", ["Served 10-30 accounts"]) == []
    assert check_summary_figures("Closed 10 deals", ["Served 10-20 accounts"]) == []


def test_year_inside_a_range_is_not_a_figure() -> None:
    assert check_summary_figures("Active 2019\u20132023", ["Shipped in 2019", "Wrapped 2023"]) == []
    assert check_summary_figures("Active 2019-2023", ["Budget 2023 units"]) == []


def test_bare_single_digits_and_phones_are_no_signal() -> None:
    assert check_summary_figures("3 teams, call 514-555-1234", ["3 squads", "Hotline 514-555-1234"]) == []


def test_no_bullets_or_no_summary_figures_is_silent() -> None:
    assert check_summary_figures("Cut costs by 40%", []) == []
    assert check_summary_figures("Seasoned engineer", ["40% faster"]) == []


# ---- bounding the summary in the extraction
TXT = "Jane Roe\nPROFILE\nCut costs 40%\nover two lines\nExperience\nShipped 40%\n"


def test_section_text_runs_to_the_next_title_case_insensitively() -> None:
    assert section_text(TXT, ["Profile", "Experience"], 0) == "Cut costs 40%\nover two lines"
    assert section_text(TXT, ["Profile", "Experience"], 1) == "Shipped 40%\n"


def test_section_text_without_the_title_line_is_none() -> None:
    assert section_text(TXT, ["Summary", "Experience"], 0) is None


def test_unknown_end_of_a_non_last_section_is_silence_not_the_whole_document() -> None:
    assert section_text(TXT, ["Profile", "Nowhere"], 0) is None


def test_the_end_is_the_immediately_next_section_never_a_later_one() -> None:
    txt = "PROFILE\nCut 40%\nEXP E R I E N C E\nShipped 40%\nSkills\nSQL\n"
    assert section_text(txt, ["Profile", "Experience", "Skills"], 0) is None
    assert section_text(txt, ["Profile", "Skills"], 0) == "Cut 40%\nEXP E R I E N C E\nShipped 40%"


def test_the_last_section_runs_to_the_end_of_the_document() -> None:
    assert section_text(TXT, ["Profile", "Experience"], 1) == "Shipped 40%\n"
    assert section_text(TXT, ["Profile"], 0) == "Cut costs 40%\nover two lines\nExperience\nShipped 40%\n"


# ---- expected dates
def head(text: str, dates: str | None = None) -> Mark:
    return {"text": text} if dates is None else {"text": text, "expected": True, "dates": dates}


def test_expected_year_before_today_is_flagged_and_names_the_entry() -> None:
    w = check_expected_past([head("B.Sc. Physics", "2024 – expected 2025")], TODAY)
    assert len(w) == 1 and "B.Sc. Physics" in w[0] and "2026" in w[0]


def test_expected_year_equal_to_today_is_silent() -> None:
    assert check_expected_past([head("B.Sc.", "2022 – 2026")], TODAY) == []


def test_expected_future_year_is_silent() -> None:
    assert check_expected_past([head("B.Sc.", "2027")], TODAY) == []


def test_undeclared_head_is_never_judged() -> None:
    assert check_expected_past([head("Analyst"), {"text": "Old", "dates": "2001"}], TODAY) == []


def test_latest_year_decides() -> None:
    assert check_expected_past([head("A", "2019 – 2027")], TODAY) == []
    assert len(check_expected_past([head("A", "2027 – 2019 (2025)")], TODAY)) == 0
    assert len(check_expected_past([head("A", "2019 – 2025")], TODAY)) == 1


def test_date_text_without_a_year_is_not_judged() -> None:
    assert check_expected_past([head("A", "soon")], TODAY) == []


# ---- the gate adapter: summary bounded in the extraction, bullets read from their located lines
def _ctx(summary: bool) -> VerifyContext:
    sec: Mark = {"text": "Profile", "page": 1, "y": 1.0, "summary": True} if summary else {"text": "Profile", "page": 1, "y": 1.0}
    line = BulletLine(1, Extent(0.0, 1.0), 9.0, "Cut spend 40% in Q3")
    layout = BulletLayout([], [], [(Pos(1, 0.0, 0.0), [line])])
    return VerifyContext(typ="", pdf="", txt=TXT, src="", backend=None, secs=[sec, {"text": "Experience"}], bullets=layout)


def test_gate_warns_on_a_declared_summary_figure_found_in_a_bullet() -> None:
    ctx = _ctx(True)
    assert _has_summary(ctx)
    got = _summary_figures(ctx)
    assert len(got) == 1 and got[0][0] is Level.WARN and '"40%"' in got[0][1]


def test_gate_does_not_apply_without_a_declaration() -> None:
    assert not _has_summary(_ctx(False))


def test_bullets_inside_the_summary_do_not_count_as_another_place() -> None:
    ctx = _ctx(True)
    assert bullets_outside("Cut spend 40% in Q3\nmore", [["Cut spend 40% in Q3"], ["Other"]]) == ["Other"]
    inner = VerifyContext(typ="", pdf="", txt="PROFILE\nCut spend 40% in Q3\nExperience\nShipped\n", src="", backend=None,
                          secs=ctx.secs, bullets=ctx.bullets)
    assert _summary_figures(inner) == []          # the only bullet sits inside the summary itself


def test_unbounded_summary_gives_no_flood() -> None:
    ctx = _ctx(True)
    lost = VerifyContext(typ="", pdf="", txt="PROFILE\nCut 40%\nEXP E R I E N C E\nCut spend 40% in Q3\n", src="", backend=None,
                         secs=ctx.secs, bullets=ctx.bullets)
    assert _summary_figures(lost) == []


# ---- the expected-date gate adapter
def _heads_ctx(declared: bool) -> VerifyContext:
    h: Mark = {"text": "B.Sc.", "kind": "entry", "expected": True, "dates": "2024"} if declared else {"text": "B.Sc.", "kind": "entry"}
    return VerifyContext(typ="", pdf="", txt="", src="", backend=None, heads=[h])


def test_expected_gate_warns_through_the_context_with_the_injected_date() -> None:
    ctx = _heads_ctx(True)
    assert _has_expected(ctx)
    got = _expected_past(ctx, TODAY)
    assert len(got) == 1 and got[0][0] is Level.WARN and "B.Sc." in got[0][1]
    assert _expected_past(ctx, date(2024, 6, 1)) == []


def test_expected_gate_does_not_apply_without_a_declaration() -> None:
    assert not _has_expected(_heads_ctx(False))
    assert not _has_expected(VerifyContext(typ="", pdf="", txt="", src="", backend=None))
