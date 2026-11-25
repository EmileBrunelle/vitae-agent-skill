"""`verify.py --json`: the one-file gate as one JSON object on stdout, through the real `cli.main` on a shipped template.

The text mode is the reference: the JSON verdict, exit code and every FAIL/WARN line must agree with it."""
import json
import re
import sys

import pytest
from _paths import ROOT
from vitae.verify import cli, jsonout

TEMPLATE = str(ROOT / "templates" / "resume.typ")


def _run(monkeypatch, capsys, *args):
    monkeypatch.setattr(sys, "argv", ["verify.py", *args])
    rc, footer = cli.main()
    cap = capsys.readouterr()
    return rc, footer, cap.out, cap.err


@pytest.fixture
def both(monkeypatch, capsys):
    def go(*extra, pages="1"):
        text = _run(monkeypatch, capsys, TEMPLATE, pages, *extra)
        js = _run(monkeypatch, capsys, TEMPLATE, pages, *extra, "--json")
        return text, js
    return go


def test_pass_agrees_with_text_mode_and_stdout_is_one_json_object(both, template_fonts):
    """Mutation: a wrong verdict/exit_code mapping, or any stray print on stdout, breaks the first lines."""
    (t_rc, _, t_out, _), (j_rc, j_footer, j_out, j_err) = both("--allow-placeholders")
    assert j_out.endswith("\n") and j_out.count("\n") == 1
    d = json.loads(j_out)
    assert (t_rc, j_rc) == (0, 0) and d["verdict"] == "PASS" and d["exit_code"] == 0
    assert j_footer is None and d["footer"] is None and d["file"] == TEMPLATE and d["pages_expected"] == 1
    assert d["tool"] == "verify" and d["checks"] and "placeholder gate skipped" in d["summary"]
    assert all(c["level"] in ("OK", "INFO", "WARN", "FAIL") and c["check"] and c["message"] for c in d["checks"])
    assert "extraction" in j_err and "extraction" in t_out         # the dump moved to stderr, text mode keeps it on stdout


def test_fail_agrees_with_text_mode_and_every_fail_and_warn_line_is_a_check(both):
    """The FAIL comes from asking for 3 pages of a 1-page template (and the unreplaced samples), so no font is needed."""
    (t_rc, _, t_out, _), (j_rc, _, j_out, _) = both(pages="3")
    d = json.loads(j_out)
    assert t_rc == 1 and j_rc == 1 and d["verdict"] == "FAIL" and d["exit_code"] == 1
    assert d["footer"] and d["footer"].startswith("NEXT")
    by_first_line = {}
    for c in d["checks"]:
        by_first_line.setdefault((c["level"], c["message"].split("\n", 1)[0]), []).append(c["message"])
    lines = t_out.split("\n")
    heads = [i for i, ln in enumerate(lines) if re.match(r"(FAIL|WARN) +\S", ln)]
    assert any(lines[i].startswith("FAIL") for i in heads)
    for i in heads:
        lvl, msg = lines[i].split(None, 1)
        cont = []
        for ln in lines[i + 1:]:                       # continuation lines are indented
            if not ln.startswith((" ", "\t")) or not ln.strip():
                break
            cont.append(ln.strip())
        assert (lvl, msg) in by_first_line, lines[i]
        assert any(all(part in full for part in cont) for full in by_first_line[(lvl, msg)]), (lines[i], cont)
    assert any(c["level"] == "FAIL" and c["check"] == "placeholders" for c in d["checks"])


def test_fill_range_and_measure_are_reported(monkeypatch, capsys):
    """Mutation: `max(fills)` -> `min(fills)` gives 40, not 90."""
    def fake(argv):
        print("INFO  fill: p1.png: ink from 4% to 40%")
        print("INFO  fill: p2.png: ink from 4% to 90%")
        return 0, None
    monkeypatch.setattr(cli, "_dispatch", fake)
    _, _, out, _ = _run(monkeypatch, capsys, "x.typ", "2", "10", "95", "--json")
    assert json.loads(out)["fill"] == {"min": 10, "max": 95, "measured": 90}


@pytest.mark.parametrize("mode", jsonout._UNSUPPORTED)
def test_every_unsupported_mode_is_json_with_exit_2(monkeypatch, capsys, mode):
    rc, _, out, err = _run(monkeypatch, capsys, mode, "x", "--json")
    d = json.loads(out)
    assert rc == 2 and d["verdict"] == "ERROR" and d["exit_code"] == 2 and mode in d["error"] and mode in err


def test_usage_error_is_json_with_exit_2(monkeypatch, capsys):
    rc, _, out, err = _run(monkeypatch, capsys, "--json")
    d = json.loads(out)
    assert rc == 2 and d["verdict"] == "ERROR" and d["exit_code"] == 2 and d["error"] and err.strip()


def test_gate_crash_is_error_exit_2_with_captured_output_kept(monkeypatch, capsys):
    """Mutation: dropping the `except Exception` leaks the traceback (no JSON); not writing the buffers loses 'half-done'."""
    def boom(argv):
        print("half-done stdout")
        print("half-done stderr", file=sys.stderr)
        raise PermissionError(13, "nope")
    monkeypatch.setattr(cli, "_dispatch", boom)
    rc, footer, out, err = _run(monkeypatch, capsys, TEMPLATE, "1", "--json")
    d = json.loads(out)
    assert out.count("\n") == 1 and rc == 2 and footer is None
    assert d["verdict"] == "ERROR" and d["exit_code"] == 2 and d["error"].startswith("PermissionError:")
    assert "half-done stdout" in err and "half-done stderr" in err


def test_dumped_cv_text_is_never_a_check(monkeypatch, capsys):
    """Mutation: parsing lines after the extraction marker with the loose `_LINE` turns the headings into checks."""
    def fake(argv):
        print("OK    pages: 1")
        print("──── extraction (check reading order) ────")
        for ln in ("INFO SYSTEMS", "FAIL SAFE", "OK Computer", "WARN LABEL", "PASS THROUGH"):
            print(ln)
        print("WARN  review record incomplete")
        print("PASS (x) all mechanical checks")
        return 0, None
    monkeypatch.setattr(cli, "_dispatch", fake)
    _, _, out, err = _run(monkeypatch, capsys, "x.typ", "1", "--json")
    d = json.loads(out)
    assert [c["message"] for c in d["checks"]] == ["pages: 1", "review record incomplete"]
    assert d["summary"] == "PASS (x) all mechanical checks"
    assert "INFO SYSTEMS" in err and "FAIL SAFE" in err


def test_doctor_failure_is_fail_exit_1(monkeypatch, capsys):
    """Mutation: treating SystemExit(1) as a usage error would give ERROR/2."""
    monkeypatch.setattr(cli, "preflight", lambda: (False, True, "none"))
    rc, _, out, _ = _run(monkeypatch, capsys, "--doctor", "--json")
    d = json.loads(out)
    assert rc == 1 and d["tool"] == "doctor" and d["verdict"] == "FAIL" and d["exit_code"] == 1


def test_doctor_supports_json(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:      # --doctor ends in sys.exit in text mode; --json returns instead
        _run(monkeypatch, capsys, "--doctor")
    capsys.readouterr()                         # the text-mode lines printed before it exited
    rc, _, out, _ = _run(monkeypatch, capsys, "--doctor", "--json")
    d = json.loads(out)
    assert rc == exc.value.code and d["tool"] == "doctor" and d["exit_code"] == rc and d["checks"]
