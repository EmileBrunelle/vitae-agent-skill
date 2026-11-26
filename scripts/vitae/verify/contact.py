"""The contact-line gate: a header contact block must not wrap onto more rows than its template declares.

lib.typ's `nb` tags every contact item <vitae-contact> (page, x, y where it starts); a family that
designs several rows (a column, a two-line block) declares it with `contact-rows(n)` (<vitae-contact-rows>).
Rows are counted from the items' measured y, never from what the text says; a CV with no tagged item
is "not measured", never guessed.
"""
from __future__ import annotations

from vitae.core.level import Finding, Level
from vitae.verify.groups.query import _is_num, _typst_values

ROW_GAP = 4.0   # pt: items of one row differ by an icon baseline (~1.5pt); the closest designed rows are ~10pt apart


def _item_ys(values: list[object]) -> dict[int, list[float]]:
    """The y of every tagged contact item, per page (a value that is not a placed item is dropped)."""
    by_page: dict[int, list[float]] = {}
    for v in values:
        if not isinstance(v, dict):
            continue
        page, y = v.get("page"), v.get("y")
        if isinstance(page, int) and _is_num(y) and isinstance(y, (int, float)):
            by_page.setdefault(page, []).append(float(y))
    return by_page


def count_rows(ys: list[float], gap: float = ROW_GAP) -> int:
    """Rows in `ys`: a new row starts where the sorted y jumps by more than `gap`."""
    ordered = sorted(ys)
    return sum(1 for a, b in zip(ordered, ordered[1:]) if b - a > gap) + 1 if ordered else 0


def _declared_rows(values: list[object] | None) -> int:
    """The rows the family declares (the largest `contact-rows`); ONE when it declares none."""
    declared = [v for v in values or [] if isinstance(v, int) and not isinstance(v, bool) and v >= 1]
    return max(declared, default=1)


def check_contact_line(typ: str, root: str | None) -> list[Finding]:
    """FAIL when the tagged contact items take more rows than declared (an item wrapped onto a new line)."""
    items = _typst_values(typ, "<vitae-contact>", root)
    if items is None:
        return [(Level.WARN, "contact line not measured: typst query unavailable")]
    by_page = _item_ys(items)
    if not by_page:
        return [(Level.INFO, "contact line not measured: no contact item built with lib nb()")]
    declared = _declared_rows(_typst_values(typ, "<vitae-contact-rows>", root))
    page, ys = next(iter(sorted(by_page.items())))
    rows = count_rows(ys)
    if rows > declared:
        return [(Level.FAIL, f"contact line wraps: {len(ys)} contact items take {rows} rows on page {page}, "
                             f"the layout declares {declared} — shorten it (drop a channel, shorter labels or URLs) "
                             "or give it a full row; if the design intends these rows, declare "
                             f"`#contact-rows({rows})` before the first contact item, then re-run the gate")]
    return [(Level.OK, f"contact line: {len(ys)} items on {rows} row(s), declared {declared}")]
