"""Typst comment strippers, one module for the three semantics the checks need.

They differ on purpose (each is pinned by the regex it replaced or by the callers' tests), so they are three
functions named for what they strip, not one function with flags:

| function                     | block `/* */`        | line `//`                                    | strings, raw spans |
|------------------------------|----------------------|----------------------------------------------|--------------------|
| `strip_block_comments`       | not nested           | kept                                         | not looked at      |
| `strip_comments_keep_urls`   | not nested           | stripped, except after a word char or `:`    | not looked at      |
| `strip_typst_comments`       | nested               | stripped, except right after `:`             | respected          |

Measured on tests/fixtures/*.typ and templates/**/*.typ, `strip_comments_keep_urls` and `strip_typst_comments` give
byte-identical output; they still differ on text with an unclosed or nested block, `a//b`, or `//` inside a string
or raw span, and their callers' tests pin those cases, so they stay separate. All three are linear in the text.

Pure functions of one string; imports nothing from this package.
"""
from __future__ import annotations


def strip_block_comments(src: str) -> str:
    """`src` without its non-nested `/* ... */` blocks; an unclosed `/*` stays as text, `//` lines are untouched.
    Same result as `re.sub(r"/\\*.*?\\*/", "", src, flags=re.S)`, which rescans to the end of the text from every
    unclosed `/*` (11 s on 100 000 characters of them); here one failed search for `*/` ends the scan, no later
    block can close."""
    out: list[str] = []
    i = 0
    while (start := src.find("/*", i)) >= 0:
        end = src.find("*/", start + 2)
        if end < 0:
            break
        out.append(src[i:start])
        i = end + 2
    out.append(src[i:])
    return "".join(out)


def strip_comments_keep_urls(src: str) -> str:
    """`src` without its Typst comments, read as plain text (strings and raw spans are not looked at):
    `/* ... */` (not nested; an unclosed `/*` is plain text) and `// ...` to the end of the line, but not a `//`
    right after a word character or `:` (a URL, `a//b`). One left-to-right pass, linear: the regex it replaced
    (`/\\*.*?\\*/|(?<![:\\w])//[^\\n]*`) rescanned to the end of the text from every unclosed `/*`, 13.9 s on
    100 000 characters of them."""
    out: list[str] = []
    n = len(src)
    last = i = 0
    closes = True            # False once a search for `*/` failed: no later `/*` can close either
    while (i := src.find("/", i)) >= 0:
        if closes and src.startswith("/*", i):
            end = src.find("*/", i + 2)
            if end < 0:
                closes = False
            else:
                out.append(src[last:i])
                last = i = end + 2
                continue
        if src.startswith("//", i) and not (i and (src[i - 1] == ":" or src[i - 1].isalnum() or src[i - 1] == "_")):
            end = src.find("\n", i)
            out.append(src[last:i])
            last = i = n if end < 0 else end
            continue
        i += 1
    out.append(src[last:])
    return "".join(out)


def _end_of_nested_block(src: str, i: int) -> int:
    """Index after the `/* ... */` that opens at `i`, nested blocks included; the text length when unclosed."""
    n = len(src)
    depth, i = 1, i + 2
    while i < n and depth:
        if src.startswith("/*", i):
            depth += 1; i += 2
        elif src.startswith("*/", i):
            depth -= 1; i += 2
        else:
            i += 1
    return i


def _end_of_raw_span(src: str, i: int) -> int:
    """Index after the backtick raw span that opens at `i` (closed by a run of the same length); the text length
    when unclosed."""
    n = len(src)
    e = 1
    while i + e < n and src[i + e] == "`":      # opening run of backticks
        e += 1
    close = src.find("`" * e, i + e)
    return n if close < 0 else close + e


def _string_step(src: str, i: int, out: list[str]) -> tuple[bool, int]:
    """Copy the character at `i` (inside a double-quoted string, not a newline) to `out`, with its escaped partner
    when it is a backslash not followed by a newline; (the string is still open, the next index)."""
    c = src[i]
    out.append(c)
    if c == "\\" and i + 1 < len(src) and src[i + 1] != "\n":
        out.append(src[i + 1])
        return True, i + 2
    return c != '"', i + 1


def strip_typst_comments(src: str) -> str:
    """`src` without `//` line comments and (nested) `/* */` blocks, read as Typst. Double-quoted strings are
    respected but never span a newline (a stray 6" in markup must not swallow the rest of the file); a backtick raw
    span is dropped whole (replaced by one space: raw text is not code). A `//` right after `:` is a URL scheme
    (`https://`), not a comment. An unclosed `/*` swallows the rest of the text."""
    out, i, n, q = [], 0, len(src), False
    while i < n:
        c = src[i]
        if c == "\n":
            q = False
            out.append(c)
        elif q:
            q, i = _string_step(src, i, out)
            continue
        elif c == "\\" and i + 1 < n and src[i + 1] != "\n":
            out.append(c + src[i + 1]); i += 1          # escaped char (\//, \", \`)
        elif c == "`":
            out.append(" ")
            i = _end_of_raw_span(src, i)
            continue
        elif c == '"':
            q = True; out.append(c)
        elif src.startswith("//", i) and (i == 0 or src[i - 1] != ":"):
            end = src.find("\n", i)
            i = n if end < 0 else end
            continue
        elif src.startswith("/*", i):
            i = _end_of_nested_block(src, i)
            continue
        else:
            out.append(c)
        i += 1
    return "".join(out)
