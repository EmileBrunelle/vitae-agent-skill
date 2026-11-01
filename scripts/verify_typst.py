"""cv.typ parsing, separated from the checks that use it and from rendering.

Pure text in, values out: every function here reads Typst source (comments and
non-markup stripped, `#section(...)` bodies, `#entry(...)` string arguments,
`#set par/text/list` leading and size) and returns values. Nothing here prints,
opens a PDF or looks at page geometry; verify.py owns the checks, the reporting
and the rendering, and imports these names explicitly.
"""
from __future__ import annotations

import re

from verify_lang import _URL_TLDS


def _section_bodies(src: str) -> list[tuple[str, str]]:
    """(title, body text) of every `#section("Title")[ ... ]` call in a Typst source, brackets matched."""
    out: list[tuple[str, str]] = []
    for m in re.finditer(r'#section\(\s*"((?:[^"\\]|\\.)*)"\s*(?:,[^)]*)?\)\s*\[', src):
        i, depth = m.end(), 1
        while i < len(src) and depth:
            c = src[i]
            if c == "\\":
                i += 1
            elif c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
            i += 1
        out.append((m.group(1), src[m.end():i - 1]))
    return out


_URL_RE = re.compile(r"(?:https?://|www\.)\S+|\b[\w.-]+\.(?:%s)(?!\w)(?:/\S*)?" % _URL_TLDS, re.I)


def _typst_prose(body: str) -> str:
    """Body text without Typst code: `#name(...)` argument lists (balanced; a trailing `[...]` content block
    stays), string literals and URLs, so `#v(10pt)` or `linkedin.com/in/jo-1234` carry no figures."""
    out, i, n = [], 0, len(body)
    while i < n:
        m = re.compile(r"#[A-Za-z_][\w.-]*\(").match(body, i)
        if not m:
            out.append(body[i])
            i += 1
            continue
        j, depth = m.end(), 1
        while j < n and depth:
            c = body[j]
            if c == '"':
                j += 1
                while j < n and body[j] != '"':
                    j += 2 if body[j] == "\\" else 1
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            j += 1
        out.append(" ")
        i = j
    text = re.sub(r'"(?:[^"\\\n]|\\.)*"', " ", "".join(out))
    return _URL_RE.sub(" ", text)


_ENTRY_CALL_RE = re.compile(r"^#[A-Za-z_][\w.-]*\(", re.M)
_DATE_ARG_RE = re.compile(r"\b(?:19|20)\d{2}\b|\b(?:present|current|now\b|présent|actuel|aujourd)", re.I)


def _call_strings(body: str, j: int) -> tuple[list[str], int]:
    """String literals of the call whose argument list starts at `j` (just after its `(`), and the index after its `)`."""
    depth = 1
    strs: list[str] = []
    while j < len(body) and depth:
        c = body[j]
        if c == '"':
            e = j + 1
            while e < len(body) and body[e] != '"':
                e += 2 if body[e] == "\\" else 1
            strs.append(body[j + 1:e])
            j = e
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        j += 1
    return strs, j


def _entries(body: str, org_is_descriptor: bool = False) -> list[tuple[str, list[str], list[str]]]:
    """(title, descriptor segments, bullets) of each `#call("title", "org", "dates", "note")` entry in a section
    body. Descriptors are the string arguments after the title (and after the org, unless `org_is_descriptor`, as
    in projects where the second argument is the one-line description) that are not dates, split on ` · ` / ` | ` / commas."""
    calls = list(_ENTRY_CALL_RE.finditer(body))
    out = []
    for k, m in enumerate(calls):
        strs, j = _call_strings(body, m.end())
        tail = body[j:calls[k + 1].start() if k + 1 < len(calls) else len(body)]
        bullets: list[str] = []
        for line in tail.split("\n"):
            if line.startswith("- "):
                bullets.append(line[2:].strip())
            elif bullets and line.startswith(("  ", "\t")) and line.strip():
                bullets[-1] += " " + line.strip()
        segs = [x.strip() for a in strs[1 if org_is_descriptor else 2:]
                if not _DATE_ARG_RE.search(a) for x in re.split(r"\s[·|]\s|,\s*", a)]
        out.append((strs[0] if strs else "", [x for x in segs if x], bullets))
    return out


def _strip_typst_comments(src: str) -> str:
    """src without // line comments and (nested) /* */ blocks. Double-quoted
    strings are respected but never span a newline (a stray 6" in markup must
    not swallow the rest of the file); backtick raw spans are skipped whole."""
    out, i, n, q = [], 0, len(src), False
    while i < n:
        c = src[i]
        if c == "\n":
            q = False
            out.append(c)
        elif q:
            out.append(c)
            if c == "\\" and i + 1 < n and src[i + 1] != "\n":
                out.append(src[i + 1]); i += 1
            elif c == '"':
                q = False
        elif c == "\\" and i + 1 < n and src[i + 1] != "\n":
            out.append(c + src[i + 1]); i += 1          # escaped char (\//, \", \`)
        elif c == "`":
            e = len(src[i:]) - len(src[i:].lstrip("`"))   # opening run of backticks
            close = src.find("`" * e, i + e)
            j = n if close < 0 else close + e
            out.append(" ")                # raw text is not code: drop it
            i = j
            continue
        elif c == '"':
            q = True; out.append(c)
        elif src.startswith("//", i) and (i == 0 or src[i - 1] != ":"):
            while i < n and src[i] != "\n":
                i += 1
            continue
        elif src.startswith("/*", i):
            depth, i = 1, i + 2
            while i < n and depth:
                if src.startswith("/*", i):
                    depth += 1; i += 2
                elif src.startswith("*/", i):
                    depth -= 1; i += 2
                else:
                    i += 1
            continue
        else:
            out.append(c)
        i += 1
    return "".join(out)


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
            e = len(src) - i - len(src[i:].lstrip("`"))
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


PAR_RE = re.compile(r"(#set\s+par\([^)]*?leading:\s*)([0-9.]+)(em[^)]*?spacing:\s*)([0-9.]+)(em)")


def _read_par(text: str) -> tuple[float, float] | None:
    m = PAR_RE.search(text)
    if not m:
        return None
    return float(m.group(2)), float(m.group(4))


def _write_par(text: str, leading: float, spacing: float) -> str:
    return PAR_RE.sub(
        lambda m: "%s%.3f%s%.3f%s" % (m.group(1), leading, m.group(3), spacing,
                                      m.group(5)), text, count=1)


_SET_RE = re.compile(r"^#set\s+(par|text|list|enum)\(")
_LEAD_ARG = re.compile(r"(?:^|[,(\s])leading\s*:\s*([0-9]*\.?[0-9]+)\s*(em|pt)\b")
_SPACING_KEY = re.compile(r"(?:^|[,(\s])spacing\s*:\s*")
_SPACING_VAL = re.compile(r"([0-9]*\.?[0-9]+)\s*(em|pt)\b")


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
_SIZE_ARG = re.compile(r"(?:^|[,(\s])size\s*:\s*([0-9]*\.?[0-9]+)\s*pt\b")


def _doc_leading(text: str) -> float | None:
    return _doc_par_list(text)[0]


def _doc_par_list(text: str) -> tuple[float | None, float | None]:
    return _doc_par_list_size(text)[:2]


def _doc_body_size(text: str) -> float | None:
    """The document's top-level body text size in pt (the last top-level `#set text(size: X pt)`
    before the body, same reader as the leading), None when there is none."""
    return _doc_par_list_size(text)[2]


def _doc_par_list_size(text: str) -> tuple[float | None, float | None, float | None]:
    """(leading, list spacing) in em: the document's effective paragraph leading in em, read from the LAST
    top-level (column 0, not inside a #let / #show body) `#set par(... leading:
    ...)` before the body, in any argument order; pt is converted with the last
    top-level `#set text(size: X pt)` (11pt when absent). None when there is none."""
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
