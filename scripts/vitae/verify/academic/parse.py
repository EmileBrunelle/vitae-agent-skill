"""Academic gate: the rendered side — layout text, page split, line classification."""
from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Sequence

from vitae.verify.academic.spec import NONDATED_HEADINGS, Footer, StreamLine

# Matches lib-academic.typ's running footer (`n / N` on its own line) for check E.
FOOTER_RE = re.compile(r'^\s*(\d+)\s*/\s*(\d+)\s*$')



def entry_start_re(statuses: Sequence[str] = ()) -> re.Pattern[str]:
    """Regex for the start of an entry: a year or year range, or one of the DECLARED undated-entry words
    (`[meta] entry_status`), matched case-insensitively as a whole word (or words; runs of whitespace are equivalent),
    not a prefix: list every inflection printed. No built-in words: with none declared only a year starts an entry."""
    words = {" ".join(w.split()) for w in statuses if w.strip()}
    alts = "|".join(r"\s+".join(re.escape(t) for t in w.split(" ")) for w in sorted(words, key=len, reverse=True))
    return re.compile(r'^(\d{4}(-\d{4})?%s)(?!\w)' % (f"|{alts}" if alts else ""), re.I)



# Matches reverse-numbered publication labels `[N]` in check A, and 4-digit years in parse_span.
NUM_RE = re.compile(r'\[(\d+)\]')
YEAR_RE = re.compile(r'\d{4}')



def parse_span(token: str) -> tuple[int, int] | None:
    """A date TOKEN (e.g. '2019-2024', '2025', 'forthcoming') -> (start, end)
    year ints, or None for an undated status word. Two years, not one,
    because a range is an INTERVAL: check B (below) needs both ends to tell
    a legitimate overlapping span (e.g. an ongoing referee role '2020-2026')
    from an actual reversal, without any tunable slack."""
    years = [int(y) for y in YEAR_RE.findall(token)]
    if not years:
        return None
    return (min(years), max(years))


# --------------------------------------------------------- pdftotext parsing
def extract_layout_text(pdf: str) -> str:
    """The PDF as `pdftotext -layout` text. -layout keeps the date column left of the entry body, which is
    what lets entry_start_re() recognise an entry by its leading year token."""
    if not shutil.which("pdftotext"):
        raise RuntimeError("pdftotext (poppler-utils) is required for the "
                            "-layout column structure the checks depend on")
    return subprocess.run(["pdftotext", "-layout", pdf, "-"],
                           capture_output=True, text=True).stdout


def parse_pages(text: str) -> list[str]:
    """pdftotext -layout output -> list of raw per-page text chunks."""
    pages = text.split("\f")
    if pages and pages[-1].strip() == "":
        pages.pop()
    return pages


def classify(text: str, headings_set: set[str], surname: str,
             statuses: Sequence[str] = (), nondated: set[str] | frozenset[str] = frozenset(NONDATED_HEADINGS)) -> tuple[
        list[list[str]], list[StreamLine], list[Footer], list[bool]]:
    """Returns (pages_lines, stream, per_page_footer, per_page_surname).

    pages_lines: list (per page) of raw content lines, header/footer lines
    stripped out.
    stream: flat [(page_idx, raw_line, stripped, is_entry_start), ...] across
    the whole document, in reading order.
    """
    raw_pages = parse_pages(text)
    pages_lines: list[list[str]] = []
    per_page_footer: list[Footer] = []
    per_page_surname: list[bool] = []
    for pt in raw_pages:
        lines: list[str] = []
        footer: Footer = None
        had_surname = False
        for raw in pt.split("\n"):
            s = raw.strip()
            if s == "":
                continue
            if surname and s == surname:    # the running head is a line that is exactly the surname
                had_surname = True
                continue
            m = FOOTER_RE.match(s)
            if m:
                footer = (int(m.group(1)), int(m.group(2)))
                continue
            lines.append(raw)
        pages_lines.append(lines)
        per_page_footer.append(footer)
        per_page_surname.append(had_surname)

    start_re = entry_start_re(statuses)
    stream: list[StreamLine] = []
    current_heading: str | None = None
    for pi, lines in enumerate(pages_lines):
        for raw in lines:
            stripped = raw.strip()
            if stripped in headings_set:
                current_heading = stripped
                stream.append((pi, raw, stripped, True))
                continue
            dated = current_heading not in nondated
            if dated:
                is_start = (not raw.startswith(" ")) and bool(start_re.match(stripped))
            else:
                is_start = True  # one line = one entry, no year column (see nondated)
            stream.append((pi, raw, stripped, is_start))

    return pages_lines, stream, per_page_footer, per_page_surname


def _canonical_headings(text: str, declared: set[str]) -> str:
    """Rewrite each line equal, up to case, to a heading DECLARED under `[headings]` into that heading's own
    spelling. The English defaults are never folded: they match as an exact uppercase whole line only, so a body line
    such as "Teaching" is not a heading."""
    by_fold = {h.casefold(): h for h in declared}
    return "\n".join(by_fold.get(ln.strip().casefold(), ln) for ln in text.split("\n"))
