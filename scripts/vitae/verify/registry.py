"""The gate contract: every check is a `check(ctx) -> list[Finding]`, run in a fixed explicit order.

Functions and frozen dataclasses only; the ordered tuples live in vitae/verify/gates.py (no import-time
self-registration), and `run_gates` is the one place that prints a gate line.
"""
from __future__ import annotations

from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Protocol

from vitae.core.context import VerifyContext
from vitae.core.level import Finding, Level


class Gate(Protocol):
    """One gate of the per-CV run. `applies` is the condition under which it runs at all (the typst
    query is available, a facts file was given); `check` returns every line it prints."""
    @property
    def name(self) -> str: ...

    def applies(self, ctx: VerifyContext) -> bool: ...

    def check(self, ctx: VerifyContext) -> list[Finding]: ...


def always(ctx: VerifyContext) -> bool:
    return True


@dataclass(frozen=True)
class FnGate:
    """A gate made of two plain functions."""
    name: str
    run: Callable[[VerifyContext], list[Finding]]
    when: Callable[[VerifyContext], bool] = always

    def applies(self, ctx: VerifyContext) -> bool:
        return self.when(ctx)

    def check(self, ctx: VerifyContext) -> list[Finding]:
        return self.run(ctx)


_sink: list[tuple[str, Level, str]] | None = None
_dump_lines: int | None = None


@contextmanager
def recording(sink: list[tuple[str, Level, str]]) -> Generator[None, None, None]:
    """While active, `run_gates` also appends (gate name, level, message) to `sink`: what `--json` reads."""
    global _sink, _dump_lines
    _sink, _dump_lines = sink, None
    try:
        yield
    finally:
        _sink = None


def note_extraction(text: str) -> None:
    """The caller is about to print `text` (the PDF extraction): remember how many lines it takes, so `--json` can
    tell where the dump ends (it has no end marker) and read the report lines after it."""
    global _dump_lines
    if _sink is not None:
        _dump_lines = len(text.split("\n"))


def extraction_lines() -> int | None:
    """Line count noted by `note_extraction` in the last `recording` block, None if there was none."""
    return _dump_lines


def run_gates(gates: Sequence[Gate], ctx: VerifyContext) -> int:
    """Print every applicable gate's lines in order; return 1 if any is a FAIL, else 0."""
    fail = 0
    for gate in gates:
        if not gate.applies(ctx):
            continue
        for lvl, msg in gate.check(ctx):
            print(f"{lvl:<5} {msg}")
            if _sink is not None:
                _sink.append((gate.name, lvl, msg))
            fail |= lvl == Level.FAIL
    return fail
