"""The grouping code replaced by the LOG320 worst-case sweep, kept verbatim as the oracle of the equivalence tests
(tests/unit/test_proximity_complexity.py): every head rebuilt the normalised words of its page (`_find_run`), re-sorted
and re-clustered them (`_lines`), searched the lines for its word (`_line_index`) and filtered every mark of the
document for the next block. Not imported by the product."""
from __future__ import annotations

from collections.abc import Sequence

from vitae.core.base import (
    GapFn,
    GroupMeasure,
    HeadMark,
    Mark,
    Measure,
    SecMark,
    SecMeasure,
    Word,
    _Line,
    is_placed,
    is_sec_placed,
)
from vitae.verify.groups.proximity import _box, _dx, _group_row, _KMark, _NextBlock
from vitae.verify.groups.query import _gnorm


def lines_rebuilt(words: Sequence[Word], x_min: float) -> list[_Line]:
    """Words (x0, y0, x1, y1, text) at or right of x_min, clustered into text
    lines by y-centre -> sorted list of dicts {y0, y1, c, x0, words}."""
    ws = sorted((w for w in words if w[0] >= x_min), key=lambda w: (w[1] + w[3]) / 2)
    out: list[_Line] = []
    for w in ws:
        c = (w[1] + w[3]) / 2
        # 3.0pt y-centre tolerance: words of slightly different sizes/weights on one baseline stay in one line
        # while adjacent lines (~12-15pt baseline-to-baseline) never merge.
        if out and abs(c - out[-1]["c"]) <= 3.0:     # same text line: centres within 3pt
            ln = out[-1]
            ln["words"].append(w)
            y0, y1 = min(ln["y0"], w[1]), max(ln["y1"], w[3])
            out[-1] = {"y0": y0, "y1": y1, "c": (y0 + y1) / 2, "x0": min(ln["x0"], w[0]), "words": ln["words"]}
        else:
            out.append({"y0": w[1], "y1": w[3], "c": c, "x0": w[0], "words": [w]})
    return out


def find_run_scanning(words: Sequence[Word], text: str, ytyp: float) -> list[Word] | None:
    """The words of `text` (first 4 tokens) nearest typst y `ytyp` -> list of
    word tuples, or None."""
    # Up to 4 tokens is enough to identify an entry head uniquely without crossing a line wrap.
    toks = [t for t in (_gnorm(w) for w in text.split()) if t][:4]
    if not toks:
        return None
    norm = [_gnorm(w[4]) for w in words]
    best = None
    for j in range(len(words)):
        if norm[j] != toks[0]:
            continue
        run, k = [j], j + 1
        for t in toks[1:]:
            while k < len(words) and norm[k] == "":
                k += 1
            if k < len(words) and norm[k] == t:
                run.append(k)
                k += 1
            else:
                break
        else:
            yc = (words[j][1] + words[j][3]) / 2
            if best is None or abs(yc - ytyp) < best[0]:
                best = (abs(yc - ytyp), run)
    # >30pt (~2 lines) from the <vitae-head> marker's y: a match that far away is a repeated word elsewhere on the page.
    if best is None or best[0] > 30:     # nearest match is over 30pt from the marker's y: not located
        return None
    return [words[k] for k in best[1]]


def line_index_scanning(lines: list[_Line], run: list[Word]) -> int | None:
    """Index in `lines` of the line holding the first word of `run` (matched by identity)."""
    w = run[0]
    for i, ln in enumerate(lines):
        if any(x is w for x in ln["words"]):
            return i
    return None


def next_block_filtering(h: HeadMark, hx: float, words: list[Word], marks: list[_KMark],
                later: list[_KMark]) -> _NextBlock | None:
    """The block after head `h`: (its mark, its words, whether it is a rail title), or None when its
    text is not located in the PDF."""
    m = min(later, key=lambda m: m.y)
    mrun = find_run_scanning(words, m.text, m.y)
    if mrun is None:
        return None
    # a rail title sits wholly LEFT of the body column (margin-index); a title
    # that merely starts left of an indented head (gutter-rail's skill rows
    # open with a drawn mark) is an in-flow title, its own line in the flow
    rail = max(w[2] for w in mrun) < hx - 2
    if rail:
        # Rail title beside the body: its y is the top of the title cell (rule
        # + gap), a few pt ABOVE the body's first line, so matching it by
        # y-centre lands one line too low. If an in-column head opens within
        # that window, THAT is the next block of this column's flow.
        h2 = [x for x in marks if x.k == "h" and x.page == h["page"]
              and _dx(x, h) <= 60 and m.y - 3 <= x.y <= m.y + 15]
        if h2:
            m = min(h2, key=lambda x: x.y)
            mrun = find_run_scanning(words, m.text, m.y)
            if mrun is None:
                return None
    return _NextBlock(m, mrun, rail)


def next_line_index_rebuilding(words: list[Word], hx: float, lines: list[_Line], run: list[Word], i0: int,
                     mrun: list[Word], rail: bool) -> tuple[list[_Line], int | None, int | None]:
    """(lines, index of the head's line, index of the next block's line) once the next block is
    known; either index is None when it cannot be placed."""
    if not rail:
        mx0 = min(w[0] for w in mrun)
        i0n: int | None = i0
        if mx0 < hx - 2:               # in-flow title starting left of an indented head
            lines = lines_rebuilt(words, mx0 - 2)
            i0n = line_index_scanning(lines, run)
        return lines, i0n, line_index_scanning(lines, mrun) if i0n is not None else None
    # title set in a rail beside the body
    mc = (mrun[0][1] + mrun[0][3]) / 2
    cand = [(abs(ln["c"] - mc), i) for i, ln in enumerate(lines)
            if i > i0 and abs(ln["c"] - mc) <= 12]
    return lines, i0, min(cand)[1] if cand else None


def measure_head_rebuilding(h: HeadMark, marks: list[_KMark], pages_words: list[list[Word]],
                  gap_fn: GapFn) -> tuple[GroupMeasure | None, bool]:
    """(row, skipped) for one head: a row when its group is measurable; skipped when its text or its next
    block could not be located; neither for a last block on its page or a single-line group."""
    if not 1 <= h["page"] <= len(pages_words):
        return None, True
    words = pages_words[h["page"] - 1]
    run = find_run_scanning(words, h["text"], h["y"])
    if run is None:
        return None, True
    hx = min(w[0] for w in run)
    lines = lines_rebuilt(words, hx - 2)
    i0 = line_index_scanning(lines, run)
    if i0 is None:
        return None, True
    # next block head on this page (entry head, skill label or section title)
    later = [m for m in marks if m.page == h["page"] and m.y > h["y"] + 2
             and not (m.k == "h" and _dx(m, h) > 60)]
    if not later:
        return None, False                 # last block on its page: no next head
    nb = next_block_filtering(h, hx, words, marks, later)
    if nb is None:
        return None, True
    lines, i0n, i_next = next_line_index_rebuilding(words, hx, lines, run, i0, nb.words, nb.rail)
    if i_next is None or i0n is None or i_next <= i0n + 1:
        return None, False                 # single-line group (or no next head): nothing inside
    return _group_row(h, nb.mark, lines, i0n, i_next, gap_fn), False


def section_rows_rebuilding(heads: list[HeadMark], secs: list[SecMark], pages_words: list[list[Word]],
                  gap_fn: GapFn) -> list[SecMeasure]:
    """Section rows: previous block's last line -> title (bar) vs title -> first line."""
    rows: list[SecMeasure] = []
    xs: dict[int, list[float]] = {}
    for h in heads:
        xs.setdefault(h["page"], []).append(h["x"])
    for sc in secs:
        pg = sc["page"]
        if not pg or pg - 1 >= len(pages_words) or pg not in xs:
            continue
        words = pages_words[pg - 1]
        srun = find_run_scanning(words, sc["text"], sc["y"])
        bx = min(xs[pg])
        if srun is None or min(w[0] for w in srun) < bx - 5:
            continue                       # unlocated, or a rail title beside the body
        lines = lines_rebuilt(words, bx - 2)
        i = line_index_scanning(lines, srun)
        if i is None or i < 1 or i + 1 >= len(lines):
            continue
        up, t, lo = _box(lines[i - 1]), _box(lines[i]), _box(lines[i + 1])
        before, after = gap_fn(pg, up, t), gap_fn(pg, t, lo)
        rows.append(SecMeasure(text=sc["text"], page=pg, before=before, after=after,
                               ratio=(before / after) if after > 0 else float("inf")))
    return rows


def measure_groups_rebuilding(heads: list[Mark], secs: list[Mark], pages_words: list[list[Word]],
                   gap_fn: GapFn | None = None) -> tuple[list[Measure], int]:
    """Whole-group proximity. A group is an entry/skill row from its FIRST line
    (the role / label) through its LAST line (org line, bullets, wrapped lines
    included), up to the next block's head (entry head, skill label or section
    title of the same column flow). Per group: internal = the MAX gap between
    consecutive lines inside it, between = the gap from its last line to the
    next block's first line; ratio = between / internal. Gaps are ink gaps when
    gap_fn is given (default: pdftotext box gap). Section titles are measured
    too: sbefore = last line of the previous block -> title (its bar), safter =
    title -> first line of its section. Returns (rows, skipped); rows are
    {kind: "group"|"sec", text, page, ...}. Single-line groups, last blocks on a
    page, rail titles beside the body and unlocated text are skipped."""
    gap_fn = gap_fn or (lambda page, up, lo: lo[2] - up[3])
    # a partial mark has no position to measure from: skipped
    placed: list[HeadMark] = [h for h in heads if is_placed(h)]
    placed_secs: list[SecMark] = [sc for sc in secs if is_sec_placed(sc)]
    rows: list[Measure] = []
    skipped = 0
    # the marks tagged with their kind ("h" head / "s" section)
    marks: list[_KMark] = [_KMark("h", h["text"], h["page"], h["y"], h["x"]) for h in placed]
    marks.extend(_KMark("s", s["text"], s["page"], s["y"], s.get("x")) for s in placed_secs)
    for h in sorted(placed, key=lambda h: (h["page"], h["y"])):
        row, skip = measure_head_rebuilding(h, marks, pages_words, gap_fn)
        skipped += skip
        if row is not None:
            rows.append(row)
    rows.extend(section_rows_rebuilding(placed, placed_secs, pages_words, gap_fn))
    return rows, skipped

