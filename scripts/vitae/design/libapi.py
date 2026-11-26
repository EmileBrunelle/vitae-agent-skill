"""Public API of a lib.typ, read from the file itself (no list to keep in sync).

lib.typ marks no function as internal, so everything an agent could need is listed: every
top-level `#let` of the file, functions with their parameters, values by name."""
from __future__ import annotations

import re
from pathlib import Path

_DEF = re.compile(r"^#let ([A-Za-z][\w-]*)(\()?", re.M)
_OPEN, _CLOSE = "([{", ")]}"


def _params(src: str, start: int) -> list[str] | None:
    """Parameter texts of the definition whose '(' sits just before `start`; None if unbalanced.

    Strings (with `\\"` escapes) and `//`, `/* */` comments are skipped; quotes inside a
    `[...]` content block are plain text."""
    stack, cur, out = ["("], "", []
    i, n = start, len(src)
    while i < n:
        ch = src[i]
        if ch == '"' and stack[-1] != "[":
            j = i + 1
            while j < n and src[j] != '"':
                j += 2 if src[j] == "\\" else 1
            cur += src[i:j + 1]
            i = j + 1
            continue
        if src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        i += 1
        if ch in _OPEN:
            stack.append(ch)
            cur += ch
        elif ch in _CLOSE:
            stack.pop()
            if not stack:
                out.append(cur)
                return [p.strip() for p in out if p.strip()]
            cur += ch
        elif ch == "," and len(stack) == 1:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    return None


def signatures(lib_src: str, failed: list[str] | None = None) -> dict[str, str]:
    """name -> `name(positional; named)` for a top-level function, bare `name` for a value.

    A parameter list that does not balance degrades to `name(?)` and its name goes to `failed`."""
    sigs: dict[str, str] = {}
    for m in _DEF.finditer(lib_src):
        name = m.group(1)
        if not m.group(2):
            if re.match(r"\s*=", lib_src[m.end():]):
                sigs[name] = name
            continue
        params = _params(lib_src, m.end())
        if params is None:
            sigs[name] = name + "(?)"
            if failed is not None:
                failed.append(name)
            continue
        pos = [p for p in params if ":" not in p.split("(")[0].split("[")[0]]
        named = [p.split(":")[0].strip() for p in params if p not in pos]
        sigs[name] = "%s(%s%s)" % (name, ", ".join(pos),
                                   ("; " + ", ".join(named)) if named else "")
    return sigs


def public_signatures(lib_path: Path) -> list[str]:
    """Signatures of every top-level `#let` of `lib_path`, in file order; never raises on syntax."""
    return list(signatures(lib_path.read_text(encoding="utf-8")).values())


def api_line(lib_path: Path) -> str:
    """The `--init` line listing the API of `lib_path`, plus a WARN tail for unparsed signatures."""
    failed: list[str] = []
    sigs = signatures(lib_path.read_text(encoding="utf-8"), failed)
    line = "  ".join(sigs.values())
    if failed:
        line += "\nWARN: parameters of %s not parsed: grep -n '^#let NAME' %s" % (
            ", ".join(failed), lib_path)
    return line
