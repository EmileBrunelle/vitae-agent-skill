"""No symlink in the repo (claude.ai rejects zips with them; Windows checkouts break them)."""
from __future__ import annotations

import os
import subprocess

from harness import ROOT

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", "mutants"}


def _tracked_or_walked() -> list[str]:
    """Tracked files in a git checkout (untracked and gitignored dirs such as .venv do not count), else a filtered walk."""
    p = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, text=True)
    if p.returncode == 0 and p.stdout:
        return [f for f in p.stdout.split("\0") if f]
    found: list[str] = []
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        found += [os.path.relpath(os.path.join(d, n), ROOT) for n in dirs + files]
    return found


def test_no_symlinks() -> None:
    links = [f for f in _tracked_or_walked() if os.path.islink(ROOT / f)]
    assert not links, f"symlinks in the repo: {links}"
