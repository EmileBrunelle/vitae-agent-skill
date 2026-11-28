"""Raster hot spots moved from Python pixel loops to Pillow: `layout.check_text_clip` (flat-box test of every word box)
and `fill.bands` (dark rows and rule-wide rows of a page). Each keeps its behaviour (equivalence with the replaced code,
kept in `_raster_ref`, on Hypothesis-generated rasters and on a real rendered page) and stays fast on a full page (work
counted in Python line events and at the Python/C boundary, no wall clock, so a loaded runner cannot flip it but a return
to a per-pixel loop does)."""
import math
import random
import tempfile
from collections.abc import Callable
from pathlib import Path

import _raster_ref
import pytest
from _complexity import assert_linear, line_events
from _paths import ROOT
from _raster_ref import bands_per_row, check_text_clip_per_pixel
from hypothesis import given, settings
from hypothesis import strategies as st
from PIL import Image
from vitae import fill
from vitae.core.base import WordBox
from vitae.core.pixels import colour_counts
from vitae.verify import layout
from vitae.verify.layout import check_text_clip
from vitae.verify.page import FURNITURE_SCALE
from vitae.verify.pdf import pdfium_render, typst_compile, word_boxes

S = FURNITURE_SCALE
WHITE = (255, 255, 255)
# A seeded generator per example: the raster builders draw thousands of values, too many to take from Hypothesis' own
# data (health check `large_base_example`); the seed is what a failing example prints and what `random.Random` replays.
_rngs = st.builds(random.Random, st.integers(0, 2**32))

# ------------------------------------------------------------------ check_text_clip


def _random_page(rng: random.Random) -> tuple[Image.Image, list[WordBox]]:
    """A 300x200 page: a tinted or white paper, 1-3 filled bands (some pale, some dark), hairline rules, glyph-like
    marks in colours that sometimes match the ground under them, and 4-14 word boxes (some on the marks, some on
    bare ground, some straddling a band's edge)."""
    paper = rng.choice([WHITE, WHITE, (245, 240, 225), (30, 30, 40)])
    im = Image.new("RGB", (300, 200), paper)
    for _ in range(rng.randint(1, 3)):
        y0 = rng.randint(0, 150)
        im.paste(rng.choice([(60, 60, 60), (200, 30, 30), (235, 235, 235), (20, 90, 160)]),
                 (0, y0, rng.choice([300, 180]), y0 + rng.randint(15, 60)))
    for _ in range(rng.randint(0, 3)):
        y = rng.randint(0, 195)
        im.paste((0, 0, 0), (rng.randint(0, 100), y, rng.randint(150, 300), y + rng.randint(1, 2)))
    boxes: list[WordBox] = []
    for _ in range(rng.randint(4, 14)):
        x, y = rng.randint(5, 220), rng.randint(2, 170)
        w, h = rng.randint(20, 70), rng.randint(8, 18)
        ink = rng.choice([WHITE, (0, 0, 0), (200, 30, 30), paper, (paper[0] ^ 20, paper[1], paper[2])])
        for gx in range(x + 2, x + w - 2, rng.choice([3, 4, 6])):
            im.paste(ink, (gx, y + 3, gx + 2, y + h - 3))
        boxes.append(((x / S, y / S, (x + w) / S, (y + h) / S), rng.choice(["linkedin.com", "Skills", "a", "Title"])))
    return im, boxes


@settings(max_examples=250)
@given(_rngs)
def test_text_clip_matches_the_per_pixel_version(rng: random.Random) -> None:
    im, boxes = _random_page(rng)
    with tempfile.TemporaryDirectory() as tmp:
        png = str(Path(tmp) / "p.png")
        im.save(png)

        assert check_text_clip(png, boxes) == check_text_clip_per_pixel(png, boxes)


def test_text_clip_equivalence_is_not_vacuous(tmp_path: Path) -> None:
    # control: the random pages exercise both findings and the quiet path, so equality is not "[] == []"
    kinds = {"cut": 0, "hidden": 0, "quiet": 0}
    for seed in range(250):
        im, boxes = _random_page(random.Random(seed))
        png = tmp_path / f"p{seed}.png"
        im.save(png)
        msgs = check_text_clip(str(png), boxes)
        kinds["cut"] += any("is cut by" in m for m in msgs)
        kinds["hidden"] += any("indistinguishable" in m for m in msgs)
        kinds["quiet"] += not msgs

    assert min(kinds.values()) >= 15, kinds


@pytest.fixture(scope="session")
def resume_pdf(tmp_path_factory: pytest.TempPathFactory) -> str:
    """templates/resume.typ compiled once into a temp dir (the PDF is untracked, a fresh clone does not have it)."""
    pdf = str(tmp_path_factory.mktemp("resume") / "resume.pdf")
    ok, err = typst_compile(str(ROOT / "templates" / "resume.typ"), pdf)
    if not ok:
        pytest.skip(f"templates/resume.typ does not compile here: {err.strip()[:200]}")
    return pdf


def _rendered_page(pdf: str, tmp_path: Path) -> tuple[str, list[WordBox]]:
    """The shipped templates/resume.typ compiled and rendered at 90 ppi (pdfium) with its words: a real page, real glyph
    anti-aliasing."""
    pages = word_boxes(pdf, with_text=True)
    if not pages:
        pytest.skip("no word boxes available for the compiled templates/resume.typ")
    png = tmp_path / "resume.png"
    pdfium_render(pdf, 90)[0].save(png)
    return str(png), pages[0]


def test_text_clip_matches_on_a_real_page(resume_pdf: str, tmp_path: Path) -> None:
    png, words = _rendered_page(resume_pdf, tmp_path)

    assert len(words) > 100
    assert check_text_clip(png, words) == check_text_clip_per_pixel(png, words)


def test_text_clip_real_page_equivalence_catches_a_hidden_word(resume_pdf: str, tmp_path: Path) -> None:
    # control: whiting out one real word makes both versions report it, so the real-page equality is not "[] == []"
    png, words = _rendered_page(resume_pdf, tmp_path)
    (x0, y0, x1, y1), _ = words[len(words) // 2]
    im = Image.open(png).convert("RGB")
    im.paste(WHITE, (int(x0 * S) - 1, int(y0 * S) - 1, int(x1 * S) + 2, int(y1 * S) + 2))
    im.save(png)

    got = check_text_clip(png, words)

    assert got == check_text_clip_per_pixel(png, words)
    assert any("indistinguishable" in m for m in got)


# ------------------------------------------------------------------ fill.bands


def _random_bands_page(rng: random.Random) -> Image.Image:
    """A 240x300 grey page on a white or tinted paper: text-like rows of short dark runs, full-width rules of 1-3 px,
    short rules around the width threshold (4 % of the page width, 9-10 px wide at this size), pale rules, a bar."""
    paper = rng.choice([255, 255, 240, 200])
    im = Image.new("L", (240, 300), paper)
    for y in range(rng.randint(5, 40), 280, rng.randint(9, 16)):
        for x in range(20, 220, rng.choice([5, 7, 9])):
            im.paste(rng.choice([0, 60, 120]), (x, y, x + rng.randint(2, 4), y + 6))
    for _ in range(rng.randint(0, 4)):
        y, x0 = rng.randint(0, 295), rng.randint(0, 200)
        im.paste(rng.choice([0, 100, paper - 15, paper - 25, paper - 40]),
                 (x0, y, x0 + rng.choice([8, 9, 10, 11, 60, 180]), y + rng.randint(1, 3)))
    if rng.random() < 0.3:
        im.paste(rng.choice([0, 90]), (10, rng.randint(0, 250), 230, rng.randint(250, 299)))
    return im


@settings(max_examples=250)
@given(_rngs)
def test_bands_match_the_per_row_version(rng: random.Random) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        png = str(Path(tmp) / "p.png")
        _random_bands_page(rng).save(png)
        thr, rule, contrast = rng.choice([100, 150, 200]), rng.choice([0.0, 0.01, 0.04, 0.08, 0.9]), rng.choice([5, 20, 60])

        assert fill.bands(png, thr=thr, rule=rule, contrast=contrast) == bands_per_row(png, thr=thr, rule=rule, contrast=contrast)


def test_bands_equivalence_is_not_vacuous(tmp_path: Path) -> None:
    # control: the random pages produce white runs and ink bands, and not always the same ones
    seen = set()
    for seed in range(250):
        png = tmp_path / f"p{seed}.png"
        _random_bands_page(random.Random(seed)).save(png)
        _, white, ink = fill.bands(str(png))
        seen.add((bool(white), bool(ink)))

    assert seen == {(False, False), (True, False), (True, True)} or {(True, True), (True, False)} <= seen


def test_bands_match_on_a_real_page(resume_pdf: str, tmp_path: Path) -> None:
    png, _ = _rendered_page(resume_pdf, tmp_path)

    got = fill.bands(png)

    assert got == bands_per_row(png)
    assert got[1]      # a CV page has white runs between its sections


def test_bands_rule_width_is_inclusive_at_the_threshold(tmp_path: Path) -> None:
    # boundary: a rule exactly ceil(rule * width) px wide counts as an ink band, one px less does not
    png = tmp_path / "p.png"
    for width, expected in ((10, True), (9, False)):    # 240 px * 0.04 = 9.6 -> 10
        im = Image.new("L", (240, 100), 255)
        im.paste(0, (20, 50, 20 + width, 52))
        im.save(png)

        got = bool(fill.bands(str(png))[2])

        assert got is expected, width
        assert got == bool(bands_per_row(str(png))[2])


# ------------------------------------------------------------------ work bounds (line events, no wall clock)

_LAYOUT = frozenset({layout.__file__})
_FILL = frozenset({fill.__file__})
_PIXEL_REF = frozenset({_raster_ref.__file__})


def _wide_words_page(width: int, n_words: int = 20) -> tuple[Image.Image, list[WordBox]]:
    """Worst case for a flat-box test: `n_words` boxes `width` px wide and 14 px tall, each filled with random RGB noise
    (about one distinct colour per pixel), so a box's modal colour costs O(pixels) at best and O(pixels^2) when each
    colour is counted by a scan of the box."""
    rng = random.Random(1)
    per_row = 8000 // width
    im = Image.new("RGB", (per_row * width, (n_words // per_row + 1) * 20), WHITE)
    boxes: list[WordBox] = []
    for i in range(n_words):
        x, y = (i % per_row) * width, (i // per_row) * 20 + 3
        im.paste(Image.frombytes("RGB", (width, 14), rng.randbytes(3 * width * 14)), (x, y))
        boxes.append(((x / S, y / S, (x + width) / S, (y + 14) / S), "word"))
    return im, boxes


def _text_clip_events(tmp_path: Path, width: int, check: Callable[[str, list[WordBox]], object], files: frozenset[str]) -> int:
    im, boxes = _wide_words_page(width)
    png = tmp_path / f"w{width}.png"
    im.save(png)
    events, _ = line_events(files, lambda: check(str(png), boxes))
    return events


def test_text_clip_work_does_not_grow_with_the_word_box_area(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # the pixels are counted by Pillow (C), so the Python work is a constant per box whatever its area; the area
    # handed to Pillow is counted at the boundary and must be one pass over each box, never a pass per colour
    handed = [0, 0]                                   # calls to colour_counts, pixels handed to it

    def counting(box: Image.Image, maxcolors: int) -> list[tuple[int, tuple[int, ...]]]:
        handed[0] += 1
        handed[1] += box.width * box.height
        return colour_counts(box, maxcolors)

    monkeypatch.setattr(layout, "colour_counts", counting)

    assert_linear(lambda width: _text_clip_events(tmp_path, width, check_text_clip, _LAYOUT), 100, bound=1.2)
    assert handed[0] == 20 * 3                        # one modal-colour pass per word box and per page size
    area = 20 * 14 * (100 + 200 + 400)
    assert area <= handed[1] <= 1.25 * area           # linear in the box area: each pixel handed to Pillow once (+ the crop's edge row and column)


def test_text_clip_does_far_less_python_work_than_the_per_pixel_loop(tmp_path: Path) -> None:
    new = _text_clip_events(tmp_path, 100, check_text_clip, _LAYOUT)
    old = _text_clip_events(tmp_path, 100, check_text_clip_per_pixel, _PIXEL_REF)

    assert new > 0
    assert old >= 20 * new                            # measured ~48x: the per-pixel loop is linear too, but with a big constant


def _bands_events(png: Path, files: frozenset[str] = _FILL) -> tuple[int, tuple[int, list[tuple[int, int]], list[tuple[int, int]]]]:
    return line_events(files, lambda: fill.bands(str(png)))


def test_bands_work_grows_linearly_with_the_page_height(tmp_path: Path) -> None:
    # worst case: every row of a 4000-wide page is chopped into 667 short dark runs (text-dense), none long enough
    # to be a rule, so each row is scanned whole for a run
    row = Image.new("L", (4000, 1), 255)
    for x in range(0, 4000, 6):
        row.paste(0, (x, 0, x + 3, 1))
    results: list[tuple[int, list[tuple[int, int]], list[tuple[int, int]]]] = []

    def measure(height: int) -> int:
        png = tmp_path / f"h{height}.png"
        row.resize((4000, height), Image.Resampling.NEAREST).save(png)
        events, result = _bands_events(png)
        results.append(result)
        return events

    assert_linear(measure, 750)
    assert [r[2] for r in results] == [[], [], []]    # no rule on any page
    assert all(r[1] == [] for r in results)           # every row holds ink: no white run either


def _dark_runs_page(tmp_path: Path, width: int, run: int, rows: int) -> Path:
    """Every row is dark runs of `run` pixels, each followed by one light pixel."""
    row = Image.new("L", (width, 1), 255)
    for x in range(0, width, run + 1):
        row.paste(0, (x, 0, min(x + run, width), 1))
    png = tmp_path / f"runs{width}.png"
    row.resize((width, rows), Image.Resampling.NEAREST).save(png)
    return png


def test_bands_python_work_does_not_depend_on_the_width_of_rows_of_runs_just_short_of_a_rule(tmp_path: Path) -> None:
    # worst case for the run search: runs of need-1 dark pixels split by one light pixel, so no start fails early.
    # The search is `bytes.find` (C), so the Python work is a constant per row whatever the width; a per-pixel scan
    # in Python would grow with it. The C scan's own linearity is bytes.find's, not measurable here.
    rows = 200
    bands_seen: list[list[tuple[int, int]]] = []

    def measure(width: int) -> int:
        need = math.ceil(fill.RULE_FLOOR * width)
        events, result = _bands_events(_dark_runs_page(tmp_path, width, need - 1, rows))
        bands_seen.append(result[2])
        return events

    assert_linear(measure, 4000, bound=1.2)
    assert bands_seen == [[], [], []]                 # need-1 is not a rule
    events_16k = measure(16000)
    assert events_16k <= 10 * rows                    # a few line events per row; a per-pixel Python scan is ~16000 x 0.88 per row
