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


def test_typst_compile_timeout_propagates_with_tool_and_limit(tmp_path, monkeypatch, fresh_typst_probes):
    _fake_tool(tmp_path, monkeypatch, "typst", 'if [ "$1" = "--version" ]; then echo "typst 0.15.2"; exit 0; fi')
    monkeypatch.setattr(env, "_typst_py_probe", lambda: env.TypstPyProbe(None, "", "", False))   # the CLI route only
    monkeypatch.setattr(proc, "TYPST_S", LIMIT)
    src = tmp_path / "cv.typ"
    src.write_text("#set page()\nhello\n", encoding="utf-8")
    t0 = time.monotonic()
    with pytest.raises(proc.ToolTimeout, match="typst compile timed out after 1 s"):
        pdf.compile_pdf(str(src), str(tmp_path / "cv.pdf"))      # not a "compile failed" result: `guarded` prints the FAIL
    assert _is_bounded(time.monotonic() - t0)


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


# a hung `pdftotext -bbox` is covered by test_timeout_is_fail.py::test_hung_pdftotext_fails_the_hidden_text_gate


def test_env_version_probe_timeout_is_marked_not_unknown(tmp_path, monkeypatch, fresh_typst_probes):
    _fake_tool(tmp_path, monkeypatch, "typst")
    monkeypatch.setattr(proc, "PROBE_S", LIMIT)
    t0 = time.monotonic()
    assert env._cli_version() == env.CLI_TIMED_OUT       # not "?": the doctor FAILs and the route skips this CLI
    assert _is_bounded(time.monotonic() - t0)


def test_rerun_limit_covers_what_it_wraps():
    """`verify.py --all` re-runs verify.py per file, and that child runs a typst compile then poppler tools in sequence:
    a RERUN_S not above their sum would cut a healthy run that merely used both limits' worth of time."""
    assert proc.RERUN_S > proc.TYPST_S + proc.POPPLER_S


# ---- no spawn outside proc.py
_SPAWNERS = {"run", "Popen", "check_output", "check_call", "call", "getoutput", "getstatusoutput"}
_OS_SPAWNERS = {"system", "popen"}


def _is_os_spawner(name: str) -> bool:
    return name in _OS_SPAWNERS or name.startswith(("spawn", "exec"))


def _bindings(tree: ast.AST) -> tuple[set[str], set[str], set[str]]:
    """(names bound to the subprocess module, to the os module, to a spawner function) by the imports of `tree`."""
    sub_mods, os_mods, funcs = {"subprocess"}, {"os"}, set[str]()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                {"subprocess": sub_mods, "os": os_mods}.get(a.name, set()).add(a.asname or a.name)
        elif isinstance(n, ast.ImportFrom) and n.module in ("subprocess", "os"):
            for a in n.names:
                if n.module == "subprocess" and a.name == "*":
                    funcs.update(_SPAWNERS)
                elif (a.name in _SPAWNERS) if n.module == "subprocess" else _is_os_spawner(a.name):
                    funcs.add(a.asname or a.name)
    return sub_mods, os_mods, funcs


def _unbounded_spawns(source: str) -> list[int]:
    """Line numbers of spawns: `subprocess.X(...)` (also through `import subprocess as sp`), `X(...)` imported from it
    (also renamed, or via `from subprocess import *`), and `os.system` / `os.popen` / `os.spawn*` / `os.exec*` (same
    aliasing shapes)."""
    tree = ast.parse(source)
    sub_mods, os_mods, funcs = _bindings(tree)
    lines = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            if (f.value.id in sub_mods and f.attr in _SPAWNERS) or (f.value.id in os_mods and _is_os_spawner(f.attr)):
                lines.append(n.lineno)
        elif isinstance(f, ast.Name) and f.id in funcs:
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


@pytest.mark.parametrize("src, lines", [
    ("import subprocess as sp\nsp.run(['a'])\nsp.Popen(['a'])\nsp.TimeoutExpired\n", [2, 3]),
    ("from subprocess import run\nrun(['a'])\n", [2]),
    ("from subprocess import Popen\nPopen(['a'])\n", [2]),
    ("from subprocess import *\ncheck_output(['a'])\nPopen(['a'])\n", [2, 3]),
    ("import os\nos.spawnv(0, 'a', [])\nos.execv('a', [])\nos.execvp('a', [])\nos.getcwd()\n", [2, 3, 4]),
    ("import os as o\no.system('a')\no.spawnlp(0, 'a')\no.path.join('a')\n", [2, 3]),
    ("from os import system, execv as ex, getcwd\nsystem('a')\nex('a', [])\ngetcwd()\n", [2, 3]),
    ("import shlex\nshlex.split('a')\nrun = 3\nrun\n", []),      # no spawn: nothing flagged
], ids=["alias", "from-run", "from-Popen", "star", "os-spawn-exec", "os-alias", "from-os", "clean"])
def test_the_spawn_detector_sees_aliases_star_imports_and_os_spawns(src, lines):
    assert _unbounded_spawns(src) == lines
