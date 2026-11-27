"""LOG320 lot: the three hot spots fixed for complexity keep their behaviour (equivalence with the replaced code, on
fixed cases and seeded random inputs) and stay fast on a worst-case input (`slow`: bounded wall time, far above the
measured time and far below the old one, so a noisy runner does not flip it but a return to O(P^2) does)."""
import itertools
import random
import re
import time

import pytest
from _comments_ref import strip_block_comments_regex, strip_comments_regex
from _reading_order_ref import reading_order_quadratic
from vitae.core.base import WordBox
from vitae.verify import fonts, pdf, placeholders, text, typst

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


@pytest.mark.parametrize("seed", range(400))
def test_reading_order_matches_the_quadratic_version(seed: int) -> None:
    words = _random_page(random.Random(seed))

    assert pdf._reading_order(words) == reading_order_quadratic(words)


@pytest.mark.parametrize("seed", range(300))
def test_reading_order_row_grouping_matches_on_mixed_heights_and_near_baselines(seed: int) -> None:
    """Words of different heights on baselines a few points apart: whether one joins the row depends on the smallest
    box already in it, and on the mean baseline of the words already in it."""
    rng = random.Random(seed)
    words: list[WordBox] = []
    for k in range(rng.randint(3, 14)):
        h = rng.choice((3.0, 6.0, 10.0))
        y = rng.uniform(0, 8)
        x = rng.uniform(0, 400)
        words.append(((x, y, x + rng.uniform(5, 40), y + h), f"w{k}"))

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


@pytest.mark.parametrize("seed", range(400))
def test_reading_order_overlapping_side_pieces_match_the_oracle_on_random_pages(seed: int) -> None:
    """A head row of pieces with long words among short ones (overlapping pieces), narrow words in the rows below."""
    rng = random.Random(seed)
    words: list[WordBox] = [((0.0, 0.0, 30.0, 10.0), "head")]
    for k in range(rng.randint(2, 7)):
        x = rng.uniform(100, 400)
        w = rng.choice((5.0, 10.0, 20.0, 150.0, 250.0))
        words.append(((x, 0.0, x + w, 10.0), f"s{k}"))
    for r in range(1, rng.randint(2, 5)):
        for k in range(rng.randint(1, 3)):
            x = rng.choice((0.0, rng.uniform(0, 600)))
            words.append(((x, r * 12.0, x + rng.uniform(5, 40), r * 12.0 + 10), f"r{r}w{k}"))
    rng.shuffle(words)

    assert pdf._reading_order(words) == reading_order_quadratic(words)


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


@pytest.mark.slow
def test_reading_order_bounds_time_on_a_large_table() -> None:
    words = _grid(8000)
    start = time.perf_counter()

    out = pdf._reading_order(words)

    assert time.perf_counter() - start < 1.0     # measured ~0.05 s; the quadratic version takes ~6 s
    assert len(out) == len(words)


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


@pytest.mark.slow
def test_reading_order_bounds_time_on_a_single_baseline() -> None:
    words = _one_baseline(8000)
    start = time.perf_counter()

    out = pdf._reading_order(words)

    assert time.perf_counter() - start < 1.0     # measured ~0.03 s; recomputing the row's mean per word took ~4 s
    assert out == words


@pytest.mark.slow
def test_reading_order_bounds_time_on_many_side_pieces_then_many_rows() -> None:
    words = _side_then_rows(3000)
    start = time.perf_counter()

    out = pdf._reading_order(words)

    assert time.perf_counter() - start < 0.5     # measured ~0.03 s; rescanning the rows per side piece took ~1.8 s
    assert len(out) == len(words)


def test_reading_order_matches_the_oracle_on_the_side_piece_worst_cases() -> None:
    """The scale-down of the two worst cases above, plus side pieces that overlap rows below (control: they do reorder)."""
    for words in (_one_baseline(60), _side_then_rows(25)):
        assert pdf._reading_order(words) == reading_order_quadratic(words)
    under = _side_then_rows(8) + [((105.0 + i * 80, 33.0 + i * 12, 150.0 + i * 80, 43.0 + i * 12), f"u{i}") for i in range(4)]
    got = pdf._reading_order(under)
    assert got == reading_order_quadratic(under)
    assert got != sorted(under, key=lambda t: (t[0][1], t[0][0]))


# ------------------------------------------------------------------ _stuffed

def _stuffed_old(t: str, max_terms: int = 0) -> str | None:
    terms = [x.strip().lower() for x in re.split(r"[,;]", t) if x.strip()]
    if len(terms) <= 1:
        terms = t.lower().split()
    words = re.findall(r"\w+", t.lower())
    repeated = sorted({x for x in terms if terms.count(x) > 1} | {w for w in words if len(w) > 2 and words.count(w) > 2})
    if (max_terms and len(terms) > max_terms) or repeated:
        return f"{len(terms)} terms" + (f", repeats {', '.join(r[:20] for r in repeated[:3])}" if repeated else "")
    return None


@pytest.mark.parametrize("seed", range(300))
def test_stuffed_matches_the_counting_version(seed: int) -> None:
    rng = random.Random(seed)
    vocab = ["python", "Python", "sql", "go", "a", "data", "rust", "ops", "été", "Été", "x1"]
    sep = rng.choice((", ", "; ", " ", ",", " , "))
    t = sep.join(rng.choice(vocab) for _ in range(rng.randint(0, 25)))
    cap = rng.choice((0, 5, 12))

    assert text._stuffed(t, cap) == _stuffed_old(t, cap)


@pytest.mark.parametrize("t, want", [
    ("python, sql, python", True),                 # a term used twice
    ("data data data", True),                      # a 3+ letter word used three times
    ("go, sql, python", False),
    ("python, sql, rust", False),
])
def test_stuffed_signals(t: str, want: bool) -> None:
    assert (text._stuffed(t) is not None) is want


@pytest.mark.slow
def test_stuffed_bounds_time_on_a_long_distinct_list() -> None:
    t = ", ".join(f"t{i}" for i in range(200_000))
    start = time.perf_counter()

    out = text._stuffed(t, max_terms=0)

    assert time.perf_counter() - start < 1.0      # measured ~0.02 s; the counting version takes ~12 s
    assert out is None


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


@pytest.mark.slow
@pytest.mark.parametrize("s", ["1" * 26 + "x", "semibold" * 22 + "x", "extralight" * 22 + "x", "1" * 20000 + "x"])
def test_font_style_bounds_time_on_a_pathological_name(s: str) -> None:
    start = time.perf_counter()

    out = fonts._FONT_STYLE_RE.match(s)

    assert time.perf_counter() - start < 0.5      # linear; the old pattern backtracks exponentially (26 digits: ~6 s; sized so the old pattern fails the bound instead of hanging the run)
    assert out is None


# ------------------------------------------------------------------ placeholders.strip_comments

@pytest.mark.parametrize("seed", range(600))
def test_strip_comments_matches_the_regex_on_random_text(seed: int) -> None:
    rng = random.Random(seed)
    alphabet = ["/", "/", "*", "*", ":", "a", "Z", "_", "é", " ", "\n", "//", "/*", "*/", "[x]", "http://"]
    src = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 40)))

    assert placeholders.strip_comments(src) == strip_comments_regex(src)


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
    assert placeholders.strip_comments(src) == want == strip_comments_regex(src)


def test_strip_comments_equivalence_is_not_vacuous() -> None:
    # control: the random texts do contain comments to strip, so equality is not the identity on both sides
    rng = random.Random(1)
    alphabet = ["/", "*", ":", "a", "\n", "//", "/*", "*/"]
    srcs = ["".join(rng.choice(alphabet) for _ in range(40)) for _ in range(200)]

    assert sum(placeholders.strip_comments(s) != s for s in srcs) > 100


@pytest.mark.slow
@pytest.mark.parametrize("unit", ["/* ", "/*", "/* // ", "/*\n// x\n"])
def test_strip_comments_bounds_time_on_unclosed_block_comments(unit: str) -> None:
    src = unit * (100_000 // len(unit))
    start = time.perf_counter()

    out = placeholders.strip_comments(src)

    assert time.perf_counter() - start < 0.5      # measured ~0.01 s; the regex takes ~12 s on the first case
    assert isinstance(out, str)


# ------------------------------------------------------------------ typst.strip_block_comments

@pytest.mark.parametrize("seed", range(600))
def test_strip_block_comments_matches_the_regex_on_random_text(seed: int) -> None:
    rng = random.Random(seed)
    alphabet = ["/", "*", "/", "*", "a", "\n", "/*", "*/", "/**/", " "]
    src = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 40)))

    assert typst.strip_block_comments(src) == strip_block_comments_regex(src)


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
    assert typst.strip_block_comments(src) == want == strip_block_comments_regex(src)


@pytest.mark.slow
@pytest.mark.parametrize("unit", ["/* ", "/*", "/*\n"])
def test_requested_families_bounds_time_on_unclosed_block_comments(unit: str) -> None:
    src = unit * (100_000 // len(unit))
    start = time.perf_counter()

    out = fonts.requested_families(src)

    assert time.perf_counter() - start < 0.5      # measured ~0.01 s; the regex took ~11 s
    assert out                                    # no font asked: Typst's own defaults
