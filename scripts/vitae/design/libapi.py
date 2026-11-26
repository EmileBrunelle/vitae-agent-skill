"""Public API of templates/lib.typ, read from the file itself (no list to keep in sync).

A function is public when a worked file (templates/resume.typ or a family's .typ) calls it;
the rest of lib.typ is internal plumbing the CV never touches."""
from __future__ import annotations

import re
from pathlib import Path

_DEF = re.compile(r"^#let ([A-Za-z][\w-]*)\(", re.M)
_OPEN, _CLOSE = "([{", ")]}"


def _params(src: str, start: int) -> list[str] | None:
    """Parameter texts of the definition whose '(' sits just before `start`; None if unbalanced."""
    depth, quote, cur, out = 1, False, "", []
    for ch in src[start:]:
        if quote:
            cur += ch
            quote = ch != '"'
            continue
        if ch == '"':
            quote, cur = True, cur + ch
        elif ch in _OPEN:
            depth, cur = depth + 1, cur + ch
        elif ch in _CLOSE:
            depth -= 1
            if depth == 0:
                out.append(cur)
                return [p.strip() for p in out if p.strip()]
            cur += ch
        elif ch == "," and depth == 1:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    return None


def signatures(lib_src: str) -> dict[str, str]:
    """name -> `name(positional; named)` for every top-level `#let name(...)` of lib.typ."""
    sigs: dict[str, str] = {}
    for m in _DEF.finditer(lib_src):
        params = _params(lib_src, m.end())
        if params is None:
            raise SystemExit("lib.typ: unbalanced parameter list for %s" % m.group(1))
        pos = [p for p in params if ":" not in p.split("(")[0].split("[")[0]]
        named = [p.split(":")[0].strip() for p in params if p not in pos]
        sigs[m.group(1)] = "%s(%s%s)" % (m.group(1), ", ".join(pos),
                                         ("; " + ", ".join(named)) if named else "")
    return sigs


def public_signatures(templates: Path) -> list[str]:
    """Signatures of the lib.typ functions that the worked files call, in lib.typ order."""
    sigs = signatures((templates / "lib.typ").read_text(encoding="utf-8"))
    used = "\n".join(p.read_text(encoding="utf-8")
                     for p in [templates / "resume.typ", *sorted(templates.glob("families/*/*.typ"))])
    return [s for n, s in sigs.items() if re.search(r"(?<![\w-])%s\(" % re.escape(n), used)]
