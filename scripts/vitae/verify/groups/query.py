"""The `typst query` mark reader and the word/line helpers the grouping and date gates share."""
from __future__ import annotations

import json
import shutil
import subprocess
from bisect import bisect_left
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, NamedTuple

from vitae.core.base import Mark, Word, _Line
from vitae.core.env import typst_font_kw, typst_py
from vitae.verify.pdf import auto_root

if TYPE_CHECKING:
    # type checking only: typing_extensions is never imported at run time (annotations are strings here)
    from typing_extensions import TypeIs

class ContactValues(NamedTuple):
    """The <vitae-contact> item values and the <vitae-contact-rows> declarations read with the marks."""
    items: list[object]
    rows: list[object]


# ---------- grouping / date / duplicate-name / forced-break gates ----------
# lib.typ tags every entry head and skill label with an invisible <vitae-head>
# metadata (text, org, page, x, y) and every section title with <vitae-sec>
# (pure metadata, no layout effect). `typst query` reads them back; the words
# come from the PDF (word_boxes(pdf, with_text=True)). Where a gate needs these
# marks and `typst query` is unavailable it WARNs "not checked" and the agent
# compares by hand; it never FAILs for that.

def _json_list(text: str) -> list[object] | None:
    """The JSON array in `text`; None when it parses to anything else (ValueError: not JSON at all)."""
    data: object = json.loads(text)
    return list(data) if isinstance(data, list) else None


def _is_num(v: object) -> bool:
    """A JSON number (a bool is not one)."""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# The Mark keys other than `text` and the check a value must pass when the key is present.
_MARK_FIELDS: tuple[tuple[str, Callable[[object], bool]], ...] = (
    ("kind", lambda v: isinstance(v, str)), ("org", lambda v: isinstance(v, str)),
    ("page", lambda v: isinstance(v, int) and not isinstance(v, bool)),
    ("x", _is_num), ("y", _is_num), ("w", _is_num), ("h", _is_num),
    ("dated", lambda v: isinstance(v, bool)), ("anchor", lambda v: isinstance(v, bool)),
    ("inline", lambda v: isinstance(v, bool)),
)


def _is_mark(v: object) -> TypeIs[Mark]:
    """A JSON object with a str `text` whose other Mark keys, when present, have their declared type."""
    if not isinstance(v, dict) or not isinstance(v.get("text"), str):
        return False
    return all(key not in v or ok(v[key]) for key, ok in _MARK_FIELDS)


def _values_py(typ: str, selector: str, root: str | None) -> list[object] | None:
    """The typst-py route of _typst_values: same query / eval fallback and root as the CLI calls."""
    mod = typst_py()
    if mod is None:
        return None
    try:
        comp = mod.Compiler(typ, root=root, **typst_font_kw()) if root else mod.Compiler(typ, **typst_font_kw())
        fn: Callable[[], object]
        for fn in (lambda: comp.query(selector, field="value", one=False),
                   lambda: comp.eval(f"query({selector}).map(it => it.value)", format="json")):
            try:
                out = fn()
                if isinstance(out, str) and out.strip().startswith("["):
                    vals = _json_list(out)
                    if vals is not None:
                        return vals
            except (RuntimeError, TypeError, ValueError, OSError):
                continue   # this typst-py route failed (typst error, signature of an older wheel, bad JSON): try the next
    except (RuntimeError, TypeError, OSError):   # Compiler() refusing the source or the keywords: marks not readable
        pass
    return None


def _typst_values(typ: str, selector: str, root: str | None = None) -> list[object] | None:
    """JSON list of the values of every element labelled `selector`, or None."""
    root = root or auto_root(typ)
    if not shutil.which("typst"):
        return _values_py(typ, selector, root)
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
                vals = _json_list(r.stdout)
            except ValueError:
                continue
            if vals is not None:
                return vals
    return None


def _first_problem(v: object) -> str:
    """What makes `v` not a Mark, as `<field> = <value>` (the first offending field)."""
    if not isinstance(v, dict):
        return f"<mark> = {v!r}"
    if not isinstance(v.get("text"), str):
        return f"text = {v.get('text')!r}"
    for key, ok in _MARK_FIELDS:
        if key in v and not ok(v[key]):
            return f"{key} = {v[key]!r}"
    return f"<mark> = {v!r}"


def _check_marks(vals: list[object]) -> tuple[list[Mark], str | None]:
    """The well-typed Marks of `vals` and the note on the dropped ones (see _typst_query_checked)."""
    marks = [v for v in vals if _is_mark(v)]
    bad = [v for v in vals if not _is_mark(v)]
    note = f"{len(bad)} lib marks ignored: malformed (first: {_first_problem(bad[0])})" if bad else None
    return marks, note


def _typst_query_checked(typ: str, selector: str, root: str | None = None) -> tuple[list[Mark] | None, str | None]:
    """The lib's Mark values (see _typst_values) and a note: an entry that is not a well-typed Mark (see _is_mark)
    is dropped, and the note says how many and the first offending field; None when nothing was dropped (valid lib
    output never has a note). The marks are None when the query is unavailable."""
    vals = _typst_values(typ, selector, root)
    if vals is None:
        return None, None
    return _check_marks(vals)


def _kind_of(v: object) -> object:
    """The `kind` of a lib metadata value, None when it is not a dict or has none."""
    return v.get("kind") if isinstance(v, dict) else None


def _typst_marks_and_contact(typ: str, selector: str, root: str | None = None) -> tuple[list[Mark] | None, str | None, ContactValues | None]:
    """ONE query for the marks and the contact labels: `selector` selects all of them (Typst `.or`), and the
    values are split by their explicit `kind` since a query drops the label: "contact" is a <vitae-contact> item,
    "contact-rows" a <vitae-contact-rows> declaration; everything else goes through _check_marks as before
    (a value with neither kind is never counted as contact). All three are None when the query is unavailable."""
    vals = _typst_values(typ, selector, root)
    if vals is None:
        return None, None, None
    rows: list[object] = []
    items: list[object] = []
    rest: list[object] = []
    for v in vals:
        kind = _kind_of(v)
        (rows if kind == "contact-rows" else items if kind == "contact" else rest).append(v)
    marks, note = _check_marks(rest)
    return marks, note, ContactValues(items=items, rows=rows)


def _typst_query(typ: str, selector: str, root: str | None = None) -> list[Mark] | None:
    """`_typst_query_checked` without the note."""
    return _typst_query_checked(typ, selector, root)[0]


def _gnorm(t: str) -> str:
    """Comparison key for a word: letters and digits only, casefolded, so punctuation and
    spacing differences between the typst source and pdftotext do not break a match."""
    return "".join(ch for ch in t.casefold() if ch.isalnum())


def _cluster(ws: Sequence[Word]) -> list[_Line]:
    """Words already sorted by y-centre, clustered into text lines -> list of dicts {y0, y1, c, x0, words}."""
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


def _lines(words: Sequence[Word], x_min: float) -> list[_Line]:
    """Words (x0, y0, x1, y1, text) at or right of x_min, clustered into text
    lines by y-centre -> sorted list of dicts {y0, y1, c, x0, words}."""
    return _cluster(sorted((w for w in words if w[0] >= x_min), key=lambda w: (w[1] + w[3]) / 2))


_TOKENS = 4          # up to 4 tokens is enough to identify an entry head uniquely without crossing a line wrap
_NEAR = 30.0         # a match farther than this (~2 lines) from the <vitae-head> marker's y is a repeated word elsewhere


class PageIndex:
    """One page's words, indexed once for every head or title measured on it: the normalised text of each word and the
    positions of each normal form, the words in y-centre order and the text lines of each distinct left edge.
    `_find_run`, `_lines` and `_line_index` rebuilt all of that for every call (O(words) each, so a page of heads was
    O(heads x words) with a heavy constant); here a call costs O(the page's words of its first token) for `find_run`,
    and the lines of a left edge are clustered once, whatever the number of heads at it. The coordinates are finite
    numbers, as pdftotext and pdfium give them."""

    def __init__(self, words: Sequence[Word]) -> None:
        self.words = words
        self._norm = [_gnorm(w[4]) for w in words]
        self._by_norm: dict[str, list[int]] = {}
        for j, n in enumerate(self._norm):
            self._by_norm.setdefault(n, []).append(j)
        centre = [(w[1] + w[3]) / 2 for w in words]
        self._centre = centre
        self._by_centre = sorted(range(len(words)), key=centre.__getitem__)          # stable: ties keep word order
        self._x0 = sorted(w[0] for w in words)
        self._lines_at: dict[int, list[_Line]] = {}
        self._first_line_of: dict[int, dict[int, int]] = {}

    def find_run(self, text: str, ytyp: float) -> list[Word] | None:
        """The words of `text` (first 4 tokens) nearest typst y `ytyp` -> list of word tuples, or None."""
        toks = [t for t in (_gnorm(w) for w in text.split()) if t][:_TOKENS]
        if not toks:
            return None
        words, norm, centre = self.words, self._norm, self._centre
        starts = self._by_norm.get(toks[0], [])
        # a start farther than _NEAR from the marker cannot be the answer (the farthest-accepted match is refused), and one
        # that is not nearer than the best so far cannot replace it: neither needs its run checked
        best: tuple[float, list[int]] | None = None
        for j in starts:
            d = abs(centre[j] - ytyp)
            if d > _NEAR or (best is not None and not d < best[0]):
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
                best = (d, run)
        return None if best is None else [words[k] for k in best[1]]

    def lines(self, x_min: float) -> list[_Line]:
        """`_lines(words, x_min)`, computed once per distinct set of words at or right of x_min."""
        k = bisect_left(self._x0, x_min)
        got = self._lines_at.get(k)
        if got is None:
            words = self.words
            got = self._lines_at[k] = _cluster([words[i] for i in self._by_centre if words[i][0] >= x_min])
            first: dict[int, int] = {}
            for i, ln in enumerate(got):
                for w in ln["words"]:
                    first.setdefault(id(w), i)
            self._first_line_of[id(got)] = first
        return got

    def line_index(self, lines: list[_Line], run: list[Word]) -> int | None:
        """`_line_index(lines, run)`: the line holding the first word of `run` (by identity), by one dict lookup
        when `lines` is a list this index returned (a list of another origin is searched as `_line_index` does)."""
        first = self._first_line_of.get(id(lines))
        return _line_index(lines, run) if first is None else first.get(id(run[0]))


def _find_run(words: Sequence[Word], text: str, ytyp: float) -> list[Word] | None:
    """The words of `text` (first 4 tokens) nearest typst y `ytyp` -> list of
    word tuples, or None."""
    return PageIndex(words).find_run(text, ytyp)


def _line_index(lines: list[_Line], run: list[Word]) -> int | None:
    """Index in `lines` of the line holding the first word of `run` (matched by identity)."""
    w = run[0]
    for i, ln in enumerate(lines):
        if any(x is w for x in ln["words"]):
            return i
    return None
