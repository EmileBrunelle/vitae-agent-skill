"""cv.typ parsing, separated from the checks that use it and from rendering.

Pure text in, values out: every function here reads Typst source (comments and
non-markup stripped, `#set par/text/list` leading and size) and returns values. Nothing here prints,
opens a PDF or looks at page geometry; verify.py owns the checks, the reporting
and the rendering, and imports these names explicitly.

This module imports only vitae.core (never verify). No module state beyond compiled regular expressions.
"""
from __future__ import annotations

import re
from bisect import bisect_left

from vitae.core.typst_source import strip_typst_comments

# Transitional name for cv.py and pdf.py, which still import it; they should import
# vitae.core.typst_source.strip_typst_comments directly, then this line goes.
_strip_typst_comments = strip_typst_comments


def _mask_non_markup(src: str) -> str:
    """src with every region where `~` is not markup blanked to spaces, newlines
    kept (so line numbers stay true): // and nested /* */ comments, "strings",
    ``` raw spans (multi-line too), $math$, and `\\~`-style escapes."""
    out, i, n = [], 0, len(src)

    def blank(j: int) -> None:
        nonlocal i
        out.append("".join(ch if ch == "\n" else " " for ch in src[i:j]))
        i = j

    while i < n:
        c = src[i]
        if c == "\\":
            blank(min(i + 2, n))
        elif c == "`":
            e = 1
            while i + e < n and src[i + e] == "`":
                e += 1
            close = src.find("`" * e, i + e)
            blank(n if close < 0 else close + e)
        elif src.startswith("/*", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if src.startswith("/*", j):
                    depth += 1; j += 2
                elif src.startswith("*/", j):
                    depth -= 1; j += 2
                else:
                    j += 1
            blank(j)
        # Same URL-scheme exception as strip_typst_comments.
        elif src.startswith("//", i) and (i == 0 or src[i - 1] != ":"):
            j = src.find("\n", i)
            blank(n if j < 0 else j)
        elif c == '"':
            j = i + 1
            while j < n and src[j] not in '"\n':
                j += 2 if src[j] == "\\" else 1
            blank(j + 1 if j < n and src[j] == '"' else i + 1)
        elif c == "$":
            j = i + 1
            while j < n and src[j] != "$":
                j += 2 if src[j] == "\\" else 1
            blank(min(j + 1, n) if j < n else i + 1)
        else:
            out.append(c)
            i += 1
    return "".join(out)


_PAR_OPEN = re.compile(r"^#set\s+par\(", re.M)
_PARENS = re.compile(r"[()]")
# `#set par(... leading: Xem ... spacing: Yem)`, the pair --tune rewrites. It only matches leading before spacing
# and em units: accepting the reverse order would make _write_par swap the two values (the unit tests pin this).
# The atomic group commits to the FIRST `leading: Xem` of the rule: a later one can only be followed by fewer `spacing:`
# than the first, so retrying it when `spacing:` is missing found nothing and rescanned the rule once per `leading:`.
PAR_RE = re.compile(r"(?>(#set\s+par\([^)]*?leading:\s*)([0-9.]+)(?=em))(em[^)]*?spacing:\s*)([0-9.]+)(em)")


def _par_rule_spans(masked: str) -> list[tuple[int, int]]:
    """(start, end) of every column-0 `#set par(... leading: ...)` rule in a _mask_non_markup'd text. Linear in the
    text: the closing parenthesis of every rule comes from one pass with a stack, and the `leading:` arguments are
    found once in the whole text (they cannot overlap each other) then looked up by bisection per rule. A rule that
    never closes runs to the end of the text, less its last character."""
    starts = list(_PAR_OPEN.finditer(masked))
    if not starts:
        return []
    close: dict[int, int] = {}
    stack: list[int] = []
    for p in _PARENS.finditer(masked):
        if p.group() == "(":
            stack.append(p.start())
        elif stack:
            close[stack.pop()] = p.start()
    # `masked[:-1]`: an unclosed rule's arguments stop one character short of the text, which is where a trailing
    # `\b` is judged; a closed rule's arguments end at its `)`, a non-word character, so both read the same.
    leads = list(_LEAD_ARG.finditer(masked[:-1]))
    lead_at = [m.start() for m in leads]
    spans = []
    for m in starts:
        end = close.get(m.end() - 1, len(masked) - 1)
        # the match may start on the `(` itself (the `^` of a slice of the arguments)
        k = bisect_left(lead_at, m.end() - 1)
        if k < len(leads) and leads[k].end() <= end:
            spans.append((m.start(), end + 1))
    return spans


def _tuned_par(text: str) -> re.Match[str] | None:
    """PAR_RE match of the rule the gate measures (the LAST column-0 `#set par(... leading: ...)`), None when
    there is none or that rule is not in the `leading: Xem ... spacing: Yem` form the tuner can rewrite.
    Offsets are those of `text` (masking keeps them)."""
    masked = _mask_non_markup(text)
    spans = _par_rule_spans(masked)
    return PAR_RE.match(masked, spans[-1][0]) if spans else None


def _read_par(text: str) -> tuple[float, float] | None:
    """(leading, spacing) in em of the rule the gate measures (see _tuned_par), None when it is not tunable."""
    m = _tuned_par(text)
    if not m:
        return None
    return float(m.group(2)), float(m.group(4))


def _write_par(text: str, leading: float, spacing: float) -> str:
    """text with the rule the gate measures (see _tuned_par) rewritten to these values (three decimals);
    other rules, earlier `#set par` lines included, are untouched. Only the two numbers are replaced, at
    the offsets of the masked match, so a comment or string inside the rule survives byte for byte."""
    m = _tuned_par(text)
    if not m:
        return text
    return "%s%.3f%s%.3f%s" % (text[:m.start(2)], leading, text[m.end(2):m.start(4)], spacing,
                               text[m.end(4):])


_RHYTHM_LINE = re.compile(r"^#let\s+rhythm(?![\w-]).*$", re.M)
_RHYTHM_RE = re.compile(r"(#let rhythm = )([0-9]+(?:\.[0-9]+)?|\.[0-9]+)[ \t\r]*;?[ \t\r]*")


def _rhythm_line(text: str) -> tuple[int, str] | None:
    """(offset, masked text) of the LAST column-0 `#let rhythm` line (Typst uses the last binding, as the
    gate does for par), None when the file has none. Searched outside comments and strings."""
    last = None
    for m in _RHYTHM_LINE.finditer(_mask_non_markup(text)):
        last = (m.start(), m.group(0))
    return last


def _rhythm_match(text: str) -> re.Match[str] | None:
    """Match of the last column-0 `#let rhythm = <number>` line (the pt-gap multiplier of the family's
    section / entry code; an integer, a trailing `;` and a trailing comment are accepted), None when the
    file has none or its last one is not in that form (see _rhythm_unparsed). Offsets are those of `text`."""
    found = _rhythm_line(text)
    if found is None:
        return None
    return _RHYTHM_RE.fullmatch(found[1])       # masked line: same offsets as the raw one


def _rhythm_unparsed(text: str) -> bool:
    """True when the file has a column-0 `#let rhythm` line (its last one) that _read_rhythm cannot read."""
    return _rhythm_line(text) is not None and _rhythm_match(text) is None


def _read_rhythm(text: str) -> float | None:
    m = _rhythm_match(text)
    return float(m.group(2)) if m else None


def _write_rhythm(text: str, rhythm: float) -> str:
    """text with the `#let rhythm` value set (three decimals); unchanged when the file has no such line."""
    found = _rhythm_line(text)
    m = _rhythm_match(text)
    if not m or found is None:
        return text
    a, b = found[0] + m.start(2), found[0] + m.end(2)
    return "%s%.3f%s" % (text[:a], rhythm, text[b:])


def _par_scope(text: str) -> int:
    """Offset from which the tuner's list-spacing scaling applies: the start of the tuned par rule when the
    file has several (a list set before it belongs to another page's rhythm), 0 when it has one."""
    masked = _mask_non_markup(text)
    spans = _par_rule_spans(masked)
    return spans[-1][0] if len(spans) > 1 else 0


# The set rules _doc_par_list_size reads; only at column 0, so a rule inside a #let or #show body never counts.
_SET_RE = re.compile(r"^#set\s+(par|text|list|enum)\(")
# The number is `[0-9]*\.?[0-9]+` written without the nested quantifiers (backtracking over a run of digits took
# quadratic time): the same strings, the same captured text.
_LEAD_ARG = re.compile(r"(?:^|[,(\s])leading\s*:\s*([0-9]+(?:\.[0-9]+)?|\.[0-9]+)\s*(em|pt)\b")
_SPACING_KEY = re.compile(r"(?:^|[,(\s])spacing\s*:\s*")
_SPACING_VAL = re.compile(r"([0-9]+(?:\.[0-9]+)?|\.[0-9]+)\s*(em|pt)\b")


def _spacing_arg(args: str) -> tuple[bool, re.Match[str] | None]:
    """(found, numeric match) for a `spacing:` argument at nesting depth 0 of `args` (a nested
    `box(spacing: ..)` is not the set-rule's own argument); found with no match = non-numeric."""
    depth, at = 0, []
    for ch in args:
        at.append(depth)
        if ch in "([{":
            depth += 1
        elif ch in ")]}" and depth:
            depth -= 1
    for km in _SPACING_KEY.finditer(args):
        pos = km.start() + (km.group(0).find("spacing"))
        if at[pos] == 0:
            return True, _SPACING_VAL.match(args, km.end())
    return False, None
_SIZE_ARG = re.compile(r"(?:^|[,(\s])size\s*:\s*([0-9]+(?:\.[0-9]+)?|\.[0-9]+)\s*pt\b")


def _scale_list_spacing(text: str, factor: float, after: int = 0) -> str:
    """text with every top-level `#set list(... spacing: X)` (numeric, em or pt) multiplied by factor
    (three decimals, unit kept); text with no explicit numeric list spacing comes back unchanged.
    Same top-level scope as _doc_par_list_size, so a nested `box(spacing:)` is never touched; only rules
    starting at offset `after` or later are scaled."""
    masked = _mask_non_markup(text)
    out, last, depth, i, n = [], 0, 0, 0, len(masked)
    while i < n:
        j = masked.find("\n", i)
        j = n if j < 0 else j
        line = masked[i:j]
        m = _SET_RE.match(line) if depth == 0 else None
        if depth == 0 and not m and line.strip() and not re.match(r"#(set|show|import|let)\b", line):
            break
        if m and m.group(1) == "list":
            k, d = i + m.end(), 1
            while k < n and d:
                d += (masked[k] == "(") - (masked[k] == ")")
                k += 1
            args = masked[i + m.end():k - 1]
            _, sp = _spacing_arg(args)
            if sp and i >= after:
                a, b = i + m.end() + sp.start(1), i + m.end() + sp.end(1)
                out.append(text[last:a])
                out.append("%.3f" % (float(sp.group(1)) * factor))
                last = b
        for ch in line:
            if ch in "([{":
                depth += 1
            elif ch in ")]}" and depth:
                depth -= 1
        i = j + 1
    out.append(text[last:])
    return "".join(out)


def _doc_par_list(text: str) -> tuple[float | None, float | None]:
    """(leading, list spacing) in em; see _doc_par_list_size."""
    return _doc_par_list_size(text)[:2]


def _doc_body_size(text: str) -> float | None:
    """The document's top-level body text size in pt (the last top-level `#set text(size: X pt)`
    before the body, same reader as the leading), None when there is none."""
    return _doc_par_list_size(text)[2]


def _doc_par_list_size(text: str) -> tuple[float | None, float | None, float | None]:
    """(leading, list spacing, body size): leading and list spacing in em, body size in pt, each None when the
    document sets none.

    Leading is that of the LAST top-level `#set par(... leading: ...)` before the body, in any argument order;
    list spacing is read the same way from `#set list(... spacing: ...)` and is None when it is not numeric
    (`auto`). Top-level means column 0 and outside any #let / #show body. A value in pt is converted to em with the
    text size set so far, 11 pt (Typst's default) before any `#set text(size: X pt)`. The returned body size is
    the last explicit one only, never that default."""
    masked = _mask_non_markup(text)
    depth, size, lead, lsp, i, n = 0, 11.0, None, None, 0, len(masked)
    explicit: float | None = None
    while i < n:
        j = masked.find("\n", i)
        j = n if j < 0 else j
        line = masked[i:j]
        m = _SET_RE.match(line) if depth == 0 else None
        if depth == 0 and not m and line.strip() and not re.match(r"#(set|show|import|let)\b", line):
            break                                # first top-level content: the body starts
        if m:
            k, d = i + m.end(), 1                # balanced scan of the call's arguments
            while k < n and d:
                d += (masked[k] == "(") - (masked[k] == ")")
                k += 1
            args = masked[i + m.end():k - 1]
            if m.group(1) == "text":
                sm = _SIZE_ARG.search(args)
                if sm:
                    size = explicit = float(sm.group(1))
            elif m.group(1) == "par":
                lm = _LEAD_ARG.search(args)
                if lm:
                    v = float(lm.group(1))
                    lead = v if lm.group(2) == "em" else v / size
            elif m.group(1) == "list":
                found, sp = _spacing_arg(args)
                if sp:
                    v = float(sp.group(1))
                    lsp = v if sp.group(2) == "em" else v / size
                elif found:
                    lsp = None                   # `spacing: auto` etc.: effective spacing unknown
        for ch in line:
            if ch in "([{":
                depth += 1
            elif ch in ")]}" and depth:
                depth -= 1
        i = j + 1
    return lead, lsp, explicit
