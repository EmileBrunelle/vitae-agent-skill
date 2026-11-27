"""Every subprocess the skill spawns has a wall-clock bound; a timeout is a clean gate FAIL naming tool and limit.

The tools are fake executables first on PATH that sleep far longer than the patched limit (8 s against 1 s), so
a missing bound shows as a wrong elapsed time instead of a hung run.
"""
import ast
import time
from pathlib import Path

import pytest
from _paths import SCRIPTS
from vitae.core import env, proc
from vitae.verify import pdf

LIMIT = 1
SLEEP = 8       # how long a fake tool runs: well past LIMIT, short enough that a missing bound fails fast
SLACK = 4       # scheduling noise allowed on top of LIMIT; SLEEP - SLACK stays above LIMIT + SLACK


def _fake_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, body: str = "") -> None:
    """`name` on PATH: runs `body` (shell) first, then sleeps. `exec` so the sleep is the process the bound kills."""
    d = tmp_path / "bin"
    d.mkdir(exist_ok=True)
    exe = d / name
    exe.write_text(f"#!/bin/sh\n{body}\nexec sleep {SLEEP}\n", encoding="utf-8")
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", f"{d}:/usr/bin:/bin")


def _is_bounded(elapsed: float) -> bool:
    return LIMIT <= elapsed < LIMIT + SLACK


def test_run_kills_a_hung_tool_and_names_tool_and_limit(tmp_path, monkeypatch):
    _fake_tool(tmp_path, monkeypatch, "slowtool")
    t0 = time.monotonic()
    with pytest.raises(proc.ToolTimeout) as ei:
        proc.run(["slowtool"], LIMIT)
    assert _is_bounded(time.monotonic() - t0)
    assert "slowtool timed out after 1 s" in str(ei.value)


def test_run_keeps_a_fast_failing_tool_as_a_result(tmp_path, monkeypatch):
    d = tmp_path / "bin"
    d.mkdir()
    (d / "failing").write_text("#!/bin/sh\necho oops >&2\nexit 3\n", encoding="utf-8")
    (d / "failing").chmod(0o755)
    monkeypatch.setenv("PATH", f"{d}:/usr/bin:/bin")
    r = proc.run(["failing"], LIMIT)
    assert (r.returncode, r.stderr.strip()) == (3, "oops")
    with pytest.raises(FileNotFoundError):
        proc.run(["no-such-tool-xyz"], LIMIT)       # a missing tool stays an OSError, not a timeout


def test_typst_compile_timeout_is_a_compile_fail_with_tool_and_limit(tmp_path, monkeypatch, fresh_typst_probes):
    _fake_tool(tmp_path, monkeypatch, "typst", 'if [ "$1" = "--version" ]; then echo "typst 0.15.2"; exit 0; fi')
    monkeypatch.setattr(env, "_typst_py_probe", lambda: env.TypstPyProbe(None, "", "", False))   # the CLI route only
    monkeypatch.setattr(proc, "TYPST_S", LIMIT)
    src = tmp_path / "cv.typ"
    src.write_text("#set page()\nhello\n", encoding="utf-8")
    t0 = time.monotonic()
    ok, msg = pdf.compile_pdf(str(src), str(tmp_path / "cv.pdf"))
    assert _is_bounded(time.monotonic() - t0)
    assert not ok and "typst compile timed out after 1 s" in msg
    assert pdf.compile_failure_messages(msg) == [f"compile failed: {msg}"]      # the gate prints it as a FAIL line


def test_poppler_timeout_reaches_the_entry_point_as_one_fail_line(tmp_path, monkeypatch, capsys):
    _fake_tool(tmp_path, monkeypatch, "pdfinfo")
    monkeypatch.setattr(proc, "POPPLER_S", LIMIT)
    t0 = time.monotonic()
    with pytest.raises(SystemExit) as ei:
        proc.guarded(lambda: pdf.count_pages(str(tmp_path / "x.pdf"), "poppler"))
    assert _is_bounded(time.monotonic() - t0)
    assert ei.value.code == 1
    out = capsys.readouterr()
    assert len(out.out.splitlines()) == 1
    assert out.out.startswith("FAIL  pdfinfo timed out after 1 s") and "Traceback" not in out.err


def test_poppler_bbox_timeout_means_no_boxes_not_a_crash(tmp_path, monkeypatch):
    _fake_tool(tmp_path, monkeypatch, "pdftotext")
    monkeypatch.setattr(proc, "POPPLER_S", LIMIT)
    monkeypatch.setattr(pdf, "pdf_backend", lambda: "poppler")
    t0 = time.monotonic()
    assert pdf.bbox_pages(str(tmp_path / "x.pdf")) is None
    assert _is_bounded(time.monotonic() - t0)


def test_env_version_probe_timeout_reads_as_unknown(tmp_path, monkeypatch, fresh_typst_probes):
    _fake_tool(tmp_path, monkeypatch, "typst")
    monkeypatch.setattr(proc, "PROBE_S", LIMIT)
    t0 = time.monotonic()
    assert env._cli_version() == "?"
    assert _is_bounded(time.monotonic() - t0)


def test_limits_are_ordered_by_what_they_wrap():
    assert 0 < proc.PROBE_S < proc.POPPLER_S < proc.TYPST_S
    assert proc.RERUN_S > proc.TYPST_S      # the verify.py re-run contains a typst compile


# ---- no spawn outside proc.py
_SPAWNERS = {"run", "Popen", "check_output", "check_call", "call", "getoutput", "getstatusoutput"}


def _unbounded_spawns(source: str) -> list[int]:
    """Line numbers of subprocess spawns (`subprocess.X(...)`, `X(...)` imported from it) and `os.system`/`os.popen`."""
    tree = ast.parse(source)
    imported = {a.asname or a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module == "subprocess"
                for a in n.names if a.name in _SPAWNERS}
    lines = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            if (f.value.id == "subprocess" and f.attr in _SPAWNERS) or (f.value.id == "os" and f.attr in {"system", "popen"}):
                lines.append(n.lineno)
        elif isinstance(f, ast.Name) and f.id in imported:
            lines.append(n.lineno)
    return lines


def test_no_subprocess_is_spawned_outside_proc_py():
    offenders = [f"{p.relative_to(SCRIPTS)}:{ln}" for p in sorted(SCRIPTS.rglob("*.py")) if p.name != "proc.py"
                 for ln in _unbounded_spawns(p.read_text(encoding="utf-8"))]
    assert offenders == [], f"spawn through vitae.core.proc.run (it carries the wall-clock bound): {offenders}"


def test_the_spawn_detector_sees_every_shape():
    src = ("import subprocess, os\nfrom subprocess import Popen as P, run\n"
           "subprocess.run(['a'])\nsubprocess.check_output(['a'])\nP(['a'])\nrun(['a'])\nos.system('a')\nos.popen('a')\n"
           "subprocess.SubprocessError\nsubprocess.TimeoutExpired\n")
    assert _unbounded_spawns(src) == [3, 4, 5, 6, 7, 8]
