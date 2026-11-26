"""The `typst query` mark reader and the word/line helpers the grouping and date gates share."""
from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from vitae.core.base import Mark, Word, _Line
from vitae.core.env import typst_font_kw, typst_py
from vitae.verify.pdf import auto_root

if TYPE_CHECKING:
    # type checking only: typing_extensions is never imported at run time (annotations are strings here)
    from typing_extensions import TypeIs

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


def _typst_query_checked(typ: str, selector: str, root: str | None = None) -> tuple[list[Mark] | None, str | None]:
    """The lib's Mark values (see _typst_values) and a note: an entry that is not a well-typed Mark (see _is_mark)
    is dropped, and the note says how many and the first offending field; None when nothing was dropped (valid lib
    output never has a note). The marks are None when the query is unavailable."""
    vals = _typst_values(typ, selector, root)
    if vals is None:
        return None, None
    marks = [v for v in vals if _is_mark(v)]
    bad = [v for v in vals if not _is_mark(v)]
    note = f"{len(bad)} lib marks ignored: malformed (first: {_first_problem(bad[0])})" if bad else None
    return marks, note


def _typst_query(typ: str, selector: str, root: str | None = None) -> list[Mark] | None:
    """`_typst_query_checked` without the note."""
    return _typst_query_checked(typ, selector, root)[0]


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
            y0, y1 = min(ln["y0"], w[1]), max(ln["y1"], w[3])
            out[-1] = {"y0": y0, "y1": y1, "c": (y0 + y1) / 2, "x0": min(ln["x0"], w[0]), "words": ln["words"]}
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
