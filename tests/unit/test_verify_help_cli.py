"""verify*.py CLI: --help/-h print usage on stdout and exit 0 (also with --json); a bad invocation prints it on stderr, exit 2."""
import subprocess
import sys

import pytest
from _paths import ROOT

SCRIPTS = ["verify.py", "verify_academic.py", "verify_letter.py"]


def run(script, *args):
    return subprocess.run([sys.executable, str(ROOT / "scripts" / script), *args], capture_output=True, text=True, check=False)


@pytest.mark.parametrize("script", SCRIPTS)
@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help_prints_usage_and_exits_zero(script, flag):
    r = run(script, flag)
    assert r.returncode == 0 and r.stdout.startswith("usage:") and r.stderr == ""


def test_help_with_json_prints_usage_not_a_json_error():
    r = run("verify.py", "--json", "--help")
    assert r.returncode == 0 and r.stdout.startswith("usage:") and r.stderr == ""


@pytest.mark.parametrize("script", SCRIPTS)
def test_bad_invocation_is_usage_error_on_stderr(script):
    r = run(script)
    assert r.returncode == 2 and r.stderr.startswith("usage:") and r.stdout == ""
