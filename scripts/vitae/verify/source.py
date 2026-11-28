"""Checks on the cv.typ source: section split, forced line breaks, literal `~`, header fill declaration.

A leaf under verify_pdf: no `import verify`.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from vitae.core.base import Mark
from vitae.verify.lang import is_latin, strip_latin_marks
from vitae.verify.pdf import family_from_path
from vitae.verify.typst import mask_non_markup

# The headings come from the SOURCE, not from a guess at what a heading looks
# like in the extraction: every family defines its own `#section(t, body)` and
# calls it `#section("Title")[...]`, so the call sites ARE the declared list.
# No font-size heuristic survives the family roster; a grep does.
SECTION_CALL_RE = re.compile(r'#section\(\s*"([^"]*)"')


# lib.typ's `runhead` emits `name #h(1fr) n / total` (core.md § Structure primitives
# table: placed IN THE FLOW, because a page `header:` field is dropped by many
# parsers). pdftotext may put the name and the `n / total` on one line or two,
# in either order, so the pagination token is what identifies the band — and a
# section heading never carries one.
PAGINATION_RE = re.compile(r"\b\d+\s*/\s*\d+\b|\bpage\s+\d+\b", re.IGNORECASE)


def _norm_heading(s: str) -> str:
    """Compare headings on letters and digits only: the extraction upper-cases
    them, and a family's device may add or drop punctuation around one. Any
    script: case-folded, accents dropped from Latin letters only, everything
    that is not a letter, digit or mark is a separator."""
    s = strip_latin_marks(s.casefold())
    return " ".join("".join(c if c.isalnum() or unicodedata.category(c)[0] == "M" else " " for c in s).split())


def _heading_words(s: str) -> frozenset[str]:
    """Loose key of a NON-Latin heading: its words with every combining mark, joiner and
    format character removed, as a set. Extraction may reorder the marks of Devanagari or Thai,
    reshape Arabic, return right-to-left words in another order, or upper-case Greek without its
    accents (ΕΜΠΕΙΡΙΑ for εμπειρία); none of that is a section split, so a heading that matches on this
    key is accepted. Latin headings: empty (exact only)."""
    h = _norm_heading(s)
    if all(is_latin(c) for c in h if c.isalpha()):
        return frozenset()
    bare = "".join(c for c in unicodedata.normalize("NFKD", h)
                   if not unicodedata.combining(c) and unicodedata.category(c) not in ("Cf", "Mn"))
    return frozenset(bare.split())


RUNNING_TOL_PT = 1.0   # a header or footer heading sits at the same y on every page


def _running(native: Sequence[Mark]) -> list[Mark]:
    """The headings left after dropping the running ones: a header or footer heading is the same (level, title)
    on more than one page at the same y (within RUNNING_TOL_PT). A repeated title at different heights is a real
    section; a record without a y or a page cannot be told, so it is kept."""
    def same(a: Mark, b: Mark) -> bool:
        return (a.get("level", 1) == b.get("level", 1) and _norm_heading(a["text"]) == _norm_heading(b["text"])
                and "page" in a and "page" in b and a["page"] != b["page"] and "y" in a and "y" in b
                and abs(a["y"] - b["y"]) <= RUNNING_TOL_PT)
    return [h for h in native if not any(same(h, o) for o in native)]


def boundary_headings(native: Sequence[Mark]) -> list[str]:
    """Titles of the native headings that START a section: those of the shallowest level, since a page that
    opens on a deeper heading is inside its section. A lone shallowest heading while deeper ones exist is
    the document title, not a section, so the next level down is used. A running heading (same title on
    several pages) is no boundary. Limit: a single `=` name over `==` entries reads as title over sections.
    Pure structure: levels and pages, never words."""
    native = _running(native)
    levels = sorted({h.get("level", 1) for h in native})
    if not levels:
        return []
    top = levels[0]
    if len(levels) > 1 and sum(h.get("level", 1) == top for h in native) == 1:
        top = levels[1]
    return [h["text"] for h in native if h.get("level", 1) == top]


def _before(h: Mark, secs: Sequence[Mark]) -> bool:
    """`h` sits above the first section mark (page, then y); False when a position is missing."""
    if "page" not in h or "y" not in h:
        return False
    first = min(((m["page"], m["y"]) for m in secs if "page" in m and "y" in m), default=None)
    return first is not None and (h["page"], h["y"]) < first


def check_native_headings(secs: Sequence[Mark], native: Sequence[Mark]) -> list[str]:
    """WARN lines for a CV that has <vitae-sec> marks AND native headings: lib section() draws no heading
    element (a block with a styled text), so a native heading is a section built by hand, which the
    grouping / date / runt / rhythm gates do not see. Named by position and page, never by its words.
    Not counted: a running heading, and the document title (the lone shallowest heading above the first mark)."""
    native = _running(native)
    if native:
        top = min(h.get("level", 1) for h in native)
        tops = [h for h in native if h.get("level", 1) == top]
        if len(tops) == 1 and tops[0] is native[0] and _before(tops[0], secs):
            native = native[1:]
    if not secs or not native:
        return []
    where = ", ".join(f"#{i} (page {h.get('page', '?')})" for i, h in enumerate(native, 1))
    return [f"{len(native)} native heading(s) of {len(native) + len(secs)} sections are not built with the family's "
            f"section(): heading {where}. Group proximity, date adjacency, runts and rhythm are NOT measured "
            "for them; build every section with section()"]


NO_BOUNDARY_MSG = ("no-split: the CV has no <vitae-sec> mark, no native heading and no #section(\"...\") call, "
                   "so no section boundary can be measured -- build every section with the family's section() "
                   "(templates/lib.typ wd-section) so the rule can be checked")


def section_titles(source: str, secs: Sequence[Mark] | None, native: Sequence[Mark] | None) -> list[str]:
    """The section boundaries check_no_split measures: the <vitae-sec> titles and the native boundary headings;
    the `#section("...")` calls of the source only when neither is there (query unavailable)."""
    titles = [m["text"] for m in secs or ()] + boundary_headings(native or ())
    return titles or SECTION_CALL_RE.findall(source)


def check_no_split(source: str, pages: list[str], *, secs: Sequence[Mark] | None = None,
                   native: Sequence[Mark] | None = None) -> list[tuple[bool, str]]:
    """SKILL.md rule 5 -- "no section may split across a page break".

    Reduced to one measurable statement: a section that starts on page P and
    is not finished there leaves content at the TOP of page P+1. So every page
    after the first must OPEN on a section heading. Contrapositive of the rule,
    not an approximation of it -- if every break lands exactly on a boundary,
    nothing straddles; if one does not, whatever section preceded it is split.

    The boundaries are, in order of preference, the <vitae-sec> marks (`secs`) together with the native
    headings (`native`: a hand-written `= Title` starts a section too), else the `#section("...")` calls of
    the source when the query was unavailable. A CV with none of them FAILs: its sections cannot be
    told apart, so the rule is unmeasurable, and an unmeasured rule is never a pass.

    Returns (is_fail, message) pairs; "single page" comes back as a non-failure, which the
    caller prints. The caller turns a FAIL into a WARN on the pypdf fallback, whose extraction is indicative only.

    Pure function of (source text, extracted pages) so the tests can feed it
    synthetic text and needs no Typst. The academic gate checks the same
    property one level down (verify_academic.check_no_straddle: the atom is the
    ENTRY there, and its heading list comes from the declared JSON spec).
    """
    titles = section_titles(source, secs, native)
    headings = {_norm_heading(t) for t in titles}
    headings.discard("")
    loose = [hw for hw in (_heading_words(t) for t in titles) if hw]
    if not headings:
        return [(True, NO_BOUNDARY_MSG)]
    # pdftotext TERMINATES the last page with \f rather than separating pages
    # with it, so a naive split leaves a trailing empty chunk — which read as
    # "page N+1 opens on nothing" and failed all 30 one-page deliverables.
    while pages and not pages[-1].strip():
        pages = pages[:-1]
    if len(pages) < 2:
        return [(False, "no-split: single page, nothing to split")]
    out: list[tuple[bool, str]] = []
    for pageno, page in enumerate(pages[1:], 2):
        lines = [l.strip() for l in page.split("\n") if l.strip()]
        for j in range(min(2, len(lines))):       # the running-head band only
            if PAGINATION_RE.search(lines[j]):
                lines = lines[j + 1:]
                break
        first = lines[0] if lines else ""
        f = _norm_heading(first)
        # A long heading can wrap, so the opening line may be a PREFIX of one.
        # Loose in the only direction that is safe: the line still has to sit
        # at the very top of the page to be considered at all.
        ok = bool(f) and any(h == f or h.startswith(f + " ") for h in headings)
        fw = _heading_words(first)
        ok = ok or (bool(fw) and any(fw <= hw for hw in loose))   # non-Latin: marks and word order not trusted
        out.append((not ok,
                    f'no-split: page {pageno} opens on "{first[:60]}"'
                    + ("" if ok else " -- not a section heading, so the "
                                     "section before the break is SPLIT "
                                     "across it (SKILL.md rule 5)")))
    return out


_BANNER_RE = re.compile(r"^\s*//\s*FAMILY:\s*([\w-]+)", re.MULTILINE)


_HEADER1_RE = re.compile(r"//\s*vitae:\s*pages=(\d+)(?:\s+fill=(\d+)-(\d+))?")


def drawn_fill(typ: str) -> tuple[tuple[int, int] | None, list[str]]:
    """The fill target pick_design.py drew, and WARN lines about the header.

    The `// vitae:` header is editable, so it is NOT the authority when the family
    is known (banner `// FAMILY:` or families/ directory): the target is that
    family's `page.fill` in pick_design.FAMILIES, whatever the header says. The
    header is used only when no family is known, and only on line 1."""
    try:
        with open(typ, encoding="utf-8") as fh:
            first = fh.readline()
            head = first + "".join(fh.readline() for _ in range(2))
    except OSError:
        return None, []
    hm = _HEADER1_RE.match(first.strip())
    header = (int(hm.group(2)), int(hm.group(3))) if hm and hm.group(2) else None
    family = family_from_path(typ)
    table: tuple[int, int] | None = None
    if family:
        from vitae.design.tables import FAMILIES
        fam = FAMILIES.get(family)
        if fam:
            lo, hi = fam["page"]["fill"].split("-")
            table = (int(lo), int(hi))
    if table is None:
        return header, []
    warns: list[str] = []
    if _BANNER_RE.search(head) and header != table:
        got = (f"{header[0]}-{header[1]}" if header
               else "no `// vitae: pages=N fill=A-B` header on line 1")
        warns.append(f"WARN  cv.typ header disagrees with family {family}: {got}; the drawn fill "
                     f"target is {table[0]}-{table[1]} (pick_design.FAMILIES) and is what is "
                     "enforced — restore the header, do not edit the target")
    return table, warns


def fill_args_ok(*vals: str | None) -> bool:
    """FAIL line + False when a fill/page argument is not a plain integer."""
    for v in vals:
        if v is not None and not re.fullmatch(r"\d+", v):
            print(f"FAIL  fill args must be integers (got {v!r}) — e.g. verify.py cv.typ 1 94 96")
            return False
    return True


# A list item opens with `-`, `+` or `1.`; its indentation marks where its continuation lines end.
LIST_ITEM_RE = re.compile(r"^(\s*)(?:[-+]|\d+\.)\s")


FORCED_BREAK_RE = re.compile(r"(?<!\\)\\(?:\s|$)|#linebreak\s*\(")


def check_forced_linebreak(src: str) -> list[str]:
    """FAIL messages: a forced line break (`\\ ` or `#linebreak()`) inside a
    bullet / list item. A bullet is one sentence that wraps on its own; a hard
    break mid-bullet leaves a ragged half-line and, in the extraction, splits
    the bullet in two. Source-text check: it needs no PDF, so it runs in every mode.
    A FAIL because the construct is unambiguous in the source, whatever the language."""
    out: list[str] = []
    indent: int | None = None
    for n, raw in enumerate(src.split("\n"), 1):
        line = re.sub(r"(?:^|(?<=\s))//.*$", "", raw)   # drop `//` comments, but not a `//` inside a URL
        m = LIST_ITEM_RE.match(line)
        if m:
            indent = len(m.group(1))
        elif indent is not None:
            # the item ends at a blank line or a line indented no deeper than its marker
            if not line.strip() or len(line) - len(line.lstrip()) <= indent:
                indent = None
        if indent is not None and FORCED_BREAK_RE.search(line):
            out.append(f"line {n}: forced line break inside a bullet "
                       f'("{raw.strip()[:50]}") — let the bullet wrap itself; '
                       "split it into two bullets or shorten it")
    return out


TILDE_RE = re.compile(r"(?:^|(?<=[\s\[(*_]))~(?=[0-9A-Za-z])", re.MULTILINE)


def check_literal_tilde(src: str) -> list[str]:
    """FAIL messages: an unescaped `~` that starts a word in content text
    (`~25 users`, `*~25 users*`). Typst reads it as a non-breaking space, so the
    PDF shows ` 25 users` and the tilde is gone, silently. Comments (line and
    block), "strings", `raw` spans (multi-line too), $math$ and `\\~` are masked
    over the whole file first; the intentional uses (`#cat~:`, `[~#sc]`) sit
    after an identifier or before `#`, so they never match."""
    out: list[str] = []
    raws = src.split("\n")
    for n, line in enumerate(mask_non_markup(src).split("\n"), 1):
        if TILDE_RE.search(line):
            out.append(f"line {n}: unescaped `~` in text "
                       f'("{raws[n - 1].strip()[:50]}") — Typst turns it into a non-breaking space; '
                       "write \\~ for a literal tilde")
    return out
