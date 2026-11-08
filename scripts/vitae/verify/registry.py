"""The gate contract: every check is a `check(ctx) -> list[Finding]`, run in a fixed explicit order.

Functions and frozen dataclasses only; the ordered tuples live in vitae/verify/gates.py (no import-time
self-registration), and `run_gates` is the one place that prints a gate line.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
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


def run_gates(gates: Sequence[Gate], ctx: VerifyContext) -> int:
    """Print every applicable gate's lines in order; return 1 if any is a FAIL, else 0."""
    fail = 0
    for gate in gates:
        if not gate.applies(ctx):
            continue
        for lvl, msg in gate.check(ctx):
            print(f"{lvl:<5} {msg}")
            fail |= lvl == Level.FAIL
    return fail
