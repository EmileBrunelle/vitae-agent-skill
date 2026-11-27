"""Placeholder gate: a sample string of the shipped templates left in the final CV's text.

FAIL on a literal placeholder of the templates (the list is read off templates/**/*.typ, so it follows
them: bracketed spans like `[Mon YYYY]`, the sample email / phone / handles / name). WARN on any other
`[...]` span with a letter: it can be legitimate, the agent decides. No wording heuristic, no language.
"""
from __future__ import annotations

import functools
import re
from pathlib import Path

from vitae.core.context import VerifyContext
from vitae.core.level import Finding, Level
from vitae.core.typst_source import strip_comments_keep_urls

TEMPLATES = Path(__file__).resolve().parents[3] / "templates"


# A bracketed span as written in a template: no nested bracket, no Typst code (#, \, ^), a letter in it; it may
# wrap over lines. A content-block argument written bare (`#f(x)[Words]`) is collected too: its brackets do not
# render, which the sync test (every derived entry must appear in the rendered text) reports.
_SPAN = re.compile(r"\[([^\[\]#\\^]{3,})\]")
# The same span with its brackets escaped, `\[City, Region\]`: how a content-block argument is written so that the
# brackets render (`#nb(mk.pin)[\[City, Region\]]`).
_ESCAPED_SPAN = re.compile(r"\\\[([^\[\]#\\^]{3,})\\\]")
# The sample contact data, by shape (reserved example domain, the fictional 555-01xx phone block).
_SAMPLES = (
    re.compile(r"[\w.+-]+\\?@example\.\w+"),
    re.compile(r"\(555\) 555-01\d\d"),
    re.compile(r"(?:linkedin\.com/in|github\.com)/handle\b"),
    re.compile(r"\bFirstname Lastname\b"),
)
# `_SAMPLES[0]` as a finditer would run it tries every start inside a long run of address characters and rescans the
# run each time (a text with no `@`: quadratic). A run is tried once, from its first character; the one other start the
# old scan had, right after a match inside the same run (`a@example.com.b@example.org`), is tried first.
_EMAIL_RUN = re.compile(r"(?<![\w.+-])" + _SAMPLES[0].pattern)


def _email_samples(src: str) -> list[re.Match[str]]:
    """The matches of `_SAMPLES[0].finditer(src)`, in linear time."""
    out: list[re.Match[str]] = []
    pos = 0
    while True:
        m = (_SAMPLES[0].match(src, pos) if out else None) or _EMAIL_RUN.search(src, pos)
        if m is None:
            return out
        out.append(m)
        pos = m.end()


_ANY_SPAN = re.compile(r"\[([^\[\]]{3,80})\]")   # capped: a stray `[` far from a `]` is not one span


# Samples the templates no longer carry (a fixed handle invents a profile for a candidate who has none) but an
# agent may still recopy from memory or an older folder: they stay a FAIL.
_RETIRED_SAMPLES = ("linkedin.com/in/handle", "github.com/handle")

_SCRATCH_PREFIXES = ("_raw", "_drawn")

_FOLD = str.maketrans({"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"', "*": None, "_": None})
_QUOTES_CASE = {k: v for k, v in _FOLD.items() if v is not None}   # the CV-text side: quotes and case only
# Used only when the templates yield no list (folder missing): the sample contact data, as shipped.
_FALLBACK = ("me@example.com", "(555) 555-0100", "linkedin.com/in/handle", "github.com/handle", "Firstname Lastname")


def _squash(s: str) -> str:
    """Compare form of a template string: no whitespace, no Typst inline markup (`*`, `_`), straight quotes,
    casefolded (a template span renders without its `*bold*` markup, with typographic quotes, upper-cased by a
    heading)."""
    return re.sub(r"\s+", "", s.translate(_FOLD)).casefold()


def _fold(s: str) -> str:
    """The CV text's form: straight quotes and case only. Its `*` and `_` are real characters (`github.com/handle_`
    is another handle than `github.com/handle`), so they are kept."""
    return s.translate(_QUOTES_CASE).casefold()


@functools.lru_cache(maxsize=512)
def _matcher(p: str) -> re.Pattern[str]:
    """Where `p` occurs in folded text, whitespace between its characters free (a wrapped line). A bracketed span
    is delimited by its own brackets; a bare sample (handle, email, name) must not continue into a longer word,
    handle or domain: `github.com/handle` is not in `github.com/handlebars-lang`, nor `Firstname Lastname` in
    `Firstname Lastnameson`."""
    body = r"\s*".join(re.escape(c) for c in _squash(p))
    if p.startswith("["):
        return re.compile(body)
    # An address may follow `www.` or `://` (`https://www.github.com/handle`); an email may not follow a dot.
    before = r"(?<![\w.+-])" if "/" not in p else r"(?:(?<![\w.+-])|(?<=://)|(?<=(?<![\w.+-])www\.))"
    return re.compile(rf"{before}{body}(?![\w-]|\.\w)")


def placeholders_in(src: str) -> set[str]:
    """The placeholder strings one template source renders: bracketed spans (written bare in a string or in markup,
    or with escaped brackets in a content-block argument) and the bare sample contact shapes."""
    src = strip_comments_keep_urls(src)
    found = {"[" + " ".join(m.group(1).split()) + "]" for rx in (_SPAN, _ESCAPED_SPAN) for m in rx.finditer(src)
             if re.search(r"[A-Za-z]", m.group(1)) and not any(r.fullmatch(m.group(1)) for r in _SAMPLES)}
    for rx in _SAMPLES[1:]:
        found.update(m.group(0).replace("\\", "") for m in rx.finditer(src))
    found.update(m.group(0).replace("\\", "") for m in _email_samples(src))
    return found


@functools.lru_cache(maxsize=4)
def placeholders_from(templates: Path) -> tuple[str, ...]:
    """Every placeholder string the templates render, longest first (so the report names the specific one)."""
    found: set[str] = set()
    for f in sorted(templates.rglob("*.typ")):
        if f.name.startswith(_SCRATCH_PREFIXES):      # a test's scratch copy of a template, never a template
            continue
        found |= placeholders_in(f.read_text(encoding="utf-8"))
    return tuple(sorted(found, key=lambda s: (-len(s), s)))


def _covered(squashed: str, keys: set[str]) -> bool:
    """True when one of the hit keys is inside the squashed span (the span is squashed once, not once per key)."""
    return any(k in squashed for k in keys)


def check_placeholders(ctx: VerifyContext, templates: Path = TEMPLATES) -> list[Finding]:
    flat = _fold(ctx.txt)
    known = placeholders_from(templates)
    if known:
        known = tuple(sorted({*known, *_RETIRED_SAMPLES}, key=lambda s: (-len(s), s)))
    out: list[Finding] = []
    if not known:
        known = _FALLBACK
        out.append((Level.WARN, "placeholder gate: no placeholder list read from the templates (templates/ not found or empty), "
                                "so it checked only the sample contact shapes — bracketed placeholders were not matched"))
    # One hit per squashed form (`[item]` and `[ITEM]` are the same placeholder), then
    # `[linkedin.com/in/handle]` also contains the bare sample: report only the outer hit.
    by_key = {_squash(p): p for p in reversed([p for p in known if _matcher(p).search(flat)])}
    hits = [p for k, p in by_key.items() if not any(j != k and k in j for j in by_key)]
    hits.sort(key=lambda p: (-len(p), p))     # the most specific first, as `known` is
    if hits:
        shown = ", ".join(f'"{p}"' for p in hits[:6]) + (f" (+{len(hits) - 6} more)" if len(hits) > 6 else "")
        out.append((Level.FAIL, f"template placeholder left in the text: {shown} — replace it with the facts' value or remove it"))
    hit_keys = {_squash(p) for p in hits}
    spans = [m for m in _ANY_SPAN.finditer(" ".join(ctx.txt.split())) if re.search(r"[A-Za-z]", m.group(1))]
    others = [m.group(0) for m in spans if not _covered(_squash(m.group(0)), hit_keys)]
    if others:
        shown = ", ".join(f'"{o}"' for o in others[:5]) + (f" (+{len(others) - 5} more)" if len(others) > 5 else "")
        out.append((Level.WARN, f"bracketed text in the extraction: {shown} — a placeholder left over, or intended?"))
    return out
