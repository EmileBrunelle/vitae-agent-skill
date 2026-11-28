"""The `typst query` mark reader and the word/line helpers the grouping and date gates share."""
from __future__ import annotations

import json
from bisect import bisect_left
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, NamedTuple

from vitae.core import proc
from vitae.core.base import Mark, TextLine, Word
from vitae.core.env import typst_font_kw, typst_py, typst_route
from vitae.core.narrow import is_object_dict, is_object_list
from vitae.verify.pdf import auto_root, current_memo, file_key

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
    return list(data) if is_object_list(data) else None


def is_num(v: object) -> bool:
    """A JSON number (a bool is not one)."""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# The Mark keys other than `text` and the check a value must pass when the key is present.
_MARK_FIELDS: tuple[tuple[str, Callable[[object], bool]], ...] = (
    ("kind", lambda v: isinstance(v, str)), ("org", lambda v: isinstance(v, str)),
    ("page", lambda v: isinstance(v, int) and not isinstance(v, bool)),
    ("x", is_num), ("y", is_num), ("w", is_num), ("h", is_num),
    ("dated", lambda v: isinstance(v, bool)), ("anchor", lambda v: isinstance(v, bool)),
    ("inline", lambda v: isinstance(v, bool)),
    ("level", lambda v: isinstance(v, int) and not isinstance(v, bool)),
)


def _is_mark(v: object) -> TypeIs[Mark]:
    """A JSON object with a str `text` whose other Mark keys, when present, have their declared type."""
    if not is_object_dict(v) or not isinstance(v.get("text"), str):
        return False
    return all(key not in v or ok(v[key]) for key, ok in _MARK_FIELDS)


# Native headings (`= Title`) are not lib marks: `--field value` drops them silently (a heading has no `value`).
# A selector that names `heading` is therefore read through `eval`, which turns each heading into the same
# kind of record as a mark (kind, text, level, page) in the SAME single query; the other elements give `.value`.
HEADING_SELECTOR = "heading"
_PLAIN = ('let plain(c) = if type(c) == str { c } else if c == [ ] { " " } else if c.func() == linebreak '
          '{ " " } else if c.func() == smartquote { " " } else if c.has("text") { c.text } else if c.has("body") '
          '{ plain(c.body) } else if c.has("children") { c.children.map(plain).join("") } else { "" }')
_HEADING_RECORD = ('(kind: "heading", text: plain(it.body), level: it.level, '
                   'page: it.location().position().page, '
                   'y: it.location().position().y.pt())')


def _eval_expr(selector: str) -> str:
    """The Typst expression whose JSON is the values of the elements `selector` selects."""
    if HEADING_SELECTOR not in selector:
        return f"query({selector}).map(it => it.value)"
    return f"{{ {_PLAIN}\nquery({selector}).map(it => if it.func() == heading {{ {_HEADING_RECORD} }} else {{ it.value }}) }}"


def _values_py(typ: str, selector: str, root: str | None) -> list[object] | None:
    """The typst-py route of typst_values: same query / eval fallback and root as the CLI calls. A wheel whose
    `query` or `eval` lacks the keyword (`typst_route().caps`) skips that call instead of failing it."""
    mod = typst_py()
    if mod is None:
        return None
    caps = typst_route().caps
    try:
        comp = mod.Compiler(typ, root=root, **typst_font_kw()) if root else mod.Compiler(typ, **typst_font_kw())
        calls: list[Callable[[], object]] = []
        if caps.query_field and HEADING_SELECTOR not in selector:
            calls.append(lambda: comp.query(selector, field="value", one=False))
        if caps.eval_format:
            calls.append(lambda: comp.eval(_eval_expr(selector), format="json"))
        for fn in calls:
            try:
                out = fn()
                if isinstance(out, str) and out.strip().startswith("["):
                    vals = _json_list(out)
                    if vals is not None:
                        return vals
            except (RuntimeError, ValueError, OSError):
                continue   # this typst-py route failed (typst error, bad JSON): try the next
    except (RuntimeError, TypeError, OSError):   # Compiler() refusing the source or the keywords: marks not readable
        pass
    return None


def typst_values(typ: str, selector: str, root: str | None = None) -> list[object] | None:
    """JSON list of the values of every element labelled `selector`, or None. Asked once per source state and selector
    inside a gate run (see pdf.run_memo)."""
    memo, key = current_memo(), file_key(typ)
    if memo is None or key is None:
        return _typst_values(typ, selector, root)
    slot = (key, selector, root)
    if slot not in memo.values:
        memo.values[slot] = _typst_values(typ, selector, root)
    return memo.values[slot]


def _typst_values(typ: str, selector: str, root: str | None) -> list[object] | None:
    root = root or auto_root(typ)
    if typst_route().query != "cli":
        return _values_py(typ, selector, root)
    rootargs = ["--root", root] if root else []
    cmds = [["typst", "eval", _eval_expr(selector), "--in", typ, "--target", "paged", *rootargs]]
    if HEADING_SELECTOR not in selector:
        cmds.insert(0, ["typst", "query", typ, selector, "--field", "value", *rootargs])
    for cmd in cmds:
        try:
            r = proc.run(cmd, proc.TYPST_S, name=f"typst {cmd[1]}")
        except OSError:   # typst missing; a timeout propagates to `proc.guarded`, and is never cached
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
    if not is_object_dict(v):
        return f"<mark> = {v!r}"
    if not isinstance(v.get("text"), str):
        return f"text = {v.get('text')!r}"
    for key, ok in _MARK_FIELDS:
        if key in v and not ok(v[key]):
            return f"{key} = {v[key]!r}"
    return f"<mark> = {v!r}"


def _check_marks(vals: list[object]) -> tuple[list[Mark], str | None]:
    """The well-typed Marks of `vals` and the note on the dropped ones (see typst_query_checked)."""
    marks = [v for v in vals if _is_mark(v)]
    bad = [v for v in vals if not _is_mark(v)]
    note = f"{len(bad)} lib marks ignored: malformed (first: {_first_problem(bad[0])})" if bad else None
    return marks, note


def typst_query_checked(typ: str, selector: str, root: str | None = None) -> tuple[list[Mark] | None, str | None]:
    """The lib's Mark values (see typst_values) and a note: an entry that is not a well-typed Mark (see _is_mark)
    is dropped, and the note says how many and the first offending field; None when nothing was dropped (valid lib
    output never has a note). The marks are None when the query is unavailable."""
    vals = typst_values(typ, selector, root)
    if vals is None:
        return None, None
    return _check_marks(vals)


def _kind_of(v: object) -> object:
    """The `kind` of a lib metadata value, None when it is not a dict or has none."""
    return v.get("kind") if is_object_dict(v) else None


def typst_marks_and_contact(typ: str, selector: str, root: str | None = None) -> tuple[list[Mark] | None, str | None, ContactValues | None]:
    """ONE query for the marks and the contact labels: `selector` selects all of them (Typst `.or`), and the
    values are split by their explicit `kind` since a query drops the label: "contact" is a <vitae-contact> item,
    "contact-rows" a <vitae-contact-rows> declaration; everything else goes through _check_marks as before
    (a value with neither kind is never counted as contact). All three are None when the query is unavailable."""
    vals = typst_values(typ, selector, root)
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


def typst_query(typ: str, selector: str, root: str | None = None) -> list[Mark] | None:
    """`typst_query_checked` without the note."""
    return typst_query_checked(typ, selector, root)[0]


def gnorm(t: str) -> str:
    """Comparison key for a word: letters and digits only, casefolded, so punctuation and
    spacing differences between the typst source and pdftotext do not break a match."""
    return "".join(ch for ch in t.casefold() if ch.isalnum())


def cluster(ws: Sequence[Word]) -> list[TextLine]:
    """Words already sorted by y-centre, clustered into text lines -> list of dicts {y0, y1, c, x0, words}."""
    out: list[TextLine] = []
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


class LineSet:
    """The text lines of one set of words (see PageIndex.lines) and the line holding each of its words."""

    def __init__(self, lines: list[TextLine]) -> None:
        self.lines = lines
        # keyed by the identity of the word tuple, not its value: two equal words are two words (the page's words
        # outlive this object, so an id is never reused)
        self._first: dict[int, int] = {}
        for i, ln in enumerate(lines):
            for w in ln["words"]:
                self._first.setdefault(id(w), i)

    def line_index(self, run: list[Word]) -> int | None:
        """The index of the line holding the first word of `run` (matched by identity), None when it is not a word
        of these lines."""
        return self._first.get(id(run[0]))


_TOKENS = 4          # up to 4 tokens is enough to identify an entry head uniquely without crossing a line wrap
_NEAR = 30.0         # a match farther than this (~2 lines) from the <vitae-head> marker's y is a repeated word elsewhere


class PageIndex:
    """One page's words, indexed once for every head or title measured on it: the normalised text of each word and the
    positions of each normal form, the words in y-centre order and the text lines of each distinct left edge.
    These were rebuilt for every call (O(words) each, so a page of heads was
    O(heads x words) with a heavy constant); here a call costs O(the page's words of its first token) for `find_run`,
    and the lines of a left edge are clustered once, whatever the number of heads at it. The coordinates are finite
    numbers, as pdftotext and pdfium give them."""

    def __init__(self, words: Sequence[Word]) -> None:
        self.words = words
        self._norm = [gnorm(w[4]) for w in words]
        self._by_norm: dict[str, list[int]] = {}
        for j, n in enumerate(self._norm):
            self._by_norm.setdefault(n, []).append(j)
        centre = [(w[1] + w[3]) / 2 for w in words]
        self._centre = centre
        self._by_centre = sorted(range(len(words)), key=centre.__getitem__)          # stable: ties keep word order
        self._x0 = sorted(w[0] for w in words)
        self._lines_at: dict[int, LineSet] = {}

    def find_run(self, text: str, ytyp: float) -> list[Word] | None:
        """The words of `text` (first 4 tokens) nearest typst y `ytyp` -> list of word tuples, or None."""
        toks = [t for t in (gnorm(w) for w in text.split()) if t][:_TOKENS]
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

    def lines(self, x_min: float) -> LineSet:
        """The text lines of the words at or right of x_min, computed once per distinct set of such words."""
        # two x_min with as many words left of them select the same words: that count is the memo key
        k = bisect_left(self._x0, x_min)
        got = self._lines_at.get(k)
        if got is None:
            words = self.words
            got = self._lines_at[k] = LineSet(cluster([words[i] for i in self._by_centre if words[i][0] >= x_min]))
        return got
