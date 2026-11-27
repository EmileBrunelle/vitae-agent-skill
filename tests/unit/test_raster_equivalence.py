"""Raster hot spots moved from Python pixel loops to Pillow: `layout.check_text_clip` (flat-box test of every word box)
and `fill.bands` (dark rows and rule-wide rows of a page). Each keeps its behaviour (equivalence with the replaced code,
kept in `_raster_ref`, on seeded random rasters and on a real rendered page) and stays fast on a full page (`slow`: wall
time bounded far above the measured time and far below the old one, so a noisy runner does not flip it but a return to
a per-pixel loop does)."""
import random
import time
from pathlib import Path

import pytest
from _paths import ROOT
from _raster_ref import bands_per_row, check_text_clip_per_pixel
from PIL import Image
from vitae import fill
from vitae.core.base import WordBox
from vitae.verify.layout import check_text_clip
from vitae.verify.page import FURNITURE_SCALE
from vitae.verify.pdf import _pdfium_render, word_boxes

S = FURNITURE_SCALE
WHITE = (255, 255, 255)

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
    for k in range(rng.randint(4, 14)):
        x, y = rng.randint(5, 220), rng.randint(2, 170)
        w, h = rng.randint(20, 70), rng.randint(8, 18)
        ink = rng.choice([WHITE, (0, 0, 0), (200, 30, 30), paper, (paper[0] ^ 20, paper[1], paper[2])])
        for gx in range(x + 2, x + w - 2, rng.choice([3, 4, 6])):
            im.paste(ink, (gx, y + 3, gx + 2, y + h - 3))
        boxes.append(((x / S, y / S, (x + w) / S, (y + h) / S), rng.choice(["linkedin.com", "Skills", "a", "Title"])))
    return im, boxes


@pytest.mark.parametrize("seed", range(250))
def test_text_clip_matches_the_per_pixel_version(tmp_path: Path, seed: int) -> None:
    im, boxes = _random_page(random.Random(seed))
    png = tmp_path / "p.png"
    im.save(png)

    assert check_text_clip(str(png), boxes) == check_text_clip_per_pixel(str(png), boxes)


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


def _rendered_page(tmp_path: Path) -> tuple[str, list[WordBox]]:
    """The shipped templates/resume.pdf at 90 ppi (pdfium) and its words: a real page, real glyph anti-aliasing."""
    pdf = str(ROOT / "templates" / "resume.pdf")
    pages = word_boxes(pdf, with_text=True)
    if not pages:
        pytest.skip("no word boxes available for templates/resume.pdf")
    png = tmp_path / "resume.png"
    _pdfium_render(pdf, 90)[0].save(png)
    return str(png), pages[0]


def test_text_clip_matches_on_a_real_page(tmp_path: Path) -> None:
    png, words = _rendered_page(tmp_path)

    assert len(words) > 100
    assert check_text_clip(png, words) == check_text_clip_per_pixel(png, words)


def test_text_clip_real_page_equivalence_catches_a_hidden_word(tmp_path: Path) -> None:
    # control: whiting out one real word makes both versions report it, so the real-page equality is not "[] == []"
    png, words = _rendered_page(tmp_path)
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


@pytest.mark.parametrize("seed", range(250))
def test_bands_match_the_per_row_version(tmp_path: Path, seed: int) -> None:
    rng = random.Random(seed)
    png = tmp_path / "p.png"
    _random_bands_page(rng).save(png)
    kw = {"thr": rng.choice([100, 150, 200]), "rule": rng.choice([0.0, 0.01, 0.04, 0.08, 0.9]),
          "contrast": rng.choice([5, 20, 60])}

    assert fill.bands(str(png), **kw) == bands_per_row(str(png), **kw)


def test_bands_equivalence_is_not_vacuous(tmp_path: Path) -> None:
    # control: the random pages produce white runs and ink bands, and not always the same ones
    seen = set()
    for seed in range(250):
        png = tmp_path / f"p{seed}.png"
        _random_bands_page(random.Random(seed)).save(png)
        _, white, ink = fill.bands(str(png))
        seen.add((bool(white), bool(ink)))

    assert seen == {(False, False), (True, False), (True, True)} or {(True, True), (True, False)} <= seen


def test_bands_match_on_a_real_page(tmp_path: Path) -> None:
    png, _ = _rendered_page(tmp_path)

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


# ------------------------------------------------------------------ time bounds


def _full_page(rng: random.Random, n_words: int = 2500) -> tuple[Image.Image, list[WordBox]]:
    """Worst case: a 1275x1650 page (150 ppi letter) with n_words glyph-dense word boxes on a grey band and on paper."""
    im = Image.new("RGB", (int(8.5 * 150), 11 * 150), WHITE)
    im.paste((60, 60, 60), (0, 0, im.width, 200))
    boxes: list[WordBox] = []
    for i in range(n_words):
        x, y = 40 + (i % 25) * 48, 10 + (i // 25) * 15
        for gx in range(x, x + 40, 4):
            im.paste((rng.randint(0, 255),) * 3, (gx, y + 3, gx + 2, y + 11))
        boxes.append(((x / S, y / S, (x + 44) / S, (y + 14) / S), "word"))
    return im, boxes


@pytest.mark.slow
def test_text_clip_bounds_time_on_a_full_page(tmp_path: Path) -> None:
    im, boxes = _full_page(random.Random(1))
    png = tmp_path / "p.png"
    im.save(png)
    start = time.perf_counter()

    check_text_clip(str(png), boxes)

    assert time.perf_counter() - start < 0.8     # measured ~0.15 s; the per-pixel version takes ~1.5 s


@pytest.mark.slow
def test_bands_bound_time_on_a_tall_page(tmp_path: Path) -> None:
    # worst case: every row of a 4000x6000 page is chopped into 667 short dark runs (text-dense), none long enough
    # to be a rule, so each row is scanned whole for a run
    row = Image.new("L", (4000, 1), 255)
    for x in range(0, 4000, 6):
        row.paste(0, (x, 0, x + 3, 1))
    png = tmp_path / "p.png"
    row.resize((4000, 6000), Image.Resampling.NEAREST).save(png)
    start = time.perf_counter()

    got = fill.bands(str(png))

    assert time.perf_counter() - start < 0.6     # measured ~0.25 s; the per-row version takes ~0.95 s
    assert got[2] == []
