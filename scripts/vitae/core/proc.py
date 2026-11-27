"""The one place a subprocess is spawned: every call has a wall-clock bound, and a timeout is a typed failure.

A hung `typst` or poppler tool must end as a clean gate FAIL (one message naming the tool and the limit), never as a
hang and never as a traceback. `run` wraps `subprocess.run` with the bound and raises `ToolTimeout` (a
`subprocess.SubprocessError`, so a site that already catches that, or `OSError`-style failures next to it, folds the
timeout into its own failure path). A site with no failure path of its own lets it reach `guarded`, which the entry
points wrap: it prints `FAIL  <message>` and exits 1. A test (tests/unit/test_subprocess_timeouts.py) forbids any
other `subprocess.run` / `Popen` / `check_output` call under scripts/, so a new site cannot skip the bound. On a timeout
the whole process tree is killed (POSIX: the child leads its own process group). The typst-py route runs in-process and
is not bounded by these limits.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
from collections.abc import Callable, Sequence
from typing import TypeVar

T = TypeVar("T")

TYPST_S = 300           # typst compile / query / eval: a large CV with many fonts compiles in seconds; this is the hang bound
POPPLER_S = 120         # pdfinfo, pdftotext, pdfdetach, pdftoppm on one CV (a 300 dpi page raster is the slowest)
PROBE_S = 20            # version / font-list probes (`typst --version`, `typst fonts`)
# verify.py re-run by `verify.py --all`: its own children run one after another (one compile, a few queries,
# poppler passes), each bounded above; this covers a full run with margin, so only a hung child is cut.
RERUN_S = 3 * TYPST_S


class ToolTimeout(subprocess.SubprocessError):
    """A spawned tool ran past its wall-clock limit and was killed. `str()` is the gate message."""

    def __init__(self, name: str, limit: float) -> None:
        super().__init__(f"{name} timed out after {limit:g} s (killed; the tool hung or the input is pathological)")
        self.tool, self.limit = name, limit


def run(argv: Sequence[str], limit: float, *, name: str | None = None,
        capture: bool = True) -> subprocess.CompletedProcess[str]:
    """`subprocess.run(argv)` with text output, never raising on a non-zero exit, killed after `limit` seconds.
    `name` is what a timeout message calls the tool (default: the program's base name). `capture=False` lets the
    child write to our stdout/stderr. Raises ToolTimeout on the limit; OSError (tool missing) goes through unchanged."""
    pipe = subprocess.PIPE if capture else None
    posix = os.name != "nt"
    stdout: str | None
    stderr: str | None
    with subprocess.Popen(list(argv), stdout=pipe, stderr=pipe, text=True, start_new_session=posix) as child:
        try:
            stdout, stderr = child.communicate(timeout=limit)
        except subprocess.TimeoutExpired:
            _kill_tree(child)
            child.communicate()
            raise ToolTimeout(name or os.path.basename(argv[0]), limit) from None
        except BaseException:
            _kill_tree(child)
            raise
    return subprocess.CompletedProcess(list(argv), child.returncode, stdout, stderr)


def _kill_tree(child: subprocess.Popen[str]) -> None:
    """SIGKILL the child's whole process group (it leads its own session, so a grandchild such as the typst a verify.py
    re-run spawned goes with it). Windows has no process groups here: a plain kill of the child, grandchildren may stay."""
    if os.name == "nt":
        child.kill()
        return
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def guarded(fn: Callable[[], T]) -> T:
    """fn(), with a ToolTimeout anywhere inside turned into `FAIL  <message>` on stdout and exit 1."""
    try:
        return fn()
    except ToolTimeout as e:
        print(f"FAIL  {e}", flush=True)
        sys.exit(1)
