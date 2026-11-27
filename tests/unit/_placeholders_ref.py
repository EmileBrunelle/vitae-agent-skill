"""placeholders.py as it was before the LOG320 worst-case sweep, kept verbatim as the oracle of the equivalence tests
(tests/unit/test_placeholders_complexity.py): the sample-shape scan that retried the e-mail pattern from every
character of a run, and `check_placeholders` squashing every bracketed span once per placeholder found. Not imported by
the product."""
import re
from pathlib import Path

from vitae.core.context import VerifyContext
from vitae.core.level import Finding, Level
from vitae.verify.placeholders import (
    _ANY_SPAN,
    _ESCAPED_SPAN,
    _FALLBACK,
    _RETIRED_SAMPLES,
    _SAMPLES,
    _SPAN,
    TEMPLATES,
    _fold,
    _matcher,
    _squash,
    placeholders_from,
    strip_comments,
)


def placeholders_in_scanning(src: str) -> set[str]:
    src = strip_comments(src)
    found = {"[" + " ".join(m.group(1).split()) + "]" for rx in (_SPAN, _ESCAPED_SPAN) for m in rx.finditer(src)
             if re.search(r"[A-Za-z]", m.group(1)) and not any(r.fullmatch(m.group(1)) for r in _SAMPLES)}
    for rx in _SAMPLES:
        found.update(m.group(0).replace("\\", "") for m in rx.finditer(src))
    return found


def check_placeholders_squashing(ctx: VerifyContext, templates: Path = TEMPLATES) -> list[Finding]:
    flat = _fold(ctx.txt)
    known = placeholders_from(templates)
    if known:
        known = tuple(sorted({*known, *_RETIRED_SAMPLES}, key=lambda s: (-len(s), s)))
    out: list[Finding] = []
    if not known:
        known = _FALLBACK
        out.append((Level.WARN, "placeholder gate: no placeholder list read from the templates (templates/ not found or empty), "
                                "so it checked only the sample contact shapes — bracketed placeholders were not matched"))
    by_key = {_squash(p): p for p in reversed([p for p in known if _matcher(p).search(flat)])}
    hits = [p for k, p in by_key.items() if not any(j != k and k in j for j in by_key)]
    hits.sort(key=lambda p: (-len(p), p))
    if hits:
        shown = ", ".join(f'"{p}"' for p in hits[:6]) + (f" (+{len(hits) - 6} more)" if len(hits) > 6 else "")
        out.append((Level.FAIL, f"template placeholder left in the text: {shown} — replace it with the facts' value or remove it"))
    hit_keys = {_squash(p) for p in hits}
    others = [m.group(0) for m in _ANY_SPAN.finditer(" ".join(ctx.txt.split()))
              if re.search(r"[A-Za-z]", m.group(1)) and not any(k in _squash(m.group(0)) for k in hit_keys)]
    if others:
        shown = ", ".join(f'"{o}"' for o in others[:5]) + (f" (+{len(others) - 5} more)" if len(others) > 5 else "")
        out.append((Level.WARN, f"bracketed text in the extraction: {shown} — a placeholder left over, or intended?"))
    return out
