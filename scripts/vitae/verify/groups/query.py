"""The `typst query` mark reader and the word/line helpers the grouping and date gates share."""
from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable, Sequence
from typing import cast

from vitae.core.base import Mark, Word, _Line
from vitae.core.env import typst_font_kw, typst_py
from vitae.verify.pdf import auto_root

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
    """The lib's Mark values (see _typst_values); anything that is not a JSON object is dropped."""
    vals = _typst_values(typ, selector, root)
    return None if vals is None else cast("list[Mark]", [v for v in vals if isinstance(v, dict)])


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
