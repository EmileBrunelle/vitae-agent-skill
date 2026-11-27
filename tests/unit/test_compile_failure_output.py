"""A compile refused by the PDF standard prints Vitae's advice as its own `FAIL  vitae:` line in the letter and academic
gates, not nested inside `compile failed:`."""
import re
import sys

import pytest
import vitae.verify.academic.cli as academic_cli
import vitae.verify.academic.gate as academic_gate
import vitae.verify.letter as letter
from _paths import ROOT
from vitae.core.env import PdfCheck
from vitae.verify import pdf

TYPST_ERR = "error: PDF/UA-1 error: missing document title\n  = hint: set a title\n"
ADVICE = pdf.standard_failure_advice(TYPST_ERR)
REFUSED = f"{ADVICE}\n{TYPST_ERR}"


def _advice_lines(out: str) -> list[str]:
    return re.findall(r"^FAIL  vitae.*$", out, flags=re.MULTILINE)


def test_the_helper_splits_the_advice_from_typsts_error() -> None:
    assert pdf.compile_failure_messages(REFUSED) == [ADVICE.removeprefix("FAIL  "), f"compile failed: {TYPST_ERR}"]


def test_a_compile_failure_without_advice_is_one_message() -> None:
    """Control: a failure the standard did not cause keeps the single `compile failed:` message."""
    assert pdf.compile_failure_messages("error: file not found") == ["compile failed: error: file not found"]


def test_letter_prints_the_advice_on_its_own_line(monkeypatch: pytest.MonkeyPatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(letter, "preflight", lambda: PdfCheck(True, "x"))
    monkeypatch.setattr(letter, "ensure_icons", lambda typ: None)
    monkeypatch.setattr(pdf, "compile_pdf", lambda typ, out: (False, REFUSED))
    typ = tmp_path / "letter.typ"
    typ.write_text("x", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["verify_letter.py", str(typ), "Acme", "Dev"])
    with pytest.raises(SystemExit) as exit_info:
        letter.main()
    out = capsys.readouterr().out
    assert exit_info.value.code == 1
    assert len(_advice_lines(out)) == 1 and "compile failed: FAIL" not in out
    assert "FAIL  compile failed: error: PDF/UA-1 error: missing document title" in out


def test_academic_prints_the_advice_on_its_own_line(monkeypatch: pytest.MonkeyPatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(academic_gate, "preflight", lambda: PdfCheck(True, "pdfium"))
    monkeypatch.setattr(academic_gate.shutil, "which", lambda name: "/usr/bin/pdftotext")
    monkeypatch.setattr(pdf, "compile_pdf", lambda typ, out: (False, REFUSED))
    typ = tmp_path / "cv.typ"
    typ.write_text("x", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["verify_academic.py", str(typ), str(ROOT / "templates/academic/faits-academique.example.toml")])
    with pytest.raises(SystemExit) as exit_info:
        academic_cli.main()
    out = capsys.readouterr().out
    assert exit_info.value.code == 1
    assert len(_advice_lines(out)) == 1 and "compile failed: FAIL" not in out

