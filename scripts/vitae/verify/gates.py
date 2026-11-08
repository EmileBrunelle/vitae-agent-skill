"""The per-CV gates after the PDF is built, as `check(ctx) -> list[Finding]` adapters and their order.

`GATES` is the order `_check_cv` prints them in: the extraction gates, then the layout gates (hidden
text, font fallback, proximity, dates, source text, duplicate names). `--gates` runs `LAYOUT_GATES` alone.
Each adapter wraps one `check_*` function of its own module and returns the exact lines it printed
before the registry existed. The fill / page-count / compile stages need the PNGs and the compiler, so
they stay in vitae/verify/cv.py.
"""
from __future__ import annotations

import re

from vitae.core.base import DetailRow, HiddenStat
from vitae.core.context import VerifyContext
from vitae.core.level import Finding, Level
from vitae.verify.groups import (
    ENTRY_MARKS,
    _typst_query,
    check_date_adjacency,
    check_duplicate_names,
    check_group_proximity,
)
from vitae.verify.layout import check_font_fallback
from vitae.verify.registry import FnGate, Gate
from vitae.verify.source import check_forced_linebreak, check_literal_tilde, check_no_split
from vitae.verify.text import check_bullet_chars, check_facts_coverage, check_hidden_text


def make_context(typ: str, pdf: str, txt: str, src: str, backend: str | None, *, root: str | None = None,
                 facts: str | None = None, can_query: bool = True,
                 detail: list[DetailRow] | None = None) -> VerifyContext:
    """Build the gates' inputs; the lib markers are queried here, once, when `typst query` is usable."""
    marks = _typst_query(typ, ENTRY_MARKS, root) if can_query else None
    heads = None if marks is None else [m for m in marks if m.get("kind") in ("entry", "skill")]
    return VerifyContext(typ=typ, pdf=pdf, txt=txt, src=src, backend=backend, root=root, facts=facts,
                         can_query=can_query, marks=marks, heads=heads, detail=detail)


def _bad(ctx: VerifyContext, msg: str) -> Finding:
    """FAIL on the reference extractor, WARN on the pypdf fallback: pypdf's extraction is indicative
    only (the run says so up front), so a hard FAIL on it would be a verdict the evidence does not support."""
    if ctx.backend != "pypdf":
        return Level.FAIL, msg
    return Level.WARN, msg + " — pypdf extraction is indicative; confirm with pdftotext before believing it"


def _extraction_empty(ctx: VerifyContext) -> list[Finding]:
    return [] if ctx.txt.strip() else [_bad(ctx, "extraction empty")]


def _letterspaced(ctx: VerifyContext) -> list[Finding]:
    # Letterspaced capitals break keyword matching in an ATS. First pattern: 4+ STANDALONE
    # capitals (the \b anchors keep "B.Sc. C S M Sc", dotted abbreviations, out). Second
    # pattern: tracking's real pdftotext shape, chunked rather than fully spaced
    # ("S O F T WA RE"). Known limit: a space injected INSIDE a word ("FORMA TION") is not
    # detectable here: it is a pypdf extraction artefact, not a layout bug, and only the
    # pypdf path (WARN-only) produces it.
    spaced: str | re.Match[str] | None = re.search(r"\b(?:[A-Z] ){3,}[A-Z]\b", ctx.txt)
    if not spaced:
        for line in ctx.txt.split("\n"):
            tok = line.split()
            if (len(tok) >= 4 and all(re.fullmatch(r"[A-Z]{1,2}", t) for t in tok)
                    and sum(len(t) == 1 for t in tok) >= 2):
                spaced = line
                break
    return [_bad(ctx, "spaced-out text in extraction (letterspacing/tracking?)")] if spaced else []


def _orphaned_dates(ctx: VerifyContext) -> list[Finding]:
    # Per PAGE: a date alone at the foot of a page is read by an ATS as belonging to no entry;
    # it lands at the end of its own page, not only at the end of the document.
    out: list[Finding] = []
    for pageno, page in enumerate(ctx.txt.split("\f"), 1):
        non_blank = [l for l in page.split("\n") if l.strip()]
        last = non_blank[-1] if non_blank else ""
        if len(last) <= 25 and re.search(r"[0-9]{4}\s*$", last):
            out.append(_bad(ctx, f'orphaned date at end of page {pageno} of the extraction ("{last}") — bullet-less grid entry; see the trap in references/ats.md'))
    return out


def _no_split(ctx: VerifyContext) -> list[Finding]:
    out: list[Finding] = []
    for is_fail, msg in check_no_split(ctx.src, ctx.txt.split("\f")):
        out.append(_bad(ctx, msg) if is_fail else (Level.OK, msg))
    return out


def _facts_coverage(ctx: VerifyContext) -> list[Finding]:
    assert ctx.facts is not None   # `applies` guards it
    try:
        facts_text = open(ctx.facts, encoding="utf-8").read()
    except OSError as e:
        return [(Level.FAIL, f"--facts: cannot read {ctx.facts} ({e.strerror})")]
    return [(Level.WARN, w.removeprefix("WARN  ")) for w in check_facts_coverage(ctx.txt, facts_text)]


def _bullet_chars(ctx: VerifyContext) -> list[Finding]:
    bullets = check_bullet_chars(ctx.txt)
    if not bullets:
        return []
    return [(Level.WARN, f'{len(bullets)} line(s) start with a bullet character in the extraction (e.g. "{bullets[0][:30]}") — ATS prints it or puts it alone on a line; draw list markers as vector shapes (references/ats.md)')]


def _query_notice(ctx: VerifyContext) -> list[Finding]:
    return [(Level.WARN, "grouping / date-adjacency / duplicate-name gates NOT checked (need the typst CLI or typst-py with query)")]


def _hidden_text(ctx: VerifyContext) -> list[Finding]:
    det: list[HiddenStat] = []
    msgs = check_hidden_text(ctx.pdf, detail=det)
    if det and not msgs:
        msgs = [(Level.OK, f"hidden text: {len(det)} words, each visibly inked (weakest contrast "
                           f"{min(d[4] for d in det if d[4] is not None):.1f}:1, smallest box {min(d[3] for d in det):.1f}pt)")]
    return msgs


def _font_fallback(ctx: VerifyContext) -> list[Finding]:
    return check_font_fallback(ctx.typ, ctx.pdf, root=ctx.root)


def _group_proximity(ctx: VerifyContext) -> list[Finding]:
    return check_group_proximity(ctx.typ, ctx.pdf, root=ctx.root, detail=ctx.detail)


def _date_adjacency(ctx: VerifyContext) -> list[Finding]:
    out: list[Finding] = []
    if ctx.heads is not None and not any(h.get("kind") == "entry" for h in ctx.heads):
        out.append((Level.WARN, "date adjacency not measured: no lib entry()/srow() heads"))
    dwarn: list[str] = []
    dst: dict[str, int] = {}
    for msg in check_date_adjacency(ctx.typ, ctx.pdf, marks=ctx.marks or [], warns=dwarn, stats=dst):
        out.append((Level.FAIL, "date adjacency: " + msg))
    if ctx.marks is not None:
        _n = dst.get("measured", 0)
        out.append((Level.INFO, f"date adjacency: {_n} lib entr{'y' if _n == 1 else 'ies'} measured, "
                                f"{dst.get('undated', 0)} undated, {dst.get('unmeasured', 0)} not measured "
                                "(a dated entry not built with lib entry() is not counted)"))
    if dwarn:
        out.append((Level.WARN, f"date adjacency not measured: {len(dwarn)} entr{'y' if len(dwarn) == 1 else 'ies'} "
                                f"({'; '.join(dwarn[:3])})"))
    if ctx.marks is None:
        out.append((Level.WARN, "date adjacency not measured: typst query unavailable"))
    return out


def _source_text(ctx: VerifyContext) -> list[Finding]:
    return [(Level.FAIL, msg) for msg in check_forced_linebreak(ctx.src) + check_literal_tilde(ctx.src)]


def _duplicate_names(ctx: VerifyContext) -> list[Finding]:
    secs = _typst_query(ctx.typ, "<vitae-sec>", ctx.root)
    if not secs:   # no <vitae-sec> marks (a CV that never wrapped `section` in wd-section(), or no query): read the #section("...") calls instead
        secs = [{"text": t} for t in re.findall(r'#section\(\s*"((?:[^"\\]|\\.)*)"', ctx.src)]
    return [(Level.FAIL, "duplicate name: " + msg) for msg in check_duplicate_names(secs, ctx.heads)]


def _can_query(ctx: VerifyContext) -> bool:
    return ctx.can_query


def _cannot_query(ctx: VerifyContext) -> bool:
    return not ctx.can_query


def _has_facts(ctx: VerifyContext) -> bool:
    return bool(ctx.facts)


EXTRACTION_GATES: tuple[Gate, ...] = (
    FnGate("extraction-empty", _extraction_empty),
    FnGate("letterspacing", _letterspaced),
    FnGate("orphaned-date", _orphaned_dates),
    FnGate("no-split", _no_split),
    FnGate("facts-coverage", _facts_coverage, _has_facts),
    FnGate("bullet-chars", _bullet_chars),
)

# Without `typst query` the grouping / date / duplicate-name gates are skipped, with a notice first.
LAYOUT_GATES: tuple[Gate, ...] = (
    FnGate("query-notice", _query_notice, _cannot_query),
    FnGate("hidden-text", _hidden_text),
    FnGate("font-fallback", _font_fallback),
    FnGate("group-proximity", _group_proximity, _can_query),
    FnGate("date-adjacency", _date_adjacency, _can_query),
    FnGate("source-text", _source_text),
    FnGate("duplicate-names", _duplicate_names, _can_query),
)

GATES: tuple[Gate, ...] = EXTRACTION_GATES + LAYOUT_GATES
