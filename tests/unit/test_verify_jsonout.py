"""vitae.verify.jsonout driven directly with a fake dispatch: the JSON object's shape, the check parsing of the
captured text, the error objects, and the version read from SKILL.md. (The real gate through `cli.main` is in
test_verify_json.py.)"""
import json
import sys

import pytest
from vitae.core.level import Level
from vitae.verify import jsonout


def _run(capsys, argv, dispatch):
    rc, footer = jsonout.run_json(argv, dispatch)
    cap = capsys.readouterr()
    assert footer is None
    return rc, json.loads(cap.out), cap.err


def _ok(argv):
    return 0, None


def _skill_md(monkeypatch, tmp_path, text):
    """Point skill_version at a temporary SKILL.md: it reads <module>/../../.. / SKILL.md, so fake the module location."""
    (tmp_path / "SKILL.md").write_text(text, encoding="utf-8")
    monkeypatch.setattr(jsonout, "__file__", str(tmp_path / "a" / "b" / "c" / "jsonout.py"))


# --- skill_version -----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("line", ['  version: "1.2.3"', "  version: 1.2.3", '  version:   "1.2.3"  '])
def test_skill_version_reads_quoted_or_bare_values(monkeypatch, tmp_path, line):
    _skill_md(monkeypatch, tmp_path, f"---\nname: x\nmetadata:\n{line}\n---\nbody\n")
    assert jsonout.skill_version() == "1.2.3"


def test_skill_version_is_none_when_the_frontmatter_has_no_version(monkeypatch, tmp_path):
    _skill_md(monkeypatch, tmp_path, "---\nname: x\n---\nbody\n")
    assert jsonout.skill_version() is None


def test_skill_version_ignores_a_version_line_in_the_body(monkeypatch, tmp_path):
    _skill_md(monkeypatch, tmp_path, "---\nname: x\n---\nbody\n  version: 9.9.9\n\n---\n\n---\nmore\n")
    assert jsonout.skill_version() is None


def test_skill_version_prefers_the_frontmatter_over_the_body(monkeypatch, tmp_path):
    _skill_md(monkeypatch, tmp_path, '---\nmetadata:\n  version: "1.0.0"\n---\nbody\n  version: 9.9.9\n')
    assert jsonout.skill_version() == "1.0.0"


def test_skill_version_is_none_when_the_file_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(jsonout, "__file__", str(tmp_path / "a" / "b" / "c" / "jsonout.py"))
    assert jsonout.skill_version() is None


# --- _checks -----------------------------------------------------------------------------------------------------

def test_checks_take_the_gate_name_from_the_recorded_sink_not_from_the_text():
    sink = [("gate-one", Level.OK, "first message"), ("gate-two", Level.WARN, "second message")]
    checks, banner = jsonout._checks("OK    first message\nWARN  second message\nPASS 2 mechanical checks\n", sink)
    assert checks == [{"level": "OK", "check": "gate-one", "message": "first message"},
                      {"level": "WARN", "check": "gate-two", "message": "second message"}]
    assert banner == "PASS 2 mechanical checks"


def test_a_multi_line_recorded_message_is_one_check_and_the_next_one_still_matches():
    sink = [("fonts", Level.FAIL, "missing font\n      install Carlito"), ("fill", Level.INFO, "fill: ok")]
    checks, _ = jsonout._checks("FAIL  missing font\n      install Carlito\nINFO  fill: ok\n", sink)
    assert [(c["check"], c["message"]) for c in checks] == [("fonts", "missing font\n      install Carlito"), ("fill", "fill: ok")]


def test_lines_the_gate_printed_itself_are_read_back_by_their_level_word():
    checks, banner = _checks_of("NEXT  fix the page count\nFAIL  something plain\nWARN  pages: 3 instead of 1\n")
    assert checks == [{"level": "INFO", "check": "cv", "message": "fix the page count"},
                      {"level": "FAIL", "check": "cv", "message": "something plain"},
                      {"level": "WARN", "check": "pages", "message": "pages: 3 instead of 1"}]
    assert banner is None


def _checks_of(text):
    return jsonout._checks(text, [])


def test_non_check_lines_go_to_stderr_not_into_the_checks(capsys):
    checks, _ = _checks_of("compile noise\nOK    fine\n")
    assert [c["message"] for c in checks] == ["fine"]
    assert capsys.readouterr().err == "compile noise\n"


# --- positionals and the object's file / pages / fill ------------------------------------------------------------

def test_flags_that_take_no_value_are_not_the_file(capsys):
    _, d, _ = _run(capsys, ["--allow-placeholders", "--rebuild", "x.typ", "2"], _ok)
    assert d["file"] == "x.typ" and d["pages_expected"] == 2


@pytest.mark.parametrize("argv", [["--facts", "f.toml", "x.typ", "2", "10", "95"], ["x.typ", "--facts", "f.toml", "2"]])
def test_facts_flag_and_its_value_are_not_positionals(capsys, argv):
    _, d, _ = _run(capsys, argv, _ok)
    assert d["file"] == "x.typ" and d["pages_expected"] == 2


def test_no_positional_means_file_null_and_no_pages_or_fill(capsys):
    _, d, _ = _run(capsys, ["--allow-placeholders"], _ok)
    assert d["file"] is None and "pages_expected" not in d and "fill" not in d


def test_only_a_file_gives_no_pages_and_no_fill(capsys):
    _, d, _ = _run(capsys, ["x.typ"], _ok)
    assert d["file"] == "x.typ" and "pages_expected" not in d and "fill" not in d


def test_non_numeric_pages_are_not_reported(capsys):
    _, d, _ = _run(capsys, ["x.typ", "two"], _ok)
    assert "pages_expected" not in d


def test_fill_needs_both_bounds_to_be_numbers(capsys):
    for argv in (["x.typ", "2", "10"], ["x.typ", "2", "abc", "95"], ["x.typ", "2", "10", "abc"]):
        _, d, _ = _run(capsys, argv, _ok)
        assert "fill" not in d, argv


def test_fill_measured_is_null_when_no_fill_check_was_printed(capsys):
    _, d, _ = _run(capsys, ["x.typ", "2", "10", "95"], _ok)
    assert d["fill"] == {"min": 10, "max": 95, "measured": None}


# --- the object around the checks ---------------------------------------------------------------------------------

def test_pass_object_carries_the_skill_version_and_the_banner(capsys):
    def dispatch(argv):
        print("OK    fine")
        print("PASS 1 mechanical checks")
        return 0, "ignored on pass"
    _, d, _ = _run(capsys, ["x.typ"], dispatch)
    assert d["version"] == jsonout.skill_version() and d["version"]
    assert d["summary"] == "PASS 1 mechanical checks" and d["verdict"] == "PASS" and d["footer"] is None


def _layout_dispatch(*lines, rc=0):
    def dispatch(argv):
        print("\n".join(lines))
        return rc, None
    return dispatch


def test_layout_review_is_the_line_printed_under_the_pass_line_and_is_no_check(capsys):
    d = _run(capsys, ["x.typ"], _layout_dispatch("OK    fine", "PASS all mechanical checks", "Layout review: other-model qwen3-vl"))
    _, obj, err = d
    assert obj["layout_review"] == "other-model qwen3-vl"
    assert [c["message"] for c in obj["checks"]] == ["fine"]
    assert "Layout review: other-model qwen3-vl" in err


def test_layout_review_is_found_when_the_pass_line_is_the_first_line_and_warnings_follow(capsys):
    """The gate repeats the lead/size warnings after the PASS line, so more lines can follow the report line."""
    _, d, _ = _run(capsys, ["x.typ"], _layout_dispatch("PASS all mechanical checks", "Layout review: self", "WARN  late"))
    assert d["layout_review"] == "self"


def test_layout_review_is_absent_when_the_gate_printed_none(capsys):
    _, d, _ = _run(capsys, ["x.typ"], _layout_dispatch("OK    fine", "PASS all mechanical checks"))
    assert "layout_review" not in d


def test_layout_review_is_absent_on_a_fail_even_if_the_text_has_such_a_line(capsys):
    _, d, _ = _run(capsys, ["x.typ"], _layout_dispatch("PASS x", "Layout review: self", "FAIL  nope", rc=1))
    assert d["verdict"] == "FAIL" and "layout_review" not in d


def test_layout_review_ignores_a_line_of_the_cv_text_above_the_pass_line(capsys):
    """The extraction dump comes before the verdict; a CV line that looks like the report line is not read."""
    _, d, _ = _run(capsys, ["x.typ"], _layout_dispatch("Layout review: self", "PASS all mechanical checks"))
    assert "layout_review" not in d


def test_layout_review_needs_a_value(capsys):
    _, d, _ = _run(capsys, ["x.typ"], _layout_dispatch("PASS all mechanical checks", "Layout review: ", "Layout review:"))
    assert "layout_review" not in d


def test_fail_object_keeps_the_footer(capsys):
    rc, d, _ = _run(capsys, ["x.typ"], lambda argv: (1, "NEXT fix it"))
    assert (rc, d["verdict"], d["exit_code"], d["footer"]) == (1, "FAIL", 1, "NEXT fix it")


def test_doctor_object_is_tool_doctor_without_file_fields(capsys):
    _, d, _ = _run(capsys, ["--doctor"], _ok)
    assert d["tool"] == "doctor" and not {"file", "pages_expected", "fill"} & set(d)


def test_check_text_is_written_as_utf8_not_escaped(monkeypatch, capsys):
    def dispatch(argv):
        print("INFO  fill: résumé → ok")
        return 0, None
    jsonout.run_json(["x.typ"], dispatch)
    assert "résumé → ok" in capsys.readouterr().out


def test_gate_stderr_is_passed_through(capsys):
    def dispatch(argv):
        print("a warning", file=sys.stderr)
        return 0, None
    _, _, err = _run(capsys, ["x.typ"], dispatch)
    assert "a warning" in err


# --- error objects ----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("mode", jsonout._UNSUPPORTED)
def test_unsupported_mode_object_is_exact(capsys, mode):
    rc, d, err = _run(capsys, [mode], _ok)
    msg = f"--json supports the one-file gate and --doctor, not {mode}"
    assert rc == 2 and d == {"tool": "verify", "verdict": "ERROR", "exit_code": 2, "error": msg} and msg in err


def test_a_gate_crash_is_an_error_object_with_the_exception(capsys):
    def boom(argv):
        print("half output")
        raise ValueError("boom")
    rc, d, err = _run(capsys, ["x.typ"], boom)
    assert rc == 2 and d == {"tool": "verify", "verdict": "ERROR", "exit_code": 2, "error": "ValueError: boom"}
    assert "half output" in err


def _exit(code):
    def dispatch(argv):
        raise SystemExit(code)
    return dispatch


def test_system_exit_with_a_message_is_a_usage_error_carrying_it(capsys):
    rc, d, err = _run(capsys, ["x.typ"], _exit("usage: verify.py FILE"))
    assert rc == 2 and d == {"tool": "verify", "verdict": "ERROR", "exit_code": 2, "error": "usage: verify.py FILE"}
    assert "usage: verify.py FILE" in err


@pytest.mark.parametrize("code", [0, 1, 2])
def test_system_exit_without_a_message_is_a_generic_usage_error(capsys, code):
    """Outside --doctor even `exit(0)`/`exit(1)` is not a verdict: the gate never ran to completion."""
    rc, d, _ = _run(capsys, ["x.typ"], _exit(code))
    assert rc == 2 and d == {"tool": "verify", "verdict": "ERROR", "exit_code": 2, "error": "usage error"}


@pytest.mark.parametrize("code, verdict", [(0, "PASS"), (1, "FAIL")])
def test_doctor_may_exit_with_its_own_verdict(capsys, code, verdict):
    rc, d, _ = _run(capsys, ["--doctor"], _exit(code))
    assert (rc, d["verdict"], d["exit_code"]) == (code, verdict, code)


def test_doctor_exiting_with_another_code_is_an_error(capsys):
    rc, d, _ = _run(capsys, ["--doctor"], _exit(2))
    assert rc == 2 and d["verdict"] == "ERROR"
