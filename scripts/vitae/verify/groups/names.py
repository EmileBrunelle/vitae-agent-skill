"""Duplicate-name gate: a section title reused as a skill row label."""
from __future__ import annotations

from collections.abc import Sequence

from vitae.core.base import Mark
from vitae.verify.groups.query import gnorm


def check_duplicate_names(secs: Sequence[Mark] | None, heads: Sequence[Mark] | None) -> list[str]:
    """FAIL messages: one name used both as a section title and as a row label
    (e.g. section LANGUAGES for spoken languages + skill label "Languages" for
    programming ones), compared case-insensitively. Two things with one name
    read as one list to a human and to an ATS. Compared on `gnorm` keys, so case and
    punctuation do not hide a clash."""
    titles: dict[str, str] = {}
    for s in secs or []:
        if gnorm(s.get("text", "")):
            titles.setdefault(gnorm(s["text"]), s["text"])
    return [f'"{h["text"].strip()}" is both a skill row label and the section title '
            f'"{titles[gnorm(h["text"])]}" — rename one (e.g. "Programming languages")'
            for h in heads or [] if h.get("kind") == "skill" and gnorm(h["text"]) in titles]
