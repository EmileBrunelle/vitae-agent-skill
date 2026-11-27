"""Structural guard (behavioural, table-driven): with EVERY `proc.run` raising ToolTimeout, each entry point must end as
a FAIL naming the tool and its limit (`timed out after`), exit 1, no traceback. A new `except Exception` / `except
SubprocessError` between a tool call and the entry point that swallows the timeout turns a row of this table red.
(Chosen over an AST scan: transitive call detection through wrappers is fragile, the behaviour is what the contract is.)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from vitae.core import env, proc
from vitae.design import cli as design_cli
from vitae.verify import cli as verify_cli
from vitae.verify import letter as letter_cli
from vitae.verify import pdf
from vitae.verify.academic import cli as academic_cli


def _raise(argv, limit, *, name=None, capture=True):
    raise proc.ToolTimeout(name or "tool", limit)


@pytest.fixture
def hung(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fresh_typst_probes):
    monkeypatch.setattr(proc, "run", _raise)
    # tool PRESENCE is faked too: the timeout path must be reached on a host with no typst / poppler on PATH
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: f"/fake/bin/{name}")
    monkeypatch.setattr(pdf, "pdf_backend", lambda: "poppler")
    monkeypatch.setattr(verify_cli, "pdf_backend", lambda: "poppler")
    monkeypatch.setattr(env, "_typst_py_probe", lambda: env.TypstPyProbe(None, "", "", False))
    typ = tmp_path / "cv.typ"
    typ.write_text("// plain\nhello\n", encoding="utf-8")
    ac = tmp_path / "ac.typ"
    ac.write_text("// vitae-academic: sections=1 entries=1\nhello\n", encoding="utf-8")
    data = tmp_path / "data.toml"
    data.write_text("", encoding="utf-8")
    pdf_path = tmp_path / "cv.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    return {"typ": str(typ), "ac": str(ac), "pdf": str(pdf_path), "data": str(data)}



ROWS = {
    "verify default": (verify_cli.run_cli, lambda f: ["verify.py", f["typ"], "1"]),
    "verify --gates": (verify_cli.run_cli, lambda f: ["verify.py", "--gates", f["typ"], f["pdf"]]),
    "verify --text": (verify_cli.run_cli, lambda f: ["verify.py", "--text", f["pdf"]]),
    "verify --render": (verify_cli.run_cli, lambda f: ["verify.py", "--render", f["pdf"]]),
    "verify --render --crops": (verify_cli.run_cli, lambda f: ["verify.py", "--render", f["pdf"], "--crops"]),
    "verify --tune": (verify_cli.run_cli, lambda f: ["verify.py", "--tune", f["typ"], "1", "94", "96"]),
    "verify --doctor": (verify_cli.run_cli, lambda f: ["verify.py", "--doctor"]),
    "verify_academic": (academic_cli.run, lambda f: ["verify_academic.py", f["ac"], f["data"]]),
    "verify_letter": (letter_cli.main, lambda f: ["verify_letter.py", f["typ"], "Acme", "Engineer"]),
}


@pytest.mark.parametrize("row", sorted(ROWS))
def test_every_entry_point_turns_a_tool_timeout_into_a_fail(row, hung, monkeypatch, capsys):
    entry, argv = ROWS[row]
    monkeypatch.setattr(sys, "argv", argv(hung))
    with pytest.raises(SystemExit) as ei:
        entry()
    out = capsys.readouterr()
    assert ei.value.code == 1, (row, out)
    assert "timed out after" in out.out + out.err, (row, out)
    assert "Traceback" not in out.err
    assert not isinstance(ei.value.code, str)
    assert subprocess.SubprocessError  # the timeout is a SubprocessError: the class of handler this guards against


def test_pick_design_turns_a_hung_typst_fonts_into_a_fail(hung, monkeypatch, capsys):
    """The CLI answers `--version` and hangs on `typst fonts`: the draw must not go on as "fonts unverified"."""
    def run(argv, limit, *, name=None, capture=True):
        if list(argv)[1:] == ["--version"]:
            return subprocess.CompletedProcess(list(argv), 0, "typst 0.15.2\n", "")
        raise proc.ToolTimeout(name or "tool", limit)

    monkeypatch.setattr(proc, "run", run)
    monkeypatch.setattr(sys, "argv", ["pick_design.py", "--name", "A B", "--field", "software"])
    with pytest.raises(SystemExit) as ei:
        design_cli.main()
    out = capsys.readouterr()
    assert ei.value.code == 1 and "typst fonts timed out after" in out.out, out
