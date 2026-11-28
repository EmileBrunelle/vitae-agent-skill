"""verify.text hot spots: `hidden_word_stats` (a luminance memo per call, two luminances per word box instead of one
per colour), `_classify_runs` (a segment tree instead of a neighbour walk per
tiny run) and `_merged_runs` (one join per run instead of a growing string). Each keeps its behaviour (equivalence with
the replaced code, kept in `_hidden_ref`, on realistic and worst-case inputs) and stays fast on a worst-case input
(work counted in Python line events, calls and concatenated characters, no wall clock: a loaded runner cannot flip it)."""
from __future__ import annotations

import math
import random
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path

import _hidden_ref
import pytest
from _complexity import assert_linear, line_events
from _hidden_ref import classify_runs_quadratic, hidden_word_stats_per_colour, merged_runs_concat
from hypothesis import given, settings
from hypothesis import strategies as st
from PIL import Image
from vitae.core import colour
from vitae.core.base import HIDDEN_PPI, HiddenStat, WordBox
from vitae.core.colour import counted_luminances, rel_luminance
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


def test_counted_luminances_are_bit_identical_to_rel_luminance() -> None:
    rng = random.Random(3)
    sample = [(rng.randrange(256), rng.randrange(256), rng.randrange(256)) for _ in range(20000)]
    sample += [(g, g, g) for g in range(256)]
    sample += [c for v in range(256) for c in ((v, 0, 0), (0, v, 0), (0, 0, v))]
    got = counted_luminances((1, c) for c in sample)

    assert got == [rel_luminance(c) for c in sample]   # == on floats: same bits, not approximately equal


_TEXT_WORK = frozenset({text.__file__, colour.__file__})


def _stats_events(tmp_path: Path, kind: str, words: int, monkeypatch: pytest.MonkeyPatch) -> tuple[int, int, int]:
    """(line events of `hidden_word_stats` on a full-size page of `words` word boxes, luminances computed one by one,
    colours handed to `counted_luminances`): the C-level work of `getcolors` is one pass per box either way."""
    im, page = _text_like_page(1275, 1650, words, kind)
    png = str(tmp_path / f"p{kind}{words}.png")
    im.save(png)
    singles = [0]
    handed = [0]

    def counting_lum(rgb: tuple[int, int, int] | tuple[int, ...]) -> float:
        singles[0] += 1
        return rel_luminance(rgb)

    def counting_many(counted: Iterable[tuple[int, Sequence[int]]]) -> list[float]:
        pairs = list(counted)
        handed[0] += len(pairs)
        return counted_luminances(pairs)

    monkeypatch.setattr(text, "rel_luminance", counting_lum)
    monkeypatch.setattr(text, "counted_luminances", counting_many)
    events, out = line_events(_TEXT_WORK, lambda: text.hidden_word_stats("x.pdf", pages=[page], pngs=[png]))
    assert len(out) == words
    return events, singles[0], handed[0]


@pytest.mark.parametrize("kind", ["gray", "colour", "noise"])
def test_word_stats_work_grows_linearly_with_the_words_of_a_full_page(kind: str, tmp_path: Path,
                                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[int, int]] = []

    def measure(words: int) -> int:
        events, singles, handed = _stats_events(tmp_path, kind, words, monkeypatch)
        seen.append((singles, handed))
        return events

    assert_linear(measure, 100)
    for (singles, handed), words in zip(seen, (100, 200, 400), strict=True):
        assert singles == words                  # one luminance for the box's background; the rest come from the tables
        assert handed >= words                   # the table path ran: at least one colour per box


@pytest.mark.parametrize(("kind", "least"), [("gray", 3), ("colour", 3), ("noise", 1000)])
def test_word_stats_computes_far_fewer_luminances_than_one_per_colour(kind: str, least: int, tmp_path: Path,
                                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    # control: the per-colour reference calls `_lum` once per distinct colour of every box
    words = 100
    _, singles, _ = _stats_events(tmp_path, kind, words, monkeypatch)
    im, page = _text_like_page(1275, 1650, words, kind)
    png = str(tmp_path / f"ref{kind}.png")
    im.save(png)
    ref_calls = [0]

    def counting_ref_lum(rgb: tuple[int, int, int] | tuple[int, ...]) -> float:
        ref_calls[0] += 1
        return rel_luminance(rgb)

    monkeypatch.setattr(_hidden_ref, "_lum", counting_ref_lum)
    expected = hidden_word_stats_per_colour("x.pdf", pages=[page], pngs=[png])

    assert singles == words
    assert ref_calls[0] >= least * singles       # measured 3.2x (gray, colour: ~3 colours a box) and ~1300x (noise)
    assert len(expected) == words

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


class _AddStr(str):
    """A `str` that counts the characters copied by each `+` (C-level work the line-event count cannot see) and
    survives it: a run text grown by `+` copies its whole length each time (quadratic), one `join` copies none here."""
    copied = 0

    def __add__(self, other: str) -> _AddStr:
        _AddStr.copied += len(self) + len(other)
        return _AddStr(str.__add__(self, other))

    def __radd__(self, other: str) -> _AddStr:
        _AddStr.copied += len(self) + len(other)
        return _AddStr(str.__add__(other, self))


_ONE_BASELINE = 3.0


def _one_baseline(n: int) -> list[Run]:
    return [(_AddStr(f"w{i}"), 10.0 + i * 0.01, 300.0, _ONE_BASELINE) for i in range(n)]


def test_classify_runs_work_grows_linearly_on_one_baseline() -> None:
    results: list[tuple[list[str], list[tuple[str, float]]]] = []

    def measure(n: int) -> int:
        _AddStr.copied = 0
        events, result = line_events(frozenset({text.__file__}), lambda: text._classify_runs(_one_baseline(n), BOX))
        results.append(result)
        return events

    assert_linear(measure, 2000)
    assert _AddStr.copied == 0                   # the block text is joined once, never grown by `+`
    for (off, tiny), n in zip(results, (2000, 4000, 8000), strict=True):
        assert off == [] and len(tiny) == 1      # one block of tiny runs, none taken for a script
        assert tiny[0][1] == _ONE_BASELINE and tiny[0][0].count(" ") == n - 1


def test_the_work_counts_tell_the_neighbour_walk_and_the_concatenation_from_the_linear_version() -> None:
    # control: on the same input the reference's line events and `+` copies grow ~4x per doubling
    ref_files = frozenset({_hidden_ref.__file__})

    def ref_events(n: int) -> int:
        _AddStr.copied = 0
        events, _ = line_events(ref_files, lambda: classify_runs_quadratic(_one_baseline(n), BOX))
        return events

    e1, e2 = ref_events(250), ref_events(500)
    c1 = _AddStr.copied
    assert e2 / e1 > 3.0                         # the neighbour walk is quadratic in the tiny runs of a baseline
    assert c1 > 0                                # and the concatenation copies the growing text


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


def _long_run(n: int) -> list[HiddenStat]:
    return [(1, _AddStr(f"w{i}"), (0.0, 0.0, 1.0, 1.0), 1.0, 1.0, False) for i in range(n)]


def test_merged_runs_work_grows_linearly_on_one_long_run() -> None:
    outs: list[list[tuple[int, str]]] = []

    def measure(n: int) -> int:
        _AddStr.copied = 0
        events, out = line_events(frozenset({text.__file__}), lambda: text._merged_runs(_long_run(n), lambda s: True))
        outs.append(out)
        return events

    assert_linear(measure, 20000)
    assert _AddStr.copied == 0                   # one join per run, never `+` on a growing string
    for out, n in zip(outs, (20000, 40000, 80000), strict=True):
        assert len(out) == 1 and out[0][1].count(" ") == n - 1


def test_the_copy_count_tells_the_concatenation_from_the_join() -> None:
    # control: the `+` reference copies the growing text at every word: ~4x the characters per doubling
    def ref_copies(n: int) -> int:
        _AddStr.copied = 0
        out = merged_runs_concat(_long_run(n), lambda s: True)
        assert len(out) == 1 and out[0][1].count(" ") == n - 1
        return _AddStr.copied

    c1, c2 = ref_copies(500), ref_copies(1000)

    assert c1 > 0
    assert c2 / c1 > 3.0
