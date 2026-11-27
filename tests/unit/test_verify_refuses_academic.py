"""The standard one-file gate refuses an academic CV (exit 2, one redirect line) instead of judging a genre it is not
calibrated for. Mutation-checked: removing `refuse_academic` from `check_cv` or from `--tune` fails these tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from vitae.verify import cli as verify_cli

ACADEMIC = "// vitae-academic: v1\n#set page(paper: \"a4\")\nHello\n"
RESUME = "#set page(paper: \"a4\")\nHello\n"


def _run(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> tuple[int, str | None]:
    monkeypatch.setattr(sys, "argv", ["verify.py", *argv])
    return verify_cli.main()


@pytest.fixture(autouse=True)
def no_compile(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a: object, **k: object) -> None:
        raise AssertionError("the gate started work on an academic CV")
    monkeypatch.setattr("vitae.verify.cv.preflight", boom, raising=False)
    monkeypatch.setattr("vitae.verify.tune.tune", boom, raising=False)


@pytest.mark.parametrize("argv", [["{f}", "2"], ["--tune", "{f}", "2", "90", "95"]], ids=["gate", "tune"])
def test_text_mode_redirects_with_exit_2(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
                                         tmp_path: Path, argv: list[str]) -> None:
    f = tmp_path / "cv.typ"
    f.write_text(ACADEMIC, encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        _run(monkeypatch, [a.replace("{f}", str(f)) for a in argv])
    cap = capsys.readouterr()
    assert e.value.code == 2
    assert cap.out == ""
    assert len(cap.err.strip().splitlines()) == 1
    assert f"{f}: academic CV" in cap.err and "scripts/verify_academic.py" in cap.err


def test_json_mode_emits_error_object(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
                                      tmp_path: Path) -> None:
    f = tmp_path / "cv.typ"
    f.write_text(ACADEMIC, encoding="utf-8")
    rc, footer = _run(monkeypatch, [str(f), "2", "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert (rc, footer) == (2, None)
    assert obj["verdict"] == "ERROR" and obj["exit_code"] == 2
    assert "academic CV" in obj["error"] and "verify_academic.py" in obj["error"]


def test_normal_resume_is_not_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from vitae.verify.cv import refuse_academic
    f = tmp_path / "cv.typ"
    f.write_text(RESUME, encoding="utf-8")
    refuse_academic(str(f))     # returns: no SystemExit
