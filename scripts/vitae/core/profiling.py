"""Maintainer-only `--profile` flag of the two gate entry points: cProfile around the whole run, the 15 most
expensive functions by cumulative time on stderr (stdout keeps only the PASS/FAIL lines), exit code unchanged."""
from __future__ import annotations

import cProfile
import pstats
import sys
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")
FLAG = "--profile"
TOP = 15


def take_flag() -> bool:
    """True when `--profile` is on the command line; it is removed from sys.argv so the mode parsers never see it."""
    if FLAG not in sys.argv[1:]:
        return False
    sys.argv = [a for a in sys.argv if a != FLAG]
    return True


def run(fn: Callable[[], T], enabled: bool) -> T:
    """fn(), profiled when `enabled`. The table is printed even when fn exits through sys.exit, then that exit goes on."""
    if not enabled:
        return fn()
    prof = cProfile.Profile()
    try:
        return prof.runcall(fn)
    finally:
        print(f"\n--profile: top {TOP} functions by cumulative time", file=sys.stderr)
        pstats.Stats(prof, stream=sys.stderr).sort_stats("cumulative").print_stats(TOP)
