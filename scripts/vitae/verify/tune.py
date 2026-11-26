"""--tune: bisect `#set par(leading:, spacing:)` to the largest rhythm that holds the page count
(it reads pdf / env / base only; `tune` returns the exit code with the footer the CLI prints last).
"""
from __future__ import annotations

import os
import re
import shlex
import tempfile

import vitae.fill as measure_fill
from vitae.core.base import (
    _FOOTER_TUNE,
    _FOOTER_TUNE_NOPAR,
    _FOOTER_TUNE_UNDER,
    _FOOTER_TUNE_WIDE,
    LEADING_WARN,
    LOWERED_FILL_FLOOR,
)
from vitae.core.env import PdfBackend, preflight
from vitae.verify.pdf import compile_pdf, count_pages, render_pngs
from vitae.verify.typst import _count_par_leadings, _read_par, _scale_list_spacing, _write_par

# ---------- auto-tuner: the fill loop, run by bisection instead of by hand ----------

# Why a bisection is valid: raising `leading` pushes every line further down, so the last ink
# row rises monotonically with it, until the last unbreakable section no longer fits and the
# page count jumps. The leading values that keep the expected page count therefore form an
# interval [lo, L*], and the best fill is at its top end. So: bisect for L*, then check the
# fill it produces.
#
# `spacing` moves WITH `leading`, keeping the family's own delta between the two: that delta
# is part of the recipe (a family with a wide paragraph spacing relative to its leading has a
# different rhythm, not just a different density), and tuning them independently would
# silently redesign the family. The explicit `#set list(spacing:)` scales by the same factor as
# the leading (new leading / original leading), so the family's leading / list-spacing ratio, the
# prose-vs-bullet rhythm, survives the tune; a file with no explicit list spacing is left alone.
#
# If the fill at L* is still under the target, no leading value reaches it: that is the
# anti-filler clause (SKILL.md rule 5) speaking, the content does not honestly fill that
# pagination. The tuner says so instead of inventing a value; the fix is the section gap,
# real content, or a different page count.


def _with_rhythm(text: str, leading: float, spacing: float) -> str:
    """text with par leading/spacing set and the list spacing scaled by leading / original leading.

    With more than one `#set par(leading:)` the tuner edits the first while the gate reads the last,
    so both of the gate's values stay untouched and the list spacing is left alone too."""
    par = _read_par(text)
    out = _write_par(text, leading, spacing)
    if not par or par[0] <= 0 or _count_par_leadings(text) > 1:
        return out
    return _scale_list_spacing(out, leading / par[0])


def _probe(typ: str, text: str, leading: float, spacing: float, expected: int,
           use_cli: bool, backend: PdfBackend) -> tuple[bool, int | None]:
    """Compile at (leading, spacing); return (pages_ok, fill_pct or None).

    Rewrites `typ` in place on every call: the caller restores the original text."""
    open(typ, "w", encoding="utf-8").write(_with_rhythm(text, leading, spacing))
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "t.pdf")
        ok, _ = compile_pdf(typ, pdf, use_cli)
        if not ok:
            return False, None
        if count_pages(pdf, backend) != str(expected):
            return False, None
        pngs = render_pngs(typ, tmp, use_cli)
        if not pngs:
            return False, None
        m = re.search(r"to (\d+)%", measure_fill.measure(pngs[-1]))
        return True, (int(m.group(1)) if m else None)


# UPWARD CAP. An under-filled page means a fact is missing, not whitespace to inflate. The
# shipped templates use body leading well under LEADING_WARN and paragraph spacing up to 1.075em; the tuner
# never goes above LEADING_WARN (the gate's own double-spacing WARN threshold, so a tuned file
# never trips it) or SPACING_CAP (the shipped maximum plus 15%, CHANGELOG) whatever range the
# caller passes. The downward (over-full) search is not capped.
SPACING_CAP = 1.24     # em; largest shipped paragraph spacing 1.075 x 1.15


# Default search bounds [0.80 * l0, max(1.30 * l0, 1.10)] and bisection step 0.005em (~7-8 probes):
# 0.005em changes a 1-page CV's bottom ink row by <0.5% of page height, finer than the 2%-wide fill band.
def tune(typ: str, expected: int, fmin: int, fmax: int, lo: float | None = None,
         hi: float | None = None, step: float = 0.005, *,
         allow_placeholders: bool = False) -> tuple[int, str | None]:
    """--tune: bisect `#set par(leading:, spacing:)` in `typ` to the largest rhythm that holds
    `expected` pages, and keep it only if the fill lands in fmin-fmax. Returns (exit code, footer): the
    code is 0 won, 1 no value in range, 2 no par line; the footer is the NEXT line the CLI prints last
    on a failure (None when preflight failed). Any failure restores the original file: a
    value that misses the target is worse than the rhythm the family was designed with."""
    deps_ok, use_cli, backend = preflight()
    if not deps_ok:
        return 1, None
    allow = " --allow-placeholders" if allow_placeholders else ""   # carried into the printed follow-up commands
    footer = _FOOTER_TUNE
    original = open(typ, encoding="utf-8").read()
    cur = _read_par(original)
    if cur is None:
        footer = _FOOTER_TUNE_NOPAR
        print("FAIL  no `#set par(... leading: Xem, spacing: Yem)` line to tune "
              "— the tuner edits that one declaration and nothing else")
        return 2, footer
    l0, s0 = cur
    delta = s0 - l0                       # the family's own rhythm, preserved
    lo_arg = lo   # kept to tell, on failure, whether the caller already passed a wide range
    lo = l0 * 0.80 if lo is None else lo
    # The default ceiling is relative, but a family with an already-tight
    # leading gets a range too narrow to ever reach the fill target, so the
    # ceiling never sits below 1.10em (then clamped to the cap below).
    hi = max(l0 * 1.30, 1.10) if hi is None else hi
    hi_arg = hi
    # the cap on leading is the tighter of the two caps once the family's delta is added to
    # the spacing; never below the current leading, so a family already above it is not forced down
    cap = max(min(LEADING_WARN, SPACING_CAP - delta), l0)
    clamped = hi > cap + 1e-9
    if clamped:
        hi = cap
    lo = min(lo, hi)
    print("tuning %s: leading %.3fem (spacing %+.3fem), searching [%.3f, %.3f], "
          "target %s pages / fill %s-%s%%"
          % (typ, l0, delta, lo, hi, expected, fmin, fmax))
    if clamped:
        print("NOTE  upper bound clamped to %.3fem: the lower of the gate's double-spacing WARN threshold "
              "(%.2fem) and the spacing cap (%.2fem) less this family's spacing offset (%+.3fem), never below "
              "the current leading; an under-filled page needs a real fact, not more air"
              % (cap, LEADING_WARN, SPACING_CAP, delta))
    try:
        ok_lo, fill_lo = _probe(typ, original, lo, lo + delta, expected,
                                use_cli, backend)
        if not ok_lo:
            open(typ, "w", encoding="utf-8").write(original)   # undo the probe
            # the floor failed, so no larger leading can hold the page count either
            print("FAIL  even the floor leading %.3fem does not give %s page(s) "
                  "— either the content is too long for %s page(s), or the search range starts "
                  "too high: try an explicit lower range, e.g. `--tune %s %s %s %s 0.45 1.0` "
                  "(FILL_MIN FILL_MAX LEAD_LO LEAD_HI)"
                  % (lo, expected, expected, typ, expected, fmin, fmax))
            return 1, footer
        best, best_fill = lo, fill_lo
        # Fill grows with leading while the page count holds, so the target band is a window
        # of leading values. Bisect on "pages hold AND fill <= fmax": that boundary is the top
        # of the window, so the answer is the largest probe that does not overshoot (also when
        # the page breaks above an fmax-overshooting stretch, where bisecting for the page
        # break alone would step over a narrow window).
        while hi - lo > step:
            mid = (lo + hi) / 2
            ok, fill = _probe(typ, original, mid, mid + delta, expected,
                              use_cli, backend)
            print("  leading %.3fem -> %s" % (
                mid, ("fill %s%%" % fill) if ok else "page count off"))
            if ok and (fill is None or fill <= fmax):
                lo = mid                  # an unmeasured fill still moves the bound...
                if fill is not None:      # ...but never replaces a measured best
                    best, best_fill = mid, fill
            else:
                hi = mid
        won = best_fill is not None and fmin <= best_fill <= fmax
        if not won:
            # A losing value is worse than no value: it silently replaces a rhythm the family was
            # designed with. Put the original back and let the caller decide.
            open(typ, "w", encoding="utf-8").write(original)
            under = best_fill is not None and best_fill < fmin
            print("FAIL  best leading %.3fem / spacing %.3fem -> fill %s%% "
                  "(target %s-%s%%); restored the original %.3fem/%.3fem"
                  % (best, best + delta, best_fill, fmin, fmax, l0, s0))
            if under:
                footer = _FOOTER_TUNE_UNDER
                print("      the page is UNDER-FILLED: a fact is missing, not whitespace. "
                      "Leading is capped at %.2fem (never widen the range). Add a real fact "
                      "from the candidate's facts (a bullet with a measurable result, a "
                      "project, a certification) — never pad. If the facts are not in "
                      "hand, ASK the user for them; never invent. Alternative, only if the "
                      "facts are exhausted: drop to fewer pages or pass a lowered target, "
                      "`verify.py %s %s FILL_MIN %s%s` (FILL_MIN = the lowest fill the gate "
                      "prints, not below %d; a page under %d%% has no lowered-target exit: a fact "
                      "is missing, or fewer pages), and say so to the user."
                      % (cap, shlex.quote(typ), expected, fmax, allow, LOWERED_FILL_FLOOR, LOWERED_FILL_FLOOR))
            else:
                if lo_arg is not None and lo_arg <= 0.40 and hi_arg >= 1.40:
                    footer = _FOOTER_TUNE_WIDE
                print("      no leading in the searched range reaches the target at "
                      "%s page(s). Widen the range by passing the bounds "
                      "positionally after FILL_MAX, e.g.\n"
                      "        verify.py --tune %s %s %s %s %.2f %.2f%s\n"
                      "      or take the space out of the section gap / add real "
                      "content / change the page count (anti-filler clause, "
                      "SKILL.md rule 5)."
                      % (expected, typ, expected, fmin, fmax,
                         max(0.40, l0 * 0.65), max(1.40, l0 * 1.60), allow))
            return 1, footer
        open(typ, "w", encoding="utf-8").write(
            _with_rhythm(original, best, best + delta))
        print("OK    wrote leading %.3fem / spacing %.3fem -> fill %s%% "
              "(target %s-%s%%)" % (best, best + delta, best_fill, fmin, fmax))
        print("      now run the gate itself: verify.py %s %s %s %s%s"
              % (typ, expected, fmin, fmax, allow))
        return 0, footer
    except BaseException:
        # kept broad: restores the file then re-raises, nothing is swallowed (Ctrl-C mid-probe must not leave a half-tuned file behind)
        open(typ, "w", encoding="utf-8").write(original)   # never leave a probe
        raise
