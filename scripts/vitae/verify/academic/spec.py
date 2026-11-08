"""Academic gate: the declared side — section spec, TOML tables, heading set."""
from __future__ import annotations

from typing import NotRequired, TypedDict


class Section(TypedDict):
    heading: str
    count: int
    undated_prefix: int
    numbered: bool
    nondated: NotRequired[bool]  # no year column (REFERENCES); default: the heading is in NONDATED_HEADINGS


# a parsed TOML document (tomllib.load): values are walked with isinstance, never indexed blindly
Toml = dict[str, object]
# one check result: (check id, passed, message)
Result = tuple[str, bool, str]
# one line of the flat document stream: (page idx, raw line, stripped, is_entry_start)
StreamLine = tuple[int, str, str, bool]
Footer = tuple[int, int] | None


# ---------------------------------------------------------------- constants
# The ENGLISH headings the shipped template prints (SECTION_DEFS / NONDATED_HEADINGS / EXTRA_HEADINGS below) are the
# only language data of this gate. The gate reads no word of any language: the words that open an undated entry are
# declared by the CV's author in the TOML (`[meta] entry_status`), never listed here.
# The skill's own finite heading set for the math/CS academic variant
# (cv.typ). Hardcoded here deliberately — design note §3.2 check C: "le
# skill connaît la liste exacte de ses propres titres (il les a générés)".
# heading -> (counts-path, undated_prefix-path-or-None, numbered?)
SECTION_DEFS: list[tuple[str, tuple[str, ...], tuple[str, ...] | None, bool]] = [
    ("EDUCATION", ("education",), None, False),
    ("APPOINTMENTS", ("appointments",), None, False),
    ("HONOURS AND AWARDS", ("honours",), None, False),
    ("PUBLICATIONS: JOURNAL ARTICLES", ("publications", "journal"),
     ("publications", "journal"), True),
    ("PUBLICATIONS: PEER-REVIEWED CONFERENCE PROCEEDINGS",
     ("publications", "conference"), ("publications", "conference"), True),
    ("PUBLICATIONS: PREPRINTS", ("publications", "preprint"),
     ("publications", "preprint"), True),
    ("INVITED PLENARY TALKS", ("talks", "plenary"), ("talks", "plenary"), False),
    ("INVITED TALKS", ("talks", "invited"), ("talks", "invited"), False),
    ("CONFERENCE TALKS", ("talks", "conference"), ("talks", "conference"), False),
    ("SEMINAR TALKS", ("talks", "seminar"), ("talks", "seminar"), False),
    ("POSTERS", ("talks", "poster"), ("talks", "poster"), False),
    ("FUNDING", ("funding",), None, False),
    ("SUPERVISION AND TRAINING", ("supervision",), None, False),
    ("TEACHING", ("teaching",), None, False),
    ("SERVICE AND EVALUATION", ("service",), None, False),
    ("KNOWLEDGE MOBILIZATION", ("knowledge_mobilization",), None, False),
    ("REFERENCES", ("references",), None, False),
]
# Headings that are NOT a dated list: "affiliations_languages is TWO PLAIN
# LINES ... no count, no antechronology check applies to it" (TOML schema
# header), and REFERENCES entries carry no `date` field either (schema:
# "[[references]] name, affiliation, email ... (optional section, US
# convention)" -- the general "every table carries date" rule explicitly
# excludes it). Both need a heading (for checks C/D) but no year-token
# entry-start rule: every non-blank line under them is its own line-item.
NONDATED_HEADINGS = {"REFERENCES", "AFFILIATIONS AND LANGUAGES"}
EXTRA_HEADINGS = ("AFFILIATIONS AND LANGUAGES",)  # heading with no counts table at all
EXTRA_KEY = "affiliations"  # its `[headings]` key


def dget(d: object, path: tuple[str, ...], default: object = 0) -> object:
    """Nested dict lookup along `path`; `default` as soon as a key is absent or a level is not a dict."""
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


# --------------------------------------------------------------- real usage
def build_sections_spec(data: Toml) -> list[Section]:
    """Turn the TOML's [counts] / [undated_prefix] tables into the per-heading spec the checks consume.
    A section missing from [counts] raises rather than defaulting to 0, so a stale data file cannot
    silently declare an empty section."""
    counts = data.get("counts", {})
    prefixes = data.get("undated_prefix", {})
    headings = data.get("headings", {})
    sections: list[Section] = []
    for heading, cpath, ppath, numbered in SECTION_DEFS:
        declared = dget(counts, cpath, default=None)
        if declared is None:
            raise ValueError(f'TOML missing counts.{".".join(cpath)}')
        prefix = dget(prefixes, ppath, default=0) if ppath else 0
        printed = dget(headings, cpath, default=None)
        for what, v in (("counts", declared), ("undated_prefix", prefix)):
            if not isinstance(v, int) or isinstance(v, bool):
                raise ValueError(f'TOML {what}.{".".join(cpath if what == "counts" else ppath or cpath)} must be an integer')
        assert isinstance(declared, int) and isinstance(prefix, int)
        sections.append({"heading": printed if isinstance(printed, str) and printed.strip() else heading,
                          "count": declared, "undated_prefix": prefix, "numbered": numbered,
                          "nondated": heading in NONDATED_HEADINGS})
    return sections


def _leaf_paths(table: object, prefix: tuple[str, ...] = ()) -> list[tuple[str, ...]]:
    if not isinstance(table, dict):
        return [prefix]
    return [p for k, v in table.items() for p in _leaf_paths(v, prefix + (k,))]


def _is_table_section(path: tuple[str, ...]) -> bool:
    return any(c[:len(path)] == path and len(c) > len(path) for _, c, _, _ in SECTION_DEFS)


def check_headings_table(data: Toml) -> list[Result]:
    """`[headings]` maps each [counts] section (same nesting: `education`, `publications.journal`) to the heading the
    CV prints, plus `affiliations` (the heading of the plain affiliations block, which has no count). It must be a
    table. A key that is not one of those, a table where a string belongs, a string where a table of subsections
    belongs, or a value that is not a non-empty string, is a FAIL naming it."""
    raw = data.get("headings", {})
    if not isinstance(raw, dict):
        return [("A", False, "[headings] must be a table")]
    known = {cpath for _, cpath, _, _ in SECTION_DEFS} | {(EXTRA_KEY,)}
    out: list[Result] = []
    for path in _leaf_paths(raw):
        if not path:
            continue
        name = ".".join(path)
        val = dget(raw, path, default=None)
        if path not in known:
            if len(path) == 1 and _is_table_section(path):
                continue                                  # reported below as "expects a table"
            out.append(("A", False, f'[headings] {name}: not a section of [counts] (known: '
                                    f'{", ".join(".".join(c) for c in sorted(known))})'))
        elif not (isinstance(val, str) and val.strip()):
            out.append(("A", False, f'[headings] {name}: must be a non-empty string'))
    for k, v in raw.items():
        if _is_table_section((k,)) and not isinstance(v, dict):
            out.append(("A", False, f'[headings] {k}: expects a table of subsections, not a string'))
    return out


def printed_headings(data: Toml) -> tuple[tuple[str, ...], list[str]]:
    """(extra headings the CV prints, every declared `[headings]` string). The affiliations heading defaults to the
    English one."""
    raw = data.get("headings", {})
    tbl: Toml = raw if isinstance(raw, dict) else {}
    found = [dget(tbl, p, default=None) for p in _leaf_paths(tbl) if p]
    declared = [d for d in found if isinstance(d, str) and d.strip()]
    aff = tbl.get(EXTRA_KEY)
    extra = (aff,) if isinstance(aff, str) and aff.strip() else EXTRA_HEADINGS
    return extra, declared


def declared_statuses(data: Toml) -> list[str]:
    """`[meta] entry_status`: the words the CV's author declares for entries that start with a status instead of a
    year (e.g. ["Sous presse", "Soumis"]). Absent -> [], and the gate then recognises years only."""
    meta = data.get("meta", {})
    raw = meta.get("entry_status", []) if isinstance(meta, dict) else []
    if not isinstance(raw, list) or not all(isinstance(w, str) for w in raw):
        raise ValueError("[meta] entry_status must be a list of strings")
    return raw
