"""Grouping, date-adjacency, duplicate-name gates and the `typst query` mark reader they share.

No `import verify`. Each gate lives in its own module; this package re-exports the names its importers use.
"""
from vitae.verify.groups.dates import ENTRY_MARKS, _entry_records, _first_word, _yc, check_date_adjacency
from vitae.verify.groups.ink import _page_ink_gap
from vitae.verify.groups.names import check_duplicate_names
from vitae.verify.groups.proximity import (
    PROX_FAIL,
    PROX_HIER,
    PROX_WARN,
    _hier_advice,
    _KMark,
    _org_on_one_line,
    check_group_proximity,
    measure_groups,
)
from vitae.verify.groups.query import (
    _find_run,
    _gnorm,
    _line_index,
    _lines,
    _typst_query,
    _typst_query_checked,
    _typst_values,
)

__all__ = [
    "ENTRY_MARKS", "PROX_FAIL", "PROX_HIER", "PROX_WARN", "_KMark", "_entry_records", "_find_run", "_first_word",
    "_gnorm", "_hier_advice", "_line_index", "_lines", "_org_on_one_line", "_page_ink_gap", "_typst_query",
    "_typst_query_checked", "_typst_values", "_yc", "check_date_adjacency", "check_duplicate_names", "check_group_proximity",
    "measure_groups",
]
