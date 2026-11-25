"""Whole-group proximity: optical line gaps, group measurement and the group/section proximity gate."""
from __future__ import annotations

import statistics
from collections.abc import Callable

from vitae.core.base import DetailRow, GapFn, LineBox, Mark, Word, _Line
from vitae.core.env import pdf_backend
from vitae.core.level import Finding, Level
from vitae.verify.groups.ink import _page_ink_gap
from vitae.verify.groups.query import _find_run, _gnorm, _line_index, _lines, _typst_query
from vitae.verify.pdf import _boxes_unavailable, word_boxes


class _KMark(Mark):
    """A Mark tagged with its kind: "h" head / "s" section."""
    _k: str


def _org_on_one_line(org: str, line: _Line) -> bool:
    """True when the org text's first and last tokens both sit on `line`: the line under the role is the
    whole org line (a wrapped role pushes the org down, a wrapped org spills onto the next line)."""
    toks = [t for t in (_gnorm(w) for w in org.split()) if t]
    if not toks:
        return False
    have = {_gnorm(w[4]) for w in line["words"]}
    return toks[0] in have and toks[-1] in have


def measure_groups(heads: list[Mark], secs: list[Mark], pages_words: list[list[Word]],
                   gap_fn: GapFn | None = None) -> tuple[list[DetailRow], int]:
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
    heads = [h for h in heads if "page" in h and "y" in h and "x" in h]   # a partial mark has no position to measure from: skipped
    secs = [sc for sc in secs if "page" in sc and "y" in sc]
    rows: list[DetailRow] = []
    skipped = 0
    # the marks tagged with their kind ("h" head / "s" section)
    marks: list[_KMark] = [_KMark(**h, _k="h") for h in heads] + [_KMark(**s, _k="s") for s in secs]
    box: Callable[[_Line], LineBox] = lambda ln: [ln["x0"], max(w[2] for w in ln["words"]), ln["y0"], ln["y1"]]
    for h in sorted(heads, key=lambda h: (h["page"], h["y"])):
        if h["page"] - 1 >= len(pages_words):
            skipped += 1
            continue
        words = pages_words[h["page"] - 1]
        run = _find_run(words, h["text"], h["y"])
        if run is None:
            skipped += 1
            continue
        hx = min(w[0] for w in run)
        lines = _lines(words, hx - 2)
        i0 = _line_index(lines, run)
        if i0 is None:
            skipped += 1
            continue
        # next block head on this page (entry head, skill label or section title)
        later = [m for m in marks if m["page"] == h["page"] and m["y"] > h["y"] + 2
                 and not (m["_k"] == "h" and abs(m["x"] - h["x"]) > 60)]
        if not later:
            continue                       # last block on its page: no next head
        m = min(later, key=lambda m: m["y"])
        mrun = _find_run(words, m["text"], m["y"])
        if mrun is None:
            skipped += 1
            continue
        # a rail title sits wholly LEFT of the body column (margin-index); a title
        # that merely starts left of an indented head (gutter-rail's skill rows
        # open with a drawn mark) is an in-flow title, its own line in the flow
        rail = max(w[2] for w in mrun) < hx - 2
        if rail:
            # Rail title beside the body: its y is the top of the title cell (rule
            # + gap), a few pt ABOVE the body's first line, so matching it by
            # y-centre lands one line too low. If an in-column head opens within
            # that window, THAT is the next block of this column's flow.
            h2 = [x for x in marks if x["_k"] == "h" and x["page"] == h["page"]
                  and abs(x["x"] - h["x"]) <= 60 and m["y"] - 3 <= x["y"] <= m["y"] + 15]
            if h2:
                m = min(h2, key=lambda x: x["y"])
                mrun = _find_run(words, m["text"], m["y"])
                if mrun is None:
                    skipped += 1
                    continue
        if not rail:
            mx0 = min(w[0] for w in mrun)
            if mx0 < hx - 2:               # in-flow title starting left of an indented head
                lines = _lines(words, mx0 - 2)
                i0 = _line_index(lines, run)
            i_next = _line_index(lines, mrun) if i0 is not None else None
        else:                              # title set in a rail beside the body
            mc = (mrun[0][1] + mrun[0][3]) / 2
            cand = [(abs(ln["c"] - mc), i) for i, ln in enumerate(lines)
                    if i > i0 and abs(ln["c"] - mc) <= 12]
            i_next = min(cand)[1] if cand else None
        if i_next is None or i0 is None or i_next <= i0 + 1:
            continue                       # single-line group (or no next head): nothing inside
        ls = [box(ln) for ln in lines[i0:i_next + 1]]
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
        if h.get("kind") == "entry" and h.get("org") and n >= 4 and _org_on_one_line(h["org"], lines[i0 + 1]):
            hb, pitch = gaps[1], statistics.median(gaps[2:])
        rows.append({"kind": "group", "text": h["text"], "page": h["page"], "n": n, "hkind": h.get("kind"),
                     "next_sec": m["_k"] == "s", "head_gap": hb, "pitch": pitch,
                     "gaps": gaps, "internal": internal, "between": between,
                     "ratio": (between / internal) if internal > 0 else float("inf"), "ls": ls,
                     "pair_in": (tx[wi], tx[wi + 1]), "pair_btw": (tx[-2], tx[-1])})
    # sections: previous block's last line -> title (bar) vs title -> first line
    xs: dict[int, list[float]] = {}
    for h in heads:
        xs.setdefault(h["page"], []).append(h["x"])
    for sc in secs:
        pg = sc.get("page")
        if not pg or pg - 1 >= len(pages_words) or pg not in xs:
            continue
        words = pages_words[pg - 1]
        srun = _find_run(words, sc["text"], sc.get("y", 0))
        bx = min(xs[pg])
        if srun is None or min(w[0] for w in srun) < bx - 5:
            continue                       # unlocated, or a rail title beside the body
        lines = _lines(words, bx - 2)
        i = _line_index(lines, srun)
        if i is None or i < 1 or i + 1 >= len(lines):
            continue
        up, t, lo = box(lines[i - 1]), box(lines[i]), box(lines[i + 1])
        before, after = gap_fn(pg, up, t), gap_fn(pg, t, lo)
        rows.append({"kind": "sec", "text": sc["text"], "page": pg, "before": before,
                     "after": after, "ratio": (before / after) if after > 0 else float("inf")})
    return rows, skipped


def _hier_advice(kind: str | None) -> str:
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
    heads = _typst_query(typ, "<vitae-head>", root) if heads is None else heads
    secs = (_typst_query(typ, "<vitae-sec>", root) or []) if secs is None else secs
    if pages is None:
        wb = word_boxes(pdf, with_text=True)
        pages = [[(b[0], b[1], b[2], b[3], t) for b, t in pg] for pg in wb] if wb else None
    if heads is None or pages is None:
        if pdf_backend() == "pdfium":
            return [(Level.WARN, "group proximity NOT checked (typst query unavailable or word positions "
                             "unreadable: " + _boxes_unavailable(pdf) + ")")]
        return [(Level.WARN, "group proximity NOT checked (typst query or pdftotext unavailable)")]
    if not heads:
        return [(Level.WARN, "group proximity not measured: no lib entry()/srow() heads")]
    # DETAIL lines are machine-readable and printed here, not returned: the self-test and --gates read them
    rows, skipped = measure_groups(heads, secs, pages, _page_ink_gap(pdf) if pdf else None)
    if detail is not None:
        detail.extend(rows)
    grp = [r for r in rows if r["kind"] == "group"]
    if not grp:
        return [(Level.WARN, f"group proximity: no checkable group ({skipped} head(s) not located) — unchecked")]
    for r in grp:
        hp = "" if r["head_gap"] is None or r["pitch"] is None else \
            f' head-gap={r["head_gap"]:.2f}pt pitch={r["pitch"]:.2f}pt'
        print(f'DETAIL group "{r["text"][:30]}" p{r["page"]} lines={r["n"]} internal={r["internal"]:.2f}pt '
              f'between={r["between"]:.2f}pt ratio={r["ratio"]:.2f}{hp}{" next=section" if r["next_sec"] else ""}')
    for row in rows:
        if row["kind"] == "sec":
            print(f'DETAIL section "{row["text"][:30]}" p{row["page"]} before-bar={row["before"]:.2f}pt '
                  f'bar-to-first={row["after"]:.2f}pt ratio={row["ratio"]:.2f}')
    out: list[Finding] = []
    if skipped:
        out.append((Level.WARN, f"group proximity not measured for {skipped} head(s) (multi-column layout, "
                    "rail title or head not located in the PDF text)"))
    sec = [r for r in rows if r["kind"] == "sec"]
    if sec:
        # a section title belongs to what FOLLOWS it: the gap above it (previous
        # block's last line -> title or its bar) must not be much smaller than
        # the gap below it (title -> first line). Same calibration as groups.
        s = min(sec, key=lambda r: r["ratio"])
        sw = (f'(worst "{s["text"][:30]}": gap above {s["before"]:.1f}pt, gap below '
              f'{s["after"]:.1f}pt, ratio {s["ratio"]:.2f}')
        sbad = [r for r in sec if not r["ratio"] >= PROX_FAIL]
        sweak = [r for r in sec if not r["ratio"] >= PROX_WARN]
        if sbad:
            out.append((Level.FAIL, f"section proximity: {len(sbad)}/{len(sec)} titles sit closer to the block "
                        f"above than to their own first line {sw}; need >= {PROX_FAIL}) — fix the family's "
                        "`section` (its `above` and the gap under the title), not the content file"))
        elif sweak:
            out.append((Level.WARN, f"section proximity: {len(sweak)}/{len(sec)} titles barely separated from "
                        f"the block above {sw}; aim for >= {PROX_WARN})"))
        else:
            out.append((Level.OK, f'section proximity: {len(sec)} titles, gap above >= {PROX_WARN} x gap below '
                        f'(tightest "{s["text"][:30]}": ratio {s["ratio"]:.2f})'))
    m = min(grp, key=lambda r: r["ratio"])
    q: Callable[[str], str] = lambda t: '"' + t + '"'
    worst = (f'(worst {q(m["text"][:30])}: largest gap inside {m["internal"]:.1f}pt '
             f'({q(m["pair_in"][0])} -> {q(m["pair_in"][1])}), gap to the next block '
             f'{m["between"]:.1f}pt ({q(m["pair_btw"][0])} -> {q(m["pair_btw"][1])}), ratio {m["ratio"]:.2f}')
    # `not x >= t` rather than `x < t`: a NaN ratio must count as failing
    bad = [r for r in grp if not r["ratio"] >= PROX_FAIL]
    if bad:
        return out + [(Level.FAIL, f'group proximity: {len(bad)}/{len(grp)} groups sit closer to the next block than '
                 f'their own lines are to each other {worst}; need >= {PROX_FAIL})\n'
                 "      do not override entry/srow above/gap/below per entry; look for a manual #v, linebreak "
                 "or blank line inside that entry (a gap that is too big inside is as bad as one too small after);\n"
                 "      if the CV uses the family file as shipped, report it: it is a template bug (never edit lib.typ)")]
    weak = [r for r in grp if not r["ratio"] >= PROX_WARN]
    if weak:
        return out + [(Level.WARN, f'group proximity: {len(weak)}/{len(grp)} groups barely separated from the next block '
                 f'{worst}; aim for >= {PROX_WARN})\n'
                 "      do not override entry/srow above/gap/below per entry; check for a manual #v, linebreak or "
                 "blank line inside that entry")]
    # hierarchy: an entry must also read as ONE unit, so the gap to the next entry has to be visibly
    # larger than the gaps inside it. Groups before a section title are left to the section rules.
    flat = [r for r in grp if not r["next_sec"] and not r["ratio"] >= PROX_HIER]
    if flat:
        f = min(flat, key=lambda r: r["ratio"])
        # Plural names every flat group (mixed kinds read as entries); the worst-case clause names f's own kind.
        many, a_one = (("skill rows", "a skill row") if all(r["hkind"] == "skill" for r in flat)
                       else ("entries", "an entry"))
        one = "skill row" if f["hkind"] == "skill" else "entry"
        fw = (f'(worst {q(f["text"][:30])}: gap to the next {one} {f["between"]:.1f}pt vs {f["internal"]:.1f}pt '
              f'inside it, ratio {f["ratio"]:.2f})')
        return out + [(Level.WARN, f"group proximity: {many} barely separated: gap between {many} ≈ gap inside "
                 f"{a_one} in {len(flat)}/{len(grp)} groups {fw}; aim for >= {PROX_HIER}\n"
                 + _hier_advice(f["hkind"]))]
    return out + [(Level.OK, f"group proximity: {len(grp)} groups, gap to next block >= {PROX_WARN} x internal gap "
             f'(tightest "{m["text"][:30]}": ratio {m["ratio"]:.2f}, {m["between"]:.1f}pt vs {m["internal"]:.1f}pt)')]
