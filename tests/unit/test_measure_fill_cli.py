"""measure_fill.py CLI: --help/-h print usage and exit 0; no argument is a usage error (stderr, exit 2)."""
import subprocess
import sys

import pytest
from _paths import ROOT

SCRIPT = ROOT / "scripts" / "measure_fill.py"


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help_prints_usage_and_exits_zero(flag):
    r = run(flag)
    assert r.returncode == 0 and "Usage:" in r.stdout and r.stderr == ""


def test_no_argument_is_usage_error_on_stderr():
    r = run()
    assert r.returncode == 2 and "Usage:" in r.stderr and r.stdout == ""


def test_image_path_is_still_measured(tmp_path):
    from PIL import Image
    png = tmp_path / "p.png"
    Image.new("L", (50, 100), 255).save(png)
    r = run(str(png))
    assert r.returncode == 0 and "blank page" in r.stdout
