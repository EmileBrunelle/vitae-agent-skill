"""vitae.verify.review_record: delivery needs a fresh, well-formed step-7 record (`review.md`) beside the CV.

The record check is pure file parsing, tested directly; the verdict wiring is tested through `cv._check_cv` with the
mechanical gates stubbed out (what they decide is covered elsewhere), so a lorem CV can reach the record step."""
import os
import shutil
import sys
from pathlib import Path

import pytest
from vitae.core.level import Level
from vitae.verify import cv
from vitae.verify.review_record import check_review_record, layout_report_line

LOREM_CV = ("#set document(title: \"Test CV\")\n#set page(width: 400pt, height: 300pt, margin: 20pt)\n#set text(size: 11pt)\n"
            "#set par(leading: 0.65em, spacing: 0.65em)\n#lorem(130)\n")


@pytest.fixture(scope="module")
def lorem_render(tmp_path_factory):
    """The lorem CV compiled once: its PDF and its 90 ppi PNG. Every test below writes this same source (a `// vitae:`
    header comment aside) and only the record beside it varies, so they share the render instead of compiling it again."""
    d = tmp_path_factory.mktemp("lorem")
    typ = d / "cv.typ"
    typ.write_text(LOREM_CV, encoding="utf-8")
    pdf = d / "cv.pdf"
    _err, failed = cv.compile_or_messages(str(typ), str(pdf))
    assert not failed, failed
    (png,) = cv.render_pngs(str(typ), str(d))
    return pdf, Path(png)


@pytest.fixture(autouse=True)
def shared_gate_inputs(monkeypatch, lorem_render):
    """The gate probes typst, fonts and PDF tools, then compiles and rasterizes the CV: ~0.25 s of subprocesses per run
    for what these tests do not vary. The probe is stubbed to "all present" and the compile and the raster copy the shared
    render; the gates that read the PDF (page count, word boxes, text) still run on it."""
    pdf, png = lorem_render
    monkeypatch.setattr(cv, "preflight", lambda: (True, "pdfium"))

    def compile_shared(typ, out):
        shutil.copy(pdf, out)
        return "", []

    def render_shared(typ, tmp_dir):
        return [shutil.copy(png, Path(tmp_dir) / "p1.png")]
    monkeypatch.setattr(cv, "compile_or_messages", compile_shared)
    monkeypatch.setattr(cv, "render_pngs", render_shared)


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
    typ.write_text(LOREM_CV, encoding="utf-8")
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


def _passes(out):
    """Positive control for every "accepted" test: no FAIL, and the INFO summary is the last item. Returns it."""
    assert not _fails(out)
    level, summary = out[-1]
    assert level == Level.INFO and summary.startswith("review record: runtime ")
    return summary


def _sources(tmp_path, record_mtime=2_000, **mtimes):
    """`data.toml`-style source files at the given mtimes (name=mtime, `.` written as `_`) beside a record."""
    _record(tmp_path, mtime=record_mtime)
    paths = []
    for name, mtime in mtimes.items():
        f = tmp_path / name.replace("_toml", ".toml")
        f.write_text("x = 1\n", encoding="utf-8")
        os.utime(f, (mtime, mtime))
        paths.append(str(f))
    return paths


def test_valid_record_passes_with_one_info_summary(tmp_path):
    out = _check(tmp_path)
    assert [lvl for lvl, _ in out] == [Level.INFO]
    assert "runtime sub-agents, 4 personas, 1 finding(s) applied, 1 rejected" in _passes(out)


def test_missing_record_names_step_7_and_the_path_to_write(tmp_path):
    (msg,) = _fails(check_review_record(str(_cv(tmp_path))))
    assert "review record missing" in msg and "7-review.md" in msg and str(tmp_path / "review.md") in msg


def test_record_older_than_the_cv_is_stale(tmp_path):
    (msg,) = _fails(_check(tmp_path, mtime=999))
    assert "older than cv.typ" in msg


def test_record_as_old_as_the_cv_is_fresh(tmp_path):
    _passes(_check(tmp_path, mtime=1_000))          # boundary: same mtime is not older


def test_missing_record_beside_a_bare_filename_is_written_to_the_current_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _cv(tmp_path)
    (msg,) = _fails(check_review_record("cv.typ"))
    assert "write " + os.path.join(".", "review.md") in msg


def test_record_that_is_a_directory_fails_with_its_name(tmp_path):
    (tmp_path / "review.md").mkdir()
    (msg,) = _fails(check_review_record(str(_cv(tmp_path))))
    assert "review.md" in msg and "not a regular file" in msg


def test_record_with_invalid_utf8_fails_as_unreadable(tmp_path):
    rec = tmp_path / "review.md"
    rec.write_bytes(b"runtime: sub-agents\n\xff\xfe\n")
    os.utime(rec, (2_000, 2_000))
    (msg,) = _fails(check_review_record(str(_cv(tmp_path))))
    assert "review record unreadable" in msg and "review.md" in msg


@pytest.mark.parametrize("line,got", [("", "nothing"), ("runtime: maybe\n", "maybe")])
def test_runtime_must_be_declared_as_sub_agents_or_none(tmp_path, line, got):
    (msg,) = _fails(_check(tmp_path, GOOD.replace("runtime: sub-agents\n", line)))
    assert "`runtime:`" in msg and f"(got '{got}')" in msg


def test_runtime_value_is_case_insensitive_with_sub_agents(tmp_path):
    assert "runtime sub-agents," in _passes(_check(tmp_path, GOOD.replace("sub-agents", "Sub-Agents")))


def test_runtime_value_is_case_insensitive_with_none(tmp_path):
    assert "runtime none," in _passes(_check(tmp_path, COMPACT.replace("none", "NONE")))


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
    "recruiter, Hiring-Manager, ATS",
    "recruiter, hiring manager, ATS expert parsing check reviewer fact diff",     # boundary: every allowed qualifier
])
def test_documented_persona_spellings_with_qualifiers_pass(tmp_path, personas):
    """Mutation: whole-name matching (no startswith) fails this test."""
    text = GOOD.replace("personas: recruiter, hiring manager, ATS, nurse-recruiter segment", f"personas: {personas}")
    _passes(_check(tmp_path, text))


@pytest.mark.parametrize("personas,lacks", [
    ("recruiter segment, hiring manager, ATS", "recruiter"),
    ("recruiter, hiring manager, ATS-savvy startup", "ATS"),
    ("recruitment agency, hiring manager, ATS", "recruiter"),
    ("recruiter, fintech hiring manager, ATS", "hiring manager"),
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
    assert "runtime none, 2 personas" in _passes(_check(tmp_path, COMPACT))


@pytest.mark.parametrize("name", ["fact-diff", "fact-diff reviewer", "ATS (fact diff)"])
def test_compact_fact_diff_stands_in_for_ats(tmp_path, name):
    _passes(_check(tmp_path, COMPACT.replace("ATS,", name + ",")))


def test_compact_fact_diff_segment_is_rejected(tmp_path):
    assert _fails(_check(tmp_path, COMPACT.replace("ATS,", "fact-diff segment,")))


@pytest.mark.parametrize("drop,name", [("ATS, ", "ATS (or fact-diff)"), (", hiring manager", "hiring manager")])
def test_compact_runtime_lacking_a_core_persona_fails(tmp_path, drop, name):
    (msg,) = _fails(_check(tmp_path, COMPACT.replace(drop, "")))
    assert msg.endswith(f"`personas:` lacks {name}")


def test_compact_runtime_does_not_excuse_a_missing_recruiter_only_on_sub_agents(tmp_path):
    text = COMPACT.replace("none", "sub-agents")
    assert any("recruiter" in m for m in _fails(_check(tmp_path, text)))


def test_fact_diff_alone_is_not_the_ats_persona_under_sub_agents(tmp_path):
    (msg,) = _fails(_check(tmp_path, GOOD.replace("ATS,", "fact-diff,")))
    assert "`personas:` lacks ATS" in msg


@pytest.mark.parametrize("line", ["", "layout:\n"])
def test_layout_line_is_required(tmp_path, line):
    text = GOOD.replace("layout: subagent haiku\n", line)
    (msg,) = _fails(_check(tmp_path, text))
    assert "`layout:`" in msg and "(got 'nothing')" in msg


@pytest.mark.parametrize("layout", ["subagent", "other-model", "other-model gemini", "selfish", "user please", "not run", "later",
                                    "not run (no redesign) maybe"])
def test_layout_must_be_a_whole_documented_form(tmp_path, layout):
    """Mutation: a prefix match (`startswith`) accepts all of these and fails this test."""
    assert any("`layout:`" in m for m in _fails(_check(tmp_path, COMPACT.replace("not run (no redesign)", layout))))


@pytest.mark.parametrize("layout", ["self", "subagent opus", "user", "not run (no redesign)",
                                    "SELF", "Subagent Opus  "])
def test_every_documented_layout_form_is_accepted_without_sub_agents(tmp_path, layout):
    _passes(_check(tmp_path, COMPACT.replace("not run (no redesign)", layout)))


@pytest.mark.parametrize("layout", ["subagent opus", "user"])
def test_sub_agents_accept_a_real_layout_review(tmp_path, layout):
    _passes(_check(tmp_path, GOOD.replace("subagent haiku", layout)))


@pytest.mark.parametrize("layout", ["self", "not run (no redesign)", "Self"])
def test_sub_agents_reject_a_layout_that_was_not_reviewed_by_another_reader(tmp_path, layout):
    """Mutation: dropping the sub-agents branch accepts `self` and fails this test."""
    (msg,) = _fails(_check(tmp_path, GOOD.replace("subagent haiku", layout)))
    assert "`layout:`" in msg and "always runs on the full path" in msg


@pytest.mark.parametrize("layout", ["subagent skipped", "subagent none", "subagent n/a", "subagent -"])
def test_layout_rejects_non_model_words(tmp_path, layout):
    """Mutation: dropping the negative lookahead on `_LAYOUT` accepts `subagent skipped`."""
    assert any("`layout:`" in m for m in _fails(_check(tmp_path, GOOD.replace("subagent haiku", layout))))


# ------------------------------------------------------------------ one record per CV set (`cv:`)

COMPACT_ACADEMIC = "runtime: none\ncv: cv.typ\npersonas: extraction auditor, department head\nlayout: not run (no redesign)\n## Findings\n"
ACADEMIC = GOOD.replace("recruiter, hiring manager, ATS, nurse-recruiter segment",
                        "Committee member, Extraction-and-counts auditor, Department head, research-university segment")


def _check_ac(tmp_path, text, **kw):
    _record(tmp_path, text, **kw)
    return check_review_record(str(_cv(tmp_path)), panel="academic")


def test_academic_panel_accepts_its_own_personas(tmp_path):
    _passes(_check_ac(tmp_path, ACADEMIC))


def test_academic_panel_rejects_the_industry_personas(tmp_path):
    """Mutation: ignoring `panel` accepts the industry set and fails this test."""
    (msg,) = _fails(_check_ac(tmp_path, GOOD))
    assert "`personas:` lacks committee member, extraction/counts auditor, department head" in msg


def test_industry_panel_rejects_the_academic_personas(tmp_path):
    assert any("`personas:` lacks" in m for m in _fails(_check(tmp_path, ACADEMIC)))


@pytest.mark.parametrize("drop,name", [("Committee member, ", "committee member"), ("Department head, ", "department head"),
                                       ("Extraction-and-counts auditor, ", "extraction")])
def test_academic_sub_agents_need_each_core_persona(tmp_path, drop, name):
    (msg,) = _fails(_check_ac(tmp_path, ACADEMIC.replace(drop, "")))
    assert name in msg


def test_academic_sub_agents_with_only_a_committee_member_name_the_two_missing(tmp_path):
    text = GOOD.replace("recruiter, hiring manager, ATS, nurse-recruiter segment", "Committee member")
    (msg,) = _fails(_check_ac(tmp_path, text))
    assert "extraction" in msg and "department head" in msg and "committee member" not in msg


def test_academic_compact_path_needs_extraction_auditor_and_department_head(tmp_path):
    assert "runtime none, 2 personas" in _passes(_check_ac(tmp_path, COMPACT_ACADEMIC))
    (msg,) = _fails(_check_ac(tmp_path, COMPACT_ACADEMIC.replace("department head", "committee member")))
    assert "department head" in msg
    (msg,) = _fails(_check_ac(tmp_path, COMPACT_ACADEMIC.replace("extraction auditor", "committee member")))
    assert "extraction" in msg


def test_academic_segment_persona_is_not_core(tmp_path):
    (msg,) = _fails(_check_ac(tmp_path, ACADEMIC.replace("Department head", "department head segment")))
    assert "department head" in msg


def test_record_older_than_a_data_file_is_stale_and_names_it(tmp_path):
    srcs = _sources(tmp_path, data_toml=3_000)
    (msg,) = _fails(check_review_record(str(_cv(tmp_path)), srcs))
    assert "older than data.toml" in msg


def test_record_as_old_as_a_data_file_is_fresh(tmp_path):
    srcs = _sources(tmp_path, data_toml=2_000)       # boundary: equal is fresh
    _passes(check_review_record(str(_cv(tmp_path)), srcs))


def test_sources_are_not_checked_when_none_are_given(tmp_path):
    _sources(tmp_path, data_toml=3_000)
    _passes(check_review_record(str(_cv(tmp_path))))


def test_a_source_that_does_not_exist_is_skipped(tmp_path):
    _record(tmp_path)
    _passes(check_review_record(str(_cv(tmp_path)), [str(tmp_path / "absent.toml")]))


def test_with_several_stale_sources_the_message_names_a_stale_one(tmp_path):
    srcs = _sources(tmp_path, fresh_toml=1_500, stale_toml=3_000, other_toml=1_000)
    (msg,) = _fails(check_review_record(str(_cv(tmp_path)), srcs))
    assert "older than stale.toml" in msg


def test_academic_cli_passes_the_data_file_as_a_source(monkeypatch, tmp_path, capsys):
    """Mutation: dropping the sources argument from the academic cli fails this test."""
    from vitae.verify.academic import cli as acli
    monkeypatch.setattr(acli, "run_gate", lambda typ, toml: (True, [], []))
    _cv(tmp_path)
    (toml,) = _sources(tmp_path, data_toml=3_000)
    _record(tmp_path, ACADEMIC, mtime=2_000)
    monkeypatch.setattr(sys, "argv", ["verify_academic.py", str(tmp_path / "cv.typ"), toml])
    with pytest.raises(SystemExit) as e:
        acli.main()
    assert e.value.code == 1 and "review record older than data.toml" in capsys.readouterr().out


HEAD = GOOD.split("## Findings")[0] + "## Findings\n"


@pytest.mark.parametrize("body,summary,failure", [
    ("1. ATS: numbered → applied\n2) ATS: paren → rejected: no\n", "1 finding(s) applied, 1 rejected", None),
    ("  - ATS: indented orphan → applied\n  - ATS: sibling → applied\n", "2 finding(s) applied, 0 rejected", None),
    ("prose line\n  - ATS: orphan after prose → applied\n", "1 finding(s) applied, 0 rejected", None),
    ("1. ATS: numbered\n", None, "numbered"),
    ("  - ATS: orphan\n", None, "orphan"),
    ("- parent → applied\n  1. numbered sub detail\n", "1 finding(s) applied, 0 rejected", None),
])
def test_numbered_and_orphan_indented_findings_are_counted_or_named(tmp_path, body, summary, failure):
    out = _check(tmp_path, HEAD + body)
    if failure is None:
        assert summary in _passes(out) and Level.WARN not in [lvl for lvl, _ in out]
    else:
        (msg,) = _fails(out)
        assert failure in msg


@pytest.mark.parametrize("body", ["Everything was fine, nothing to report.\n", "No findings.\n\nSee below.\n"])
def test_findings_text_with_no_parseable_finding_is_a_fail_not_a_warn(tmp_path, body):
    """Mutation: dropping the non-empty-block check turns this into WARN + PASS and fails this test."""
    (msg,) = _fails(_check(tmp_path, HEAD + body))
    assert "no parseable finding" in msg


@pytest.mark.parametrize("ending", ["→ applied.", "→ applied (bullet 3)", "→ APPLIED"])
def test_applied_may_carry_a_trailing_note_and_any_case(tmp_path, ending):
    assert "2 finding(s) applied, 1 rejected" in _passes(_check(tmp_path, GOOD + f"- ATS: dates {ending}\n"))


def test_cv_line_is_required_and_names_the_file(tmp_path):
    (msg,) = _fails(_check(tmp_path, GOOD.replace("cv: cv.typ\n", "")))
    assert "`cv:` must list cv.typ" in msg and "got nothing)" in msg


def test_cv_line_names_what_it_lists_instead(tmp_path):
    (msg,) = _fails(_check(tmp_path, GOOD.replace("cv: cv.typ", "cv: a.typ,b.typ")))
    assert "got a.typ, b.typ)" in msg


@pytest.mark.parametrize("line", ["cv: other.typ", "cv: cv.typ.bak", "cv: CV.typ"])
def test_cv_line_must_list_the_verified_cv(tmp_path, line):
    (msg,) = _fails(_check(tmp_path, GOOD.replace("cv: cv.typ", line)))
    assert "must list cv.typ" in msg


def test_cv_line_lists_several_cvs(tmp_path):
    _passes(_check(tmp_path, GOOD.replace("cv: cv.typ", "cv: cv_2p.typ,  cv.typ , other.typ")))


def test_cv_basenames_may_be_separated_by_a_bare_comma(tmp_path):
    _passes(_check(tmp_path, GOOD.replace("cv: cv.typ", "cv: cv_2p.typ,cv.typ")))


@pytest.mark.parametrize("heading", ["## Findings", "  ## Findings"])
def test_header_fields_are_read_only_above_the_findings_heading(tmp_path, heading):
    text = GOOD.replace("layout: subagent haiku\n## Findings\n", f"{heading}\nlayout: subagent haiku\n")
    (msg,) = _fails(_check(tmp_path, text))
    assert "`layout:`" in msg and "(got 'nothing')" in msg


def test_every_failing_check_is_reported_together(tmp_path):
    text = "runtime: none\npersonas: recruiter\n"        # no cv, no layout, no Findings, wrong personas
    out = _check(tmp_path, text)
    assert len(_fails(out)) == 4 and len(out) == 4


# ------------------------------------------------------------------ markdown tolerance

def test_findings_heading_may_carry_text(tmp_path):
    assert "1 finding(s) applied, 1 rejected" in _passes(_check(tmp_path, GOOD.replace("## Findings", "## Findings (2)")))


def test_findings_heading_is_case_insensitive(tmp_path):
    assert "1 finding(s) applied, 1 rejected" in _passes(_check(tmp_path, GOOD.replace("## Findings", "## findings")))


@pytest.mark.parametrize("heading", ["### Findings", "##Findings", "# Findings"])
def test_findings_heading_must_be_a_level_2_heading_with_a_space(tmp_path, heading):
    (msg,) = _fails(_check(tmp_path, GOOD.replace("## Findings", heading)))
    assert "no `## Findings` section" in msg


def test_crlf_line_endings_are_read_like_lf(tmp_path):
    assert "runtime sub-agents, 4 personas, 1 finding(s) applied, 1 rejected" in _passes(
        _check(tmp_path, GOOD.replace("\n", "\r\n")))


@pytest.mark.parametrize("indent", ["  ", "\t"])
def test_continuation_lines_join_the_bullet_before_the_ending_is_tested(tmp_path, indent):
    text = GOOD + f"- ATS: a long finding that wraps\n{indent}onto a second line → applied\n"
    assert "2 finding(s) applied" in _passes(_check(tmp_path, text))


def test_an_unresolved_finding_is_quoted_up_to_100_characters(tmp_path):
    (msg,) = _fails(_check(tmp_path, GOOD + "- " + "x" * 150 + "\n"))
    assert msg.endswith("): " + "x" * 100)


def test_wrapped_finding_without_an_ending_still_fails(tmp_path):
    (msg,) = _fails(_check(tmp_path, GOOD + "- ATS: wraps\n  onto a second line\n"))
    assert "wraps onto a second line" in msg


def test_nested_sub_bullets_are_not_findings_and_belong_to_the_parent(tmp_path):
    text = GOOD + "- ATS: parent → applied\n  - sub detail without a verdict\n    continuation of the sub-bullet\n* star bullet → rejected: no\n"
    assert "2 finding(s) applied, 2 rejected" in _passes(_check(tmp_path, text))


def test_a_sub_bullet_does_not_resolve_its_parent(tmp_path):
    (msg,) = _fails(_check(tmp_path, GOOD + "- ATS: parent\n  - child → applied\n"))
    assert "parent" in msg


@pytest.mark.parametrize("bullet", [
    "- ATS: keyword missing",
    "- ATS: keyword missing → pending",
    "- ATS: keyword missing → rejected:",
    "- ATS: keyword missing → rejected.",
])
def test_unresolved_finding_fails_and_is_named(tmp_path, bullet):
    (msg,) = _fails(_check(tmp_path, GOOD + bullet + "\n"))
    assert "keyword missing" in msg


@pytest.mark.parametrize("finding", ["- ATS: rename 'Docker -> applied containers' to the posting's term",
                                     "- ATS: x -> applied -> maybe", "- ATS: x → rejected: because -> later"])
def test_resolution_must_be_the_last_arrow(tmp_path, finding):
    """Mutation: an unanchored resolution regex reads a mid-sentence `-> applied …` as resolved."""
    assert any("not resolved" in m for m in _fails(_check(tmp_path, GOOD + finding + "\n")))


def test_ascii_arrow_notes_and_dashes_in_the_reason_are_counted(tmp_path):
    text = GOOD + ("- ATS: a -> applied\n- ATS: b -> rejected: not in facts\n"
                   "- ATS: c -> applied (bullet 3)\n- ATS: d → rejected: not in facts - skip\n")
    assert "3 finding(s) applied, 3 rejected" in _passes(_check(tmp_path, text))


def test_bullets_outside_the_findings_section_are_not_findings(tmp_path):
    assert "1 finding(s) applied, 1 rejected" in _passes(_check(tmp_path, GOOD + "## Notes\n- free text without a verdict\n"))


def test_zero_findings_is_a_warn_not_a_fail(tmp_path):
    out = _check(tmp_path, COMPACT)
    assert out[0] == (Level.WARN, "review record lists no findings")
    assert "0 finding(s) applied, 0 rejected" in _passes(out)


def test_missing_findings_section_fails(tmp_path):
    assert any("## Findings" in m for m in _fails(_check(tmp_path, GOOD.split("## Findings")[0])))


# ------------------------------------------------------------------ wiring in the one-file gate

@pytest.fixture
def gate(monkeypatch):
    """_check_cv with the mechanical gates stubbed out and the fill measurement fixed at 80%: only the record (and
    the fill target) decide the verdict."""
    monkeypatch.setattr(cv, "run_gates", lambda gates, ctx: 0)
    monkeypatch.setattr(cv, "check_whitespace", lambda *a, **k: [])
    monkeypatch.setattr(cv.measure_fill, "measure", lambda path: "ink from 10% to 80%")
    return lambda typ, *args, **kw: cv._check_cv(str(typ), "1", *args, **kw)


def _lines(capsys):
    return [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]


def test_failing_record_gives_exit_1_no_footer_and_ends_on_fail_without_pass(gate, tmp_path, capsys):
    rc, footer = gate(_cv(tmp_path), "60", "100")
    lines = _lines(capsys)
    assert rc == 1 and footer is None
    assert lines[-1].startswith("FAIL") and not any(ln.startswith("PASS") for ln in lines)


def test_failing_record_is_printed_after_the_mechanical_verdict(gate, tmp_path, capsys):
    gate(_cv(tmp_path), "60", "100")
    lines = _lines(capsys)
    mech = next(i for i, ln in enumerate(lines) if ln.startswith("mechanical gates: PASS (fill 80%)"))
    assert any(ln.startswith("FAIL  review record missing") for ln in lines[mech + 1:])


def test_failing_record_tells_the_agent_to_look_at_the_pngs_first(gate, tmp_path, capsys):
    """Mutation: dropping the cue fails here."""
    gate(_cv(tmp_path), "60", "100")
    verdict = next(ln for ln in _lines(capsys) if ln.startswith("mechanical gates: PASS"))
    assert "now LOOK at the PNGs (Visual pass:), then step 7" in verdict


def test_valid_record_passes_and_prints_the_info_before_the_pass(gate, tmp_path, capsys):
    typ = _cv(tmp_path)
    _record(tmp_path)
    rc, _ = gate(typ, "60", "100")
    lines = _lines(capsys)
    info = next(i for i, ln in enumerate(lines) if ln.startswith("INFO  review record: runtime sub-agents"))
    assert rc == 0 and not any(ln.startswith("FAIL") for ln in lines)
    assert any(ln.startswith("PASS  all mechanical checks") for ln in lines[info + 1:])


def test_mechanical_fail_keeps_its_behaviour_and_skips_the_record(gate, tmp_path, capsys):
    rc, footer = gate(_cv(tmp_path), "90", "100")          # the stubbed 80% fill is under the 90% minimum
    out = capsys.readouterr().out
    assert rc == 1 and footer and "FAIL  fill" in out
    assert "review record" not in out and "mechanical gates: PASS" not in out


def test_allow_placeholders_run_does_not_check_the_record(gate, tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(cv, "placeholders_allowed", lambda typ: True)
    rc, _ = gate(_cv(tmp_path), "60", "100", allow_placeholders=True)
    out = capsys.readouterr().out
    assert rc == 0 and "review record" not in out and "PASS (placeholder gate skipped)" in out


def test_gates_mode_does_not_check_the_record(gate, tmp_path, capsys, monkeypatch):
    from vitae.verify import cli
    typ = _cv(tmp_path)
    monkeypatch.setattr(cli, "pdf_backend", lambda: None)
    monkeypatch.setattr(cli, "extract_text", lambda pdf, backend: "")
    monkeypatch.setattr(cli, "make_context", lambda *a, **k: None)
    monkeypatch.setattr(cli, "run_gates", lambda gates, ctx: 0)
    monkeypatch.setattr(sys, "argv", ["verify.py", "--gates", str(typ), str(tmp_path / "cv.pdf")])
    rc, _ = cli.main()                                     # no review.md beside the CV
    assert rc == 0 and "review record" not in capsys.readouterr().out


def test_without_gates_mode_the_same_cv_lacks_its_record(gate, tmp_path, capsys, monkeypatch):
    """Positive control of the --gates test: the same CV, same missing record, fails in the one-file gate."""
    from vitae.verify import cli
    monkeypatch.setattr(sys, "argv", ["verify.py", str(_cv(tmp_path)), "1", "60", "100"])
    rc, _ = cli.main()
    assert rc == 1 and "FAIL  review record missing" in capsys.readouterr().out


def test_lowered_fill_warn_sits_right_under_the_mechanical_verdict_when_the_record_fails(gate, tmp_path, capsys):
    typ = _cv(tmp_path)
    typ.write_text("// vitae: pages=1 fill=70-80\n" + typ.read_text(encoding="utf-8"), encoding="utf-8")
    gate(typ, "60", "100")
    lines = capsys.readouterr().out.splitlines()
    mech = next(i for i, ln in enumerate(lines) if ln.startswith("mechanical gates: PASS"))
    assert lines[mech + 1].startswith("WARN  fill target lowered below drawn target")


def test_failing_record_without_fill_args_keeps_the_except_fill_wording(gate, tmp_path, capsys):
    """Mutation: printing `PASS (fill N%)` regardless of the args fails the first assert."""
    gate(_cv(tmp_path), None, None)
    out = capsys.readouterr().out
    assert "mechanical gates: PASS except fill (no FILL_MIN FILL_MAX given)" in out
    assert "mechanical gates: PASS (fill" not in out


def test_rebuild_skips_only_the_record_and_says_so_on_the_verdict_line(gate, tmp_path, capsys):
    """Mutation: ignoring `rebuild` leaves the missing record a FAIL and fails the first assert."""
    rc, _ = gate(_cv(tmp_path), "60", "100", rebuild=True)       # no review.md at all
    out = capsys.readouterr().out
    assert rc == 0 and "PASS (review record skipped: --rebuild, candidate rebuild) all mechanical checks" in out
    assert "review record" not in out.replace("review record skipped", "")


def test_rebuild_does_not_excuse_a_mechanical_fail(gate, tmp_path, capsys):
    rc, footer = gate(_cv(tmp_path), "90", "100", rebuild=True)       # stubbed 80% fill under the 90% minimum
    assert rc == 1 and footer and "PASS (review record skipped" not in capsys.readouterr().out


def test_rebuild_flag_reaches_the_gate_from_the_command_line(gate, tmp_path, capsys, monkeypatch):
    from vitae.verify import cli
    typ = str(_cv(tmp_path))                                      # no review.md at all
    monkeypatch.setattr(sys, "argv", ["verify.py", typ, "1", "60", "100", "--rebuild"])
    rc, _ = cli.main()
    assert rc == 0 and "review record skipped" in capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", ["verify.py", typ, "1", "60", "100"])
    rc, _ = cli.main()
    assert rc == 1 and "FAIL  review record missing" in capsys.readouterr().out


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
    lines = _lines(capsys)
    assert lines[0].startswith("mechanical gates: PASS") and "FAIL  review record missing" in lines[1]
    assert lines[-1].startswith("FAIL") and not any(ln.startswith("PASS") for ln in lines)


def test_academic_with_a_valid_record_passes(academic, tmp_path, capsys):
    _cv(tmp_path)
    _record(tmp_path, ACADEMIC)
    assert academic() == 0
    out = capsys.readouterr().out
    assert "INFO  review record: runtime sub-agents" in out and "PASS  all five checks hold" in out.splitlines()


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


def test_field_names_are_case_insensitive(tmp_path):
    """A hand-written record may say `Runtime:` / `CV:`; the key is not case-sensitive (the value rules are separate)."""
    text = GOOD.replace("runtime:", "Runtime:").replace("cv:", "CV:").replace("personas:", "PERSONAS:").replace("layout:", "Layout:")
    _passes(_check(tmp_path, text))


def test_failure_messages_read_as_the_instruction_the_agent_acts_on(tmp_path):
    """The FAIL text is what the agent reads to fix the record: each one is a whole sentence starting `review record: `
    with the documented forms, not just a keyword."""
    (msg,) = _fails(_check(tmp_path, GOOD.replace("## Findings", "### Findings")))
    assert msg == "review record: no `## Findings` section"
    (msg,) = _fails(_check(tmp_path, HEAD + "Everything was fine.\n"))
    assert msg == ("review record: the Findings section has text but no parseable finding — one bullet per finding "
                   "(`-`, `*` or `1.`), each ending `→ applied` or `→ rejected: <reason>`")
    (msg,) = _fails(_check(tmp_path, GOOD.replace("subagent haiku", "later")))
    assert msg == ("review record: `layout:` must be one of subagent <model> | self | user | "
                   "not run (no redesign) (got 'later')")
    (msg,) = _fails(_check(tmp_path, GOOD.replace("subagent haiku", "self")))
    assert msg == ("review record: `layout:` with `runtime: sub-agents` must be subagent <model> | "
                   "user — the layout reviewer always runs on the full path (got 'self')")


# ------------------------------------------------------------------ the `Layout review:` report line, from the record

@pytest.mark.parametrize("layout,line", [
    ("subagent haiku", "Layout review: subagent haiku"),
    ("Subagent   Haiku 4.5", "Layout review: subagent Haiku 4.5"),
    ("user", "Layout review: user"),
    ("SELF", "Layout review: self"),
    ("Not Run (no redesign)", "Layout review: not run (no redesign)"),
])
def test_layout_report_line_is_the_documented_form_of_the_layout_field(tmp_path, layout, line):
    _record(tmp_path, GOOD.replace("subagent haiku", layout))
    assert layout_report_line(str(_cv(tmp_path))) == line


def test_layout_report_line_drops_control_characters_and_ansi_escapes(tmp_path):
    _record(tmp_path, GOOD.replace("subagent haiku", "subagent \x1b[31mhai\x07ku\x1b[0m\x9b"))
    assert layout_report_line(str(_cv(tmp_path))) == "Layout review: subagent haiku"


def test_layout_report_line_caps_a_long_value(tmp_path):
    _record(tmp_path, GOOD.replace("subagent haiku", "subagent " + "m" * 5000))
    line = layout_report_line(str(_cv(tmp_path)))
    assert line == "Layout review: subagent " + "m" * 71 + "…"
    _record(tmp_path, GOOD.replace("subagent haiku", "subagent " + "m" * 71))
    assert layout_report_line(str(_cv(tmp_path))) == "Layout review: subagent " + "m" * 71   # exactly 80: untouched


def test_layout_report_line_cut_drops_the_space_before_the_ellipsis(tmp_path):
    cut = "m" * 70 + " " + "n" * 40                                  # the 80-character cut ends on a space
    _record(tmp_path, GOOD.replace("subagent haiku", "subagent " + cut))
    line = layout_report_line(str(_cv(tmp_path)))
    assert line == "Layout review: subagent " + "m" * 70 + "…"


def test_layout_report_line_is_none_without_a_readable_record_or_field(tmp_path):
    typ = str(_cv(tmp_path))
    assert layout_report_line(typ) is None                                        # no review.md
    _record(tmp_path, GOOD.replace("layout: subagent haiku\n", ""))
    assert layout_report_line(typ) is None                                        # no layout field
    _record(tmp_path, GOOD.replace("subagent haiku", "later"))
    assert layout_report_line(typ) is None                                        # not a documented form
    (tmp_path / "review.md").write_bytes(b"\xff\xfe layout: self")
    assert layout_report_line(typ) is None                                        # unreadable


def test_layout_report_line_reads_the_record_beside_the_cv_not_the_working_directory(tmp_path, monkeypatch):
    other = tmp_path / "elsewhere"
    other.mkdir()
    (other / "review.md").write_text(GOOD.replace("subagent haiku", "user"), encoding="utf-8")
    _record(tmp_path)
    monkeypatch.chdir(other)
    assert layout_report_line(str(_cv(tmp_path))) == "Layout review: subagent haiku"


LAYOUT_LINE = "Layout review: subagent haiku"


def test_gate_output_carries_the_layout_line_right_after_the_pass_line(gate, tmp_path, capsys):
    typ = _cv(tmp_path)
    _record(tmp_path)
    rc, _ = gate(typ, "60", "100")
    lines = _lines(capsys)
    pass_at = next(i for i, ln in enumerate(lines) if ln.startswith("PASS  all mechanical checks"))
    assert rc == 0 and lines[pass_at + 1] == LAYOUT_LINE and lines.count(LAYOUT_LINE) == 1


def test_gate_layout_line_follows_a_lowered_fill_pass_too(gate, tmp_path, capsys):
    typ = _cv(tmp_path)
    typ.write_text("// vitae: pages=1 fill=70-80\n" + typ.read_text(encoding="utf-8"), encoding="utf-8")
    os.utime(typ, (1_000, 1_000))
    _record(tmp_path, GOOD.replace("runtime: sub-agents", "runtime: none").replace("subagent haiku", "self"))
    rc, _ = gate(typ, "60", "100")
    lines = _lines(capsys)
    pass_at = next(i for i, ln in enumerate(lines) if ln.startswith("PASS (fill target lowered"))
    assert rc == 0 and "Layout review: self" in lines[pass_at + 1:]


@pytest.mark.parametrize("runtime,layout", [("none", "not run (no redesign)"), ("none", "self"), ("sub-agents", "user")])
def test_gate_layout_line_maps_every_documented_layout_value(gate, tmp_path, capsys, runtime, layout):
    _record(tmp_path, GOOD.replace("runtime: sub-agents", f"runtime: {runtime}").replace("subagent haiku", layout))
    rc, _ = gate(_cv(tmp_path), "60", "100")
    assert rc == 0 and f"Layout review: {layout}" in _lines(capsys)


def test_gate_prints_no_layout_line_without_a_record(gate, tmp_path, capsys):
    rc, _ = gate(_cv(tmp_path), "60", "100")
    assert rc == 1 and not any(ln.startswith("Layout review") for ln in _lines(capsys))


def test_gate_prints_no_layout_line_for_an_invalid_record(gate, tmp_path, capsys):
    _record(tmp_path, GOOD.replace("recruiter, ", ""))                        # personas lack the recruiter: FAIL
    rc, _ = gate(_cv(tmp_path), "60", "100")
    out = capsys.readouterr().out
    assert rc == 1 and "FAIL  review record: `personas:` lacks recruiter" in out and "Layout review" not in out


def test_gate_prints_no_layout_line_when_the_record_is_skipped(gate, tmp_path, capsys, monkeypatch):
    _record(tmp_path)                                                         # a valid record is there, but skipped
    rc, _ = gate(_cv(tmp_path), "60", "100", rebuild=True)
    assert rc == 0 and "Layout review" not in capsys.readouterr().out
    monkeypatch.setattr(cv, "placeholders_allowed", lambda typ: True)
    rc, _ = gate(_cv(tmp_path), "60", "100", allow_placeholders=True)
    assert rc == 0 and "Layout review" not in capsys.readouterr().out


def test_gates_mode_prints_no_layout_line_even_with_a_valid_record(gate, tmp_path, capsys, monkeypatch):
    from vitae.verify import cli
    typ = _cv(tmp_path)
    _record(tmp_path)
    monkeypatch.setattr(cli, "pdf_backend", lambda: None)
    monkeypatch.setattr(cli, "extract_text", lambda pdf, backend: "")
    monkeypatch.setattr(cli, "make_context", lambda *a, **k: None)
    monkeypatch.setattr(cli, "run_gates", lambda gates, ctx: 0)
    monkeypatch.setattr(sys, "argv", ["verify.py", "--gates", str(typ), str(tmp_path / "cv.pdf")])
    rc, _ = cli.main()
    assert rc == 0 and "Layout review" not in capsys.readouterr().out


def test_gate_json_exposes_the_layout_review_and_does_not_count_it_as_a_check(gate, tmp_path, capsys, monkeypatch):
    import json

    from vitae.verify import cli
    _record(tmp_path)
    monkeypatch.setattr(sys, "argv", ["verify.py", str(_cv(tmp_path)), "1", "60", "100", "--json"])
    rc, _ = cli.main()
    cap = capsys.readouterr()
    d = json.loads(cap.out)
    assert rc == 0 and d["verdict"] == "PASS" and d["layout_review"] == "subagent haiku"
    assert not any("Layout review" in c["message"] for c in d["checks"])
    assert LAYOUT_LINE in cap.err                                             # a non-check line goes to stderr


def test_gate_json_has_no_layout_review_without_a_valid_record(gate, tmp_path, capsys, monkeypatch):
    import json

    from vitae.verify import cli
    monkeypatch.setattr(sys, "argv", ["verify.py", str(_cv(tmp_path)), "1", "60", "100", "--json"])
    rc, _ = cli.main()
    d = json.loads(capsys.readouterr().out)
    assert rc == 1 and d["verdict"] == "FAIL" and "layout_review" not in d


def test_academic_layout_line_is_the_last_line_after_the_pass_line(academic, tmp_path, capsys):
    _cv(tmp_path)
    _record(tmp_path, ACADEMIC)
    assert academic() == 0
    assert _lines(capsys)[-2:] == ["PASS  all five checks hold", LAYOUT_LINE]


def test_academic_prints_no_layout_line_when_the_record_is_missing_or_skipped(academic, tmp_path, capsys):
    _cv(tmp_path)
    assert academic() == 1
    assert "Layout review" not in capsys.readouterr().out
    _record(tmp_path, ACADEMIC)
    assert academic("--rebuild") == 0
    assert "Layout review" not in capsys.readouterr().out
