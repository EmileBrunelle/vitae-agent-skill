"""vitae.verify.rhythm: a bullet's wrapped second line must sit closer than the next bullet.

Positions only, no wording and no script assumption. From the same <vitae-bullet> marks as the runts gate
(runts.located_bullets), per list column (markers sharing an x): the wrapped pitch is the median
baseline-to-baseline distance between consecutive lines of one bullet, the bullet pitch the median distance
from a bullet's last line to the next bullet's first line. The next bullet is the following marker of the
same column; a pair is left out when an entry head or part mark lies between the two markers, when the
bullet runs on to another page (the next bullet is then above its last line), or when the lines are
farther apart than _MAX_GAP line heights (something else sits between them). When `#set list(spacing:)` is not above the paragraph leading,
a wrapped line sits as far as (or farther than) the next bullet and the eye cannot tell one bullet's lines
from the next bullet: that is the FAIL."""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Callable
from dataclasses import dataclass
from statistics import median

from vitae.core.base import Mark, WordBox, is_placed
from vitae.core.level import Finding, Level
from vitae.verify.pdf import _bbox_pages
from vitae.verify.runts import BulletLine, Pos, located_bullets

MIN_STEP = 0.5          # pt: the bullet pitch must exceed the wrapped pitch by at least this
_MAX_GAP = 3.0          # line heights: a farther next bullet has something between it and this one
_MAX_WRAP = 1.75        # line heights: a line farther below the previous one is not the bullet's wrapped line (a section heading sharing its edge)
_X_SLACK = 1.5          # pt: markers of one list column share their x within this
_MARK_REACH = 40.0      # pt: a head or part mark counts as being in a bullet's column when this near its lines
_MIN_PAIRS = 2          # bullet pairs a column needs before its bullet pitch is a measure

_FIX = ("make `#set list(spacing:)` exceed the paragraph leading (`par(leading:)`); `--tune` keeps their ratio")


@dataclass(frozen=True)
class Column:
    x: float
    wrapped: float | None      # median wrapped pitch, None when no bullet of the column wraps
    bullet: float | None       # median bullet pitch, None when fewer than _MIN_PAIRS pairs
    pairs: int
    page: int                  # the first page the column's bullets are on


class _HeadIndex:
    """The entry head and part marks of each page as (y, x) sorted by y, so that the heads between two bullet
    markers are found by bisection instead of by filtering every mark for every pair of bullets."""

    def __init__(self, marks: list[Mark]) -> None:
        by_page: dict[int, list[tuple[float, float]]] = {}
        for m in marks:
            if is_placed(m) and m.get("kind") != "bullet":
                by_page.setdefault(m["page"], []).append((m["y"], m["x"]))
        self._ys: dict[int, list[float]] = {}
        self._xs: dict[int, list[float]] = {}
        for page, pts in by_page.items():
            pts.sort()
            self._ys[page] = [y for y, _ in pts]
            self._xs[page] = [x for _, x in pts]

    def separated(self, a: Pos, b: Pos, lo: float, hi: float) -> bool:
        """An entry head or part mark between the two bullet markers, on the markers' page and near the bullet's
        column (a head in a sidebar beside the list does not separate two of its bullets). A section title always
        has an entry head or skill label after it, so its own mark (not queried) is not needed."""
        ys = self._ys.get(a.page)
        if ys is None:
            return False
        xs = self._xs[a.page]
        return any(lo - _MARK_REACH <= xs[k] <= hi for k in range(bisect_right(ys, a.y), bisect_left(ys, b.y)))


def _own_lines(lines: list[BulletLine]) -> list[BulletLine]:
    """The bullet's lines up to the first one set apart by more than _MAX_WRAP line heights: what follows is
    the next block (a section heading shares the bullets' edge and the runts gate's reach), not a wrapped line."""
    for k in range(1, len(lines)):
        if lines[k].page == lines[k - 1].page and lines[k].y1 - lines[k - 1].y1 > _MAX_WRAP * lines[k - 1].height:
            return lines[:k]
    return lines


def measure_columns(marks: list[Mark], pages: list[list[WordBox]], heights: list[float] | None = None) -> list[Column]:
    """One Column per list column of the document (markers clustered on their x)."""
    placed = [(pos, _own_lines(ls)) for pos, ls in located_bullets(marks, pages, heights)]
    placed.sort(key=lambda b: b[0].x)
    clusters: list[list[tuple[Pos, list[BulletLine]]]] = []
    for item in placed:
        if clusters and item[0].x - clusters[-1][-1][0].x <= _X_SLACK:
            clusters[-1].append(item)
        else:
            clusters.append([item])
    cols: list[Column] = []
    heads = _HeadIndex(marks)
    for cl in clusters:
        cl.sort(key=lambda b: (b[0].page, b[0].y))
        wrapped = [b.y1 - a.y1 for _, ls in cl for a, b in zip(ls, ls[1:]) if a.page == b.page]
        gaps: list[float] = []
        for (pa, la), (pb, lb) in zip(cl, cl[1:]):
            if pa.page != pb.page:
                continue    # no pitch across a page break, whatever the two y values say
            # a bullet that runs on to the next page gives a gap <= 0 here
            gap = lb[0].y1 - la[-1].y1
            lo = min(ln.extent.x0 for ln in la)
            hi = max(ln.extent.x1 for ln in la)
            if gap <= 0 or gap > _MAX_GAP * la[-1].height or heads.separated(pa, pb, lo, hi):
                continue
            gaps.append(gap)
        cols.append(Column(cl[0][0].x, median(wrapped) if wrapped else None,
                           median(gaps) if len(gaps) >= _MIN_PAIRS else None, len(gaps), cl[0][0].page))
    return cols


def check_rhythm(marks: list[Mark] | None, pdf: str, *, fail: Callable[[str], Finding],
                 min_step: float = MIN_STEP) -> list[Finding]:
    """FAIL per list column whose bullet pitch does not exceed its wrapped-line pitch by `min_step` pt; an INFO
    when no column could be measured (no wrapped bullet, or fewer than two bullet pairs); a WARN when the
    bullets cannot be located at all."""
    if marks is None:
        return [(Level.WARN, "spacing rhythm not measured: typst query unavailable")]
    if not any(m.get("kind") == "bullet" for m in marks):
        return [(Level.WARN, "spacing rhythm not measured: no lib bullet marks "
                             "(draw the list through lib list-marker or bullet-marked)")]
    sized = _bbox_pages(pdf)
    if sized is None:
        return [(Level.WARN, "spacing rhythm not measured: word positions unavailable")]
    cols = measure_columns(marks, [items for _, _, items in sized], [h for _, h, _ in sized])
    out: list[Finding] = []
    measured = 0
    for c in cols:
        if c.wrapped is None or c.bullet is None:
            continue
        measured += 1
        if c.bullet - c.wrapped < min_step:
            state = "inverted" if c.bullet < c.wrapped else "flat"
            out.append(fail(f"spacing rhythm: in the list at x={c.x:.0f}pt (page {c.page}) a bullet's wrapped line "
                            f"is {c.wrapped:.1f}pt from the one above and the next bullet {c.bullet:.1f}pt: "
                            f"{state}, so a wrapped line reads as farther from its bullet than the next bullet is — {_FIX}"))
    if not measured:
        out.append((Level.INFO, "spacing rhythm not measured: no list with a wrapped bullet and two bullet pairs"))
    return out
