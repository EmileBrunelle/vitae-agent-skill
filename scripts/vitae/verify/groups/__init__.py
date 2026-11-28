"""Grouping, date-adjacency, duplicate-name gates and the `typst query` mark reader they share.

No `import verify`. Each gate lives in its own module; this package re-exports the names its importers use.
"""
from vitae.verify.groups.dates import ENTRY_MARKS, check_date_adjacency, entry_records, first_word, y_center
from vitae.verify.groups.ink import page_ink_gap
from vitae.verify.groups.names import check_duplicate_names
from vitae.verify.groups.proximity import (
    PROX_FAIL,
    PROX_HIER,
    PROX_WARN,
    KMark,
    check_group_proximity,
    hier_advice,
    measure_groups,
    org_on_one_line,
)
from vitae.verify.groups.query import (
    HEADING_SELECTOR,
    ContactValues,
    gnorm,
    typst_marks_and_contact,
    typst_query,
    typst_query_checked,
    typst_values,
)

__all__ = [
    "ENTRY_MARKS",
    "HEADING_SELECTOR",
    "PROX_FAIL",
    "PROX_HIER",
    "PROX_WARN",
    "ContactValues",
    "KMark",
    "check_date_adjacency",
    "check_duplicate_names",
    "check_group_proximity",
    "entry_records",
    "first_word",
    "gnorm",
    "hier_advice",
    "measure_groups",
    "org_on_one_line",
    "page_ink_gap",
    "typst_marks_and_contact",
    "typst_query",
    "typst_query_checked",
    "typst_values",
    "y_center",
]
