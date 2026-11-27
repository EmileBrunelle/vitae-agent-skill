"""LOG320 lot: the three hot spots fixed for complexity keep their behaviour (equivalence with the replaced code, on
fixed cases and seeded random inputs) and stay fast on a worst-case input (`slow`: bounded wall time, far above the
measured time and far below the old one, so a noisy runner does not flip it but a return to O(P^2) does)."""
import itertools
import random
import re
import time

import pytest
from _reading_order_ref import reading_order_quadratic
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
