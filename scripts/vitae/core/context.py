"""What every extraction and layout gate reads, computed once per run.

A leaf like level.py: it imports no sibling module of vitae/verify/, so the registry and the gates can share it.
"""
from __future__ import annotations

from dataclasses import dataclass

from vitae.core.base import BulletLayout, DetailRow, Mark


@dataclass(frozen=True)
class VerifyContext:
    """The inputs of one gate run. `marks`, `heads` and `secs` are lib.typ's `typst query` results (None: the
    query was unavailable or failed); `detail` is the caller's list that the proximity gate fills for
    `--gates`; `backend` is the PDF text extractor ("pypdf" downgrades the extraction gates to WARN)."""
    typ: str
    pdf: str
    txt: str
    src: str
    backend: str | None
    root: str | None = None
    facts: str | None = None
    can_query: bool = True
    marks: list[Mark] | None = None
    heads: list[Mark] | None = None
    secs: list[Mark] | None = None   # the <vitae-sec> section titles, same query (the lib gives them no kind)
    detail: list[DetailRow] | None = None
    contact_items: list[object] | None = None   # <vitae-contact> values, read with the marks (None: query unavailable)
    contact_rows: list[object] | None = None    # <vitae-contact-rows> values, same query
    mark_notes: tuple[str, ...] = ()   # what the marks query dropped (malformed lib marks): a WARN, never silent
    bullets: BulletLayout | None = None   # the words and the located bullets (None: no marks, or no word positions)
