"""Shared shapes and constants of the verify modules (a leaf: it imports no sibling).

Shared by the modules under vitae/verify/ and vitae/core/. It holds no mutable state: the message footer a failed
run prints last is returned by the mode that computes it (see `_run` in vitae/verify/cli.py).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, NotRequired, TypeAlias, TypedDict

if TYPE_CHECKING:
    # type checking only: typing_extensions is never imported at run time (annotations are strings here)
    from typing_extensions import ReadOnly, TypeIs

# ---------- shapes passed around ----------
# Geometry, in PDF points unless said otherwise (pdftotext -bbox).
Box: TypeAlias = tuple[float, float, float, float]            # x0, y0, x1, y1
WordBox: TypeAlias = tuple[Box, str]                          # a word and its box
Word: TypeAlias = tuple[float, float, float, float, str]      # x0, y0, x1, y1, text
Band: TypeAlias = tuple[int, int]                             # first, last pixel row of a run
LineBox: TypeAlias = list[float]                              # [x0, x1, y0, y1] of one text line
GapFn: TypeAlias = Callable[[int, LineBox, LineBox], float]   # optical gap (pt) between two lines
# One extracted word of the hidden-text gate: page, word, box, box height (pt),
# contrast against its own background (None: no raster), off the page.
HiddenStat: TypeAlias = tuple[int, str, Box, float, float | None, bool]


class _MarkExtras(TypedDict, total=False):
    """The keys only some marks carry (shared by Mark and HeadMark)."""
    kind: ReadOnly[str]           # "entry" / "skill" (heads) or "date" / "org" / "date-col" (parts)
    org: ReadOnly[str]            # heads only
    w: ReadOnly[float]            # measured cell width (parts)
    h: ReadOnly[float]            # measured cell height (parts)
    dated: ReadOnly[bool]         # entry heads of a lib that tags them: given a date?
    anchor: ReadOnly[bool]        # entry heads of a lib that tags them: date anchor present
    inline: ReadOnly[bool]        # date parts: set inline after the role


class Mark(_MarkExtras):
    """One value of lib.typ's invisible markers, read back by `typst query`
    (<vitae-head> / <vitae-part> / <vitae-sec>). Only `text` is on every one: a
    section title has no x and no kind, and the fallback marks built from the
    source (and partial marks of an old lib) carry no position. The gates that
    measure positions work on HeadMark / SecMark, which they narrow to."""
    text: ReadOnly[str]
    page: NotRequired[ReadOnly[int]]
    x: NotRequired[ReadOnly[float]]
    y: NotRequired[ReadOnly[float]]


class HeadMark(_MarkExtras):
    """A Mark known to carry its x: an entry head, skill label or part (<vitae-head> / <vitae-part>)."""
    text: ReadOnly[str]
    page: ReadOnly[int]
    x: ReadOnly[float]
    y: ReadOnly[float]


class SecMark(_MarkExtras):
    """A section title mark (<vitae-sec>) with its position. The lib gives it no kind and no x; the optional
    keys are only here so that a Mark with a page and a y narrows to it (is_sec_placed)."""
    text: ReadOnly[str]
    page: ReadOnly[int]
    y: ReadOnly[float]
    x: NotRequired[ReadOnly[float]]


def is_placed(m: Mark) -> TypeIs[HeadMark]:
    """A mark that carries its position (page, x, y), as every lib entry head and part mark does."""
    return "page" in m and "x" in m and "y" in m


def is_sec_placed(m: Mark) -> TypeIs[SecMark]:
    """A mark that carries the page and y a section title is measured from (its x, if any, is not read)."""
    return "page" in m and "y" in m


@dataclass(frozen=True, slots=True)
class _EntryRecord:
    """_entry_records(): an entry head with the part marks that follow it (built in process, never serialized)."""
    head: HeadMark
    date: HeadMark | None
    org: HeadMark | None
    date_first: bool | None


class _Line(TypedDict):
    """_lines(): the words of one text line, clustered by y-centre."""
    y0: ReadOnly[float]
    y1: ReadOnly[float]
    c: ReadOnly[float]
    x0: ReadOnly[float]
    words: ReadOnly[list[Word]]


@dataclass(frozen=True, slots=True)
class GroupMeasure:
    """measure_groups() row of an entry or skill group (built in process; `group_detail` turns it into the DETAIL
    row at the serialization boundary)."""
    text: str
    page: int
    n: int                                    # lines in the group, less one
    gaps: list[float]                         # gaps between consecutive lines inside it
    internal: float                           # the largest of them
    between: float                            # last line -> next block's first line
    ratio: float                              # between / internal
    hkind: str | None                         # the head mark kind: "entry" or "skill"
    next_sec: bool                            # the next block is a section title
    head_gap: float | None                    # org line -> first bullet (entries with an org line and >= 2 bullet lines)
    pitch: float | None                       # median gap between the bullet lines
    ls: list[LineBox]
    pair_in: tuple[str, str]                  # the line pair behind `internal`
    pair_btw: tuple[str, str]                 # the line pair behind `between`


@dataclass(frozen=True, slots=True)
class SecMeasure:
    """measure_groups() row of a section title (built in process; see GroupMeasure)."""
    text: str
    page: int
    before: float                             # previous block -> title (its bar)
    after: float                              # title -> first line of its section
    ratio: float


Measure: TypeAlias = GroupMeasure | SecMeasure


class GroupRow(TypedDict):
    """DETAIL row of an entry or skill group: the JSON shape of a GroupMeasure (`DETAIL ` line of the verify CLI)."""
    kind: ReadOnly[Literal["group"]]
    text: ReadOnly[str]
    page: ReadOnly[int]
    n: ReadOnly[int]
    gaps: ReadOnly[list[float]]
    internal: ReadOnly[float]
    between: ReadOnly[float]
    ratio: ReadOnly[float]
    hkind: ReadOnly[str | None]
    next_sec: ReadOnly[bool]
    head_gap: ReadOnly[float | None]
    pitch: ReadOnly[float | None]
    ls: ReadOnly[list[LineBox]]
    pair_in: ReadOnly[tuple[str, str]]
    pair_btw: ReadOnly[tuple[str, str]]


class SecRow(TypedDict):
    """DETAIL row of a section title: the JSON shape of a SecMeasure."""
    kind: ReadOnly[Literal["sec"]]
    text: ReadOnly[str]
    page: ReadOnly[int]
    before: ReadOnly[float]
    after: ReadOnly[float]
    ratio: ReadOnly[float]


DetailRow: TypeAlias = GroupRow | SecRow


# The last lines printed when a run ends on a non-zero exit (see `_run`). A reader (human or
# model) acts on what it sees LAST, so the instruction is here, not only in the header.
# Armed (set non-None) only after preflight succeeded, per mode, so a missing
# dependency or a usage error never gets a footer that blames cv.typ.
_NO_READ = ("      Do not open verify.py or lib.typ: their code is not the fix, and "
            "reading them costs your context.")
# Lowering FILL_MIN below the drawn target is a WARN down to LOWERED_FILL_FLOOR; below it
# it is a FAIL so a dummy target (e.g. `1 10 100`) cannot bypass the fill gate.
# 60 = below the 65% observed in the 0.9.0 real run (thin 2-job persona, facts exhausted)
# with margin, still above a half-empty page; still a WARN.
LOWERED_FILL_FLOOR = 60
_FOOTER_GATE = ("NEXT  Apply the fix each FAIL above names, then re-run the same command. "
                "Edit cv.typ only; a lib.typ FAIL is fixed by the printed `cp` command "
                "(recopy it, never edit it).\n" + _NO_READ)
_FOOTER_TUNE = ("NEXT  Run the command printed above (wider range), or add real content / "
                "change the page count in cv.typ; do not edit leading by hand.\n" + _NO_READ)
_FOOTER_TUNE_UNDER = ("NEXT  The page is under-filled: do not re-run --tune or widen the range "
                      "(leading is capped). Add a real fact from the candidate's facts (a bullet "
                      "with a measurable result, a project, a certification); raising the body type size "
                      "is the same padding, not an alternative; never pad or invent "
                      "— if the facts are not in hand, ask the user. Only if the facts are "
                      "exhausted: fewer pages or a lowered target, `verify.py cv.typ PAGES FILL_MIN FILL_MAX` "
                      "(FILL_MIN = the lowest fill the gate prints, not below "
                      f"{LOWERED_FILL_FLOOR}; under {LOWERED_FILL_FLOOR}% there is no lowered-target "
                      "exit: a fact is missing, or fewer pages), and tell the user.\n" + _NO_READ)
_FOOTER_TUNE_NOPAR = ("NEXT  Add the `#set par(leading: Xem, spacing: Yem)` line to cv.typ "
                      "(copy it from the template), then re-run the same command.\n" + _NO_READ)
_FOOTER_TUNE_WIDE = ("NEXT  The range was already wide: do not re-run --tune. Add real content "
                     "or change the page count in cv.typ.\n" + _NO_READ)


# The shipped templates stay well below this body leading (today's highest is about 0.72em); the tuner
# may go up to LEADING_WARN (1.00em). Above 1.00em multi-line text (profile summary, wrapped bullets) reads as
# double-spaced while every mechanical check still passes.
LEADING_WARN = 1.00    # em; strictly above it the WARN fires

# Relative twin: prose leading against bullet spacing. The family-relative form compares the file's
# leading / list-spacing ratio with the same ratio of its family's shipped default (resume.typ, or
# resume-2page.typ for a 2-page file when the family ships one); strictly above the constant the WARN
# fires. Calibrated 2026-11: shipped files (resume, resume-pair-b, 2-page, fixtures) score <= 1.050;
# the five measured post-`--tune` runs score 1.161-1.616 (margin 0.06).
LEADING_FAMILY_RATIO_WARN = 1.10
# Fallback with no FAMILY header or an unknown family: absolute leading / list spacing, strictly above
# it the WARN fires (a real 1.0em/0.5em run, ratio 2.00, read double-spaced; highest shipped is 1.89).
LEADING_ABS_RATIO_WARN = 1.95


# Shared by verify_pdf (render default) and verify_text (hidden-text raster).
HIDDEN_PPI = 150          # own raster: tiny legit text needs more than the 90 ppi fill scan


# ---------- the bullets of one run (read by the runts and rhythm gates; built once, see runts.bullet_layout) ----------
@dataclass(frozen=True)
class Extent:
    x0: float
    x1: float


@dataclass(frozen=True)
class Pos:
    """Where a bullet starts: its marker's page, x and y."""
    page: int
    x: float
    y: float


@dataclass(frozen=True)
class BulletLine:
    page: int
    extent: Extent
    height: float
    text: str
    y1: float = 0.0


@dataclass(frozen=True)
class BulletLayout:
    """The words of the PDF and the bullets located in them, computed once per run: the words of each page and its
    height, and per bullet mark its position and its lines top to bottom (a bullet whose first line cannot be found
    is absent). `located` is empty when a page is denser than bounds.MAX_PAGE_WORK: the gates refuse such a page
    (bounds.density_guard) before they read it."""
    pages: list[list[WordBox]]
    heights: list[float]
    located: list[tuple[Pos, list[BulletLine]]]
