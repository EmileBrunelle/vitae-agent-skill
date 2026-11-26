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

from collections.abc import Callable
from dataclasses import dataclass

from vitae.core.base import HeadMark, Mark, Word, WordBox, _Line, is_placed
from vitae.core.level import Finding, Level
from vitae.verify.groups.query import _lines
from vitae.verify.pdf import _bbox_pages

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


@dataclass(frozen=True)
class Extent:
    x0: float
    x1: float


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
    y1: float = 0.0


def _positions(marks: list[Mark]) -> list[Pos]:
    placed: list[HeadMark] = [m for m in marks if is_placed(m)]
    return [Pos(m["page"], m["x"], m["y"]) for m in placed if m.get("kind") == "bullet"]


def _text_side(words: list[Word], m: Pos) -> bool | None:
    """True when the bullet's text is right of its marker (left-to-right), False when left of it, None when
    no word sits near the marker's y: the side of the horizontally nearest word."""
    near = [w for w in words if abs((w[1] + w[3]) / 2 - m.y) <= _MARKER_BAND]
    right = [w[0] - m.x for w in near if w[0] >= m.x - 0.5]
    left = [m.x - w[2] for w in near if w[2] <= m.x + 0.5]
    if not right and not left:
        return None
    return min(right, default=float("inf")) <= min(left, default=float("inf"))


def _column(words: list[Word], m: Pos, ltr: bool) -> tuple[float, float]:
    """The x range of the marker's column: from the marker out to the first clear vertical channel (wider
    than a few interword spaces: no word of any line below crosses it, so justified text is not cut) in the words at or below the marker, so a sidebar beside it is not part of it."""
    below = [w for w in words if (w[1] + w[3]) / 2 >= m.y - _MARKER_BAND
             and (w[0] >= m.x - 0.5 if ltr else w[2] <= m.x + 0.5)]
    if not below:
        return (m.x - 0.5, float("inf")) if ltr else (float("-inf"), m.x + 0.5)
    below.sort(key=lambda w: w[0] if ltr else -w[2])
    gap = _CHANNEL * max(w[3] - w[1] for w in below[:1])
    edge = below[0][2] if ltr else below[0][0]
    for w in below:
        if ltr:
            if w[0] - edge > gap:
                return (m.x - 0.5, edge + 0.5)
            edge = max(edge, w[2])
        else:
            if edge - w[2] > gap:
                return (edge - 0.5, m.x + 0.5)
            edge = min(edge, w[0])
    return (m.x - 0.5, float("inf")) if ltr else (float("-inf"), m.x + 0.5)


def _window(words: list[WordBox], col: tuple[float, float]) -> list[_Line]:
    """The text lines made of the words inside the column's x range only."""
    ws = [(b[0], b[1], b[2], b[3], t) for b, t in words if b[0] >= col[0] - 0.5 and b[2] <= col[1] + 0.5]
    return _lines(ws, float("-inf"))


def _first_line(lines: list[_Line], y: float) -> int | None:
    """The line whose centre is nearest the marker's y, if within the band (at most half the line pitch,
    so at small type the previous bullet's line is not taken for it)."""
    if not lines:
        return None
    j = min(range(len(lines)), key=lambda k: abs(lines[k]["c"] - y))
    near = [abs(lines[k]["c"] - lines[j]["c"]) for k in (j - 1, j + 1) if 0 <= k < len(lines)]
    band = min(_MARKER_BAND, min(near) / 2) if near else _MARKER_BAND
    return j if abs(lines[j]["c"] - y) <= band else None


def _follow(lines: list[_Line], start: int, edge: float, ltr: bool, nxt: float, pg: int,
            got: list[BulletLine], prev: _Line | None) -> bool:
    """Append the lines from `start` that continue the bullet, up to the next bullet's first line; True when
    it ran to the end of the column (so it may go on at the top of the next page)."""
    stop = _first_line(lines, nxt) if nxt != float("inf") else None
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


def _next_head(heads: list[HeadMark], page: int, after: float, col: tuple[float, float]) -> float:
    """The y of the first entry head or part mark below `after` on `page`, in the bullet's column (within
    _HEAD_REACH of its x range, so a sidebar's heads do not count): the next entry starts there, and its first
    line is not a continuation of the bullet above even though it shares its edge."""
    return min((h["y"] for h in heads if h["page"] == page and h["y"] > after
                and col[0] - _HEAD_REACH <= h["x"] <= col[1] + _HEAD_REACH), default=float("inf"))


def _at_bottom(pages: list[list[WordBox]], pg: int, col: tuple[float, float], last: BulletLine,
               page_h: float | None) -> bool:
    """True when the bullet's last line (on page `pg`, 1-based) sits where its column's content ends, so the
    next line would not have fitted: within _BOTTOM_LINES line heights (widow/orphan control moves two lines
    together) of the content bottom. The bottom is read from the document: the lowest text of the column's x
    band on any page; it counts only when another page reaches about as low as this one (else the bullet is its own
    only evidence). Alone, the bottom margin is taken as large as the next page's top margin (its topmost text),
    which is a guess for unequal margins. A footer inside the column band raises the bottom: a split can be
    missed there, never invented."""
    lowest = [max((b[3] for b, _ in page if b[0] >= col[0] - 0.5 and b[2] <= col[1] + 0.5), default=float("-inf"))
              for page in pages]
    window = _BOTTOM_LINES * last.height
    others = max((v for i, v in enumerate(lowest) if i != pg - 1), default=float("-inf"))
    if others >= last.y1 - last.height:
        return last.y1 >= max(others, lowest[pg - 1]) - window
    if page_h is None:
        return last.y1 >= lowest[pg - 1] - 0.5
    return last.y1 >= page_h - min(b[1] for b, _ in pages[pg]) - window


def bullet_lines(marks: list[Mark], pages: list[list[WordBox]],
                 heights: list[float] | None = None) -> list[tuple[int, list[BulletLine]]]:
    """Per bullet mark (page, lines top to bottom); a bullet whose first line cannot be located is dropped.
    Only the words of the marker's own column count, and a bullet runs on across a page break when its last
    line is at the bottom of the content (`heights`: the page heights)."""
    return [(pos.page, got) for pos, got in located_bullets(marks, pages, heights)]


def located_bullets(marks: list[Mark], pages: list[list[WordBox]],
                    heights: list[float] | None = None) -> list[tuple[Pos, list[BulletLine]]]:
    """bullet_lines with the bullet's marker position (page, x, y) instead of its page."""
    bullets = sorted(_positions(marks), key=lambda p: (p.page, p.y))
    heads: list[HeadMark] = [h for h in marks if is_placed(h) and h.get("kind") != "bullet"]
    out: list[tuple[Pos, list[BulletLine]]] = []
    for i, m in enumerate(bullets):
        pg = m.page
        if not 1 <= pg <= len(pages):
            continue
        raw = [(b[0], b[1], b[2], b[3], t) for b, t in pages[pg - 1]]
        ltr = _text_side(raw, m)
        if ltr is None:
            continue
        col = _column(raw, m, ltr)
        lines = _window(pages[pg - 1], col)
        j = _first_line(lines, m.y)
        if j is None:
            continue
        first = _extent(lines[j]["words"])
        edge = first.x0 if ltr else first.x1
        got = [BulletLine(pg, first, lines[j]["y1"] - lines[j]["y0"], " ".join(w[4] for w in lines[j]["words"]),
                            lines[j]["y1"])]
        nxt = min(next((b.y for b in bullets[i + 1:] if b.page == pg and abs(b.x - m.x) <= _EDGE_SLACK and b.y > m.y + 1),
                       float("inf")), _next_head(heads, pg, m.y + 1, col))
        at_end = _follow(lines, j + 1, edge, ltr, nxt, pg, got, lines[j])
        if at_end and pg < len(pages) and _at_bottom(pages, pg, col, got[-1], heights[pg - 1] if heights else None):
            # ran to the bottom of the column: the bullet may go on at the top of the next page, same column
            nxt = min((b.y for b in bullets if b.page == pg + 1 and abs(b.x - m.x) <= _EDGE_SLACK),
                      default=float("inf"))
            nxt = min(nxt, _next_head(heads, pg + 1, float("-inf"), col))
            _follow(_window(pages[pg], col), 0, edge, ltr, nxt, pg + 1, got, None)
        out.append((m, got))
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
                             "(draw the list through lib list-marker or bullet-marked; drawn-marker is the untagged inline separator)")]
    sized = _bbox_pages(pdf)
    if sized is None:
        return [(Level.WARN, "bullet runt lines not measured: word positions unavailable")]
    out: list[Finding] = []
    for _, lines in bullet_lines(marks, [items for _, _, items in sized], [h for _, h, _ in sized]):
        pg = lines[-1].page
        if is_runt(lines, runt_em, runt_frac):
            out.append(fail(f'bullet runt line on page {pg}: last line of a {len(lines)}-line bullet is '
                            f'"{lines[-1].text}" (a few glyphs alone) — a bullet is one line or its lines are '
                            "full: tighten it to one line, or develop it so the last line is substantial; "
                            "re-run --tune and the gate"))
    return out
