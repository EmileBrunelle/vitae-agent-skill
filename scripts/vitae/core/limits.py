"""Bounds on what a command line may ask for, checked at the CLI boundary before any heavy work.

An out-of-range option or an oversize input file ends as ONE error line on stderr and exit code 2 (argparse's
own usage-error code), before a subprocess is spawned or a file is read. Pure stdlib; no gate imports it back.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Callable
from typing import NoReturn

# --- numeric options -------------------------------------------------------------------------------------------
# --render --ppi: raster memory and time scale with ppi squared; shipped code rasterises at 90 (fill scan), HIDDEN_PPI
# 150 and 300 (crops). 10 is already unreadable; 600 (~35 Mpx per A4 page, ~100 MB RGB) is 2x the largest shipped use.
PPI_MIN, PPI_MAX = 10, 600
# PAGES positional: one compile + one raster pass per page. Shipped targets are 1-2 pages (academic CVs run to a few dozen).
PAGES_MIN, PAGES_MAX = 1, 100
# FILL_MIN / FILL_MAX positionals are a percentage of the page height.
FILL_MIN_PCT, FILL_MAX_PCT = 0, 100
# --tune LEADING_LO / LEADING_HI, in em: shipped leadings are ~0.5-0.9 em and the default search tops out near 1.3 em;
# 0.1-5 em leaves room for a font swap while keeping the bisection (step 0.005 em) to a bounded number of compiles.
LEADING_MIN, LEADING_MAX = 0.1, 5.0

# --- input file sizes ------------------------------------------------------------------------------------------
MIB = 1024 * 1024
# Largest shipped .typ: templates/lib.typ, 48 020 B. 4 MiB is ~87x that.
MAX_TYP_BYTES = 4 * MIB
# Largest shipped PDF: templates/resume.pdf, 44 569 B. 16 MiB is ~376x that.
MAX_PDF_BYTES = 16 * MIB
# Largest shipped TOML: templates/academic/academic.example.toml, 15 225 B. 1 MiB is ~69x that.
MAX_TOML_BYTES = 1 * MIB
# facts.md: a hand-written facts sheet, a few KB; no shipped example, so the TOML cap is reused (1 MiB).
MAX_FACTS_BYTES = 1 * MIB
# Page PNG read by measure_fill.py: a 90-300 ppi A4 page of mostly white is well under 1 MB; none is shipped, so 32 MiB.
MAX_PNG_BYTES = 32 * MIB


def _prog() -> str:
    return os.path.basename(sys.argv[0]) or "vitae"


def fail(message: str) -> NoReturn:
    """One error line on stderr, exit 2 (the argparse usage-error convention)."""
    print(f"{_prog()}: error: {message}", file=sys.stderr)
    sys.exit(2)


_LIMIT_MESSAGE = re.compile(r"argument \S+: (?:.* is out of range, must be |.* is not an? (?:integer|number)$)")


def is_limit_error(message: str) -> bool:
    """True when an argparse error message came from one of the validators below (not a missing-argument error)."""
    return _LIMIT_MESSAGE.match(message) is not None


def int_in(lo: int, hi: int) -> Callable[[str], int]:
    """An argparse `type=`: the integer in [lo, hi], else ArgumentTypeError naming the range."""
    def parse(text: str) -> int:
        try:
            value = int(text)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{text!r} is not an integer") from None
        if not lo <= value <= hi:
            raise argparse.ArgumentTypeError(f"{value} is out of range, must be {lo}..{hi}")
        return value
    return parse


def float_in(lo: float, hi: float) -> Callable[[str], float]:
    """An argparse `type=`: the finite number in [lo, hi], else ArgumentTypeError naming the range."""
    def parse(text: str) -> float:
        try:
            value = float(text)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{text!r} is not a number") from None
        if not lo <= value <= hi:      # also False for nan
            raise argparse.ArgumentTypeError(f"{text} is out of range, must be {lo:g}..{hi:g}")
        return value
    return parse


def digits_in(lo: int, hi: int) -> Callable[[str], str]:
    """A `type=` for a positional the gate keeps as text: an all-digit value must lie in [lo, hi]; any other text
    passes through unchanged, so the gate's own "must be integers" message (exit 1) still handles it."""
    parse_int = int_in(lo, hi)

    def parse(text: str) -> str:
        if text.isascii() and text.isdigit():
            parse_int(text)
        return text
    return parse


def number_text_in(lo: float, hi: float) -> Callable[[str], str]:
    """Like `float_in` but returns the text unchanged, for a positional the caller converts itself."""
    parse_float = float_in(lo, hi)

    def parse(text: str) -> str:
        parse_float(text)
        return text
    return parse


def check_size(path: str, cap: int) -> None:
    """Exit 2 with one line (file, size, cap) when `path` is larger than `cap` bytes. An unreadable or missing
    path is left to the caller's own error. Uses os.stat only: nothing is read."""
    try:
        size = os.stat(path).st_size
    except OSError:
        return
    if size > cap:
        fail(f"{path} is {size} bytes, over the {cap}-byte limit for this kind of input")
