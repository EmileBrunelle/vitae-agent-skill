"""No symlink in the repo (claude.ai rejects zips with them; Windows checkouts break them)."""
from __future__ import annotations

import os

from harness import ROOT

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", "mutants"}


def _walked() -> list[str]:
    """Every path of the working tree except SKIP_DIRS (.venv, .git, caches), untracked files included, as the old `find` saw them."""
    found: list[str] = []
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        found += [os.path.relpath(os.path.join(d, n), ROOT) for n in dirs + files]
    return found


def test_no_symlinks() -> None:
    links = [f for f in _walked() if os.path.islink(ROOT / f)]
    assert not links, f"symlinks in the repo: {links}"
