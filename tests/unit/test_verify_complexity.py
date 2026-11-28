"""LOG320 lot: the hot spots fixed for complexity keep their behaviour (equivalence with the replaced code, on fixed
cases and Hypothesis-generated inputs) and keep their work linear on a worst-case input: a deterministic count of the
work (Python line events, characters scanned by `find`, ways a regex can split) grows at most 2.2 x per doubling of
the input, where a return to O(P^2) quadruples it. No wall-clock measurement, so a loaded runner cannot flip it."""
import itertools
import operator
import random
import re
from collections.abc import Callable
from typing import SupportsIndex

import pytest
from _comments_ref import strip_block_comments_regex, strip_comments_regex
from _complexity import assert_linear, line_events
from _reading_order_ref import reading_order_quadratic
from _stuffed_ref import stuffed_counting
from hypothesis import given, settings
from hypothesis import strategies as st
from vitae.core import typst_source
from vitae.core.base import WordBox
from vitae.verify import fonts, pdf, text

# ------------------------------------------------------------------ _reading_order


def _random_page(rng: random.Random) -> list[WordBox]:
    """Rows of words at random x gaps (so rows split in pieces), heights 8-12, small baseline jitter, a column of
    right-flushed dates, then shuffled: content-stream order is arbitrary."""
    words: list[WordBox] = []
    y = 20.0
    for r in range(rng.randint(1, 14)):
        h = rng.choice((8.0, 10.0, 12.0))
        x = rng.choice((10.0, 10.0, 40.0, 120.0))
        for k in range(rng.randint(1, 6)):
            w = rng.uniform(15, 70)
            if rng.random() < 0.15:                    # a long word: its piece reaches past the next piece's left edge
                w = rng.uniform(150, 400)
            words.append(((x, y + rng.uniform(-1, 1), x + w, y + h + rng.uniform(-1, 1)), f"r{r}w{k}"))
            x += w + rng.choice((3.0, 3.0, 4.0, 30.0, 90.0))
        if rng.random() < 0.4:
            words.append(((420.0, y, 480.0, y + h), f"r{r}date"))
        y += h + rng.choice((2.0, 4.0, 12.0))
    rng.shuffle(words)
    return words


def _mixed_heights_page(rng: random.Random) -> list[WordBox]:
    """Words of different heights on baselines a few points apart: whether one joins the row depends on the smallest
    box already in it, and on the mean baseline of the words already in it."""
    words: list[WordBox] = []
    for k in range(rng.randint(3, 14)):
        h = rng.choice((3.0, 6.0, 10.0))
        y = rng.uniform(0, 8)
        x = rng.uniform(0, 400)
        words.append(((x, y, x + rng.uniform(5, 40), y + h), f"w{k}"))
    return words


def _overlapping_side_pieces_page(rng: random.Random) -> list[WordBox]:
    """A head row of pieces with long words among short ones (a short word inside a long one starts a piece that lies
    within the previous piece), then rows of one narrow piece anywhere past the head (so it is not a side piece itself
    and can overlap only some of the head's pieces) or at the left edge."""
    words: list[WordBox] = [((0.0, 0.0, 30.0, 10.0), "head")]
    for k in range(rng.randint(3, 8)):
        x = rng.uniform(100, 400)
        w = rng.choice((5.0, 10.0, 20.0, 150.0, 250.0))
        words.append(((x, 0.0, x + w, 10.0), f"s{k}"))
    for r in range(1, rng.randint(2, 6)):
        x = rng.choice((0.0, rng.uniform(100, 420), rng.uniform(100, 420)))
        words.append(((x, r * 12.0, x + rng.uniform(5, 40), r * 12.0 + 10), f"r{r}"))
    rng.shuffle(words)
    return words


@settings(max_examples=300)
@given(st.randoms(use_true_random=False), st.sampled_from((_random_page, _mixed_heights_page)))
def test_reading_order_matches_the_quadratic_version(rng: random.Random, shape: Callable[[random.Random], list[WordBox]]) -> None:
    words = shape(rng)

    assert pdf._reading_order(words) == reading_order_quadratic(words)


@settings(max_examples=600)
@given(st.randoms(use_true_random=False))
def test_reading_order_overlapping_side_pieces_match_the_oracle_on_random_pages(rng: random.Random) -> None:
    words = _overlapping_side_pieces_page(rng)

    assert pdf._reading_order(words) == reading_order_quadratic(words)


def test_reading_order_side_pieces_that_overlap_on_their_row_match_the_oracle() -> None:
    """A long word makes a piece overlap the next one on its row, so the right edges of the side pieces are not sorted:
    `y` (390-395, row 2) is under LONGSIDE (200-400), which comes before S2 (260-280) but ends after it."""
    def wb(x0: float, x1: float, row: int, t: str) -> WordBox:
        return ((x0, row * 12.0, x1, row * 12.0 + 10), t)

    words = [wb(0, 30, 0, "Role"), wb(200, 400, 0, "LONGSIDE"), wb(210, 220, 0, "b"), wb(260, 280, 0, "S2"),
             wb(0, 30, 1, "org"), wb(390, 395, 2, "y")]

    got = [t for _, t in pdf._reading_order(words)]

    assert got == [t for _, t in reading_order_quadratic(words)]
    assert got == ["Role", "org", "LONGSIDE", "b", "y", "S2"]


def test_reading_order_equivalence_is_not_vacuous() -> None:
    # control: the random pages exercise the side-piece (right-flushed date) branch, which reorders words
    moved = sum(pdf._reading_order(w) != sorted(w, key=lambda t: (t[0][1], t[0][0]))
                for w in (_random_page(random.Random(s)) for s in range(400)))

    assert moved > 100


def test_reading_order_dated_heads_keep_their_entry_lines() -> None:
    head = [((10.0, 0.0, 80.0, 10.0), "Role"), ((420.0, 0.0, 480.0, 10.0), "2020"),
            ((10.0, 12.0, 90.0, 22.0), "line1"), ((10.0, 24.0, 90.0, 34.0), "line2"),
            ((10.0, 40.0, 80.0, 50.0), "Role2"), ((420.0, 40.0, 480.0, 50.0), "2018")]

    got = [t for _, t in pdf._reading_order(head)]

    assert got == [t for _, t in reading_order_quadratic(head)]


def _grid(n: int, per_row: int = 20) -> list[WordBox]:
    """Worst case: `per_row` pieces on every row (a table), every piece overlapping pieces of the rows above."""
    return [((10.0 + (i % per_row) * 60, 10.0 + (i // per_row) * 12, 18.0 + (i % per_row) * 60 + 30,
              20.0 + (i // per_row) * 12), f"w{i}") for i in range(n)]




_PDF_FILE = frozenset({pdf._reading_order.__code__.co_filename})


def _reading_order_events(words: list[WordBox]) -> int:
    events, out = line_events(_PDF_FILE, lambda: pdf._reading_order(words))
    assert len(out) == len(words)
    return events


def test_reading_order_work_grows_linearly_on_a_large_table() -> None:
    # the quadratic version compared every piece with every piece above it (6 s on 8000 words)
    assert_linear(lambda n: _reading_order_events(_grid(n)), 1000)


def _one_baseline(n: int) -> list[WordBox]:
    """Worst case of the row grouping: every word on one baseline (n words, one row, no gap wide enough to split it)."""
    return [((10.0 + i * 5, 10.0, 14.0 + i * 5, 20.0), f"w{i}") for i in range(n)]


def _side_then_rows(n: int) -> list[WordBox]:
    """Worst case of the side-piece pass: n right-flushed pieces beside a head on one row, then n rows of one piece
    each, none under a side piece (so no row ends the search early)."""
    words: list[WordBox] = [((10.0, 10.0, 40.0, 20.0), "head")]
    words += [((100.0 + i * 40, 10.0, 120.0 + i * 40, 20.0), f"s{i}") for i in range(n)]
    words += [((10.0, 30.0 + r * 12, 40.0, 40.0 + r * 12), f"r{r}") for r in range(n)]
    return words


def test_reading_order_work_grows_linearly_on_a_single_baseline() -> None:
    # recomputing the row's mean per word was quadratic (4 s on 8000 words)
    assert_linear(lambda n: _reading_order_events(_one_baseline(n)), 1000)
    words = _one_baseline(1000)
    assert pdf._reading_order(words) == words


def test_reading_order_work_grows_linearly_on_many_side_pieces_then_many_rows() -> None:
    # rescanning the rows per side piece was quadratic (1.8 s on 3000 + 3000)
    assert_linear(lambda n: _reading_order_events(_side_then_rows(n)), 400)


def test_reading_order_matches_the_oracle_on_the_side_piece_worst_cases() -> None:
    """The scale-down of the two worst cases above, plus side pieces that overlap rows below (control: they do reorder)."""
    for words in (_one_baseline(60), _side_then_rows(25)):
        assert pdf._reading_order(words) == reading_order_quadratic(words)
    under = _side_then_rows(8) + [((105.0 + i * 80, 33.0 + i * 12, 150.0 + i * 80, 43.0 + i * 12), f"u{i}") for i in range(4)]
    got = pdf._reading_order(under)
    assert got == reading_order_quadratic(under)
    assert got != sorted(under, key=lambda t: (t[0][1], t[0][0]))


# ------------------------------------------------------------------ _stuffed

_VOCAB = ["python", "Python", "sql", "go", "a", "data", "rust", "ops", "été", "Été", "x1", "data science", "sql server"]


@settings(max_examples=300)
@given(st.sampled_from((", ", "; ", " ", ",", " , ")), st.lists(st.sampled_from(_VOCAB), max_size=25), st.sampled_from((0, 5, 12)))
def test_stuffed_matches_the_counting_version(sep: str, terms: list[str], cap: int) -> None:
    t = sep.join(terms)

    assert text._stuffed(t, cap) == stuffed_counting(t, cap)


@pytest.mark.parametrize("t, want", [
    ("python, sql, python", True),                 # a term used twice
    ("data data data", True),                      # a 3+ letter word used three times
    ("go, sql, python", False),
    ("python, sql, rust", False),
])
def test_stuffed_signals(t: str, want: bool) -> None:
    assert (text._stuffed(t) is not None) is want


def _stuffedline_events(n: int) -> int:
    """Python line events inside `text._stuffed` on `n` distinct terms."""
    t = ", ".join(f"t{i}" for i in range(n))
    events, out = line_events(frozenset({text._stuffed.__code__.co_filename}), lambda: text._stuffed(t, max_terms=0))
    assert out is None
    return events


def test_stuffed_work_grows_linearly_on_a_long_distinct_list() -> None:
    base = 1000
    e1, e2, e4 = (_stuffedline_events(base * k) for k in (1, 2, 4))

    # linear: doubling the input roughly doubles the events (a per-term count over the list would quadruple them)
    assert e2 / e1 <= 2.2
    assert e4 / e2 <= 2.2


class _CountingStr(str):
    """A `str` that counts its comparisons and hashes and survives `strip` and `lower`: C-level work (`list.count`,
    `in` on a list, `==`) that the line-event count cannot see."""
    operations = 0

    def __eq__(self, other: object) -> bool:
        _CountingStr.operations += 1
        return str.__eq__(self, other)

    def __hash__(self) -> int:
        _CountingStr.operations += 1
        return str.__hash__(self)

    def __ne__(self, other: object) -> bool:
        _CountingStr.operations += 1
        return str.__ne__(self, other)

    def __lt__(self, other: str) -> bool:
        _CountingStr.operations += 1
        return str.__lt__(self, other)

    def split(self, sep: str | None = None, maxsplit: SupportsIndex = -1) -> list[str]:
        return [_CountingStr(p) for p in str.split(self, sep, maxsplit)]

    def strip(self, chars: str | None = None, /) -> "_CountingStr":
        return _CountingStr(str.strip(self, chars))

    def lower(self) -> "_CountingStr":
        return _CountingStr(str.lower(self))


class _CountingRe:
    """Stands in for the `re` module inside `text`: `split` and `findall` return counting strings."""

    def split(self, pattern: str, string: str) -> list[str]:
        return [_CountingStr(p) for p in re.split(pattern, string)]

    def findall(self, pattern: str, string: str) -> list[str]:
        return [_CountingStr(w) for w in re.findall(pattern, string)]


def _stuffed_operations(monkeypatch: pytest.MonkeyPatch, n: int, sep: str) -> int:
    """Comparisons and hashes of the terms and words `text._stuffed` makes on `n` distinct terms joined by `sep`
    (`", "`: the comma branch; `" "`: the whitespace fallback)."""
    monkeypatch.setattr(text, "re", _CountingRe())
    t = _CountingStr(sep.join(f"t{i}" for i in range(n)))
    _CountingStr.operations = 0

    out = text._stuffed(t, max_terms=0)

    assert out is None
    assert _CountingStr.operations > 0       # the branch ran on counting strings: the count is not vacuous
    return _CountingStr.operations


@pytest.mark.parametrize("sep", [", ", " "], ids=["comma", "whitespace-fallback"])
def test_stuffed_comparisons_grow_linearly_on_a_long_distinct_list(monkeypatch: pytest.MonkeyPatch, sep: str) -> None:
    # The line-event count above cannot see C-level work (`terms.count(t)` per term is n line events but n*n
    # comparisons); counting `__eq__`, `__hash__` and the like on the terms and words does, and is as deterministic as it.
    base = 1000
    o1, o2, o4 = (_stuffed_operations(monkeypatch, base * k, sep) for k in (1, 2, 4))

    assert o2 / o1 <= 2.2
    assert o4 / o2 <= 2.2


# ------------------------------------------------------------------ _FONT_STYLE_RE

_OLD_STYLE = re.compile(r"^(?:\d+|pt|variable|regular|roman|book|medium|semibold|bold|extrabold|black|heavy|"
                        r"thin|light|extralight|italic|oblique|condensed|semicondensed|cond|narrow|display|text|"
                        r"psmt|mt|vf|upright|pro|std|semi|demi|ultra|extra)*$")
_WORDS = ("pt variable regular roman book medium semibold bold extrabold black heavy thin light extralight italic "
          "oblique condensed semicondensed cond narrow display text psmt mt vf upright pro std semi demi ultra extra").split()
REAL = ["", "regular", "medium", "bold", "semibold", "semicondensedbold", "extralight", "extrabolditalic", "boldoblique",
        "96pt", "12", "psmt", "vf", "upright", "variableregular", "italic", "mono", "monobold", "sc", "semiboldx", "x",
        "extra", "ultralight", "demibold", "condbold", "condensedlight", "textbold", "displaymedium", "romanpro",
        "bookstd", "heavyitalic", "blackoblique", "thin", "123456789", "boldmono"]


@pytest.mark.parametrize("s", REAL)
def test_font_style_matches_the_old_pattern_on_real_names_and_edges(s: str) -> None:
    assert bool(fonts._FONT_STYLE_RE.match(s)) == bool(_OLD_STYLE.match(s))


def test_font_style_matches_the_old_pattern_on_every_short_sequence() -> None:
    # every concatenation of up to 3 style words, bare and followed by a junk letter or a digit run
    for n in (1, 2, 3):
        for combo in itertools.product(_WORDS, repeat=n):
            s = "".join(combo)
            for tail in ("", "x", "12", "-"):
                assert bool(fonts._FONT_STYLE_RE.match(s + tail)) == bool(_OLD_STYLE.match(s + tail)), s + tail


def test_font_style_control_rejects_a_foreign_word() -> None:
    assert fonts._FONT_STYLE_RE.match("semibolditalic")
    assert not fonts._FONT_STYLE_RE.match("boldmono")


def _style_alternatives() -> list[str]:
    pattern = fonts._FONT_STYLE_RE.pattern
    head, tail = "^(?:", ")*$"
    assert pattern.startswith(head) and pattern.endswith(tail)
    body = pattern[len(head):-len(tail)]
    assert not any(c in body for c in "()[]{}*+?."), "nested group or quantifier: split the alternatives by a real parser"
    return body.split("|")


def _style_splits(alternatives: list[re.Pattern[str]], s: str) -> int:
    """The number of ways `s` splits into the alternatives under the pattern's star. A failing match backtracks once
    per way (the old pattern: 2 ways per `semibold`, so 2**22 on 22 of them, ~6 s), so the count IS the work of the
    engine, which no Python-level counter sees."""
    ways = [1] + [0] * len(s)
    for end in range(1, len(s) + 1):
        for start in range(end):
            if ways[start]:
                ways[end] += ways[start] * sum(1 for alt in alternatives if alt.fullmatch(s, start, end))
    return ways[len(s)]


def test_font_style_alternatives_never_concatenate_into_another_way_to_split() -> None:
    # Two alternatives that concatenate into a third (or into another split of the same text) make a failing match
    # backtrack through every combination: `semi` + `bold` next to `semibold`. Every pair of the live pattern's
    # alternatives (`\d` stands for the digit "1") must split in the one way it was written.
    texts = [alt if alt.isalpha() else "1" for alt in _style_alternatives()]
    assert all(alt.isalpha() or alt == r"\d" for alt in _style_alternatives()), "an alternative that is neither a word nor `\\d`"
    compiled = [re.compile(alt) for alt in _style_alternatives()]

    ambiguous = [a + b for a in texts for b in texts if _style_splits(compiled, a + b) != 1]

    assert not ambiguous


def test_font_style_rejects_a_failing_name() -> None:
    # short on purpose: a pattern that backtracks fails the pair test above, and must not hang this one
    assert fonts._FONT_STYLE_RE.match("1" * 20 + "x") is None
    assert fonts._FONT_STYLE_RE.match("semibold" * 3 + "x") is None


# ------------------------------------------------------------------ typst_source.strip_comments_keep_urls

@settings(max_examples=200)
@given(st.lists(st.sampled_from(["/", "/", "*", "*", ":", "a", "Z", "_", "é", " ", "\n", "//", "/*", "*/", "[x]", "http://"]),
                max_size=40).map("".join))
def test_strip_comments_matches_the_regex_on_random_text(src: str) -> None:
    assert typst_source.strip_comments_keep_urls(src) == strip_comments_regex(src)


@pytest.mark.parametrize("src, want", [
    ("a /* b */ c", "a  c"),
    ("a // b\nc", "a \nc"),
    ("a /* unclosed [x]", "a /* unclosed [x]"),                    # an unclosed block comment is text
    ("/* unclosed\n// line\nrest", "/* unclosed\n\nrest"),         # ... and a line comment after it still goes
    ("http://x.org // y", "http://x.org "),                       # `//` after `:` or a word character is not a comment
    ("a/*b*/c", "ac"),
    ("/*/ x */y", "y"),                                           # `/*/` does not close itself
    ("// a /* b\nc */", "\nc */"),                                 # a line comment hides the `/*`
    ("/* a // b */ c", " c"),                                      # a block comment hides the `//`
    ("x///y", "x/"),                                              # the first `/` follows `x` (no comment); the second starts one
    ("", ""),
])
def test_strip_comments_cases(src: str, want: str) -> None:
    assert typst_source.strip_comments_keep_urls(src) == want == strip_comments_regex(src)


def test_strip_comments_equivalence_is_not_vacuous() -> None:
    # control: the random texts do contain comments to strip, so equality is not the identity on both sides
    rng = random.Random(1)
    alphabet = ["/", "*", ":", "a", "\n", "//", "/*", "*/"]
    srcs = ["".join(rng.choice(alphabet) for _ in range(40)) for _ in range(200)]

    assert sum(typst_source.strip_comments_keep_urls(s) != s for s in srcs) > 100


class _ScanStr(str):
    """A `str` that counts the characters its `find` scans (up to the hit, or to the end when it fails): the C-level
    work of a search that restarts from every unclosed `/*`, which the line-event count cannot see."""
    scanned = 0
    calls = 0

    def find(self, sub: str, start: SupportsIndex | None = None, end: SupportsIndex | None = None, /) -> int:
        _ScanStr.calls += 1
        begin = 0 if start is None else operator.index(start)
        found = str.find(self, sub, start, end)
        _ScanStr.scanned += (len(self) if found < 0 else found) - begin
        return found


_COMMENT_FILES = frozenset({typst_source.strip_comments_keep_urls.__code__.co_filename, fonts.requested_families.__code__.co_filename})


def _scan_work(strip: Callable[[str], object], src: str) -> int:
    """Python line events in `typst_source` and `fonts` plus characters scanned by `find` on the source text."""
    _ScanStr.scanned = _ScanStr.calls = 0
    events, out = line_events(_COMMENT_FILES, lambda: strip(_ScanStr(src)))
    assert out
    # the scan went through the counted `find`: a regex (`re.sub(r"/\*.*?\*/")`) scans in C without calling it, and
    # its quadratic rescan would go unseen
    assert _ScanStr.calls > 0
    assert _ScanStr.scanned > 0
    return events + _ScanStr.scanned


@pytest.mark.parametrize("unit", ["/* ", "/*", "/* // ", "/*\n// x\n"])
def test_strip_comments_work_grows_linearly_on_unclosed_block_comments(unit: str) -> None:
    # the regex it replaced rescanned to the end of the text from every unclosed `/*` (13.9 s on 100 000 characters)
    assert_linear(lambda n: _scan_work(typst_source.strip_comments_keep_urls, unit * (n // len(unit))), 4000)


# ------------------------------------------------------------------ typst_source.strip_block_comments

@settings(max_examples=200)
@given(st.lists(st.sampled_from(["/", "*", "/", "*", "a", "\n", "/*", "*/", "/**/", " "]), max_size=40).map("".join))
def test_strip_block_comments_matches_the_regex_on_random_text(src: str) -> None:
    assert typst_source.strip_block_comments(src) == strip_block_comments_regex(src)


@pytest.mark.parametrize("src, want", [
    ("a /* b */ c", "a  c"),
    ("a /* b */ c /* d */ e", "a  c  e"),
    ("a /* unclosed", "a /* unclosed"),
    ("/* closed */ x /* unclosed", " x /* unclosed"),
    ("/*/ x", "/*/ x"),                             # `/*/` does not close itself
    ("/**/x", "x"),
    ("/* a\nb */c", "c"),                           # across lines
    ("/* a /* b */ c */", " c */"),                 # not nested: the first `*/` closes
    ("", ""),
])
def test_strip_block_comments_cases(src: str, want: str) -> None:
    assert typst_source.strip_block_comments(src) == want == strip_block_comments_regex(src)


@pytest.mark.parametrize("unit", ["/* ", "/*", "/*\n"])
def test_requested_families_work_grows_linearly_on_unclosed_block_comments(unit: str) -> None:
    # the regex rescanned to the end of the text from every unclosed `/*` (11 s on 100 000 characters)
    assert_linear(lambda n: _scan_work(fonts.requested_families, unit * (n // len(unit))), 4000)
