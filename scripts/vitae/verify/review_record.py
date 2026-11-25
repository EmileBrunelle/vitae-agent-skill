"""Review-record gate: delivery needs the step-7 record `review.md` next to the CV, newer than its last edit.

Objective checks only (file exists and is fresh, declared runtime, core personas named, a layout line, every finding
resolved as applied or rejected with a reason); whether the review was any good is not judged. The format is
documented in references/steps/7-review.md. Run by `cv._check_cv` after every mechanical gate passed.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from vitae.core.level import Finding, Level

RECORD_NAME = "review.md"
STEP_7 = Path(__file__).resolve().parents[3] / "references" / "steps" / "7-review.md"

_LAYOUT = re.compile(r"(?:(?:subagent|other-model)\s+(?!(?:skipped|none|n/a|na|not run|no|-)\s*$)\S.*|self|user|not run \(no redesign\))\s*", re.I)
# core persona -> (stem a normalized name must start with, as whole words; words allowed after it, None = any).
# reviews.md: "Recruiter, 30-second scan", "Hiring manager of the field", "ATS / parsing expert". A name containing
# `segment` ("nurse recruiter segment", "fintech hiring manager segment") is a market-segment persona, never a core one
_INDUSTRY = {
    "recruiter": ("recruiter", None),
    "hiring manager": ("hiring manager", None),
    "ATS": ("ats", {"expert", "parsing", "check", "reviewer", "fact", "diff"}),
}
_ACADEMIC = {
    "committee member": ("committee member", None),
    "extraction/counts auditor": ("extraction", None),
    "department head": ("department head", None),
}
_FACT_DIFF = ("fact diff", {"reviewer", "check", "ats"})
_ATS_FACT_DIFF = "ats fact diff"
_RESOLVED = re.compile(r"(?:→|->)\s*(?:applied(?:\s*(?!→|->)[(\[:;,.—–-](?:(?!→|->).)*)?\s*|rejected\s*:\s*(\S(?:(?!→|->).)*))$", re.I)
_BULLET = re.compile(r"(\s*)(?:[-*]|\d+[.)])\s+(\S.*)")


def _field(lines: list[str], key: str) -> str | None:
    """The value of the first `key: value` line before `## Findings` (case-insensitive key), None when absent."""
    for ln in lines:
        if ln.lstrip().startswith("##"):
            break
        m = re.match(rf"\s*{key}\s*:\s*(.*?)\s*$", ln, re.I)
        if m:
            return m.group(1)
    return None


def _split_personas(value: str) -> list[str]:
    """Comma-separated names, normalized: lower case, parentheses dropped, hyphens, underscores and slashes read as
    spaces, trimmed."""
    return [" ".join(re.sub(r"[-_/+]+", " ", re.sub(r"[()]", " ", p.lower())).split()) for p in value.split(",") if p.strip()]


def _is_core(name: str, stem: str, after: set[str] | None) -> bool:
    """A persona name is the core persona when it starts with `stem` as whole words, is no segment persona, and (when
    `after` is given) carries no other words after the stem."""
    if "segment" in name or not (name == stem or name.startswith(stem + " ")):
        return False
    return after is None or set(name[len(stem):].split()) <= after


def _has(personas: list[str], core: tuple[str, set[str] | None]) -> bool:
    return any(_is_core(p, *core) for p in personas)


def _findings_block(lines: list[str]) -> list[str] | None:
    """The lines under `## Findings` up to the next `## ` heading; None when the heading is absent."""
    for i, ln in enumerate(lines):
        if re.match(r"##\s+findings\b", ln.strip(), re.I):
            out: list[str] = []
            for nxt in lines[i + 1:]:
                if nxt.startswith("## "):
                    break
                out.append(nxt)
            return out
    return None


def _findings(block: list[str]) -> list[str]:
    """The findings in a block: one string per bullet (`-`, `*`, `1.`, `1)`) that is not nested under another, its
    indented continuation lines joined on. A bullet nested deeper than the finding above it belongs to that finding;
    an indented bullet with no finding above it (after prose or at the block start) is a finding of its own."""
    items: list[list[str]] = []
    cur: list[str] | None = None
    cur_indent = 0
    sub = False
    for ln in block:
        m = _BULLET.fullmatch(ln)
        indent = len(m.group(1).expandtabs()) if m else 0
        if m and (cur is None or indent <= cur_indent):
            cur, cur_indent, sub = [m.group(2).strip()], indent, False
            items.append(cur)
        elif m:
            sub = True
        elif ln.strip() and ln[0] in " \t":
            if cur is not None and not sub:
                cur.append(ln.strip())
        elif ln.strip():
            cur = None
    return [" ".join(i) for i in items]


def check_review_record(typ: str, sources: tuple[str, ...] | list[str] = (), panel: str = "industry") -> list[Finding]:
    """Findings for `review.md` beside `typ`: FAIL lines when the record does not make step 7 verifiable, else an
    INFO summary (plus a WARN when it lists no findings). `sources` are the other files the CV is built from (the
    academic data.toml): the record must be newer than each. `panel` is `industry` or `academic` (reviews.md)."""
    cv_name = os.path.basename(typ)
    path = os.path.join(os.path.dirname(os.path.abspath(typ)), RECORD_NAME)
    where = os.path.join(os.path.dirname(typ) or ".", RECORD_NAME)
    if not os.path.isfile(path):
        return [(Level.FAIL, f"review record missing: step 7 is next — read {STEP_7}, run it, write {where}")]
    for src in (typ, *sources):
        if os.path.isfile(src) and os.path.getmtime(path) < os.path.getmtime(src):
            return [(Level.FAIL, f"review record older than {os.path.basename(src)}: update {RECORD_NAME} after the last edit")]
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as e:
        return [(Level.FAIL, f"review record unreadable: {where} ({e})")]

    fails: list[str] = []
    runtime = (_field(lines, "runtime") or "").lower()
    if runtime not in ("sub-agents", "none"):
        fails.append(f"review record: `runtime:` must be `sub-agents` or `none` (got {runtime or 'nothing'!r}) — see {STEP_7}")
    personas = _split_personas(_field(lines, "personas") or "")
    academic = panel == "academic"
    core = _ACADEMIC if academic else _INDUSTRY
    if runtime == "sub-agents":
        missing = [name for name, c in core.items() if not _has(personas, c)]
    elif runtime == "none" and academic:
        missing = [name for name in ("extraction/counts auditor", "department head") if not _has(personas, core[name])]
    elif runtime == "none":
        has_ats = _has(personas, core["ATS"]) or _has(personas, _FACT_DIFF) or _ATS_FACT_DIFF in personas
        missing = ([] if has_ats else ["ATS (or fact-diff)"]) + ([] if _has(personas, core["hiring manager"]) else ["hiring manager"])
    else:
        missing = []
    if missing:
        fails.append(f"review record: `personas:` lacks {', '.join(missing)}")
    covered = [c.strip() for c in (_field(lines, "cv") or "").split(",") if c.strip()]
    if cv_name not in covered:
        fails.append(f"review record: `cv:` must list {cv_name} (one record per CV set, comma-separated basenames; "
                     f"got {', '.join(covered) or 'nothing'})")
    layout = _field(lines, "layout") or ""
    if not _LAYOUT.fullmatch(layout):
        fails.append("review record: `layout:` must be one of subagent <model> | self | other-model <model> | user | "
                     f"not run (no redesign) (got {layout or 'nothing'!r})")
    elif runtime == "sub-agents" and layout.lower().startswith(("self", "not run")):
        fails.append("review record: `layout:` with `runtime: sub-agents` must be subagent <model> | other-model <model> | "
                     f"user — the layout reviewer always runs on the full path (got {layout!r})")

    block = _findings_block(lines)
    applied = rejected = 0
    if block is None:
        fails.append("review record: no `## Findings` section")
    else:
        found = _findings(block)
        if not found and any(ln.strip() for ln in block):
            fails.append("review record: the Findings section has text but no parseable finding — one bullet per finding "
                         "(`-`, `*` or `1.`), each ending `→ applied` or `→ rejected: <reason>`")
        for text in found:
            res = _RESOLVED.search(text)
            if res:
                rejected += res.group(1) is not None
                applied += res.group(1) is None
            else:
                fails.append(f"review record: finding not resolved (end it with `→ applied` or `→ rejected: <reason>`): {text[:100]}")
    if fails:
        return [(Level.FAIL, f) for f in fails]
    out: list[Finding] = []
    if applied + rejected == 0:
        out.append((Level.WARN, "review record lists no findings"))
    out.append((Level.INFO, f"review record: runtime {runtime}, {len(personas)} personas, "
                            f"{applied} finding(s) applied, {rejected} rejected"))
    return out
