"""Header spacing, every family: the line under the name never touches it.

A header whose name and the next line collide (a title drawn over the bottom of the name, a contact line
glued to the title) reads as a rendering bug whatever the content is. The gate has no verdict on it, so the
rendered fixtures (one per family, header included) are measured here with the tight glyph boxes pdfium gives.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from harness import ROOT, CheckResult, importable_isolated
from vitae.core.pdfium import PdfiumDoc

FIXTURES = sorted(p.stem for p in (ROOT / "tests" / "fixtures").glob("*.typ"))

# (left, bottom, right, top, text), PDF points, y up; a word is a run of non-space characters.
Word = tuple[float, float, float, float, str]

MIN_NAME_GAP = 2.0   # pt between the name's bottom and the top of the line under it (tightest family today: 2.5)
MIN_LINE_GAP = 0.5   # pt between that line and the next one: they may be tight, never touching (tightest: 1.1)


def _page_words(pdf: Path) -> list[Word]:
    doc = importlib.import_module("pypdfium2").PdfDocument(str(pdf))
    assert isinstance(doc, PdfiumDoc)
    tp = doc[0].get_textpage()
    text = tp.get_text_range()
    assert len(text) == tp.count_chars(), "a character past the BMP shifts pdfium's indices"
    words: list[Word] = []
    cur: list[tuple[float, float, float, float, str]] = []
    for i, ch in enumerate(text):
        if ch.strip() == "":
            if cur:
                words.append(_word(cur))
                cur = []
        else:
            left, bottom, right, top = tp.get_charbox(i)
            cur.append((left, bottom, right, top, ch))
    if cur:
        words.append(_word(cur))
    return words


def _word(chars: list[tuple[float, float, float, float, str]]) -> Word:
    return (min(c[0] for c in chars), min(c[1] for c in chars), max(c[2] for c in chars),
            max(c[3] for c in chars), "".join(c[4] for c in chars))


def header_gaps(words: list[Word], name_words: tuple[str, ...] = ("Firstname", "Lastname")) -> list[float]:
    """[gap name -> line under it, gap line -> the next line] in points (negative = overlap).

    The line under a reference is the word, below its vertical midpoint and sharing some of its x-range, with
    the highest top; the line is every word whose box is level with that one."""
    name = [w for w in words if w[4] in name_words]
    assert name, f"name not found in {sorted({w[4] for w in words})[:8]}"
    left, right = min(w[0] for w in name), max(w[2] for w in name)
    bottom, top = min(w[1] for w in name), max(w[3] for w in name)
    gaps: list[float] = []
    for _ in range(2):
        mid = (bottom + top) / 2
        below = [w for w in words if w[3] < mid and w[0] < right and w[2] > left]
        assert below, "nothing under the header line"
        nxt = max(below, key=lambda w: w[3])
        level = [w for w in words if w[1] < nxt[3] and w[3] > nxt[1] and w[3] < mid]
        gaps.append(bottom - nxt[3])
        bottom, top = min(w[1] for w in level), nxt[3]
    return gaps


# ---------- the measurement itself, on boxes drawn by hand ----------

NAME: list[Word] = [(50, 700, 150, 725, "Firstname"), (155, 700, 250, 725, "Lastname")]


def test_title_clear_of_the_name_is_measured_as_a_positive_gap() -> None:
    words = [*NAME, (50, 683, 200, 695, "Title"), (50, 668, 200, 679, "Contact")]
    assert header_gaps(words) == pytest.approx([5.0, 4.0])


def test_title_touching_the_name_is_measured_as_no_gap() -> None:
    assert header_gaps([*NAME, (50, 690, 200, 700, "Title"), (50, 670, 200, 680, "Contact")])[0] == 0.0


def test_title_drawn_over_the_name_is_measured_as_overlap() -> None:
    assert header_gaps([*NAME, (50, 690, 200, 704, "Title"), (50, 670, 200, 680, "Contact")])[0] < 0


def test_a_word_off_to_the_side_is_not_the_line_under_the_name() -> None:
    words = [*NAME, (400, 690, 500, 700, "Aside"), (50, 683, 200, 695, "Title"), (50, 668, 200, 679, "Contact")]
    assert header_gaps(words)[0] == pytest.approx(5.0)


# ---------- every family ----------

@pytest.mark.usefixtures("_not_quick")
@pytest.mark.parametrize("name", FIXTURES)
def test_line_under_the_name_clears_it(name: str, fixtures_rendered: tuple[CheckResult, Path]) -> None:
    if not importable_isolated("pypdfium2"):
        pytest.skip("needs pypdfium2")
    pdf = fixtures_rendered[1] / f"{name}.pdf"
    assert pdf.is_file(), f"{name}: no PDF rendered"
    name_gap, line_gap = header_gaps(_page_words(pdf))
    assert name_gap >= MIN_NAME_GAP, f"{name}: the line under the name sits {name_gap:.1f}pt from it (min {MIN_NAME_GAP})"
    assert line_gap >= MIN_LINE_GAP, f"{name}: the header's second line sits {line_gap:.1f}pt from the first (min {MIN_LINE_GAP})"
