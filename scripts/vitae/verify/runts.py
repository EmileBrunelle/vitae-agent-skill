"""vitae.verify.runts: a bullet that wraps and whose last line is a few glyphs alone.

A bullet is one line, or its lines are full: "ms." or "min." alone on the second line reads as a layout slip.
Positions only, no wording and no script assumption: lib.typ's list marker carries a <vitae-bullet> mark
(page, x, y). The bullet's text is on the side of the marker where the first line's words are (right of it
for a left-to-right script, left of it for a right-to-left one); a later line belongs to the bullet when it
shares the reading-side edge of the first line's text (left edge, or right edge for right-to-left text), is
not on the next bullet's line, and is not set apart by more than a line's height. The runt test is the WIDTH of the
last line, against the line's height (an em-proportional unit that does not depend on the script) and
against the widest line of the bullet, so a few CJK characters, one Thai run or one Arabic word are
judged like "ms." is. Only the words of the marker's own column are looked at (a sidebar beside it is cut
off at the first clear vertical channel), and a bullet that breaks across a page goes on at the top of the
next page in the same column. A line the extractor returns as one "word" works the same."""
from __future__ import annotations

from bisect import bisect_left
from collections.abc import Callable, Sequence
from itertools import chain, islice

from vitae.core.base import (
    BulletLayout,
    BulletLine,
    Extent,
    HeadMark,
    Mark,
    Pos,
    Word,
    WordBox,
    _Line,
    is_placed,
)
from vitae.core.level import Finding, Level
from vitae.verify.bounds import density_guard, page_at, too_dense
from vitae.verify.groups.query import cluster

# A last line is a runt when it is at most RUNT_EM line heights wide AND at most RUNT_FRAC of the bullet's
# widest line. Both: the first keeps a short line of a narrow column from being judged by the column alone,
# the second keeps a wide, large-type bullet from being judged by the type alone.
RUNT_EM = 2.5
RUNT_FRAC = 0.15
_EDGE_SLACK = 1.5      # pt: continuation lines share the first line's edge within this
_MARKER_BAND = 8.0     # pt: how far from the marker's y a text line may sit and still be its first line
_CHANNEL = 0.4         # line heights: a gap this wide, free of words on every line below the marker, ends the column
_HEAD_REACH = 40.0     # pt: an entry head this near the bullet's column (its role line sits left of the bullets) ends the bullet
_BOTTOM_LINES = 2.3    # line heights: a bullet's last line this close to the content bottom may go on at the next page


def _extent(words: list[Word]) -> Extent:
    return Extent(min(w[0] for w in words), max(w[2] for w in words))


def _positions(marks: list[Mark]) -> list[Pos]:
    placed: list[HeadMark] = [m for m in marks if is_placed(m)]
    return [Pos(m["page"], m["x"], m["y"]) for m in placed if m.get("kind") == "bullet"]


class _Window:
    """The text lines of one column of one page, with their y-centres in order, so that the line nearest a y is a
    bisection (it was a scan of every line of the column, for every bullet and every next-bullet bound)."""

    def __init__(self, lines: list[_Line]) -> None:
        self.lines = lines
        order = sorted(range(len(lines)), key=lambda k: (lines[k]["c"], k))
        self._ids = order
        self._cs = [lines[k]["c"] for k in order]

    def nearest(self, y: float) -> int | None:
        """The index of the line whose centre is nearest `y` (the first of equals), None when there is no line. The
        distance to a centre only grows away from `y` on each side, so the nearest are around the insertion point; all
        lines at that exact distance are read, because the first of them in line order is the answer."""
        cs, ids = self._cs, self._ids
        pos = bisect_left(cs, y)
        side = [abs(cs[k] - y) for k in (pos - 1, pos) if 0 <= k < len(cs)]
        if not side:
            return None
        best = min(side)
        found = []
        k = pos
        while k < len(cs) and abs(cs[k] - y) == best:
            found.append(ids[k])
            k += 1
        k = pos - 1
        while k >= 0 and abs(cs[k] - y) == best:
            found.append(ids[k])
            k -= 1
        return min(found)

    def first_line(self, y: float) -> int | None:
        """The line whose centre is nearest the marker's y, if within the band (at most half the line pitch,
        so at small type the previous bullet's line is not taken for it)."""
        lines = self.lines
        j = self.nearest(y)
        if j is None:
            return None
        near = [abs(lines[k]["c"] - lines[j]["c"]) for k in (j - 1, j + 1) if 0 <= k < len(lines)]
        band = min(_MARKER_BAND, min(near) / 2) if near else _MARKER_BAND
        return j if abs(lines[j]["c"] - y) <= band else None


def _follow(win: _Window, start: int, edge: float, ltr: bool, nxt: float, pg: int,
            got: list[BulletLine], prev: _Line | None) -> bool:
    """Append the lines from `start` that continue the bullet, up to the next bullet's first line; True when
    it ran to the end of the column (so it may go on at the top of the next page)."""
    lines = win.lines
    stop = win.first_line(nxt) if nxt != float("inf") else None
    for k in range(start, len(lines)):
        ln = lines[k]
        if stop is not None and k >= stop:
            return False
        # a lowered inline element can split the next bullet's first line so that `stop` is None: its lines
        # are still at or below the next marker
        if nxt != float("inf") and ln["c"] >= nxt - (ln["y1"] - ln["y0"]) / 2:
            return False
        if prev is not None and ln["y0"] - prev["y1"] > prev["y1"] - prev["y0"]:
            return False
        e = _extent(ln["words"])
        if abs((e.x0 if ltr else e.x1) - edge) > _EDGE_SLACK:
            return False
        got.append(BulletLine(pg, e, ln["y1"] - ln["y0"], " ".join(w[4] for w in ln["words"]), ln["y1"]))
        prev = ln
    return True


def _next_head(heads: Sequence[HeadMark], page: int, after: float, col: tuple[float, float]) -> float:
    """The y of the first entry head or part mark below `after` on `page`, in the bullet's column (within
    _HEAD_REACH of its x range, so a sidebar's heads do not count): the next entry starts there, and its first
    line is not a continuation of the bullet above even though it shares its edge."""
    return min((h["y"] for h in heads if h["page"] == page and h["y"] > after
                and col[0] - _HEAD_REACH <= h["x"] <= col[1] + _HEAD_REACH), default=float("inf"))


def _in_col(x0: float, x1: float, col: tuple[float, float]) -> bool:
    """True when a word spanning x0..x1 lies inside the column's x range (half a point of slack each side)."""
    return x0 >= col[0] - 0.5 and x1 <= col[1] + 0.5


class _Page:
    """One page's words, prepared once for every bullet on it. A bullet used to rebuild the word list, sort the words
    of its column and re-cluster them into lines: O(words log words) each, so O(bullets x words) for a page. Here the
    words are held in y order and in x order, and the lines of a column are clustered once per distinct column."""

    def __init__(self, items: list[WordBox]) -> None:
        self.raw: list[Word] = [(b[0], b[1], b[2], b[3], t) for b, t in items]
        raw = self.raw
        self.centre = [(w[1] + w[3]) / 2 for w in raw]
        self.by_centre = sorted(range(len(raw)), key=self.centre.__getitem__)       # stable: ties keep word order
        self.centres = [self.centre[i] for i in self.by_centre]
        self.by_left = sorted(range(len(raw)), key=lambda i: (raw[i][0], i))
        self.lefts = [raw[i][0] for i in self.by_left]
        self.by_right = sorted(range(len(raw)), key=lambda i: (-raw[i][2], i))      # right edge, the rightmost first
        self.neg_rights = [-raw[i][2] for i in self.by_right]
        self.windows: dict[tuple[float, float], _Window] = {}

    def text_side(self, m: Pos) -> bool | None:
        """True when the bullet's text is right of its marker (left-to-right), False when left of it, None when
        no word sits near the marker's y: the side of the horizontally nearest word."""
        lo = bisect_left(self.centres, True, key=lambda c: c - m.y >= -_MARKER_BAND)
        hi = bisect_left(self.centres, True, key=lambda c: c - m.y > _MARKER_BAND)
        near = [self.raw[i] for i in self.by_centre[lo:hi]]
        right = [w[0] - m.x for w in near if w[0] >= m.x - 0.5]
        left = [m.x - w[2] for w in near if w[2] <= m.x + 0.5]
        if not right and not left:
            return None
        return min(right, default=float("inf")) <= min(left, default=float("inf"))

    def column(self, m: Pos, ltr: bool) -> tuple[float, float]:
        """The x range of the marker's column: from the marker out to the first clear vertical channel (wider
        than a few interword spaces: no word of any line below crosses it, so justified text is not cut) in the words at or below the marker, so a sidebar beside it is not part of it."""
        if ltr:
            order, start = self.by_left, bisect_left(self.lefts, m.x - 0.5)
        else:
            order, start = self.by_right, bisect_left(self.neg_rights, -(m.x + 0.5))
        floor = m.y - _MARKER_BAND
        below = (self.raw[i] for i in islice(order, start, None) if self.centre[i] >= floor)    # in x order
        first = next(below, None)
        if first is None:
            return (m.x - 0.5, float("inf")) if ltr else (float("-inf"), m.x + 0.5)
        gap = _CHANNEL * (first[3] - first[1])
        edge = first[2] if ltr else first[0]
        for w in chain((first,), below):
            if ltr:
                if w[0] - edge > gap:
                    return (m.x - 0.5, edge + 0.5)
                edge = max(edge, w[2])
            else:
                if edge - w[2] > gap:
                    return (edge - 0.5, m.x + 0.5)
                edge = min(edge, w[0])
        return (m.x - 0.5, float("inf")) if ltr else (float("-inf"), m.x + 0.5)

    def window(self, col: tuple[float, float]) -> _Window:
        """The text lines made of the words inside the column's x range only, clustered once per column."""
        got = self.windows.get(col)
        if got is None:
            raw = self.raw
            got = self.windows[col] = _Window(cluster([raw[i] for i in self.by_centre
                                                       if _in_col(raw[i][0], raw[i][2], col)]))
        return got


class _Document:
    """What the bullets of one run share: the prepared pages, the content bottom of each column, the top of each
    page, and the bullet markers by page."""

    def __init__(self, pages: list[list[WordBox]], bullets: list[Pos], heads: list[HeadMark]) -> None:
        self.pages = pages
        self.heads_on: dict[int, list[HeadMark]] = {}
        for h in heads:
            self.heads_on.setdefault(h["page"], []).append(h)
        self._prepared: dict[int, _Page] = {}
        self._lowest: dict[tuple[float, float], list[float]] = {}
        self._top: dict[int, float] = {}
        self.bullets_on: dict[int, list[Pos]] = {}
        for b in bullets:
            self.bullets_on.setdefault(b.page, []).append(b)

    def page(self, pg: int) -> _Page | None:
        """The prepared page `pg` (1-based), None when the document has no such page."""
        words = page_at(self.pages, pg)
        if words is None:
            return None
        got = self._prepared.get(pg)
        if got is None:
            got = self._prepared[pg] = _Page(words)
        return got

    def _lowest_per_page(self, col: tuple[float, float]) -> list[float]:
        """The bottom of the text inside the column's x band, on each page."""
        return [max((b[3] for b, _ in page if _in_col(b[0], b[2], col)), default=float("-inf"))
                for page in self.pages]

    def at_bottom(self, pg: int, col: tuple[float, float], last: BulletLine, page_h: float | None) -> bool:
        """True when the bullet's last line (on page `pg`, 1-based) sits where its column's content ends, so the
        next line would not have fitted: within _BOTTOM_LINES line heights (widow/orphan control moves two lines
        together) of the content bottom. The bottom is read from the document: the lowest text of the column's x
        band on any page; it counts only when another page reaches about as low as this one (else the bullet is its own
        only evidence). Alone, the bottom margin is taken as large as the next page's top margin (its topmost text),
        which is a guess for unequal margins. A footer inside the column band raises the bottom: a split can be
        missed there, never invented."""
        lowest = self._lowest.get(col)
        if lowest is None:
            lowest = self._lowest[col] = self._lowest_per_page(col)
        window = _BOTTOM_LINES * last.height
        others = max((v for i, v in enumerate(lowest) if i != pg - 1), default=float("-inf"))
        if others >= last.y1 - last.height:
            return last.y1 >= max(others, lowest[pg - 1]) - window
        if page_h is None:
            return last.y1 >= lowest[pg - 1] - 0.5
        top = self._top.get(pg)
        if top is None:
            # a next page with no words has no top margin to guess from (min() of nothing raised ValueError): the
            # bullet is then taken to be at the bottom, and there is nothing to read on the page it would run on to
            top = self._top[pg] = min((b[1] for b, _ in self.pages[pg]), default=float("inf"))
        return last.y1 >= page_h - top - window


def _next_marker(bullets: list[Pos], i: int, m: Pos) -> float:
    """The y of the next bullet marker of `m`'s list on its page (`bullets`: sorted by page, then y), inf when none."""
    for b in islice(bullets, i + 1, None):
        if b.page > m.page:
            break
        if b.page == m.page and abs(b.x - m.x) <= _EDGE_SLACK and b.y > m.y + 1:
            return b.y
    return float("inf")


def located_bullets(marks: list[Mark], pages: list[list[WordBox]],
                    heights: list[float] | None = None) -> list[tuple[Pos, list[BulletLine]]]:
    """Per bullet mark its position (page, x, y) and its lines top to bottom; a bullet whose first line cannot be
    located, or whose page is not one of `pages`, is dropped. Only the words of the marker's own column count, and a
    bullet runs on across a page break when its last line is at the bottom of the content (`heights`: the page
    heights)."""
    bullets = sorted(_positions(marks), key=lambda p: (p.page, p.y))
    heads: list[HeadMark] = [h for h in marks if is_placed(h) and h.get("kind") != "bullet"]
    doc = _Document(pages, bullets, heads)
    out: list[tuple[Pos, list[BulletLine]]] = []
    for i, m in enumerate(bullets):
        pg = m.page
        page = doc.page(pg)
        if page is None:
            continue
        ltr = page.text_side(m)
        if ltr is None:
            continue
        col = page.column(m, ltr)
        win = page.window(col)
        lines = win.lines
        j = win.first_line(m.y)
        if j is None:
            continue
        first = _extent(lines[j]["words"])
        edge = first.x0 if ltr else first.x1
        got = [BulletLine(pg, first, lines[j]["y1"] - lines[j]["y0"], " ".join(w[4] for w in lines[j]["words"]),
                            lines[j]["y1"])]
        nxt = min(_next_marker(bullets, i, m), _next_head(doc.heads_on.get(pg, ()), pg, m.y + 1, col))
        at_end = _follow(win, j + 1, edge, ltr, nxt, pg, got, lines[j])
        following = doc.page(pg + 1) if at_end else None
        if following is not None and doc.at_bottom(pg, col, got[-1], heights[pg - 1] if heights else None):
            # ran to the bottom of the column: the bullet may go on at the top of the next page, same column
            nxt = min((b.y for b in doc.bullets_on.get(pg + 1, ()) if abs(b.x - m.x) <= _EDGE_SLACK),
                      default=float("inf"))
            nxt = min(nxt, _next_head(doc.heads_on.get(pg + 1, ()), pg + 1, float("-inf"), col))
            _follow(following.window(col), 0, edge, ltr, nxt, pg + 1, got, None)
        out.append((m, got))
    return out


def bullet_layout(marks: list[Mark], sized: list[tuple[float, float, list[WordBox]]]) -> BulletLayout:
    """The words and the located bullets of one run, for the runts and rhythm gates to share: the bullets are
    located once, and not at all on a page denser than the declared size (the gates refuse that page)."""
    pages = [items for _, _, items in sized]
    heights = [h for _, h, _ in sized]
    located = [] if too_dense("", pages, marks) is not None else located_bullets(marks, pages, heights)
    return BulletLayout(pages, heights, located)


def is_runt(lines: list[BulletLine], runt_em: float = RUNT_EM, runt_frac: float = RUNT_FRAC) -> bool:
    """A wrapped bullet whose last line is narrow both in line heights and against its widest line."""
    if len(lines) < 2:
        return False
    last = lines[-1]
    width = last.extent.x1 - last.extent.x0
    widest = max(ln.extent.x1 - ln.extent.x0 for ln in lines)
    return width <= runt_em * last.height and width <= runt_frac * widest


def check_runts(marks: list[Mark] | None, layout: BulletLayout | None, *, fail: Callable[[str], Finding],
                runt_em: float = RUNT_EM, runt_frac: float = RUNT_FRAC) -> list[Finding]:
    """FAIL per wrapped bullet whose last line is a runt; a WARN when the bullets could not be measured
    (no bullet marks: a CV that does not draw its list through the lib marker; `layout` None: no word positions)."""
    if marks is None:
        return [(Level.WARN, "bullet runt lines not measured: typst query unavailable")]
    if not any(m.get("kind") == "bullet" for m in marks):
        return [(Level.WARN, "bullet runt lines not measured: no lib bullet marks "
                             "(draw the list through lib list-marker or bullet-marked; drawn-marker is the untagged inline separator)")]
    if layout is None:
        return [(Level.WARN, "bullet runt lines not measured: word positions unavailable")]
    if (dense := density_guard("bullet runts", layout.pages, marks, fail)) is not None:
        return dense
    out: list[Finding] = []
    for _, lines in layout.located:
        pg = lines[-1].page
        if is_runt(lines, runt_em, runt_frac):
            out.append(fail(f'bullet runt line on page {pg}: last line of a {len(lines)}-line bullet is '
                            f'"{lines[-1].text}" (a few glyphs alone) — a bullet is one line or its lines are '
                            "full: tighten it to one line, or develop it so the last line is substantial; "
                            "re-run --tune and the gate"))
    return out
