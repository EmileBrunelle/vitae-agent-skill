"""Grouping, date-adjacency, duplicate-name gates and the `typst query` mark reader they share.

No `import verify`.
"""
from __future__ import annotations

import atexit
import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from typing import Literal, cast

from PIL import Image

from vitae.core.base import DetailRow, GapFn, LineBox, Mark, Word, WordBox, _EntryRecord, _Line
from vitae.core.env import pdf_backend, typst_font_kw, typst_py
from vitae.core.level import Finding, Level
from vitae.verify.page import INK_DELTA, INK_DPI, RULE_PT, _row_stats, _xheight_band
from vitae.verify.pdf import _boxes_unavailable, _pdfium_render, auto_root, word_boxes

# ---------- grouping / date / duplicate-name / forced-break gates ----------
# lib.typ tags every entry head and skill label with an invisible <vitae-head>
# metadata (text, org, page, x, y) and every section title with <vitae-sec>
# (pure metadata, no layout effect). `typst query` reads them back; the words
# come from the PDF (word_boxes(pdf, with_text=True)). Where a gate needs these
# marks and `typst query` is unavailable it WARNs "not checked" and the agent
# compares by hand; it never FAILs for that.

def _typst_values(typ: str, selector: str, root: str | None = None) -> list[object] | None:
    """JSON list of the values of every element labelled `selector`, or None."""
    root = root or auto_root(typ)
    if not shutil.which("typst"):
        mod = typst_py()
        if mod is None:
            return None
        try:   # typst-py: same query / eval fallback and root as the CLI calls below
            comp = mod.Compiler(typ, root=root, **typst_font_kw()) if root else mod.Compiler(typ, **typst_font_kw())
            fn: Callable[[], object]
            for fn in (lambda: comp.query(selector, field="value", one=False),
                       lambda: comp.eval(f"query({selector}).map(it => it.value)", format="json")):
                try:
                    out = fn()
                    if isinstance(out, str) and out.strip().startswith("["):
                        return cast("list[object]", json.loads(out))
                except Exception:
                    continue
        except Exception:
            pass
        return None
    rootargs = ["--root", root] if root else []
    for cmd in (["typst", "query", typ, selector, "--field", "value"] + rootargs,
                ["typst", "eval", f"query({selector}).map(it => it.value)",
                 "--in", typ, "--target", "paged"] + rootargs):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
        except (FileNotFoundError, OSError):
            return None
        if r.returncode == 0 and r.stdout.strip().startswith("["):
            try:
                return cast("list[object]", json.loads(r.stdout))
            except ValueError:
                continue
    return None


def _typst_query(typ: str, selector: str, root: str | None = None) -> list[Mark] | None:
    """The lib's Mark values (see _typst_values); the lib writes dict markers only."""
    return cast("list[Mark] | None", _typst_values(typ, selector, root))


def _gnorm(t: str) -> str:
    """Comparison key for a word: letters and digits only, casefolded, so punctuation and
    spacing differences between the typst source and pdftotext do not break a match."""
    return "".join(ch for ch in t.casefold() if ch.isalnum())


def _lines(words: Sequence[Word], x_min: float) -> list[_Line]:
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
            ln["y0"], ln["y1"] = min(ln["y0"], w[1]), max(ln["y1"], w[3])
            ln["x0"] = min(ln["x0"], w[0])
            ln["c"] = (ln["y0"] + ln["y1"]) / 2
        else:
            out.append({"y0": w[1], "y1": w[3], "c": c, "x0": w[0], "words": [w]})
    return out


def _find_run(words: Sequence[Word], text: str, ytyp: float) -> list[Word] | None:
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


def _line_index(lines: list[_Line], run: list[Word]) -> int | None:
    """Index in `lines` of the line holding the first word of `run` (matched by identity)."""
    w = run[0]
    for i, ln in enumerate(lines):
        if any(x is w for x in ln["words"]):
            return i
    return None


def _page_ink_gap(pdf: str) -> GapFn:
    """gap_fn(page, up, lo) -> OPTICAL gap (pt) between two text lines
    ([x0, x1, y0, y1] pdftotext boxes), measured on a 300 dpi raster of `pdf`
    (pdftoppm; pages rendered lazily): from the BASELINE of the upper line to the
    x-HEIGHT TOP of the lower one. The baseline and x-height top come from each
    line's ink row profile (_xheight_band), so ascenders, capitals and descenders
    do not move them: the gap depends on the layout, never on the words. A line
    on a filled band counts as the band (top/bottom edge of the fill); a rule
    between the two lines splits the gap, and the longest part is returned (a
    title bar is what separates the title from the block above). With no
    raster, the gap is the pdftotext box gap (lower top - upper bottom)."""
    # per-call state: rasters are rendered lazily, once per page, into one temp dir
    cache: dict[int, Image.Image | None] = {}
    tmp: list[str] = []
    pbg: dict[int, int] = {}
    met: dict[tuple[float, ...], tuple[int, int] | None] = {}
    k = INK_DPI / 72.0

    def img(page: int) -> Image.Image | None:
        if page not in cache:
            cache[page] = None
            try:
                if not tmp:
                    tmp.append(tempfile.mkdtemp(prefix="vitae-prox-"))
                    # a 300 dpi page raster is ~9 MB: remove the directory at exit, even on a crash
                    atexit.register(shutil.rmtree, tmp[0], True)
                pre = os.path.join(tmp[0], f"p{page}")
                if pdf_backend() == "pdfium":
                    cache[page] = _pdfium_render(pdf, INK_DPI, gray=True, pages=[page])[0]
                    return cache[page]
                r = subprocess.run(["pdftoppm", "-r", str(INK_DPI), "-gray", "-singlefile",
                                    "-f", str(page), "-l", str(page), pdf, pre],
                                   capture_output=True)
                if r.returncode == 0:
                    gray = Image.open(pre + ".pgm").convert("L")
                    cache[page] = gray
                    gray.load()
            except (OSError, ValueError, RuntimeError):
                cache[page] = None
        return cache[page]

    def page_bg(page: int, im: Image.Image) -> int:
        # background = the PAGE's dominant tone, not the crop's (a reversed-out
        # band would otherwise count as "background")
        if page not in pbg:
            hp = im.histogram()
            pbg[page] = max(range(256), key=hp.__getitem__)
        return pbg[page]

    def tbl_for(bg: int) -> bytes:
        return bytes(1 if abs(v - bg) > INK_DELTA else 0 for v in range(256))

    def metrics(page: int, im: Image.Image, ln: LineBox) -> tuple[int, int] | None:
        """(top, base) pixel rows of one text line: x-height band of its ink, or
        the edges of the fill it sits on."""
        key = (page,) + tuple(round(v, 1) for v in ln)
        if key in met:
            return met[key]
        res: tuple[int, int] | None = None
        ya, yb = max(int(ln[2] * k), 0), min(int(ln[3] * k) + 1, im.height)
        xa, xb = max(int(ln[0] * k), 0), min(int(ln[1] * k) + 1, im.width)
        if yb - ya >= 3 and xb > xa:
            reg = im.crop((xa, ya, xb, yb))
            hp = reg.histogram()
            lbg = max(range(256), key=hp.__getitem__)
            pg = page_bg(page, im)
            if abs(lbg - pg) > INK_DELTA:
                # line on a filled band (or field): its optical extent is the fill's
                # rows, found on a strip just left / right of the text
                m = int(3 * k)
                res = None
                for sx in ((max(xa - m, 0), max(xa - 1, 0)), (min(xb + 1, im.width), min(xb + m, im.width))):
                    if sx[1] - sx[0] < 2:
                        continue
                    strip = im.crop((sx[0], 0, sx[1], im.height))
                    sd, sw = strip.tobytes(), strip.width
                    stb = bytes(1 if abs(v - lbg) <= INK_DELTA else 0 for v in range(256))
                    full: Callable[..., bool] = lambda r, sd=sd, sw=sw, stb=stb: sd[r * sw:(r + 1) * sw].translate(stb).count(b"\x01") >= 0.9 * sw
                    c = (ya + yb) // 2
                    if not full(c):
                        continue
                    t = b = c
                    while t > 0 and full(t - 1):
                        t -= 1
                    while b < im.height - 1 and full(b + 1):
                        b += 1
                    # <=3x the text line height: a title bar/pill around the line, whereas a sidebar or page fill is much taller.
                    if b - t + 1 <= 3 * (yb - ya):       # a band round the line, not a page-high field
                        res = (t, b)
                        break
            if res is None:
                tbl = tbl_for(lbg)
                data, w = reg.tobytes(), reg.width
                prof = []
                for r in range(reg.height):
                    n, run = _row_stats(data, w, r, tbl)
                    prof.append(-1 if run >= RULE_PT * k else n)    # underline / rule rows are not glyphs
                bd = _xheight_band(prof)
                if bd and bd[1] - bd[0] >= 2:
                    res = (ya + bd[0], ya + bd[1])
        met[key] = res
        return res

    def gap(page: int, up: LineBox, lo: LineBox) -> float:
        im = img(page) if pdf else None
        if im is None:
            return lo[2] - up[3]
        mu, ml = metrics(page, im, up), metrics(page, im, lo)
        if mu is None or ml is None:
            return lo[2] - up[3]
        a, b = mu[1] + 1, ml[0]                    # first row below the upper baseline .. lower x-height top
        if b <= a:
            return 0.0
        # rules between the two lines split the gap
        xa = max(int(min(up[0], lo[0]) * k), 0)
        xb = min(int(max(up[1], lo[1]) * k) + 1, im.width)
        if xb <= xa:
            return (b - a) / k
        reg = im.crop((xa, a, xb, b))
        tbl = tbl_for(page_bg(page, im))
        data, w = reg.tobytes(), reg.width
        edges, last = [], a
        for r in range(reg.height):
            if _row_stats(data, w, r, tbl)[1] >= RULE_PT * k:
                edges.append((last, a + r))        # blank stretch [last, a+r)
                last = a + r + 1
        edges.append((last, b))
        return max(e1 - e0 for e0, e1 in edges) / k

    return gap


class _KMark(Mark):
    """A Mark tagged with its kind: "h" head / "s" section."""
    _k: str


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
        rows.append({"kind": "group", "text": h["text"], "page": h["page"], "n": len(ls) - 1,
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


# Gestalt-proximity thresholds on between/internal gap ratio; their calibration is recorded in
# check_group_proximity's docstring. Section titles use the same two.
PROX_FAIL, PROX_WARN = 0.7, 0.85


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
    rows, kind "sec")."""
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
        print(f'DETAIL group "{r["text"][:30]}" p{r["page"]} lines={r["n"]} internal={r["internal"]:.2f}pt '
              f'between={r["between"]:.2f}pt ratio={r["ratio"]:.2f}')
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
    return out + [(Level.OK, f"group proximity: {len(grp)} groups, gap to next block >= {PROX_WARN} x internal gap "
             f'(tightest "{m["text"][:30]}": ratio {m["ratio"]:.2f}, {m["between"]:.1f}pt vs {m["internal"]:.1f}pt)')]


# Date adjacency is measured from POSITIONS, never from what a date looks like:
# lib.typ `entry` tags its head (<vitae-head>, with `dated`), its date cell and
# the line under the head (<vitae-part>: "date" / "org") with the x/y where
# their first glyph starts and the measured size of the cell. The date's words
# are the PDF words inside the date cell's box; their reading-order index is
# their position in `pdftotext -bbox` (the same layout analysis as the text an
# ATS reads). No regex decides what a date is, so an org "Vision 2020 Inc", a
# bullet "5000 users" or a role "Tier 2 Support" cannot be mistaken for one.
ENTRY_MARKS = "selector(<vitae-head>).or(<vitae-part>)"


def _entry_records(marks: list[Mark] | None) -> list[_EntryRecord]:
    """Marks in document order -> one record per entry head:
    {"head": mark, "date": mark|None, "org": mark|None, "date_first": bool}.
    A part mark belongs to the entry head emitted before it; `date_first` records which of the
    two was emitted first, since the emission order is what an ATS extraction follows."""
    recs: list[_EntryRecord] = []
    cur: _EntryRecord | None = None
    for m in marks or []:
        k = m.get("kind")
        if k == "entry":
            cur = {"head": m, "date": None, "org": None, "date_first": None}
            recs.append(cur)
        elif k in ("date", "org") and cur is not None:
            part = cast(Literal["date", "org"], k)
            if cur[part] is None:
                cur[part] = m
                if cur["date_first"] is None:
                    cur["date_first"] = part == "date"
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
    warn: Callable[[str], object] = (lambda m: warns.append(m)) if warns is not None else (lambda m: None)
    why = (" (pdftotext, like the ATS extractors that cluster lines the same way, reads a "
           "right-flushed date in place only when a text line under it overlaps its x-range; "
           "references/ats.md, Entry-with-no-bullets trap)")

    def action(name: str, h: Mark, d: Mark, o: Mark | None) -> str:
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
    for ix, r in enumerate(recs):
        h, d, o = r["head"], r["date"], r["org"]
        name = f'entry "{(h.get("text") or "")[:40]}"'
        if "dated" not in h:
            warn(f"{name}: no lib markers")
            continue
        if not h["dated"]:
            st["undated"] += 1
            continue                       # entry given no date: nothing to order
        st["unmeasured"] += 1              # counted unmeasured until the judgement below is reached; each `continue` before it keeps it so
        if d is None:
            warn(f"{name}: dated but no date marker")
            continue
        if o is not None and not r["date_first"]:
            out.append(f"rebuild {name} with the family's job() / lib entry(), cells in lib "
                       "order: its employer line is EMITTED before its date (hand-built or "
                       "reordered entry), so a parser reads the date as missing")
            continue
        pg = h.get("page") or 1
        if d.get("page") != pg:
            out.append(f"rebuild {name} with the family's job() / lib entry(): its date is set "
                       f"on page {d.get('page')}, its head on page {pg}, so the date is read with "
                       "the wrong entry")
            continue
        if not 0 < pg <= len(words):
            warn(f"{name}: page {pg} not in the PDF")
            continue
        pw = words[pg - 1]
        # the org line's first word: it starts exactly at the marker's x (the
        # lib's date anchor may have set the line flush right); nearest in y
        oi = None
        if o is not None and o.get("page") == pg and o["y"] > d["y"]:
            tol = max(o.get("h", 0), 6) + 10
            c = [i for i, w in enumerate(pw) if abs(w[0][0] - o["x"]) <= 1.5
                 and abs(_yc(w) - o["y"]) <= tol and _yc(w) > d["y"]]
            oi = min(c, key=lambda i: abs(_yc(pw[i]) - o["y"])) if c else None
        d_end = pw[oi][0][1] if oi is not None else d["y"] + 4 * max(d.get("h", 0), 6)
        di = [i for i, w in enumerate(pw)
              if w[0][0] >= d["x"] - 1.5 and w[0][2] <= d["x"] + d.get("w", 0) + 1.5
              and min(d["y"], h["y"]) - 2 <= _yc(w) < d_end]
        if d.get("inline") and di:
            # inline date (lib entry, after the role): one unbreakable box on ONE
            # line, maybe the role's second; keep the line nearest the marker
            yl = min({round(_yc(pw[i])) for i in di}, key=lambda y: abs(y - d["y"]))
            di = [i for i in di if abs(_yc(pw[i]) - yl) <= 3]
        hi = _first_word(pw, h["x"], h["y"], d_end, x_end=None if d.get("inline") else d["x"] - 1)
        if not di or hi is None:
            warn(f"{name}: {'date' if not di else 'head'} words not found at the marker position")
            continue
        last = max(di)
        # the entry's column: role start .. date end; "below" = under the date row
        cl, cr = h["x"] - 1.5, d["x"] + d.get("w", 0) + 1.5
        d_bot = max(pw[i][0][3] for i in di)
        nr = next((n for n in recs[ix + 1:]
                   if (n["head"].get("page") or 1) == pg and abs(n["head"]["x"] - h["x"]) <= 2), None)
        nxt = nr["head"] if nr is not None else None
        n_end = (nr["date"]["x"] - 1 if nr is not None and nr["date"] is not None
                 and nr["date"].get("page") == pg else cr)
        ni = _first_word(pw, nxt["x"], nxt["y"], nxt["y"] + 40, x_end=n_end) if nxt is not None else None
        # first word READ of anything set below the head block in this column
        # (org line, bullet, next head, next section title)
        bi = min((i for i, w in enumerate(pw)
                  if _yc(w) > d_bot and w[0][0] < cr and w[0][2] > cl), default=None)
        st["unmeasured"] -= 1
        st["measured"] += 1
        # words of the role (head rows, left of a right-flushed date / before an
        # inline one): the date must not be read before any of them. Checks below run
        # in order of how specific the symptom is; the first that matches is reported.
        dl = sum(_yc(pw[i]) for i in di) / len(di)
        rw = [i for i, w in enumerate(pw) if i not in di and w[0][0] >= h["x"] - 1.5
              and h["y"] - 2 <= _yc(w) <= dl + 3
              and (w[0][2] <= d["x"] - 1 if not d.get("inline") else
                   (_yc(w) < dl - 3 or w[0][2] <= d["x"] - 1))]
        if rw and max(rw) > min(di):
            out.append(action(name, h, d, o) + f" \u2014 measured: {name}'s date is read in the "
                       f'middle of its role (before "{pw[max(rw)][1][:30]}")' + why)
        elif ni is not None and last > ni:
            out.append(action(name, h, d, o) + f" — measured: {name}'s date is emitted AFTER "
                       "the next entry starts, so it is read with the wrong entry" + why)
        elif oi is not None and last > oi:
            out.append(action(name, h, d, o) + f" — measured: the extracted text reads "
                       f"{name}'s employer line BEFORE its date, so a parser reads the date as "
                       "missing" + why)
        elif bi is not None and last > bi:
            out.append(action(name, h, d, o) + f" — measured: {name}'s date is emitted "
                       f'AFTER text set below the entry head (read first: "{pw[bi][1][:30]}")' + why)
        elif o is not None and oi is None:
            warn(f"{name}: employer line words not found at the marker position")
    return out


def check_duplicate_names(secs: Sequence[Mark] | None, heads: Sequence[Mark] | None) -> list[str]:
    """FAIL messages: one name used both as a section title and as a row label
    (e.g. section LANGUAGES for spoken languages + skill label "Languages" for
    programming ones), compared case-insensitively. Two things with one name
    read as one list to a human and to an ATS. Compared on `_gnorm` keys, so case and
    punctuation do not hide a clash."""
    titles: dict[str, str] = {}
    for s in secs or []:
        if _gnorm(s.get("text", "")):
            titles.setdefault(_gnorm(s["text"]), s["text"])
    out = []
    for h in heads or []:
        if h.get("kind") == "skill" and _gnorm(h["text"]) in titles:
            out.append(f'"{h["text"].strip()}" is both a skill row label and the section title '
                       f'"{titles[_gnorm(h["text"])]}" — rename one (e.g. "Programming languages")')
    return out
