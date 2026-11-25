"""vitae.verify.review_record: delivery needs a fresh, well-formed step-7 record (`review.md`) beside the CV.

The record check is pure file parsing, tested directly; the verdict wiring is tested through `cv._check_cv` with the
mechanical gates stubbed out (what they decide is covered elsewhere), so a lorem CV can reach the record step."""
import os
import re
import sys

import pytest
from vitae.core.level import Level
from vitae.verify import cv
from vitae.verify.review_record import check_review_record

GOOD = """runtime: sub-agents
cv: cv.typ
personas: recruiter, hiring manager, ATS, nurse-recruiter segment
layout: subagent haiku
## Findings
- recruiter: the summary buries the title → applied
- ATS: keyword Kubernetes only in skills → rejected: the facts show no cluster work
"""


def _cv(tmp_path):
    typ = tmp_path / "cv.typ"
    typ.write_text("#set page(width: 400pt, height: 300pt, margin: 20pt)\n#set text(size: 11pt)\n"
                   "#set par(leading: 0.65em, spacing: 0.65em)\n#lorem(130)\n", encoding="utf-8")
    os.utime(typ, (1_000, 1_000))
    return typ


def _record(tmp_path, text=GOOD, mtime=2_000):
    rec = tmp_path / "review.md"
    rec.write_text(text, encoding="utf-8")
    os.utime(rec, (mtime, mtime))
    return rec


def _check(tmp_path, text=GOOD, **kw):
    _record(tmp_path, text, **kw)
    return check_review_record(str(_cv(tmp_path)))


def _fails(out):
    return [m for lvl, m in out if lvl == Level.FAIL]


def test_valid_record_passes_with_one_info_summary(tmp_path):
    out = _check(tmp_path)
    assert [lvl for lvl, _ in out] == [Level.INFO]
    assert "runtime sub-agents, 4 personas, 1 finding(s) applied, 1 rejected" in out[0][1]


def test_missing_record_names_step_7_and_the_path_to_write(tmp_path):
    (msg,) = _fails(check_review_record(str(_cv(tmp_path))))
    assert "review record missing" in msg and "7-review.md" in msg and str(tmp_path / "review.md") in msg


def test_record_older_than_the_cv_is_stale_and_equal_age_is_fresh(tmp_path):
    (msg,) = _fails(_check(tmp_path, mtime=999))
    assert "older than cv.typ" in msg
    assert not _fails(_check(tmp_path, mtime=1_000))          # boundary: same mtime is not older


@pytest.mark.parametrize("line", ["", "runtime: maybe\n", "runtime:\n"])
def test_runtime_must_be_declared_as_sub_agents_or_none(tmp_path, line):
    text = GOOD.replace("runtime: sub-agents\n", line)
    assert any("`runtime:`" in m for m in _fails(_check(tmp_path, text)))


@pytest.mark.parametrize("persona", ["recruiter", "hiring manager", "ATS"])
def test_sub_agents_runtime_needs_each_core_persona(tmp_path, persona):
    text = GOOD.replace("personas: recruiter, hiring manager, ATS,", "personas:").replace(
        "nurse-recruiter segment", ", ".join(p for p in ("recruiter", "hiring manager", "ATS") if p != persona))
    (msg,) = _fails(_check(tmp_path, text))
    assert persona in msg and "`personas:` lacks" in msg


@pytest.mark.parametrize("personas", [
    "Recruiter (30-second scan), Hiring manager of the field, ATS / parsing expert",
    "recruiter, hiring manager (fact diff), ATS check",
    "recruiter, hiring manager, ATS (parsing expert)",
])
def test_documented_persona_spellings_with_qualifiers_pass(tmp_path, personas):
    """Mutation: whole-name matching (no startswith) fails this test."""
    text = GOOD.replace("personas: recruiter, hiring manager, ATS, nurse-recruiter segment", f"personas: {personas}")
    assert not _fails(_check(tmp_path, text))


def test_persona_spellings_are_tolerated(tmp_path):
    text = GOOD.replace("recruiter, hiring manager, ATS,", "Recruiter, Hiring-Manager, ATS expert,")
    assert not _fails(_check(tmp_path, text))
    text = GOOD.replace("recruiter, hiring manager, ATS,", "Recruiter 30-second scan, hiring_manager,  ATS / parsing expert ,")
    assert not _fails(_check(tmp_path, text))


@pytest.mark.parametrize("personas,lacks", [
    ("nurse-recruiter segment, hiring manager, ATS", "recruiter"),
    ("recruiter, fintech hiring manager segment, ATS", "hiring manager"),
    ("recruiter, hiring manager, ATS-savvy startup", "ATS"),
    ("recruiter segment, hiring manager, ATS", "recruiter"),
    ("recruitment agency, hiring manager, ATS", "recruiter"),
])
def test_a_segment_persona_is_not_a_core_persona(tmp_path, personas, lacks):
    """Mutation: matching by substring (`recruiter in name`) accepts these and fails this test."""
    text = GOOD.replace("personas: recruiter, hiring manager, ATS, nurse-recruiter segment", f"personas: {personas}")
    (msg,) = _fails(_check(tmp_path, text))
    assert "`personas:` lacks" in msg and lacks in msg


def test_ats_must_be_a_word_not_a_substring(tmp_path):
    text = GOOD.replace("ATS,", "stats reviewer,")
    assert any("ATS" in m for m in _fails(_check(tmp_path, text)))


COMPACT = "runtime: none\ncv: cv.typ\npersonas: ATS, hiring manager\nlayout: not run (no redesign)\n## Findings\n"


def test_compact_runtime_needs_only_ats_and_hiring_manager(tmp_path):
    assert not _fails(_check(tmp_path, COMPACT))
    assert not _fails(_check(tmp_path, COMPACT.replace("ATS,", "fact-diff,")))


@pytest.mark.parametrize("drop,name", [("ATS, ", "ATS"), (", hiring manager", "hiring manager")])
def test_compact_runtime_lacking_a_core_persona_fails(tmp_path, drop, name):
    (msg,) = _fails(_check(tmp_path, COMPACT.replace(drop, "")))
    assert name in msg


def test_compact_runtime_does_not_excuse_a_missing_recruiter_only_on_sub_agents(tmp_path):
    text = COMPACT.replace("none", "sub-agents")
    assert any("recruiter" in m for m in _fails(_check(tmp_path, text)))


@pytest.mark.parametrize("line", ["", "layout:\n", "layout: later\n"])
def test_layout_line_is_required(tmp_path, line):
    text = GOOD.replace("layout: subagent haiku\n", line)
    assert any("`layout:`" in m for m in _fails(_check(tmp_path, text)))


@pytest.mark.parametrize("layout", ["subagent", "other-model", "subagent  ", "selfish", "user please", "not run", "later",
                                    "not run (no redesign) maybe"])
def test_layout_must_be_a_whole_documented_form(tmp_path, layout):
    """Mutation: a prefix match (`startswith`) accepts all of these and fails this test."""
    assert any("`layout:`" in m for m in _fails(_check(tmp_path, COMPACT.replace("not run (no redesign)", layout))))


@pytest.mark.parametrize("layout", ["SELF", "Subagent Opus  ", "Other-Model gemini 2", "USER", "Not Run (No Redesign)"])
def test_layout_forms_are_case_insensitive(tmp_path, layout):
    assert not _fails(_check(tmp_path, COMPACT.replace("not run (no redesign)", layout)))


@pytest.mark.parametrize("layout", ["self", "subagent opus", "other-model gemini", "user", "not run (no redesign)"])
def test_every_documented_layout_form_is_accepted_without_sub_agents(tmp_path, layout):
    assert not _fails(_check(tmp_path, COMPACT.replace("not run (no redesign)", layout)))


@pytest.mark.parametrize("layout", ["subagent opus", "other-model gemini", "user"])
def test_sub_agents_accept_a_real_layout_review(tmp_path, layout):
    assert not _fails(_check(tmp_path, GOOD.replace("subagent haiku", layout)))


@pytest.mark.parametrize("layout", ["self", "not run (no redesign)", "Self"])
def test_sub_agents_reject_a_layout_that_was_not_reviewed_by_another_reader(tmp_path, layout):
    """Mutation: dropping the sub-agents branch accepts `self` and fails this test."""
    (msg,) = _fails(_check(tmp_path, GOOD.replace("subagent haiku", layout)))
    assert "`layout:`" in msg and "always runs on the full path" in msg


def test_none_runtime_may_still_use_self_layout(tmp_path):
    assert not _fails(_check(tmp_path, COMPACT.replace("not run (no redesign)", "self")))


# ------------------------------------------------------------------ one record per CV set (`cv:`)

COMPACT_ACADEMIC = "runtime: none\ncv: cv.typ\npersonas: extraction auditor, department head\nlayout: not run (no redesign)\n## Findings\n"
ACADEMIC = GOOD.replace("recruiter, hiring manager, ATS, nurse-recruiter segment",
                        "Committee member, Extraction-and-counts auditor, Department head, research-university segment")


def _check_ac(tmp_path, text, **kw):
    _record(tmp_path, text, **kw)
    return check_review_record(str(_cv(tmp_path)), panel="academic")


def test_academic_panel_accepts_its_own_personas(tmp_path):
    assert not _fails(_check_ac(tmp_path, ACADEMIC))


def test_academic_panel_rejects_the_industry_personas(tmp_path):
    """Mutation: ignoring `panel` accepts the industry set and fails this test."""
    (msg,) = _fails(_check_ac(tmp_path, GOOD))
    assert "committee member" in msg and "department head" in msg and "extraction" in msg


def test_industry_panel_rejects_the_academic_personas(tmp_path):
    assert any("`personas:` lacks" in m for m in _fails(_check(tmp_path, ACADEMIC)))


@pytest.mark.parametrize("drop,name", [("Committee member, ", "committee member"), ("Department head, ", "department head"),
                                       ("Extraction-and-counts auditor, ", "extraction")])
def test_academic_sub_agents_need_each_core_persona(tmp_path, drop, name):
    (msg,) = _fails(_check_ac(tmp_path, ACADEMIC.replace(drop, "")))
    assert name in msg


def test_academic_compact_path_needs_extraction_auditor_and_department_head(tmp_path):
    assert not _fails(_check_ac(tmp_path, COMPACT_ACADEMIC))
    (msg,) = _fails(_check_ac(tmp_path, COMPACT_ACADEMIC.replace("department head", "committee member")))
    assert "department head" in msg
    (msg,) = _fails(_check_ac(tmp_path, COMPACT_ACADEMIC.replace("extraction auditor", "committee member")))
    assert "extraction" in msg


def test_academic_segment_persona_is_not_core(tmp_path):
    (msg,) = _fails(_check_ac(tmp_path, ACADEMIC.replace("Department head", "department head segment")))
    assert "department head" in msg


def test_record_older_than_a_data_file_is_stale_and_names_it(tmp_path):
    _record(tmp_path, mtime=2_000)
    toml = tmp_path / "data.toml"
    toml.write_text("x = 1\n", encoding="utf-8")
    os.utime(toml, (3_000, 3_000))
    (msg,) = _fails(check_review_record(str(_cv(tmp_path)), [str(toml)]))
    assert "older than data.toml" in msg
    os.utime(toml, (2_000, 2_000))                    # boundary: equal is fresh
    assert not _fails(check_review_record(str(_cv(tmp_path)), [str(toml)]))
    os.utime(toml, (3_000, 3_000))
    assert not _fails(check_review_record(str(_cv(tmp_path))))   # no sources given: not checked


def test_academic_cli_passes_the_data_file_as_a_source(monkeypatch, tmp_path, capsys):
    """Mutation: dropping the sources argument from the academic cli fails this test."""
    from vitae.verify.academic import cli as acli
    monkeypatch.setattr(acli, "run_gate", lambda typ, toml: (True, [], []))
    _cv(tmp_path)
    _record(tmp_path, ACADEMIC, mtime=2_000)
    toml = tmp_path / "data.toml"
    toml.write_text("x = 1\n", encoding="utf-8")
    os.utime(toml, (3_000, 3_000))
    monkeypatch.setattr(sys, "argv", ["verify_academic.py", str(tmp_path / "cv.typ"), str(toml)])
    with pytest.raises(SystemExit) as e:
        acli.main()
    assert e.value.code == 1 and "review record older than data.toml" in capsys.readouterr().out


@pytest.mark.parametrize("body,n", [
    ("1. ATS: numbered → applied\n2) ATS: paren → rejected: no\n", 2),
    ("  - ATS: indented orphan → applied\n  - ATS: sibling → applied\n", 2),
    ("prose line\n  - ATS: orphan after prose → applied\n", 1),
    ("- ATS: parent → applied\n  1. numbered sub detail\n", 1),
])
def test_numbered_and_orphan_indented_findings_are_counted(tmp_path, body, n):
    out = _check(tmp_path, GOOD.split("## Findings")[0] + "## Findings\n" + body)
    assert not _fails(out)
    got = sum(int(x) for x in re.findall(r"(\d+) finding\(s\) applied, (\d+) rejected", out[-1][1])[0])
    assert got == n
    assert out[-1][0] == Level.INFO and Level.WARN not in [lvl for lvl, _ in out]


def test_unresolved_numbered_or_orphan_findings_fail(tmp_path):
    head = GOOD.split("## Findings")[0] + "## Findings\n"
    assert any("numbered" in m for m in _fails(_check(tmp_path, head + "1. ATS: numbered\n")))
    assert any("orphan" in m for m in _fails(_check(tmp_path, head + "  - ATS: orphan\n")))


@pytest.mark.parametrize("body", ["Everything was fine, nothing to report.\n", "No findings.\n\nSee below.\n"])
def test_findings_text_with_no_parseable_finding_is_a_fail_not_a_warn(tmp_path, body):
    """Mutation: dropping the non-empty-block check turns this into WARN + PASS and fails this test."""
    out = _check(tmp_path, GOOD.split("## Findings")[0] + "## Findings\n" + body)
    (msg,) = _fails(out)
    assert "no parseable finding" in msg


def test_blank_findings_section_stays_a_warn(tmp_path):
    out = _check(tmp_path, GOOD.split("## Findings")[0] + "## Findings\n\n")
    assert not _fails(out) and out[0][0] == Level.WARN


@pytest.mark.parametrize("ending", ["→ applied.", "→ applied (bullet 3)", "-> applied, see line 4", "→ applied"])
def test_applied_may_carry_a_trailing_note(tmp_path, ending):
    out = _check(tmp_path, GOOD + f"- ATS: dates {ending}\n")
    assert not _fails(out) and "2 finding(s) applied" in out[-1][1]


def test_rejected_still_needs_a_reason_after_a_note_rule(tmp_path):
    assert _fails(_check(tmp_path, GOOD + "- ATS: dates → rejected: \n"))
    assert _fails(_check(tmp_path, GOOD + "- ATS: dates → rejected.\n"))


def test_cv_line_is_required_and_names_the_file(tmp_path):
    (msg,) = _fails(_check(tmp_path, GOOD.replace("cv: cv.typ\n", "")))
    assert "`cv:`" in msg and "cv.typ" in msg


@pytest.mark.parametrize("line", ["cv: other.typ", "cv: cv.typ.bak", "cv:", "cv: CV.typ"])
def test_cv_line_must_list_the_verified_cv(tmp_path, line):
    (msg,) = _fails(_check(tmp_path, GOOD.replace("cv: cv.typ", line)))
    assert "must list cv.typ" in msg


def test_cv_line_lists_several_cvs(tmp_path):
    assert not _fails(_check(tmp_path, GOOD.replace("cv: cv.typ", "cv: cv_2p.typ,  cv.typ , other.typ")))


# ------------------------------------------------------------------ markdown tolerance

def test_findings_heading_may_carry_text(tmp_path):
    out = _check(tmp_path, GOOD.replace("## Findings", "## Findings (2)"))
    assert not _fails(out) and "1 finding(s) applied, 1 rejected" in out[0][1]


def test_continuation_lines_join_the_bullet_before_the_ending_is_tested(tmp_path):
    text = GOOD + "- ATS: a long finding that wraps\n  onto a second line → applied\n"
    out = _check(tmp_path, text)
    assert not _fails(out) and "2 finding(s) applied" in out[0][1]


def test_wrapped_finding_without_an_ending_still_fails(tmp_path):
    (msg,) = _fails(_check(tmp_path, GOOD + "- ATS: wraps\n  onto a second line\n"))
    assert "wraps onto a second line" in msg


def test_nested_sub_bullets_are_not_findings_and_belong_to_the_parent(tmp_path):
    text = GOOD + "- ATS: parent → applied\n  - sub detail without a verdict\n    continuation of the sub-bullet\n* star bullet → rejected: no\n"
    out = _check(tmp_path, text)
    assert not _fails(out) and "2 finding(s) applied, 2 rejected" in out[0][1]


def test_a_sub_bullet_does_not_resolve_its_parent(tmp_path):
    (msg,) = _fails(_check(tmp_path, GOOD + "- ATS: parent\n  - child → applied\n"))
    assert "parent" in msg


@pytest.mark.parametrize("bullet", [
    "- ATS: keyword missing",
    "- ATS: keyword missing → pending",
    "- ATS: keyword missing → rejected:",
    "- ATS: keyword missing → rejected:   ",
])
def test_unresolved_finding_fails_and_is_named(tmp_path, bullet):
    (msg,) = _fails(_check(tmp_path, GOOD + bullet + "\n"))
    assert "keyword missing" in msg


def test_ascii_arrow_is_accepted(tmp_path):
    out = _check(tmp_path, GOOD + "- ATS: dates -> applied\n- ATS: other -> rejected: not in facts\n")
    assert not _fails(out) and "2 finding(s) applied, 2 rejected" in out[-1][1]


def test_bullets_outside_the_findings_section_are_not_findings(tmp_path):
    assert not _fails(_check(tmp_path, GOOD + "## Notes\n- free text without a verdict\n"))


def test_zero_findings_is_a_warn_not_a_fail(tmp_path):
    out = _check(tmp_path, COMPACT)
    assert (Level.WARN, "review record lists no findings") in out and not _fails(out)


def test_missing_findings_section_fails(tmp_path):
    assert any("## Findings" in m for m in _fails(_check(tmp_path, GOOD.split("## Findings")[0])))


# ------------------------------------------------------------------ wiring in the one-file gate

@pytest.fixture
def gate(monkeypatch):
    """_check_cv with the mechanical gates stubbed out: only the record decides the verdict."""
    monkeypatch.setattr(cv, "run_gates", lambda gates, ctx: 0)
    monkeypatch.setattr(cv, "check_whitespace", lambda *a, **k: [])
    return lambda typ, *args, **kw: cv._check_cv(str(typ), "1", *args, **kw)


def test_failing_record_ends_on_a_fail_line_with_exit_1_and_no_pass(gate, tmp_path, capsys):
    typ = _cv(tmp_path)
    rc, footer = gate(typ, "60", "100")
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    assert rc == 1 and footer is None
    assert lines[-1].startswith("FAIL") and not any(ln.startswith("PASS") for ln in lines)
    mech = next(i for i, ln in enumerate(lines) if ln.startswith("mechanical gates: PASS (fill "))
    assert any(ln.startswith("FAIL  review record missing") for ln in lines[mech:])
    assert "now LOOK at the PNGs (Visual pass:), then step 7" in lines[mech]   # Mutation: dropping the cue fails here


def test_valid_record_passes_and_prints_the_info(gate, tmp_path, capsys):
    typ = _cv(tmp_path)
    _record(tmp_path)
    os.utime(typ, (1_000, 1_000))
    rc, _ = gate(typ, "60", "100")
    out = capsys.readouterr().out
    assert rc == 0 and "PASS  all mechanical checks" in out and "INFO  review record: runtime sub-agents" in out


def test_mechanical_fail_keeps_its_behaviour_and_skips_the_record(gate, tmp_path, capsys):
    typ = _cv(tmp_path)
    rc, footer = gate(typ, "99", "100")          # the lorem page is far under 99% fill
    out = capsys.readouterr().out
    assert rc == 1 and footer and "review record" not in out and "mechanical gates: PASS" not in out


def test_allow_placeholders_run_does_not_check_the_record(gate, tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(cv, "placeholders_allowed", lambda typ: True)
    rc, _ = gate(_cv(tmp_path), "60", "100", allow_placeholders=True)
    out = capsys.readouterr().out
    assert rc == 0 and "review record" not in out and "PASS (placeholder gate skipped)" in out


def test_no_record_check_in_gates_mode():
    import inspect

    from vitae.verify import cli
    src = inspect.getsource(cli)
    assert "check_review_record" not in src and "LAYOUT_GATES" in src     # --gates runs the layout gates only


def test_lowered_fill_warn_sits_right_under_the_mechanical_verdict_when_the_record_fails(gate, tmp_path, capsys):
    typ = _cv(tmp_path)
    typ.write_text("// vitae: pages=1 fill=70-80\n" + typ.read_text(encoding="utf-8"), encoding="utf-8")
    gate(typ, "60", "100")
    lines = capsys.readouterr().out.splitlines()
    mech = next(i for i, ln in enumerate(lines) if ln.startswith("mechanical gates: PASS"))
    assert "fill target lowered: 70-80 → 60-100" in lines[mech]
    assert lines[mech + 1].startswith("WARN  fill target lowered below drawn target")


def test_failing_record_without_fill_args_keeps_the_except_fill_wording(gate, tmp_path, capsys):
    """Mutation: printing `PASS (fill N%)` regardless of the args fails the first assert."""
    gate(_cv(tmp_path), None, None)
    out = capsys.readouterr().out
    assert "mechanical gates: PASS except fill (no FILL_MIN FILL_MAX given)" in out
    assert "mechanical gates: PASS (fill" not in out


def test_rebuild_skips_only_the_record_and_says_so_on_the_verdict_line(gate, tmp_path, capsys):
    """Mutation: ignoring `rebuild` leaves the missing record a FAIL and fails the first assert."""
    typ = _cv(tmp_path)                           # no review.md at all
    rc, _ = gate(typ, "60", "100", rebuild=True)
    out = capsys.readouterr().out
    assert rc == 0 and "PASS (review record skipped: --rebuild, candidate rebuild) all mechanical checks" in out
    assert "review record" not in out.replace("review record skipped", "")


def test_rebuild_does_not_excuse_a_mechanical_fail(gate, tmp_path, capsys):
    rc, footer = gate(_cv(tmp_path), "99", "100", rebuild=True)       # far under 99% fill
    assert rc == 1 and footer and "PASS (review record skipped" not in capsys.readouterr().out


def test_rebuild_flag_reaches_the_gate_from_the_command_line(tmp_path, monkeypatch):
    from vitae.verify import cli
    seen = {}
    monkeypatch.setattr(cli, "_check_cv", lambda *a, **k: seen.update(args=a) or (0, None))
    monkeypatch.setattr(sys, "argv", ["verify.py", "cv.typ", "1", "60", "100", "--rebuild"])
    cli.main()
    assert seen["args"][-1] is True and seen["args"][:4] == ("cv.typ", "1", "60", "100")
    monkeypatch.setattr(sys, "argv", ["verify.py", "cv.typ", "1"])
    cli.main()
    assert seen["args"][-1] is False


# ------------------------------------------------------------------ academic path

@pytest.fixture
def academic(monkeypatch, tmp_path):
    from vitae.verify.academic import cli as acli
    monkeypatch.setattr(acli, "run_gate", lambda typ, toml: (True, [], []))

    def run(*extra):
        monkeypatch.setattr(sys, "argv", ["verify_academic.py", str(tmp_path / "cv.typ"), "data.toml", *extra])
        with pytest.raises(SystemExit) as e:
            acli.main()
        return e.value.code
    return run


def test_academic_without_a_record_ends_on_fail_and_never_prints_pass(academic, tmp_path, capsys):
    """Mutation: removing the record check from the academic cli makes it exit 0 and fails this test."""
    _cv(tmp_path)
    assert academic() == 1
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    assert lines[0].startswith("mechanical gates: PASS") and "FAIL  review record missing" in lines[1]
    assert lines[-1].startswith("FAIL") and not any(ln.startswith("PASS") for ln in lines)


def test_academic_with_a_valid_record_passes(academic, tmp_path, capsys):
    _cv(tmp_path)
    _record(tmp_path, ACADEMIC)
    assert academic() == 0
    out = capsys.readouterr().out
    assert "INFO  review record: runtime sub-agents" in out and out.splitlines()[-1] == "PASS  all five checks hold"


def test_academic_rebuild_skips_only_the_record(academic, tmp_path, capsys):
    _cv(tmp_path)
    assert academic("--rebuild") == 0
    assert "PASS  all five checks hold (review record skipped: --rebuild, candidate rebuild)" in capsys.readouterr().out


def test_academic_mechanical_fail_skips_the_record(monkeypatch, tmp_path, capsys):
    from vitae.verify.academic import cli as acli
    monkeypatch.setattr(acli, "run_gate", lambda typ, toml: (False, [(True, "x")], []))
    monkeypatch.setattr(sys, "argv", ["verify_academic.py", str(_cv(tmp_path)), "data.toml"])
    with pytest.raises(SystemExit) as e:
        acli.main()
    assert e.value.code == 1 and "review record" not in capsys.readouterr().out


@pytest.mark.parametrize("layout", ["subagent skipped", "other-model none", "subagent n/a", "subagent not run", "subagent -", "subagent No"])
def test_layout_rejects_non_model_words(tmp_path, layout):
    """Mutation: dropping the negative lookahead on `_LAYOUT` accepts `subagent skipped`."""
    assert any("`layout:`" in m for m in _fails(_check(tmp_path, GOOD.replace("subagent haiku", layout))))


@pytest.mark.parametrize("finding", ["- ATS: rename 'Docker -> applied containers' to the posting's term",
                                     "- ATS: x -> applied -> maybe", "- ATS: x → rejected: because -> later"])
def test_resolution_must_be_the_last_arrow(tmp_path, finding):
    """Mutation: an unanchored resolution regex reads a mid-sentence `-> applied …` as resolved."""
    assert any("not resolved" in m for m in _fails(_check(tmp_path, GOOD + finding + "\n")))


def test_resolution_with_note_and_dash_in_reason_is_fine(tmp_path):
    assert not _fails(_check(tmp_path, GOOD + "- ATS: x -> applied (bullet 3)\n- ATS: y → rejected: not in facts - skip\n"))


@pytest.mark.parametrize("name", ["fact-diff reviewer", "fact-diff check", "fact diff"])
def test_compact_fact_diff_is_a_stem(tmp_path, name):
    assert not _fails(_check(tmp_path, COMPACT.replace("ATS,", name + ",")))


def test_compact_fact_diff_segment_is_rejected(tmp_path):
    assert _fails(_check(tmp_path, COMPACT.replace("ATS,", "fact-diff segment,")))
