"""Deterministic work counts for the complexity tests: Python line events executed in chosen source files, and the
growth check over doubling sizes. No wall-clock measurement, so a loaded runner cannot flip a result."""
import sys
from collections.abc import Callable
from types import FrameType
from typing import Protocol, TypeVar


class TraceFunction(Protocol):
    def __call__(self, frame: FrameType, event: str, arg: object, /) -> "TraceFunction | None": ...


_T = TypeVar("_T")


def line_events(files: frozenset[str], call: Callable[[], _T]) -> tuple[int, _T]:
    """Run `call` and count the Python line events executed in the source `files` (all their frames, comprehensions and
    lambdas included): a deterministic measure of the Python-level work, immune to runner load. It does not see C-level
    work (`str.find`, `list.count`, a regex): see `_scan_str.ScanStr` for those."""
    events = 0

    def local(frame: FrameType, event: str, arg: object) -> TraceFunction | None:
        nonlocal events
        if event == "line":
            events += 1
        return local

    def tracer(frame: FrameType, event: str, arg: object) -> TraceFunction | None:
        return local if event == "call" and frame.f_code.co_filename in files else None

    previous = sys.gettrace()
    sys.settrace(tracer)
    try:
        result = call()
    finally:
        sys.settrace(previous)
    return events, result


def assert_linear(measure: Callable[[int], int], base: int, bound: float = 2.2) -> None:
    """The work at `base`, 2 x `base` and 4 x `base` grows at most `bound` x per doubling (a quadratic one: 4 x)."""
    w1, w2, w4 = (measure(base * k) for k in (1, 2, 4))
    assert w1 > 0                    # the measure saw some work: the ratios are not vacuous
    assert w2 / w1 <= bound
    assert w4 / w2 <= bound
