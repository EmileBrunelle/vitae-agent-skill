"""Date adjacency: an entry's date is read before its org line and the next entry, measured from positions."""
from __future__ import annotations

from collections.abc import Callable, Sequence

from vitae.core.base import HeadMark, Mark, WordBox, _EntryRecord, is_placed
from vitae.core.env import pdf_backend
from vitae.verify.groups.query import _typst_query
from vitae.verify.pdf import _boxes_unavailable, word_boxes

# Date adjacency is measured from POSITIONS, never from what a date looks like:
# lib.typ `entry` tags its head (<vitae-head>, with `dated`), its date cell and
# the line under the head (<vitae-part>: "date" / "org") with the x/y where
# their first glyph starts and the measured size of the cell. The date's words
# are the PDF words inside the date cell's box; their reading-order index is
# their position in `pdftotext -bbox` (the same layout analysis as the text an
# ATS reads). No regex decides what a date is, so an org "Vision 2020 Inc", a
# bullet "5000 users" or a role "Tier 2 Support" cannot be mistaken for one.
ENTRY_MARKS = "selector(<vitae-head>).or(<vitae-part>).or(<vitae-bullet>)"


def _entry_records(marks: list[Mark] | None) -> list[_EntryRecord]:
    """Marks in document order -> one record per entry head:
    {"head": mark, "date": mark|None, "org": mark|None, "date_first": bool}.
    A part mark belongs to the entry head emitted before it; `date_first` records which of the
    two was emitted first, since the emission order is what an ATS extraction follows."""
    recs: list[_EntryRecord] = []
    cur: _EntryRecord | None = None
    for m in marks or []:
        if not is_placed(m):              # a mark without a position cannot be measured: ignored
            continue
        k = m.get("kind")
        if k == "entry":
            cur = {"head": m, "date": None, "org": None, "date_first": None}
            recs.append(cur)
        elif k in ("date", "org") and cur is not None:
            # a record is never edited in place: the filled copy replaces it (cur is always the last record)
            first = cur["date_first"]
            if k == "date" and cur["date"] is None:
                cur = {**cur, "date": m, "date_first": True if first is None else first}
                recs[-1] = cur
            elif k == "org" and cur["org"] is None:
                cur = {**cur, "org": m, "date_first": False if first is None else first}
                recs[-1] = cur
        elif k == "skill":
            cur = None                     # other part kinds ("date-col") are ignored
    return recs


def _yc(w: WordBox) -> float:
    """Vertical centre of a word box."""
    return (w[0][1] + w[0][3]) / 2


def _first_word(words: Sequence[WordBox], x: float, y: float, y_end: float,
                x_end: float | None = None) -> int | None:
    """Reading-order index of the first word of the line starting at (x, y):
    words whose centre lies in [y - 2, y_end) and that start at or right of x
    (before x_end), top line first, then leftmost. None when nothing is there."""
    c = [i for i, w in enumerate(words)
         if y - 2 <= _yc(w) < y_end and w[0][0] >= x - 1.5
         and (x_end is None or w[0][0] < x_end)]
    if not c:
        return None
    top = min(_yc(words[i]) for i in c)
    return min((i for i in c if _yc(words[i]) <= top + 3), key=lambda i: words[i][0][0])


_WHY = (" (pdftotext, like the ATS extractors that cluster lines the same way, reads a "
        "right-flushed date in place only when a text line under it overlaps its x-range; "
        "references/ats.md, Entry-with-no-bullets trap)")


def _date_action(name: str, h: HeadMark, d: HeadMark, o: HeadMark | None) -> str:
    """The FIRST clause of a FAIL: what to change in cv.typ that clears it."""
    if "anchor" not in h:
        return (f"rebuild {name} with the current lib's entry() / the family's job() "
                "(recopy the skill's lib.typ if the CV's copy is older): its markers come "
                "from a lib whose entry() does not anchor its date")
    short = d["x"] - ((o["x"] + o.get("w", 0)) if o is not None else h["x"]) + 3
    if d.get("inline") or short <= 3:
        return (f"rebuild {name} with the family's unmodified job() / lib entry() (no "
                "override of its org-st/date-st/meta-size, no hand-built head): lib entry() "
                + ("already set its date inline after the role" if d.get("inline") else
                   "already runs its org line under the date")
                + ", so only a modified entry is read out of order; if it already is "
                "unmodified, report the .typ and PDF")
    return (f"lengthen the org/descriptor line of {name} by at least {short:.0f}pt so it runs "
            "under the date (a hand-built head: rebuild it with the family's job() / lib "
            "entry(), which sets such a date inline): nothing under the right-flushed date "
            "anchors it, so pdftotext does not read it in place")


def _org_first_word(pw: list[WordBox], o: HeadMark | None, d: HeadMark, pg: int) -> int | None:
    """The org line's first word: it starts exactly at the marker's x (the lib's date anchor may have
    set the line flush right); nearest in y."""
    if o is not None and o.get("page") == pg and o["y"] > d["y"]:
        tol = max(o.get("h", 0), 6) + 10
        c = [i for i, w in enumerate(pw) if abs(w[0][0] - o["x"]) <= 1.5
             and abs(_yc(w) - o["y"]) <= tol and _yc(w) > d["y"]]
        return min(c, key=lambda i: abs(_yc(pw[i]) - o["y"])) if c else None
    return None


def _date_word_indices(pw: list[WordBox], h: HeadMark, d: HeadMark, d_end: float) -> list[int]:
    """Reading-order indices of the date's words: the PDF words inside the date cell's box."""
    di = [i for i, w in enumerate(pw)
          if w[0][0] >= d["x"] - 1.5 and w[0][2] <= d["x"] + d.get("w", 0) + 1.5
          and min(d["y"], h["y"]) - 2 <= _yc(w) < d_end]
    if d.get("inline") and di:
        # inline date (lib entry, after the role): one unbreakable box on ONE
        # line, maybe the role's second; keep the line nearest the marker
        yl = min({round(_yc(pw[i])) for i in di}, key=lambda y: abs(y - d["y"]))
        di = [i for i in di if abs(_yc(pw[i]) - yl) <= 3]
    return di


def _next_head_word(pw: list[WordBox], recs: list[_EntryRecord], ix: int, h: HeadMark, pg: int,
                    cr: float) -> int | None:
    """Reading-order index of the first word of the next entry head in the same column, or None."""
    nr = next((n for n in recs[ix + 1:]
               if (n["head"].get("page") or 1) == pg and abs(n["head"]["x"] - h["x"]) <= 2), None)
    if nr is None:
        return None
    nxt = nr["head"]
    nd = nr["date"]
    n_end = nd["x"] - 1 if nd is not None and nd.get("page") == pg else cr
    return _first_word(pw, nxt["x"], nxt["y"], nxt["y"] + 40, x_end=n_end)


def _read_order_failure(name: str, h: HeadMark, d: HeadMark, o: HeadMark | None, pw: list[WordBox], di: list[int],
                        oi: int | None, ni: int | None, bi: int | None, warn: Callable[[str], object]) -> str | None:
    """The FAIL message when the date is read out of order, else None (warning when the org line's
    words were not found). `di` is non-empty. Words of the role (head rows, left of a right-flushed
    date / before an inline one): the date must not be read before any of them. Checks run in order
    of how specific the symptom is; the first that matches is reported."""
    last = max(di)
    dl = sum(_yc(pw[i]) for i in di) / len(di)
    rw = [i for i, w in enumerate(pw) if i not in di and w[0][0] >= h["x"] - 1.5
          and h["y"] - 2 <= _yc(w) <= dl + 3
          and (w[0][2] <= d["x"] - 1 if not d.get("inline") else
               (_yc(w) < dl - 3 or w[0][2] <= d["x"] - 1))]
    if rw and max(rw) > min(di):
        return (_date_action(name, h, d, o) + f" \u2014 measured: {name}'s date is read in the "
                f'middle of its role (before "{pw[max(rw)][1][:30]}")' + _WHY)
    if ni is not None and last > ni:
        return (_date_action(name, h, d, o) + f" — measured: {name}'s date is emitted AFTER "
                "the next entry starts, so it is read with the wrong entry" + _WHY)
    if oi is not None and last > oi:
        return (_date_action(name, h, d, o) + f" — measured: the extracted text reads "
                f"{name}'s employer line BEFORE its date, so a parser reads the date as "
                "missing" + _WHY)
    if bi is not None and last > bi:
        return (_date_action(name, h, d, o) + f" — measured: {name}'s date is emitted "
                f'AFTER text set below the entry head (read first: "{pw[bi][1][:30]}")' + _WHY)
    if o is not None and oi is None:
        warn(f"{name}: employer line words not found at the marker position")
    return None


def _check_entry(ix: int, recs: list[_EntryRecord], words: list[list[WordBox]], st: dict[str, int],
                 warn: Callable[[str], object]) -> str | None:
    """The FAIL message for entry `recs[ix]` (None when fine, skipped or only noted); updates the
    measured / undated / unmeasured counts in `st`."""
    r = recs[ix]
    h, d, o = r["head"], r["date"], r["org"]
    name = f'entry "{(h.get("text") or "")[:40]}"'
    if "dated" not in h:
        warn(f"{name}: no lib markers")
        return None
    if not h["dated"]:
        st["undated"] += 1
        return None                        # entry given no date: nothing to order
    st["unmeasured"] += 1                  # counted unmeasured until the judgement below is reached; each early return before it keeps it so
    if d is None:
        warn(f"{name}: dated but no date marker")
        return None
    if o is not None and not r["date_first"]:
        return (f"rebuild {name} with the family's job() / lib entry(), cells in lib "
                "order: its employer line is EMITTED before its date (hand-built or "
                "reordered entry), so a parser reads the date as missing")
    pg = h.get("page") or 1
    if d.get("page") != pg:
        return (f"rebuild {name} with the family's job() / lib entry(): its date is set "
                f"on page {d.get('page')}, its head on page {pg}, so the date is read with "
                "the wrong entry")
    if not 0 < pg <= len(words):
        warn(f"{name}: page {pg} not in the PDF")
        return None
    pw = words[pg - 1]
    oi = _org_first_word(pw, o, d, pg)
    d_end = pw[oi][0][1] if oi is not None else d["y"] + 4 * max(d.get("h", 0), 6)
    di = _date_word_indices(pw, h, d, d_end)
    hi = _first_word(pw, h["x"], h["y"], d_end, x_end=None if d.get("inline") else d["x"] - 1)
    if not di or hi is None:
        warn(f"{name}: {'date' if not di else 'head'} words not found at the marker position")
        return None
    # the entry's column: role start .. date end; "below" = under the date row
    cl, cr = h["x"] - 1.5, d["x"] + d.get("w", 0) + 1.5
    d_bot = max(pw[i][0][3] for i in di)
    ni = _next_head_word(pw, recs, ix, h, pg, cr)
    # first word READ of anything set below the head block in this column
    # (org line, bullet, next head, next section title)
    bi = min((i for i, w in enumerate(pw)
              if _yc(w) > d_bot and w[0][0] < cr and w[0][2] > cl), default=None)
    st["unmeasured"] -= 1
    st["measured"] += 1
    return _read_order_failure(name, h, d, o, pw, di, oi, ni, bi, warn)


def check_date_adjacency(typ: str, pdf: str, marks: list[Mark] | None = None, root: str | None = None,
                         warns: list[str] | None = None, words: list[list[WordBox]] | None = None,
                         stats: dict[str, int] | None = None) -> list[str]:
    """FAIL messages: in the extracted text (what an ATS reads) an entry's date
    must come BEFORE the line under its head (org / descriptor: ats.md, the org
    line anchors the date) and before the NEXT entry's head. Positions come from
    lib.typ's markers; the order is pdftotext's. `warns` (list) collects
    "not measured" notes. An entry given no date (`dated: false`) is skipped.
    `stats` (dict) receives the counts: measured / undated / unmeasured lib
    entries (an entry not built with lib `entry` carries no marker and is in
    none of them).

    A FAIL only when the order was measured and is wrong. A missing marker, missing word
    positions or an entry the words could not be matched to is a "not measured" note,
    never a FAIL."""
    marks = _typst_query(typ, ENTRY_MARKS, root) if marks is None else marks
    out: list[str] = []
    warn: Callable[[str], object] = (warns.append) if warns is not None else (lambda m: None)
    recs = _entry_records(marks)
    st = stats if stats is not None else {}
    st.update(measured=0, undated=0, unmeasured=0)
    if not recs:
        return out
    if not any("dated" in r["head"] for r in recs):
        warn("no lib markers (entry heads carry no date/org part marks: old lib.typ "
             "or hand-built heads)")
        return out
    words = word_boxes(pdf, with_text=True) if words is None else words
    if words is None:
        warn("pdftotext unavailable (word positions needed)" if pdf_backend() != "pdfium"
             else f"word positions needed, {_boxes_unavailable(pdf)}")
        return out
    for ix in range(len(recs)):
        fail = _check_entry(ix, recs, words, st, warn)
        if fail is not None:
            out.append(fail)
    return out
