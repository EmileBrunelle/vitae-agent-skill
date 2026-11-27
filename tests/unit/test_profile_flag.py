"""`--profile` (maintainers): the 15-function cumulative-time table goes to stderr, stdout and the exit code are
those of the same run without the flag."""
import subprocess
import sys
from pathlib import Path

import pytest
from _paths import ROOT

TABLE = "function calls"
RUNS = [      # (script, args, whether the plain run exits non-zero: the equality of exit codes is then not "0 == 0")
    pytest.param("verify.py", ["--doctor"], False, id="verify-doctor"),
    pytest.param("verify.py", ["no-such-file.typ", "1"], True, id="verify-failing-gate"),
    pytest.param("verify_academic.py", ["--doctor"], False, id="academic-doctor"),
    pytest.param("verify_academic.py", ["no-such-file.typ", "no-such.toml"], True, id="academic-failing-gate"),
]


def run(script: str, args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / script), *args],
                          capture_output=True, text=True, cwd=cwd)


@pytest.mark.parametrize(("script", "args", "fails"), RUNS)
def test_profile_prints_the_table_on_stderr_and_changes_nothing_else(script: str, args: list[str], fails: bool,
                                                                     tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()                                  # a gate may drop files in its cwd: one directory per run
    plain = run(script, args, tmp_path / "a")
    profiled = run(script, ["--profile", *args], tmp_path / "b")

    assert TABLE not in plain.stderr                          # control: the table comes from the flag
    assert TABLE in profiled.stderr and "cumulative" in profiled.stderr and "ncalls" in profiled.stderr
    assert TABLE not in profiled.stdout
    assert profiled.stdout.replace(str(tmp_path / "b"), "CWD") == plain.stdout.replace(str(tmp_path / "a"), "CWD")
    assert profiled.returncode == plain.returncode
    assert (plain.returncode != 0) or not fails        # control: a failing gate keeps failing under the flag
    assert len([ln for ln in profiled.stderr.splitlines() if "{" in ln or ".py:" in ln]) >= 5

