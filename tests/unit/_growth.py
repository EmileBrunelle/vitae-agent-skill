"""Growth-ratio timing for the `slow` complexity tests: time at size N and 2N, take the best of a few repetitions of each
(a noisy runner slows both runs alternately, a one-off stall hits one repetition), and compare. A linear function gives ~2, a
quadratic one ~4, so a bound of 3 separates them at any speed of the machine."""
from __future__ import annotations

import time
from collections.abc import Callable

GROWTH_BOUND = 3.0


def _timed(call: Callable[[], object]) -> float:
    start = time.perf_counter()
    call()
    return time.perf_counter() - start


def best_time(call: Callable[[], object], repeats: int = 5) -> float:
    """Best wall time of `repeats` calls: an absolute bound on it holds on a noisy runner (a stall hits one repetition)
    and complements the growth ratio, which cannot see a function that is linear but a constant factor too slow."""
    return min(_timed(call) for _ in range(repeats))


def growth_ratio(prepare: Callable[[int], Callable[[], object]], n: int, repeats: int = 3) -> float:
    """best time of `prepare(2 * n)()` over best time of `prepare(n)()`; `prepare(size)` builds the input (untimed)
    and returns the call to time. The two sizes alternate in each repetition, so a burst of load slows both."""
    small, large = prepare(n), prepare(2 * n)
    pairs = [(_timed(small), _timed(large)) for _ in range(repeats)]
    return min(t for _, t in pairs) / min(t for t, _ in pairs)
