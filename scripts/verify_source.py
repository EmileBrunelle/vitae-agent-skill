"""Checks on the cv.typ source: section split, forced line breaks, literal `~`, header fill declaration.

Moved out of verify.py unchanged, re-exported there under the same names. A leaf under verify_pdf: no `import verify`.
"""
from __future__ import annotations

import re
import unicodedata

from verify_lang import _is_latin, _strip_latin_marks
from verify_pdf import family_from_path
from verify_typst import _mask_non_markup

# The headings come from the SOURCE, not from a guess at what a heading looks
# like in the extraction: every family defines its own `#section(t, body)` and
# calls it `#section("Title")[...]`, so the call sites ARE the declared list.
# No font-size heuristic survives the family roster; a grep does.
SECTION_CALL_RE = re.compile(r'#section\(\s*"([^"]*)"')


# lib.typ's `runhead` emits `name #h(1fr) n / total` (core.md § the device
# table: placed IN THE FLOW, because a page `header:` field is dropped by many
# parsers). pdftotext may put the name and the `n / total` on one line or two,
# in either order, so the pagination token is what identifies the band — and a
# section heading never carries one.
PAGINATION_RE = re.compile(r"\b\d+\s*/\s*\d+\b|\bpage\s+\d+\b", re.I)


def _norm_heading(s: str) -> str:
    """Compare headings on letters and digits only: the extraction upper-cases
    them, and a family's device may add or drop punctuation around one. Any
    script: case-folded, accents dropped from Latin letters only, everything
    that is not a letter, digit or mark is a separator."""
    s = _strip_latin_marks(s.casefold())
    return " ".join("".join(c if c.isalnum() or unicodedata.category(c)[0] == "M" else " " for c in s).split())


def _heading_words(s: str) -> frozenset[str]:
    """Loose key of a NON-Latin heading: its words with every combining mark, joiner and
    format character removed, as a set. Extraction may reorder the marks of Devanagari or Thai,
    reshape Arabic, return right-to-left words in another order, or upper-case Greek without its
    accents (ΕΜΠΕΙΡΙΑ for εμπειρία); none of that is a section split, so a heading that matches on this
    key is accepted. Latin headings: empty (exact only)."""
    h = _norm_heading(s)
    if all(_is_latin(c) for c in h if c.isalpha()):
        return frozenset()
    bare = "".join(c for c in unicodedata.normalize("NFKD", h)
                   if not unicodedata.combining(c) and unicodedata.category(c) not in ("Cf", "Mn"))
    return frozenset(bare.split())


def check_no_split(source: str, pages: list[str]) -> list[tuple[bool, str]]:
    """SKILL.md rule 5 -- "no section may split across a page break".

    Reduced to one measurable statement: a section that starts on page P and
    is not finished there leaves content at the TOP of page P+1. So every page
    after the first must OPEN on a section heading. Contrapositive of the rule,
    not an approximation of it -- if every break lands exactly on a boundary,
    nothing straddles; if one does not, whatever section preceded it is split.

    Returns (is_fail, message) pairs; "no #section call" and "single page" come back as non-failures, which the
    caller prints. The caller turns a FAIL into a WARN on the pypdf fallback, whose extraction is indicative only.

    Pure function of (source text, extracted pages) so the selftest can feed it
    synthetic text and needs no Typst. The academic gate checks the same
    property one level down (verify_academic.check_no_straddle: the atom is the
    ENTRY there, and its heading list comes from the declared JSON spec).
    """
    headings = {_norm_heading(t) for t in SECTION_CALL_RE.findall(source)}
    headings.discard("")
    loose = [hw for hw in (_heading_words(t) for t in SECTION_CALL_RE.findall(source)) if hw]
    if not headings:
        return [(False, 'no-split: no #section("...") call in the source '
                        "-- not checked")]
    # pdftotext TERMINATES the last page with \f rather than separating pages
    # with it, so a naive split leaves a trailing empty chunk — which read as
    # "page N+1 opens on nothing" and failed all 30 one-page deliverables.
    while pages and not pages[-1].strip():
        pages = pages[:-1]
    if len(pages) < 2:
        return [(False, "no-split: single page, nothing to split")]
    out = []
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
        ok = ok or bool(fw) and any(fw <= hw for hw in loose)   # non-Latin: marks and word order not trusted
        out.append((not ok,
                    f'no-split: page {pageno} opens on "{first[:60]}"'
                    + ("" if ok else " -- not a section heading, so the "
                                     "section before the break is SPLIT "
                                     "across it (SKILL.md rule 5)")))
    return out


_BANNER_RE = re.compile(r"^\s*//\s*FAMILY:\s*([\w-]+)", re.M)


_HEADER1_RE = re.compile(r"//\s*vitae:\s*pages=(\d+)(?:\s+fill=(\d+)-(\d+))?")


def _drawn_fill(typ: str) -> tuple[tuple[int, int] | None, list[str]]:
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
        import pick_design as pd
        fam = pd.FAMILIES.get(family)
        if fam:
            lo, hi = fam["page"]["fill"].split("-")
            table = (int(lo), int(hi))
    if table is None:
        return header, []
    warns = []
    if _BANNER_RE.search(head) and header != table:
        got = (f"{header[0]}-{header[1]}" if header
               else "no `// vitae: pages=N fill=A-B` header on line 1")
        warns.append(f"WARN  cv.typ header disagrees with family {family}: {got}; the drawn fill "
                     f"target is {table[0]}-{table[1]} (pick_design.FAMILIES) and is what is "
                     "enforced — restore the header, do not edit the target")
    return table, warns


def _fill_args_ok(*vals: str | None) -> bool:
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
    out, indent = [], None
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


TILDE_RE = re.compile(r"(?:^|(?<=[\s\[(*_]))~(?=[0-9A-Za-z])", re.M)


def check_literal_tilde(src: str) -> list[str]:
    """FAIL messages: an unescaped `~` that starts a word in content text
    (`~25 users`, `*~25 users*`). Typst reads it as a non-breaking space, so the
    PDF shows ` 25 users` and the tilde is gone, silently. Comments (line and
    block), "strings", `raw` spans (multi-line too), $math$ and `\\~` are masked
    over the whole file first; the intentional uses (`#cat~:`, `[~#sc]`) sit
    after an identifier or before `#`, so they never match."""
    out = []
    raws = src.split("\n")
    for n, line in enumerate(_mask_non_markup(src).split("\n"), 1):
        if TILDE_RE.search(line):
            out.append(f"line {n}: unescaped `~` in text "
                       f'("{raws[n - 1].strip()[:50]}") — Typst turns it into a non-breaking space; '
                       "write \\~ for a literal tilde")
    return out
