"""LOG320 worst-case sweep of typst.py: the rewritten scanners return exactly what the code they replaced returned
(the old code is kept verbatim in _typst_ref.py; Hypothesis builds texts from the fragments the parsers react to,
so rules that never close, nest, overlap, end on a word character or repeat `leading:` all come up), and stay
linear on the worst case (deterministic work counts, no wall clock: Python line events plus the characters the regex
and `find` calls consume; the number patterns' backtracking is C-level, so it is pinned structurally)."""
import re
from collections.abc import Callable

import pytest
from _complexity import assert_linear, line_events
from _scan_str import ScanStr
from _typst_ref import _LEAD_ARG as LEAD_OLD
from _typst_ref import _RHYTHM_RE as RHYTHM_OLD
from _typst_ref import _SIZE_ARG as SIZE_OLD
from _typst_ref import _SPACING_VAL as SPACING_OLD
from _typst_ref import PAR_RE as PAR_RE_OLD
from _typst_ref import mask_non_markup_quadratic, par_rule_spans_quadratic
from hypothesis import given, settings
from hypothesis import strategies as st
from vitae.verify import typst

# What the parsers react to: the keys, numbers (digits, dots), units, brackets, quoting and comment openers.
_FRAGMENTS = ["leading", "spacing", "size", "rhythm", ":", ": ", " ", "\t", "\n", "1", "0", "5", ".", "em", "pt", "x",
              "(", ")", ",", "leading: 1em", "leading: 1emx", "leading: 0.5em", "spacing: 2em", "spacing: 1.5pt",
              "#set par(", "\n#set par(", "\n#set par(\n", "#let rhythm = ", "`", "``", "```", '"', "$", "\\", "/*",
              "*/", "//", "a"]
_texts = st.lists(st.sampled_from(_FRAGMENTS), max_size=24).map("".join)


def _groups(m: re.Match[str] | None) -> tuple[int, int, tuple[str | None, ...]] | None:
    return None if m is None else (m.start(), m.end(), m.groups())


@settings(max_examples=600, deadline=None)
@given(_texts)
def test_number_patterns_match_the_same_text_as_the_old_ones(s: str) -> None:
    pairs = [(typst._LEAD_ARG, LEAD_OLD, "search"), (typst._SIZE_ARG, SIZE_OLD, "search"),
             (typst._SPACING_VAL, SPACING_OLD, "match"), (typst._RHYTHM_RE, RHYTHM_OLD, "search")]
    for new, old, how in pairs:
        assert _groups(getattr(new, how)(s)) == _groups(getattr(old, how)(s))


@settings(max_examples=300, deadline=None)
@given(st.text(alphabet="0123456789. \temptx:", max_size=14), st.sampled_from(["leading: ", "size: ", "", "#let rhythm = "]))
def test_number_patterns_agree_on_every_short_string_of_their_alphabet(tail: str, head: str) -> None:
    s = head + tail
    for new, old in ((typst._LEAD_ARG, LEAD_OLD), (typst._SIZE_ARG, SIZE_OLD), (typst._RHYTHM_RE, RHYTHM_OLD)):
        assert _groups(new.search(s)) == _groups(old.search(s))
    assert _groups(typst._SPACING_VAL.match(tail)) == _groups(SPACING_OLD.match(tail))


def test_number_pattern_equivalence_is_not_vacuous() -> None:
    # control: the strings the patterns accept and the ones they reject both occur
    assert typst._LEAD_ARG.search("(leading: 0.65em)") is not None
    assert typst._LEAD_ARG.search("(leading: 1.2.3em)") is None
    assert typst._LEAD_ARG.search("xleading: .5pt") is None       # no delimiter before `leading`
    assert typst._LEAD_ARG.search("leading: .5pt") is not None
    assert typst._SPACING_VAL.match(".5pt") is not None
    assert typst._SPACING_VAL.match("5.pt") is None


@settings(max_examples=800, deadline=None)
@given(_texts)
def test_par_rule_spans_match_the_old_scan(s: str) -> None:
    assert typst._par_rule_spans(s) == par_rule_spans_quadratic(s)


@settings(max_examples=300, deadline=None)
@given(st.lists(st.sampled_from(["#set par(", "\n#set par(", "\n", "(", ")", "leading: 1em", " leading:1pt", "x", "1em"]),
                min_size=1, max_size=30).map("".join))
def test_par_rule_spans_match_on_nested_unclosed_and_boundary_rules(s: str) -> None:
    # rules inside rules, a missing `)` at the end, a `leading:` unit cut by the end of the text
    assert typst._par_rule_spans(s) == par_rule_spans_quadratic(s)
    assert typst._par_rule_spans(s + "x") == par_rule_spans_quadratic(s + "x")


def test_par_rule_spans_equivalence_is_not_vacuous() -> None:
    assert typst._par_rule_spans("#set par(leading: 1em)\n") == [(0, 22)]
    assert typst._par_rule_spans("#set par(justify: true)\n") == []
    assert typst._par_rule_spans("#set par(leading: 1em") == []        # the unclosed rule drops its last character
    assert typst._par_rule_spans("#set par(leading: 1em ") == [(0, 22)]


@settings(max_examples=600, deadline=None)
@given(_texts)
def test_par_re_matches_like_the_old_one(s: str) -> None:
    text = "#set par(" + s
    assert _groups(typst.PAR_RE.match(text, 0)) == _groups(PAR_RE_OLD.match(text, 0))


@settings(max_examples=300, deadline=None)
@given(st.lists(st.sampled_from(["leading: 1em", "leading: 2.5em", "leading: x", "spacing: 3em", "spacing: 1pt",
                                 "leading:1em,spacing:0.5em", ",", " ", ")", "em"]), max_size=14).map(" ".join))
def test_par_re_matches_with_repeated_leading_and_spacing(s: str) -> None:
    text = "#set par(" + s
    assert _groups(typst.PAR_RE.match(text, 0)) == _groups(PAR_RE_OLD.match(text, 0))


def test_par_re_equivalence_is_not_vacuous() -> None:
    assert typst.PAR_RE.match("#set par(leading: 0.5em, spacing: 1em)", 0) is not None
    assert typst.PAR_RE.match("#set par(leading: x, leading: 0.5em, spacing: 1em)", 0) is not None   # a later leading wins
    assert typst.PAR_RE.match("#set par(spacing: 1em, leading: 0.5em)", 0) is None


@settings(max_examples=600, deadline=None)
@given(_texts)
def test_mask_non_markup_matches_the_old_one(s: str) -> None:
    assert typst.mask_non_markup(s) == mask_non_markup_quadratic(s)


_FILES = frozenset({typst.mask_non_markup.__code__.co_filename})


class _CountedPattern:
    """A compiled pattern that charges the characters each call consumes (a full pass for `finditer`, up to the match end
    or the search limit for `match` and `search`): the C-level work of a rescan per rule, invisible to line events."""
    scanned = 0
    calls = 0

    def __init__(self, pattern: re.Pattern[str]) -> None:
        self._p = pattern

    def finditer(self, string: str) -> list[re.Match[str]]:
        _CountedPattern.calls += 1
        _CountedPattern.scanned += len(string)
        return list(self._p.finditer(string))

    def match(self, string: str, pos: int = 0) -> re.Match[str] | None:
        _CountedPattern.calls += 1
        m = self._p.match(string, pos)
        _CountedPattern.scanned += (m.end() if m else pos) - pos
        return m

    def search(self, string: str, pos: int = 0, endpos: int | None = None) -> re.Match[str] | None:
        _CountedPattern.calls += 1
        m = self._p.search(string, pos) if endpos is None else self._p.search(string, pos, endpos)
        _CountedPattern.scanned += (m.end() if m else (len(string) if endpos is None else endpos)) - pos
        return m


def _count_patterns(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("_PAR_OPEN", "_PARENS", "_LEAD_ARG", "PAR_RE"):
        monkeypatch.setattr(typst, name, _CountedPattern(getattr(typst, name)))
    _CountedPattern.scanned = _CountedPattern.calls = 0


@pytest.mark.parametrize("make", [lambda n: "#set par(\n" * n, lambda n: "#set par(\n" * n + ")" * n,
                                  lambda n: "#set par(leading: 1em\n" * n],
                         ids=["unclosed", "nested", "unclosed-with-leading"])
def test_par_rule_work_grows_linearly_on_unclosed_and_nested_rules(monkeypatch: pytest.MonkeyPatch,
                                                                   make: Callable[[int], str]) -> None:
    # the old scan rescanned the rest of the text per rule (~24 s on 8000 of them)
    _count_patterns(monkeypatch)

    def work(n: int) -> int:
        _CountedPattern.scanned = _CountedPattern.calls = 0
        text = make(n)
        events, _ = line_events(_FILES, lambda: (typst._par_rule_spans(text), typst._tuned_par(text)))
        assert _CountedPattern.calls > 0                  # the patterns ran: the count sees the scans
        return events + _CountedPattern.scanned

    assert_linear(work, 500)


# The one number form every pattern uses. Its alternatives start with a digit run then an optional `.digits`, or with `.`:
# no digit can be read two ways, and the token after it (`\s*`, a unit, `;`, `)`) is never a digit or a dot, so a failing
# match on a long digit run costs one pass. The old `[0-9]*\.?[0-9]+` splits a run of n digits n ways (~15 s on 40 000).
_NUMBER = r"([0-9]+(?:\.[0-9]+)?|\.[0-9]+)"


@pytest.mark.parametrize("name", ["_LEAD_ARG", "_SIZE_ARG", "_SPACING_VAL", "_RHYTHM_RE"])
def test_number_patterns_read_a_number_in_the_one_unambiguous_form(name: str) -> None:
    pattern = getattr(typst, name).pattern
    assert pattern.count(_NUMBER) == 1
    assert r"[0-9]*\.?[0-9]+" not in pattern            # the old nested form


def test_number_patterns_decide_long_digit_runs_without_backtracking_in_the_pattern() -> None:
    # PAR_RE commits to the first `leading: Xem` (atomic group); without it a later one is retried once per `leading:`
    assert typst.PAR_RE.pattern.startswith("(?>")
    digits = "1" * 4000
    assert typst._LEAD_ARG.search(" leading: " + digits + "x") is None
    assert typst._SIZE_ARG.search(" size: " + digits + "x") is None
    assert typst._SPACING_VAL.match(digits + "x") is None
    assert typst._RHYTHM_RE.search("#let rhythm = " + digits + "x") is not None     # the rhythm form ends at the digits
    assert typst.PAR_RE.match("#set par(" + "leading: 1em, " * 200, 0) is None


@pytest.mark.parametrize("unit", ["`a", "``a", "`"])
def test_mask_non_markup_work_grows_linearly_on_many_backticks(unit: str) -> None:
    # copying the rest of the text per backtick took ~1 s on 200 000 pairs: slices and `find` scans are counted
    def work(n: int) -> int:
        ScanStr.reset()
        events, out = line_events(_FILES, lambda: typst.mask_non_markup(ScanStr(unit * n)))
        assert out
        assert ScanStr.calls > 0                          # the raw-span search went through the counted `find`
        return events + ScanStr.scanned

    assert_linear(work, 2000)
