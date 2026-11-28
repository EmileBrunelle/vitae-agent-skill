"""Checks on what the CV DECLARES through lib.typ arguments: the summary section (`section(.., summary: true)`)
and an expected date (`entry(.., expected: true)`). They read digits only and no word of any language: what a
script cannot know (which section is the summary, which date is a plan) comes from the declaration.

A leaf under verify: no `import verify`.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from vitae.core.base import Mark
from vitae.verify.text import figures_in, years_in


def section_text(txt: str, titles: Sequence[str], index: int) -> str | None:
    """The extracted lines of section `index`: from its title line (case-insensitive, whole line) to the title
    line of the NEXT section. None when its title is not found as a line (letterspaced, or drawn as a graphic), and
    None when it is not the last section but the next section's title is not found as a line: its end is unknown,
    and skipping to a later title would take the unfound section for the summary."""
    def first(title: str, start: int) -> int | None:
        want = title.strip().casefold()
        return next((i for i in range(start, len(lines)) if lines[i].strip().casefold() == want), None)

    lines = txt.split("\n")
    begin = first(titles[index], 0)
    if begin is None:
        return None
    if index == len(titles) - 1:
        return "\n".join(lines[begin + 1:])
    end = first(titles[index + 1], begin + 1)          # the IMMEDIATELY next section, never a later one
    return None if end is None else "\n".join(lines[begin + 1:end])


def bullets_outside(section: str, bullets: Sequence[Sequence[str]]) -> list[str]:
    """The text of the bullets (each given as its lines) that are not inside `section`: a bullet whose first line
    is a line of the section's text belongs to it, and is not "another place" for the section's own figures."""
    inside = {" ".join(ln.split()) for ln in section.split("\n")}
    return [" ".join(b) for b in bullets if b and " ".join(b[0].split()) not in inside]


def check_summary_figures(summary: str, bullets: Sequence[str]) -> list[str]:
    """One message per figure of the summary text (years, month+year dates and phones excluded; "1.500" and
    "1,500" read alike; 40% is not 40 and 10-20 is one figure) that a bullet repeats: the summary states a claim once, the bullet is where it is proved."""
    in_bullets = [f for b in bullets for f in figures_in(b)]
    found: dict[str, None] = {}
    for f in figures_in(summary):
        if any(f.same(g) for g in in_bullets):
            found[f.token] = None
    return [f'summary figure "{t}" is repeated in a bullet — keep it in one place: state it in the summary '
            "OR prove it in the bullet, not both" for t in found]


def check_expected_past(heads: Sequence[Mark], today: date) -> list[str]:
    """One message per entry declared `expected` whose latest year is before today's year. Year level only: the
    same year is never reported (a month is not read), and a date text without a year is not judged."""
    out: list[str] = []
    for h in heads:
        if not h.get("expected"):
            continue
        years = years_in(h.get("dates", ""))
        if years and max(years) < today.year:
            out.append(f'entry "{h["text"]}" is declared expected but its date ({h.get("dates", "").strip()}) '
                       f"is already past ({today.year}) — update it, or drop expected: true once it is done")
    return out
