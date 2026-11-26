"""vitae.verify.runts: a bullet that wraps and whose last line is a few glyphs alone.

A bullet is one line, or its lines are full: "ms." or "min." alone on the second line reads as a layout slip.
Positions only, no wording and no script assumption: lib.typ's list marker carries a <vitae-bullet> mark
(page, x, y). The bullet's text is on the side of the marker where the first line's words are (right of it
for a left-to-right script, left of it for a right-to-left one); a later line belongs to the bullet when it
shares an edge with the first line's text (left edge, or right edge for right-to-left text), is not on the
next bullet's line, and is not set apart by more than a line's height. The runt test is the WIDTH of the
last line, against the line's height (an em-proportional unit that does not depend on the script) and
against the widest line of the bullet, so a few CJK characters, one Thai run or one Arabic word are
judged like "ms." is. A line the extractor returns as one "word" works the same."""
from __future__ import annotations

from bisect import bisect_left
from collections.abc import Callable
from dataclasses import dataclass

from vitae.core.base import HeadMark, Mark, Word, WordBox, _Line, is_placed
from vitae.core.level import Finding, Level
from vitae.verify.groups.query import _lines
from vitae.verify.pdf import word_boxes

# A last line is a runt when it is at most RUNT_EM line heights wide AND at most RUNT_FRAC of the bullet's
# widest line. Both: the first keeps a short line of a narrow column from being judged by the column alone,
# the second keeps a wide, large-type bullet from being judged by the type alone.
RUNT_EM = 2.5
RUNT_FRAC = 0.15
_EDGE_SLACK = 1.5      # pt: continuation lines share the first line's edge within this
_MARKER_BAND = 8.0     # pt: how far from the marker's y a text line may sit and still be its first line


@dataclass(frozen=True)
class Extent:
    x0: float
    x1: float


def _side(words: list[Word], mx: float) -> list[Word]:
    """The words of a line on the text side of the marker: the side the majority of them is on."""
    right = [w for w in words if w[0] >= mx - 0.5]
    left = [w for w in words if w[2] <= mx + 0.5]
    return right if len(right) >= len(left) else left


def _extent(words: list[Word]) -> Extent:
    return Extent(min(w[0] for w in words), max(w[2] for w in words))


@dataclass(frozen=True)
class Pos:
    """Where a bullet starts: its marker's page, x and y."""
    page: int
    x: float
    y: float


@dataclass(frozen=True)
class BulletLine:
    page: int
    extent: Extent
    height: float
    text: str


def _positions(marks: list[Mark]) -> list[Pos]:
    placed: list[HeadMark] = [m for m in marks if is_placed(m)]
    return [Pos(m["page"], m["x"], m["y"]) for m in placed if m.get("kind") == "bullet"]


def bullet_lines(marks: list[Mark], pages: list[list[WordBox]]) -> list[tuple[int, list[BulletLine]]]:
    """Per bullet mark (page, lines top to bottom); a bullet whose first line cannot be located is dropped.
    Text lines are clustered once per page and looked up by y."""
    page_lines: dict[int, tuple[list[_Line], list[float]]] = {}
    bullets = sorted(_positions(marks), key=lambda p: (p.page, p.y))
    out: list[tuple[int, list[BulletLine]]] = []
    for i, m in enumerate(bullets):
        pg = m.page
        if not 1 <= pg <= len(pages):
            continue
        if pg not in page_lines:
            ls = _lines([(b[0], b[1], b[2], b[3], t) for b, t in pages[pg - 1]], float("-inf"))
            page_lines[pg] = (ls, [ln["c"] for ln in ls])
        lines, centres = page_lines[pg]
        nxt = next((b.y for b in bullets[i + 1:] if b.page == pg and b.y > m.y + 1), float("inf"))
        j = bisect_left(centres, m.y - _MARKER_BAND)
        while j < len(lines) and not _side(lines[j]["words"], m.x) and lines[j]["c"] <= m.y + _MARKER_BAND:
            j += 1
        if j >= len(lines) or abs(lines[j]["c"] - m.y) > _MARKER_BAND:
            continue
        first = _extent(_side(lines[j]["words"], m.x))
        got = [BulletLine(pg, first, lines[j]["y1"] - lines[j]["y0"], " ".join(w[4] for w in lines[j]["words"]))]
        prev = lines[j]
        for ln in lines[j + 1:]:
            if ln["c"] >= nxt - _MARKER_BAND or ln["y0"] - prev["y1"] > prev["y1"] - prev["y0"]:
                break
            ws = _side(ln["words"], m.x)
            if not ws:
                break
            e = _extent(ws)
            if abs(e.x0 - first.x0) > _EDGE_SLACK and abs(e.x1 - first.x1) > _EDGE_SLACK:
                break
            got.append(BulletLine(pg, e, ln["y1"] - ln["y0"], " ".join(w[4] for w in ws)))
            prev = ln
        out.append((pg, got))
    return out


def is_runt(lines: list[BulletLine], runt_em: float = RUNT_EM, runt_frac: float = RUNT_FRAC) -> bool:
    """A wrapped bullet whose last line is narrow both in line heights and against its widest line."""
    if len(lines) < 2:
        return False
    last = lines[-1]
    width = last.extent.x1 - last.extent.x0
    widest = max(ln.extent.x1 - ln.extent.x0 for ln in lines)
    return width <= runt_em * last.height and width <= runt_frac * widest


def check_runts(marks: list[Mark] | None, pdf: str, *, fail: Callable[[str], Finding],
                runt_em: float = RUNT_EM, runt_frac: float = RUNT_FRAC) -> list[Finding]:
    """FAIL per wrapped bullet whose last line is a runt; a WARN when the bullets could not be measured
    (no bullet marks: a CV that does not draw its list through the lib marker)."""
    if marks is None:
        return [(Level.WARN, "bullet runt lines not measured: typst query unavailable")]
    if not any(m.get("kind") == "bullet" for m in marks):
        return [(Level.WARN, "bullet runt lines not measured: no lib bullet marks "
                             "(the list marker is not lib drawn-marker / bullet-marked)")]
    pages = word_boxes(pdf, with_text=True)
    if pages is None:
        return [(Level.WARN, "bullet runt lines not measured: word positions unavailable")]
    out: list[Finding] = []
    for pg, lines in bullet_lines(marks, pages):
        if is_runt(lines, runt_em, runt_frac):
            out.append(fail(f'bullet runt line on page {pg}: last line of a {len(lines)}-line bullet is '
                            f'"{lines[-1].text}" (a few glyphs alone) — a bullet is one line or its lines are '
                            "full: tighten it to one line, or develop it so the last line is substantial; "
                            "re-run --tune and the gate"))
    return out
