"""Subprocess helpers for the tests that drive scripts/pick_design.py end to end."""
import subprocess
import sys

from _paths import PICK_DESIGN


def run(*args):
    """pick_design.py with the given arguments (no font check); returns the CompletedProcess."""
    return subprocess.run([sys.executable, str(PICK_DESIGN), "--no-font-check", *args],
                          capture_output=True, text=True, check=False)


def init(folder, name, field, *extra):
    return run("--name", name, "--field", field, "--market", "ca", "--init", str(folder), *extra)


def report(name, field, *extra):
    return run("--name", name, "--field", field, *extra).stdout


def family(name, field):
    return next(ln.split(":")[1].split()[0] for ln in report(name, field).splitlines()
                if ln.startswith("design family"))
