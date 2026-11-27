"""verify.text hot spots: `hidden_word_stats` (a luminance memo per call, two luminances per word box instead of one
per colour), `_classify_runs` (a segment tree instead of a neighbour walk per
tiny run) and `_merged_runs` (one join per run instead of a growing string). Each keeps its behaviour (equivalence with
the replaced code, kept in `_hidden_ref`, on realistic and worst-case inputs) and stays fast on a worst-case input
(`slow`: wall time bounded far above the measured time and far below the old one)."""
from __future__ import annotations

import math
import random
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest
from _hidden_ref import classify_runs_quadratic, hidden_word_stats_per_colour, merged_runs_concat
from hypothesis import given, settings
from hypothesis import strategies as st
from PIL import Image
from vitae.core.base import HIDDEN_PPI, HiddenStat, WordBox
from vitae.core.colour import rel_luminance
from vitae.verify import text

SC = HIDDEN_PPI / 72.0
Page = tuple[float, float, list[WordBox]]

# ------------------------------------------------------------------ hidden_word_stats


def _raster(kind: str, seed: int, w: int, h: int) -> Image.Image:
    """A page raster: `gray` (black text on white, antialiasing levels), `colour` (a few inks and grounds, some one
    level apart so luminance ties and near ties occur), `noise` (thousands of colours), `ramp` (every
    gray level)."""
    rng = random.Random(seed)
    if kind == "ramp":
        return Image.frombytes("RGB", (w, h), bytes(v for i in range(w * h) for v in [(i * 7) % 256] * 3))
    if kind == "noise":
        return Image.frombytes("RGB", (w, h), rng.randbytes(3 * w * h))
    if kind == "gray":
        palette = [(v, v, v) for v in (0, 40, 128, 200, 255, 255, 255)]
    else:
        palette = [(255, 255, 255), (255, 255, 254), (10, 20, 30), (200, 30, 30), (30, 30, 200), (250, 250, 250), (0, 0, 0)]
    im = Image.new("RGB", (w, h), palette[0])
    for _ in range(rng.randint(2, 30)):
        x, y = rng.randint(0, w - 1), rng.randint(0, h - 1)
        im.paste(rng.choice(palette), (x, y, x + rng.randint(1, w // 2), y + rng.randint(1, h // 3)))
    return im


@st.composite
def _pages(draw: st.DrawFn) -> tuple[Image.Image, Page]:
    kind = draw(st.sampled_from(["gray", "gray", "colour", "colour", "noise", "ramp"]))
    w, h = draw(st.integers(8, 60)), draw(st.integers(8, 50))
    im = _raster(kind, draw(st.integers(0, 10**6)), w, h)
    coord = st.floats(-4.0, w / SC + 4.0, allow_nan=False)
    items: list[WordBox] = []
    for _ in range(draw(st.integers(0, 12))):
        x0, y0 = draw(coord), draw(st.floats(-4.0, h / SC + 4.0, allow_nan=False))
        items.append(((x0, y0, x0 + draw(st.floats(0.0, 12.0)), y0 + draw(st.floats(0.0, 6.0))),
                      draw(st.sampled_from(["word", "a", "x1", "--"]))))
    return im, (w / SC, h / SC, items)


def _both(im: Image.Image, page: Page) -> tuple[list[HiddenStat], list[HiddenStat]]:
    with tempfile.TemporaryDirectory() as tmp:
        png = str(Path(tmp) / "p.png")
        im.save(png)
        expected = hidden_word_stats_per_colour("x.pdf", pages=[page], pngs=[png])
        return text.hidden_word_stats("x.pdf", pages=[page], pngs=[png]), expected


@settings(deadline=None, max_examples=300)
@given(_pages())
def test_word_stats_match_the_per_colour_version(case: tuple[Image.Image, Page]) -> None:
    got, expected = _both(*case)

    assert got == expected


def test_word_stats_equivalence_is_not_vacuous() -> None:
    # control: ratios span all three bands (FAIL under 1.5, WARN under 3, clean) on gray, colour, noise and ramp pages
    ratios: set[str] = set()
    for kind in ("gray", "colour", "noise", "ramp"):
        for seed in range(6):
            im = _raster(kind, seed, 60, 50)
            page: Page = (60 / SC, 50 / SC, [((x / SC, y / SC, (x + 14) / SC, (y + 8) / SC), "ab") for x in (0, 20, 40) for y in (0, 20, 40)])
            got, expected = _both(im, page)
            assert got == expected
            ratios |= {"fail" if r < 1.5 else "warn" if r < 3 else "ok" for _, _, _, _, r, _ in got if r is not None}
    pale = Image.new("RGB", (60, 50), (255, 255, 255))   # pale ink (level 200) on white: barely visible, 1.5 <= ratio < 3
    pale.paste((200, 200, 200), (2, 2, 12, 8))
    got, expected = _both(pale, (60 / SC, 50 / SC, [((0.0, 0.0, 14 / SC, 8 / SC), "ab")]))
    assert got == expected
    ratios |= {"fail" if r < 1.5 else "warn" if r < 3 else "ok" for _, _, _, _, r, _ in got if r is not None}
    assert ratios == {"fail", "warn", "ok"}


def test_background_tie_goes_to_the_larger_colour() -> None:
    # half black, half white: both are the most common colour; the larger one (white) is the background, so the
    # strongest pixel is black against white, ratio 21 (the other way round gives the same, but a tie broken on the
    # smaller level would not differ here: add a mid-gray box to make the choice visible)
    im = Image.new("RGB", (20, 10), (255, 255, 255))
    im.paste((0, 0, 0), (0, 0, 10, 10))
    box: WordBox = ((0.0, 0.0, 20 / SC - 1.5 / SC, 10 / SC - 1.5 / SC), "ab")
    got, expected = _both(im, (20 / SC, 10 / SC, [box]))

    assert got == expected
    assert got[0][4] == pytest.approx(21.0)


def _text_like_page(w: int, h: int, words: int, kind: str) -> tuple[Image.Image, Page]:
    rng = random.Random(7)
    im = _raster(kind, 3, w, h) if kind == "noise" else Image.new("RGB", (w, h), (255, 255, 255))
    items: list[WordBox] = []
    for i in range(words):
        x, y = rng.randint(0, w - 80), rng.randint(0, h - 30)
        if kind != "noise":
            ink = (rng.randint(0, 255),) * 3 if kind == "gray" else (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))
            for k in range(0, 60, 3):
                im.paste(ink, (x + k, y + 4, x + k + 2, y + 16))
        items.append(((x / SC, y / SC, (x + 60) / SC, (y + 18) / SC), f"w{i}"))
    return im, (w / SC, h / SC, items)


@pytest.mark.parametrize("kind", ["gray", "colour"])
def test_word_stats_compute_one_luminance_per_page_colour(kind: str) -> None:
    # the old code called `_lum` once per distinct colour of EVERY word box (~150 per word on a real page)
    im, page = _text_like_page(400, 300, 200, kind)
    colours = len(im.getcolors(400 * 300) or [])
    calls = 0
    real = rel_luminance

    def counting(rgb: tuple[int, ...]) -> float:
        nonlocal calls
        calls += 1
        return real(rgb)
    with tempfile.TemporaryDirectory() as tmp, mock.patch.object(text, "_lum", counting):
        png = str(Path(tmp) / "p.png")
        im.save(png)
        out = text.hidden_word_stats("x.pdf", pages=[page], pngs=[png])

    assert len(out) == 200 and 0 < colours <= 65536
    assert calls <= colours


@pytest.mark.slow
@pytest.mark.parametrize(("kind", "bound"), [("gray", 1.5), ("colour", 1.5), ("noise", 6.0)])
def test_word_stats_bound_time_on_a_full_page(kind: str, bound: float) -> None:
    im, page = _text_like_page(1275, 1650, 3000, kind)
    with tempfile.TemporaryDirectory() as tmp:
        png = str(Path(tmp) / "p.png")
        im.save(png)
        start = time.perf_counter()

        out = text.hidden_word_stats("x.pdf", pages=[page], pngs=[png])

        assert time.perf_counter() - start < bound   # measured ~0.05 s (gray, colour) and ~2.1 s (noise: 1000+ colours per box; bound 6.0 s = 2.9x margin); a coarse bound, the constant factor is tested by call count
    assert len(out) == 3000

# ------------------------------------------------------------------ _classify_runs

Run = tuple[str, float, float, float]
BOX = (0.0, 0.0, 600.0, 800.0)


@st.composite
def _run_lists(draw: st.DrawFn) -> list[Run]:
    sizes = st.sampled_from([0.0, 2.0, 2.3, 3.0, 4.0, 4.6, 4.9, 5.0, 5.5, 6.0, 6.9, 8.0, 9.6, 12.0, math.nan, math.inf])
    ys = st.sampled_from([100.0, 100.0, 100.3, 100.5, 101.0, 102.4, 103.0, 106.0, 99.5, 400.0, -9.0, 900.0, math.nan, math.inf])
    xs = st.sampled_from([10.0, 20.0, 30.0, 50.0, 700.0, -50.0, 15.5])
    n = draw(st.integers(0, 14))
    return [(f"t{i}", draw(xs), draw(ys), draw(sizes)) for i in range(n)]


@settings(deadline=None, max_examples=2000)
@given(_run_lists())
def test_classify_runs_matches_the_neighbour_walk(runs: list[Run]) -> None:
    assert text._classify_runs(runs, BOX) == classify_runs_quadratic(runs, BOX)


def test_classify_runs_equivalence_is_not_vacuous() -> None:
    # control: a "10th" superscript is dropped, a loose tiny block is merged and reported at its smallest size, and an
    # off-page run is found, so equality is not "([], []) == ([], [])"
    runs: list[Run] = [("10", 10.0, 100.0, 9.6), ("th", 20.0, 103.0, 4.0), ("tiny", 30.0, 300.0, 4.0), ("small", 40.0, 300.0, 3.0),
                       ("away", 900.0, 300.0, 9.0)]
    off, tiny = text._classify_runs(runs, BOX)

    assert (off, tiny) == (["away"], [("tiny small", 3.0)])
    assert (off, tiny) == classify_runs_quadratic(runs, BOX)


def test_classify_runs_a_superscript_between_equal_sizes_is_still_found() -> None:
    # the walk skips same-size neighbours on the baseline ("10th" may be two runs): 4 tiny runs, then the larger one
    runs: list[Run] = [("big", 10.0, 100.0, 9.0), ("a", 20.0, 103.0, 4.0), ("b", 25.0, 103.0, 4.0), ("c", 30.0, 103.0, 4.0)]

    assert text._classify_runs(runs, BOX) == classify_runs_quadratic(runs, BOX) == ([], [])


@pytest.mark.slow
def test_classify_runs_bounds_time_on_one_baseline() -> None:
    runs: list[Run] = [(f"w{i}", 10.0 + i * 0.01, 300.0, 3.0) for i in range(8000)]
    start = time.perf_counter()

    off, tiny = text._classify_runs(runs, BOX)

    assert time.perf_counter() - start < 1.0     # measured ~0.05 s; the neighbour walk and the string `+` took ~5 s
    assert off == [] and len(tiny) == 1 and tiny[0][1] == 3.0 and tiny[0][0].count(" ") == 7999

# ------------------------------------------------------------------ _merged_runs


def _stats(picks: list[tuple[int, bool]]) -> list[HiddenStat]:
    return [(pno, f"w{i}", (0.0, 0.0, 1.0, 1.0), 1.0, 1.0 if sel else 9.0, False) for i, (pno, sel) in enumerate(picks)]


@settings(deadline=None, max_examples=500)
@given(st.lists(st.tuples(st.integers(1, 3), st.booleans()), max_size=30))
def test_merged_runs_match_the_concatenation(picks: list[tuple[int, bool]]) -> None:
    stats = _stats(picks)

    def pick(st_: HiddenStat) -> bool:
        return st_[4] is not None and st_[4] < 2.0

    assert text._merged_runs(stats, pick) == merged_runs_concat(stats, pick)


def test_merged_runs_equivalence_is_not_vacuous() -> None:
    # control: adjacent words merge, a gap or a page change splits
    stats = _stats([(1, True), (1, True), (1, False), (1, True), (2, True), (2, True)])

    assert text._merged_runs(stats, lambda s: s[4] is not None and s[4] < 2.0) == [(1, "w0 w1"), (1, "w3"), (2, "w4 w5")]


@pytest.mark.slow
def test_merged_runs_bound_time_on_one_long_run() -> None:
    stats = _stats([(1, True)] * 150000)
    start = time.perf_counter()

    out = text._merged_runs(stats, lambda s: True)

    assert time.perf_counter() - start < 1.0     # measured ~0.02 s; growing the string took ~3 s at 150000 words
    assert len(out) == 1 and out[0][1].count(" ") == 149999
