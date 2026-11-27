"""runts.py code replaced by the LOG320 worst-case sweep, kept verbatim (but for one `default=` in at_bottom_rescanning, see
there) as the oracle of the equivalence tests
(tests/unit/test_runts_complexity.py): every bullet rebuilt the word list of its page, re-sorted it for the column,
re-clustered the words of the column into lines and rescanned every page for the content bottom. Not imported by the
product."""
from __future__ import annotations

from _proximity_ref import lines_rebuilt
from vitae.core.base import HeadMark, Mark, Word, WordBox, _Line, is_placed
from vitae.verify.runts import (
    _BOTTOM_LINES,
    _CHANNEL,
    _EDGE_SLACK,
    _MARKER_BAND,
    BulletLine,
    Pos,
    _extent,
    _next_head,
    _positions,
)


def text_side_filtering(words: list[Word], m: Pos) -> bool | None:
    """True when the bullet's text is right of its marker (left-to-right), False when left of it, None when
    no word sits near the marker's y: the side of the horizontally nearest word."""
    near = [w for w in words if abs((w[1] + w[3]) / 2 - m.y) <= _MARKER_BAND]
    right = [w[0] - m.x for w in near if w[0] >= m.x - 0.5]
    left = [m.x - w[2] for w in near if w[2] <= m.x + 0.5]
    if not right and not left:
        return None
    return min(right, default=float("inf")) <= min(left, default=float("inf"))


def column_sorting(words: list[Word], m: Pos, ltr: bool) -> tuple[float, float]:
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


def window_rebuilding(words: list[WordBox], col: tuple[float, float]) -> list[_Line]:
    """The text lines made of the words inside the column's x range only."""
    ws = [(b[0], b[1], b[2], b[3], t) for b, t in words if b[0] >= col[0] - 0.5 and b[2] <= col[1] + 0.5]
    return lines_rebuilt(ws, float("-inf"))


def at_bottom_rescanning(pages: list[list[WordBox]], pg: int, col: tuple[float, float], last: BulletLine,
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
    return last.y1 >= page_h - min((b[1] for b, _ in pages[pg]), default=float("inf")) - window    # verbatim but for `default=`: an empty next page raised ValueError


def located_bullets_rebuilding(marks: list[Mark], pages: list[list[WordBox]],
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
        ltr = text_side_filtering(raw, m)
        if ltr is None:
            continue
        col = column_sorting(raw, m, ltr)
        lines = window_rebuilding(pages[pg - 1], col)
        j = first_line_scanning(lines, m.y)
        if j is None:
            continue
        first = _extent(lines[j]["words"])
        edge = first.x0 if ltr else first.x1
        got = [BulletLine(pg, first, lines[j]["y1"] - lines[j]["y0"], " ".join(w[4] for w in lines[j]["words"]),
                            lines[j]["y1"])]
        nxt = min(next((b.y for b in bullets[i + 1:] if b.page == pg and abs(b.x - m.x) <= _EDGE_SLACK and b.y > m.y + 1),
                       float("inf")), _next_head(heads, pg, m.y + 1, col))
        at_end = follow_scanning(lines, j + 1, edge, ltr, nxt, pg, got, lines[j])
        if at_end and pg < len(pages) and at_bottom_rescanning(pages, pg, col, got[-1], heights[pg - 1] if heights else None):
            # ran to the bottom of the column: the bullet may go on at the top of the next page, same column
            nxt = min((b.y for b in bullets if b.page == pg + 1 and abs(b.x - m.x) <= _EDGE_SLACK),
                      default=float("inf"))
            nxt = min(nxt, _next_head(heads, pg + 1, float("-inf"), col))
            follow_scanning(window_rebuilding(pages[pg], col), 0, edge, ltr, nxt, pg + 1, got, None)
        out.append((m, got))
    return out

def first_line_scanning(lines: list[_Line], y: float) -> int | None:
    """The line whose centre is nearest the marker's y, if within the band (at most half the line pitch,
    so at small type the previous bullet's line is not taken for it)."""
    if not lines:
        return None
    j = min(range(len(lines)), key=lambda k: abs(lines[k]["c"] - y))
    near = [abs(lines[k]["c"] - lines[j]["c"]) for k in (j - 1, j + 1) if 0 <= k < len(lines)]
    band = min(_MARKER_BAND, min(near) / 2) if near else _MARKER_BAND
    return j if abs(lines[j]["c"] - y) <= band else None


def follow_scanning(lines: list[_Line], start: int, edge: float, ltr: bool, nxt: float, pg: int,
            got: list[BulletLine], prev: _Line | None) -> bool:
    """Append the lines from `start` that continue the bullet, up to the next bullet's first line; True when
    it ran to the end of the column (so it may go on at the top of the next page)."""
    stop = first_line_scanning(lines, nxt) if nxt != float("inf") else None
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
