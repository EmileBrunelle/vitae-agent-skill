"""The typst.py code replaced by the LOG320 worst-case sweep, kept verbatim as the oracle of the equivalence tests
(tests/unit/test_typst_complexity.py): the regexes with the quadratic number pattern, `PAR_RE` with its retried lazy
scans, `_par_rule_spans` rescanning to the end of the text from every unclosed `#set par(`, and the backtick branch of
`_mask_non_markup` copying the rest of the text per backtick. Not imported by the product."""
import re

_LEAD_ARG = re.compile(r"(?:^|[,(\s])leading\s*:\s*([0-9]*\.?[0-9]+)\s*(em|pt)\b")
_SPACING_VAL = re.compile(r"([0-9]*\.?[0-9]+)\s*(em|pt)\b")
_SIZE_ARG = re.compile(r"(?:^|[,(\s])size\s*:\s*([0-9]*\.?[0-9]+)\s*pt\b")


PAR_RE = re.compile(r"(#set\s+par\([^)]*?leading:\s*)([0-9.]+)(em[^)]*?spacing:\s*)([0-9.]+)(em)")


def par_rule_spans_quadratic(masked: str) -> list[tuple[int, int]]:
    """(start, end) of every column-0 `#set par(... leading: ...)` rule in a _mask_non_markup'd text."""
    spans = []
    for m in re.finditer(r"^#set\s+par\(", masked, re.MULTILINE):
        k, d = m.end(), 1
        while k < len(masked) and d:
            d += (masked[k] == "(") - (masked[k] == ")")
            k += 1
        if _LEAD_ARG.search(masked[m.end():k - 1]):
            spans.append((m.start(), k))
    return spans


def mask_non_markup_quadratic(src: str) -> str:
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


_RHYTHM_RE = re.compile(r"(#let rhythm = )([0-9]*\.?[0-9]+)[ \t\r]*;?[ \t\r]*")
