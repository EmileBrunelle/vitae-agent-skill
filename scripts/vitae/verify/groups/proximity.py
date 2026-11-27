"""Whole-group proximity: optical line gaps, group measurement and the group/section proximity gate."""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Literal

from vitae.core.base import (
    DetailRow,
    GapFn,
    GroupMeasure,
    GroupRow,
    HeadMark,
    LineBox,
    Mark,
    Measure,
    SecMark,
    SecMeasure,
    SecRow,
    TextLine,
    Word,
    is_placed,
    is_sec_placed,
)
from vitae.core.env import pdf_backend
from vitae.core.level import Finding, Level
from vitae.verify.bounds import density_guard, page_at
from vitae.verify.groups.ink import page_ink_gap
from vitae.verify.groups.query import LineSet, PageIndex, gnorm, typst_query
from vitae.verify.pdf import boxes_unavailable, word_boxes


@dataclass(frozen=True, slots=True)
class KMark:
    """A head or section mark tagged with its kind: "h" head / "s" section (a section has no x)."""
    k: Literal["h", "s"]
    text: str
    page: int
    y: float
    x: float | None


@dataclass(frozen=True, slots=True)
class _NextBlock:
    """The block after a head: its mark, its words in the PDF, and whether it is a rail title."""
    mark: KMark
    words: list[Word]
    rail: bool


@dataclass(frozen=True, slots=True)
class _HeadSpot:
    """Where a head sits in the PDF text: the words of its first line, its left edge and the lines of its column
    with the index of that line."""
    hx: float
    lines: LineSet
    run: list[Word]
    i0: int


def _dx(m: KMark, h: HeadMark) -> float:
    """Horizontal distance from head `h` to mark `m`; a section mark has no x, so it is infinitely far."""
    return abs(m.x - h["x"]) if m.x is not None else float("inf")


def org_on_one_line(org: str, line: TextLine) -> bool:
    """True when the org text's first and last tokens both sit on `line`: the line under the role is the
    whole org line (a wrapped role pushes the org down, a wrapped org spills onto the next line)."""
    toks = [t for t in (gnorm(w) for w in org.split()) if t]
    if not toks:
        return False
    have = {gnorm(w[4]) for w in line["words"]}
    return toks[0] in have and toks[-1] in have


def _box(ln: TextLine) -> LineBox:
    """The [x0, x1, y0, y1] box of a text line."""
    return [ln["x0"], max(w[2] for w in ln["words"]), ln["y0"], ln["y1"]]


def _next_block(h: HeadMark, hx: float, idx: PageIndex, page_marks: list[KMark],
                later: list[KMark]) -> _NextBlock | None:
    """The block after head `h`, or None when its text is not located in the PDF.
    `page_marks`: the marks on `h`'s page."""
    m = min(later, key=lambda m: m.y)
    mrun = idx.find_run(m.text, m.y)
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
        h2 = [x for x in page_marks if x.k == "h"
              and _dx(x, h) <= 60 and m.y - 3 <= x.y <= m.y + 15]
        if h2:
            m = min(h2, key=lambda x: x.y)
            mrun = idx.find_run(m.text, m.y)
            if mrun is None:
                return None
    return _NextBlock(m, mrun, rail)


def _next_line_index(idx: PageIndex, spot: _HeadSpot, nb: _NextBlock) -> tuple[LineSet, int | None, int | None]:
    """(lines, index of the head's line, index of the next block's line) once the next block is
    known; either index is None when it cannot be placed."""
    hx, lines, run, i0 = spot.hx, spot.lines, spot.run, spot.i0
    mrun = nb.words
    if not nb.rail:
        mx0 = min(w[0] for w in mrun)
        i0n: int | None = i0
        if mx0 < hx - 2:               # in-flow title starting left of an indented head
            lines = idx.lines(mx0 - 2)
            i0n = lines.line_index(run)
        return lines, i0n, lines.line_index(mrun) if i0n is not None else None
    # title set in a rail beside the body
    mc = (mrun[0][1] + mrun[0][3]) / 2
    cand = [(abs(ln["c"] - mc), i) for i, ln in enumerate(lines.lines)
            if i > i0 and abs(ln["c"] - mc) <= 12]
    return lines, i0, min(cand)[1] if cand else None


def _group_row(h: HeadMark, m: KMark, lines: list[TextLine], i0: int, i_next: int,
               gap_fn: GapFn) -> GroupMeasure:
    """The measured row of the group running from line i0 through line i_next (the next block's)."""
    ls = [_box(ln) for ln in lines[i0:i_next + 1]]
    tx = [" ".join(w[4] for w in sorted(ln["words"], key=lambda w: w[0])[:4])[:28]
          for ln in lines[i0:i_next + 1]]
    gaps = [gap_fn(h["page"], ls[i], ls[i + 1]) for i in range(len(ls) - 2)]
    between = gap_fn(h["page"], ls[-2], ls[-1])
    internal = max(gaps)
    wi = gaps.index(internal)              # the line pair behind the largest internal gap
    # head -> first bullet vs the bullet pitch: line 0 is the role, line 1 the org/descriptor line
    # (only when the entry was given an org), the lines after it the bullets. An entry whose role or
    # org wraps is skipped: its line 1 would not be the whole org line, so gaps[1] is not that gap.
    n = len(ls) - 1
    hb: float | None = None
    pitch: float | None = None
    org = h.get("org")
    if h.get("kind") == "entry" and org and n >= 4 and org_on_one_line(org, lines[i0 + 1]):
        hb, pitch = gaps[1], statistics.median(gaps[2:])
    return GroupMeasure(text=h["text"], page=h["page"], n=n, hkind=h.get("kind"),
                        next_sec=m.k == "s", head_gap=hb, pitch=pitch,
                        gaps=gaps, internal=internal, between=between,
                        ratio=(between / internal) if internal > 0 else float("inf"), ls=ls,
                        pair_in=(tx[wi], tx[wi + 1]), pair_btw=(tx[-2], tx[-1]))


def _measure_head(h: HeadMark, page_marks: list[KMark], idx: PageIndex | None,
                  gap_fn: GapFn) -> tuple[GroupMeasure | None, bool]:
    """(row, skipped) for one head: a row when its group is measurable; skipped when its text or its next
    block could not be located; neither for a last block on its page or a single-line group. `idx`: the index of
    the head's page (None when the PDF has no such page), `page_marks`: the marks on that page."""
    if idx is None:
        return None, True
    run = idx.find_run(h["text"], h["y"])
    if run is None:
        return None, True
    hx = min(w[0] for w in run)
    lines = idx.lines(hx - 2)
    i0 = lines.line_index(run)
    if i0 is None:
        return None, True
    # next block head on this page (entry head, skill label or section title)
    later = [m for m in page_marks if m.y > h["y"] + 2
             and not (m.k == "h" and _dx(m, h) > 60)]
    if not later:
        return None, False                 # last block on its page: no next head
    nb = _next_block(h, hx, idx, page_marks, later)
    if nb is None:
        return None, True
    lines, i0n, i_next = _next_line_index(idx, _HeadSpot(hx, lines, run, i0), nb)
    if i_next is None or i0n is None or i_next <= i0n + 1:
        return None, False                 # single-line group (or no next head): nothing inside
    return _group_row(h, nb.mark, lines.lines, i0n, i_next, gap_fn), False


def _section_rows(heads: list[HeadMark], secs: list[SecMark], pages: list[PageIndex],
                  gap_fn: GapFn) -> list[SecMeasure]:
    """Section rows: previous block's last line -> title (bar) vs title -> first line."""
    rows: list[SecMeasure] = []
    xs: dict[int, list[float]] = {}
    for h in heads:
        xs.setdefault(h["page"], []).append(h["x"])
    for sc in secs:
        pg = sc["page"]
        idx = page_at(pages, pg)
        if idx is None or pg not in xs:
            continue
        srun = idx.find_run(sc["text"], sc["y"])
        bx = min(xs[pg])
        if srun is None or min(w[0] for w in srun) < bx - 5:
            continue                       # unlocated, or a rail title beside the body
        lines = idx.lines(bx - 2)
        i = lines.line_index(srun)
        if i is None or i < 1 or i + 1 >= len(lines.lines):
            continue
        up, t, lo = _box(lines.lines[i - 1]), _box(lines.lines[i]), _box(lines.lines[i + 1])
        before, after = gap_fn(pg, up, t), gap_fn(pg, t, lo)
        rows.append(SecMeasure(text=sc["text"], page=pg, before=before, after=after,
                               ratio=(before / after) if after > 0 else float("inf")))
    return rows


def measure_groups(heads: list[Mark], secs: list[Mark], pages_words: list[list[Word]],
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
    GroupMeasure / SecMeasure. Single-line groups, last blocks on a
    page, rail titles beside the body and unlocated text are skipped."""
    gap_fn = gap_fn or (lambda page, up, lo: lo[2] - up[3])
    # a partial mark has no position to measure from: skipped
    placed: list[HeadMark] = [h for h in heads if is_placed(h)]
    placed_secs: list[SecMark] = [sc for sc in secs if is_sec_placed(sc)]
    rows: list[Measure] = []
    skipped = 0
    # the marks tagged with their kind ("h" head / "s" section)
    marks: list[KMark] = [KMark("h", h["text"], h["page"], h["y"], h["x"]) for h in placed]
    marks.extend(KMark("s", s["text"], s["page"], s["y"], s.get("x")) for s in placed_secs)
    by_page: dict[int, list[KMark]] = {}
    for m in marks:
        by_page.setdefault(m.page, []).append(m)
    # one index per page, built once for every head and title on it
    pages = [PageIndex(words) for words in pages_words]
    for h in sorted(placed, key=lambda h: (h["page"], h["y"])):
        row, skip = _measure_head(h, by_page[h["page"]], page_at(pages, h["page"]), gap_fn)
        skipped += skip
        if row is not None:
            rows.append(row)
    rows.extend(_section_rows(placed, placed_secs, pages, gap_fn))
    return rows, skipped


def hier_advice(kind: str | None) -> str:
    """Where to widen the gap between entries: the family's own wrapper, once, for every entry."""
    if kind == "skill":
        return ("      widen the gap between skill rows in the family's `skill` wrapper (its `srow(above:)`, or "
                "`#set par(spacing:)` for bare rows), once for every row; never per row, never in lib.typ, not the content")
    return ("      widen the gap between entries in the family's `job` wrapper (its `entry(above:)`), once for every "
            "entry; never per entry, never in lib.typ, not the content")


# Gestalt-proximity thresholds on between/internal gap ratio; their calibration is recorded in
# check_group_proximity's docstring. Section titles use the first two; PROX_HIER (groups not followed
# by a section title) is the visible-hierarchy floor.
PROX_FAIL, PROX_WARN, PROX_HIER = 0.7, 0.85, 1.2


def _print_detail(rows: list[Measure], grp: list[GroupMeasure]) -> None:
    """The machine-readable DETAIL lines (the tests and --gates read them)."""
    for r in grp:
        hp = "" if r.head_gap is None or r.pitch is None else \
            f' head-gap={r.head_gap:.2f}pt pitch={r.pitch:.2f}pt'
        print(f'DETAIL group "{r.text[:30]}" p{r.page} lines={r.n} internal={r.internal:.2f}pt '
              f'between={r.between:.2f}pt ratio={r.ratio:.2f}{hp}{" next=section" if r.next_sec else ""}')
    for row in rows:
        if isinstance(row, SecMeasure):
            print(f'DETAIL section "{row.text[:30]}" p{row.page} before-bar={row.before:.2f}pt '
                  f'bar-to-first={row.after:.2f}pt ratio={row.ratio:.2f}')


def _section_finding(sec: list[SecMeasure]) -> Finding:
    """The verdict on the section titles: a title belongs to what FOLLOWS it, so the gap above it (previous
    block's last line -> title or its bar) must not be much smaller than the gap below it (title -> first
    line). Same calibration as groups."""
    s = min(sec, key=lambda r: r.ratio)
    sw = (f'(worst "{s.text[:30]}": gap above {s.before:.1f}pt, gap below '
          f'{s.after:.1f}pt, ratio {s.ratio:.2f}')
    sbad = [r for r in sec if not r.ratio >= PROX_FAIL]
    sweak = [r for r in sec if not r.ratio >= PROX_WARN]
    if sbad:
        return (Level.FAIL, f"section proximity: {len(sbad)}/{len(sec)} titles sit closer to the block "
                f"above than to their own first line {sw}; need >= {PROX_FAIL}) — fix the family's "
                "`section` (its `above` and the gap under the title), not the content file")
    if sweak:
        return (Level.WARN, f"section proximity: {len(sweak)}/{len(sec)} titles barely separated from "
                f"the block above {sw}; aim for >= {PROX_WARN})")
    return (Level.OK, f'section proximity: {len(sec)} titles, gap above >= {PROX_WARN} x gap below '
            f'(tightest "{s.text[:30]}": ratio {s.ratio:.2f})')


def _q(t: str) -> str:
    return '"' + t + '"'


def _flat_finding(flat: list[GroupMeasure], grp: list[GroupMeasure]) -> Finding:
    """The WARN for entries (or skill rows) too close to the next one to read as separate units."""
    f = min(flat, key=lambda r: r.ratio)
    # Plural names every flat group (mixed kinds read as entries); the worst-case clause names f's own kind.
    many, a_one = (("skill rows", "a skill row") if all(r.hkind == "skill" for r in flat)
                   else ("entries", "an entry"))
    one = "skill row" if f.hkind == "skill" else "entry"
    fw = (f'(worst {_q(f.text[:30])}: gap to the next {one} {f.between:.1f}pt vs {f.internal:.1f}pt '
          f'inside it, ratio {f.ratio:.2f})')
    return (Level.WARN, f"group proximity: {many} barely separated: gap between {many} ≈ gap inside "
            f"{a_one} in {len(flat)}/{len(grp)} groups {fw}; aim for >= {PROX_HIER}\n"
            + hier_advice(f.hkind))


def _group_finding(grp: list[GroupMeasure]) -> Finding:
    """The verdict on the entry/skill groups: the first of FAIL, WARN, hierarchy WARN, OK that applies."""
    m = min(grp, key=lambda r: r.ratio)
    worst = (f'(worst {_q(m.text[:30])}: largest gap inside {m.internal:.1f}pt '
             f'({_q(m.pair_in[0])} -> {_q(m.pair_in[1])}), gap to the next block '
             f'{m.between:.1f}pt ({_q(m.pair_btw[0])} -> {_q(m.pair_btw[1])}), ratio {m.ratio:.2f}')
    # `not x >= t` rather than `x < t`: a NaN ratio must count as failing
    bad = [r for r in grp if not r.ratio >= PROX_FAIL]
    if bad:
        return (Level.FAIL, f'group proximity: {len(bad)}/{len(grp)} groups sit closer to the next block than '
                f'their own lines are to each other {worst}; need >= {PROX_FAIL})\n'
                "      do not override entry/srow above/gap/below per entry; look for a manual #v, linebreak "
                "or blank line inside that entry (a gap that is too big inside is as bad as one too small after);\n"
                "      if the CV uses the family file as shipped, report it: it is a template bug (never edit lib.typ)")
    weak = [r for r in grp if not r.ratio >= PROX_WARN]
    if weak:
        return (Level.WARN, f'group proximity: {len(weak)}/{len(grp)} groups barely separated from the next block '
                f'{worst}; aim for >= {PROX_WARN})\n'
                "      do not override entry/srow above/gap/below per entry; check for a manual #v, linebreak or "
                "blank line inside that entry")
    # hierarchy: an entry must also read as ONE unit, so the gap to the next entry has to be visibly
    # larger than the gaps inside it. Groups before a section title are left to the section rules.
    flat = [r for r in grp if not r.next_sec and not r.ratio >= PROX_HIER]
    if flat:
        return _flat_finding(flat, grp)
    return (Level.OK, f"group proximity: {len(grp)} groups, gap to next block >= {PROX_WARN} x internal gap "
            f'(tightest "{m.text[:30]}": ratio {m.ratio:.2f}, {m.between:.1f}pt vs {m.internal:.1f}pt)')


def group_detail(r: GroupMeasure) -> GroupRow:
    """The DETAIL row of a group (the key order is the order of the printed JSON)."""
    return {"kind": "group", "text": r.text, "page": r.page, "n": r.n, "hkind": r.hkind, "next_sec": r.next_sec,
            "head_gap": r.head_gap, "pitch": r.pitch, "gaps": r.gaps, "internal": r.internal,
            "between": r.between, "ratio": r.ratio, "ls": r.ls, "pair_in": r.pair_in, "pair_btw": r.pair_btw}


def sec_detail(r: SecMeasure) -> SecRow:
    """The DETAIL row of a section title."""
    return {"kind": "sec", "text": r.text, "page": r.page, "before": r.before, "after": r.after, "ratio": r.ratio}


def detail_row(r: Measure) -> DetailRow:
    """The DETAIL row (the JSON shape) of a measured row: the serialization boundary of measure_groups."""
    return group_detail(r) if isinstance(r, GroupMeasure) else sec_detail(r)


def check_group_proximity(typ: str, pdf: str, root: str | None = None,
                          heads: list[Mark] | None = None, secs: list[Mark] | None = None,
                          pages: list[list[Word]] | None = None,
                          detail: list[DetailRow] | None = None) -> list[Finding]:
    """[(level, message)], level FAIL/WARN/OK. Gestalt proximity on whole
    groups: for every entry/skill row (first line through last line, org line
    and bullets included), the gap from its last line to the NEXT block's first
    line must not be much smaller than the largest gap between two lines
    inside it (ratio between/internal; OPTICAL gaps at 300 dpi, baseline of
    the upper line to x-height top of the lower one, so the words never move
    the ratio): FAIL below PROX_FAIL (0.7 — the head visibly belongs to the
    wrong block), WARN below PROX_WARN (0.85). Calibrated by eye on templates,
    fixtures and real model output with the earlier ink-gap measure (groups
    at 0.24-0.49 read as attached to the next entry, 0.82-0.96 as acceptable),
    then re-mapped to the optical measure by sweeping entry `above` 8pt -> 3pt
    on 6 families: the old FAIL line (0.6) lands at 0.64-0.79 optical (mean
    0.71), the old WARN line (0.83-0.86) at 0.81-0.91; shipped templates and
    fixtures sit at >= 0.85. Section titles get the same thresholds on gap above
    the title (or its bar) / gap below it to the section's first line (DETAIL
    rows, kind "sec").

    PROX_HIER (1.2, WARN, 2026-11-25): attached-to-next is not the only defect;
    an entry also has to read as one unit, i.e. the gap between entries clearly
    larger than the line gaps inside one. Groups followed by a section title are
    excluded (their `between` includes the section's `above`: 1.5-4.2). Measured
    per-file minimum ratio over the entry-to-entry groups: the previous (visibly
    defective) templates median 1.15; the fixed templates median 1.42, minimum
    1.07; real model CVs 0.92-1.19. 1.2 sits between the two template medians.

    Each group row also records head_gap (org line -> first bullet) and pitch
    (median bullet-to-bullet gap), printed in DETAIL for entries with an org line
    and >= 2 bullet lines. Measured head_gap/pitch (per-file minimum): previous
    templates 0.43-0.77, fixed templates 0.62-1.15 (most 0.82-1.1): the two
    ranges overlap, so it is a DETAIL figure only, never a finding."""
    heads = typst_query(typ, "<vitae-head>", root) if heads is None else heads
    secs = (typst_query(typ, "<vitae-sec>", root) or []) if secs is None else secs
    if pages is None:
        wb = word_boxes(pdf, with_text=True)
        pages = [[(b[0], b[1], b[2], b[3], t) for b, t in pg] for pg in wb] if wb else None
    if heads is None or pages is None:
        if pdf_backend() == "pdfium":
            return [(Level.WARN, "group proximity NOT checked (typst query unavailable or word positions "
                             "unreadable: " + boxes_unavailable(pdf) + ")")]
        return [(Level.WARN, "group proximity NOT checked (typst query or pdftotext unavailable)")]
    if not heads:
        return [(Level.WARN, "group proximity not measured: no lib entry()/srow() heads")]
    if (dense := density_guard("group proximity", pages, [*heads, *secs], lambda msg: (Level.FAIL, msg))) is not None:
        return dense
    # DETAIL lines are machine-readable and printed here, not returned: the tests and --gates read them
    rows, skipped = measure_groups(heads, secs, pages, page_ink_gap(pdf) if pdf else None)
    if detail is not None:
        detail.extend(detail_row(r) for r in rows)
    grp = [r for r in rows if isinstance(r, GroupMeasure)]
    if not grp:
        return [(Level.WARN, f"group proximity: no checkable group ({skipped} head(s) not located) — unchecked")]
    _print_detail(rows, grp)
    out: list[Finding] = []
    if skipped:
        out.append((Level.WARN, f"group proximity not measured for {skipped} head(s) (multi-column layout, "
                    "rail title or head not located in the PDF text)"))
    sec = [r for r in rows if isinstance(r, SecMeasure)]
    if sec:
        out.append(_section_finding(sec))
    return [*out, _group_finding(grp)]
