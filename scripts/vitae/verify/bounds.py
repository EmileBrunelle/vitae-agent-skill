"""vitae.verify.bounds: the declared size beyond which the position gates refuse a page instead of measuring it.

The runts, rhythm and proximity gates look up, for each mark of a page, the words around it: O(marks x words) on one page
in the worst case (a column whose words reach the page edge is read to its end for every bullet, and every distinct left
edge re-clusters the page). Their cost is flat for a real CV (a few dozen marks over a few hundred words) and bounded by
this limit otherwise: about a second at the limit, measured on pages of contiguous words. A page past it is not a
résumé page (two million word-mark pairs is 20 times the densest academic page seen), so the gate says so instead
of running long."""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence

from vitae.core.base import Mark

MAX_PAGE_WORK = 2_000_000      # marks on a page x words on it


def too_dense(gate: str, pages: Sequence[Sequence[object]], marks: Iterable[Mark]) -> str | None:
    """The FAIL message for the first page (lowest number) whose marks x words exceed MAX_PAGE_WORK, else None."""
    per_page = Counter(m["page"] for m in marks if "page" in m)
    for page in sorted(per_page):
        if 1 <= page <= len(pages):
            words, n = len(pages[page - 1]), per_page[page]
            if n * words > MAX_PAGE_WORK:
                return (f"{gate} not measured: page {page} has {n} marks over {words} words ({n * words:,} pairs, "
                        f"limit {MAX_PAGE_WORK:,}) — a résumé page is a few hundred words; a page this dense is "
                        "unreadable, cut its text (the limit keeps the gate's time bounded, see verify/bounds.py)")
    return None
