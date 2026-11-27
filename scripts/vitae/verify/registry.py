"""The gate contract: every check is a `check(ctx) -> list[Finding]`, run in a fixed explicit order.

Functions and frozen dataclasses only; the ordered tuples live in vitae/verify/gates.py (no import-time
self-registration), and `run_gates` is the one place that prints a gate line.
"""
from __future__ import annotations

from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from vitae.core.context import VerifyContext
from vitae.core.level import Finding, Level


def always(ctx: VerifyContext) -> bool:
    return True


@dataclass(frozen=True)
class FnGate:
    """One gate of the per-CV run, made of two plain functions: `run` returns every line it prints, `when` is the
    condition under which it runs at all (the typst query is available, a facts file was given)."""
    name: str
    run: Callable[[VerifyContext], list[Finding]]
    when: Callable[[VerifyContext], bool] = always

    def applies(self, ctx: VerifyContext) -> bool:
        return self.when(ctx)

    def check(self, ctx: VerifyContext) -> list[Finding]:
        return self.run(ctx)


@dataclass
class Recorder:
    """What one `recording` block collects: the (gate name, level, message) lines and the extraction dump length."""
    sink: list[tuple[str, Level, str]]
    dump_lines: int | None = None


_recorder: ContextVar[Recorder | None] = ContextVar("vitae_verify_recorder", default=None)


@contextmanager
def recording(sink: list[tuple[str, Level, str]]) -> Generator[Recorder, None, None]:
    """While active, `run_gates` also appends (gate name, level, message) to `sink`: what `--json` reads.
    Yields the Recorder, whose `dump_lines` is the count noted by `note_extraction` (None if there was none)."""
    rec = Recorder(sink)
    token = _recorder.set(rec)
    try:
        yield rec
    finally:
        _recorder.reset(token)


def note_extraction(text: str) -> None:
    """The caller is about to print `text` (the PDF extraction): remember how many lines it takes, so `--json` can
    tell where the dump ends (it has no end marker) and read the report lines after it."""
    rec = _recorder.get()
    if rec is not None:
        rec.dump_lines = len(text.split("\n"))


def run_gates(gates: Sequence[FnGate], ctx: VerifyContext) -> int:
    """Print every applicable gate's lines in order; return 1 if any is a FAIL, else 0."""
    fail = 0
    for gate in gates:
        if not gate.applies(ctx):
            continue
        for lvl, msg in gate.check(ctx):
            print(f"{lvl:<5} {msg}")
            rec = _recorder.get()
            if rec is not None:
                rec.sink.append((gate.name, lvl, msg))
            fail |= lvl == Level.FAIL
    return fail
