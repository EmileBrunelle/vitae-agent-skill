"""Academic gate: the five checks (A counts and numbering, B antechronology, C orphan heading, D straddle, E running head)."""
from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from vitae.verify.academic.parse import NUM_RE, _canonical_headings, classify, entry_start_re, parse_span
from vitae.verify.academic.spec import NONDATED_HEADINGS, Footer, Result, Section, StreamLine


# ------------------------------------------------------------------ checks
def check_counts_and_chrono(stream: list[StreamLine], sections: list[Section],
                            headings_set: set[str], statuses: Sequence[str] = (),
                            nondated: set[str] | frozenset[str] = frozenset(NONDATED_HEADINGS)) -> list[Result]:
    """Check A (count round-trip + numbering) and B (antechronology)."""
    results: list[Result] = []
    start_re = entry_start_re(statuses)
    positions: dict[str, int] = {}
    for idx, (pi, raw, stripped, is_start) in enumerate(stream):
        if stripped in headings_set and stripped not in positions:
            positions[stripped] = idx

    for sec in sections:
        heading, declared, prefix, numbered = (
            sec["heading"], sec["count"], sec["undated_prefix"], sec["numbered"])
        start_idx = positions.get(heading)
        entries: list[tuple[str, str]] = []  # (stripped_line, token)
        if start_idx is not None:
            for idx in range(start_idx + 1, len(stream)):
                _, _, stripped, is_start = stream[idx]
                if stripped in headings_set:
                    break
                if is_start:
                    m = start_re.match(stripped)
                    token = m.group(0) if m else stripped
                    entries.append((stripped, token))

        if start_idx is None and declared > 0 and heading not in nondated:
            results.append(("A", False, f'{heading}: declared {declared} but this heading was not found in the PDF text '
                                        f'(the counts check looks for the English template heading; if the CV prints another one, declare it under '
                                        f'[headings] in the data file)'))
            continue
        if prefix > 0 and not statuses:
            results.append(("A", False, f'{heading}: undated_prefix is {prefix} but [meta] entry_status is not declared, '
                                        f'so an entry that starts with a word instead of a year cannot be recognised'))
        n_extracted = len(entries)
        ok_a = (n_extracted == declared)
        results.append(("A", ok_a,
                         f'{heading}: declared {declared}, extracted {n_extracted}'))
        if not ok_a:
            continue

        if numbered and declared > 0:
            nums: list[int | None] = []
            for stripped, _ in entries:
                m = NUM_RE.search(stripped)
                nums.append(int(m.group(1)) if m else None)
            expected = list(range(declared, 0, -1))
            ok_num = nums == expected
            results.append(("A", ok_num,
                             f'{heading}: entry numbers {nums} (expected {expected})'))

        if heading in nondated:
            continue  # no date field, per schema -- check B does not apply

        dated_entries = entries[prefix:]
        spans = [parse_span(tok) for _, tok in dated_entries]
        real_spans = cast("list[tuple[int, int]]", spans)
        if any(s is None for s in spans):
            results.append(("B", False,
                             f'{heading}: an entry past the declared undated_prefix '
                             f'({prefix}) has no year'))
            continue
        ok_b = True
        bad_pair: tuple[tuple[int, int], tuple[int, int]] | None = None
        for i in range(len(spans) - 1):
            if real_spans[i][1] < real_spans[i + 1][0]:  # prev.end < curr.start: a genuine reversal
                ok_b = False
                bad_pair = (real_spans[i], real_spans[i + 1])
                break
        msg = f'{heading}: spans after prefix {prefix} -> {spans}'
        if not ok_b:
            msg += f'  -- reversal at {bad_pair}'
        results.append(("B", ok_b, msg))

    return results


def check_no_orphan_heading(stream: list[StreamLine], headings_set: set[str],
                            declared_counts: dict[str, int]) -> list[Result]:
    """Check C, strengthened form: a heading is followed by >=2 content
    lines on the SAME page (never the last line of a page with nothing --
    or only one line -- of its list under it).

    The required minimum scales down to the section's own DECLARED entry
    count (min(2, declared)) rather than a flat 2: a section with a single
    real entry (e.g. one plenary talk) legitimately produces only one line
    after its heading, and that is not a page-break defect -- it is the
    whole section. Requiring 2 regardless fired on real, correctly laid out
    1-entry sections (measured against the shipped example). A declared
    count of 0 (a heading with nothing under it at all, which a correctly
    behaved template never emits) still requires >=1, so a bare heading
    always fails."""
    results: list[Result] = []
    n = len(stream)
    for idx, (pi, raw, stripped, is_start) in enumerate(stream):
        if stripped not in headings_set:
            continue
        following = 0
        j = idx + 1
        while j < n and stream[j][0] == pi and stream[j][2] not in headings_set:
            following += 1
            j += 1
        declared = declared_counts.get(stripped)
        required = 2 if declared is None else max(1, min(2, declared))
        results.append(("C", following >= required,
                         f'heading "{stripped}": {following} line(s) follow it on its '
                         f'page (needs >= {required})'))
    return results


def check_no_straddle(pages_lines: list[list[str]],
                      headings_set: set[str], statuses: Sequence[str] = ()) -> list[Result]:
    """Check D: the first content line of every page AFTER a break (running
    head excluded) is a heading or an entry-start token -- never a
    continuation of the previous page's last entry."""
    results: list[Result] = []
    start_re = entry_start_re(statuses)
    for pi in range(1, len(pages_lines)):
        lines = pages_lines[pi]
        if not lines:
            continue
        first = lines[0]
        stripped = first.strip()
        ok = (stripped in headings_set
              or ((not first.startswith(" ")) and bool(start_re.match(stripped))))
        results.append(("D", ok, f'page {pi + 1} first content line: "{stripped[:60]}"'))  # [:60] keeps one-line diagnostic output
    return results


def check_running_head(per_page_footer: list[Footer],
                       per_page_surname: list[bool],
                       total_pages: int) -> list[Result]:
    """Check E: running head (surname) + 'n / N' pagination on every page,
    beyond 2 pages (academic-mode.md "Correctness properties" E: deliberately not required at
    1-2 pages)."""
    if total_pages <= 2:
        return [("E", True, f'{total_pages} page(s) -- running head/pagination '
                             f'applies beyond 2 pages, not checked')]
    results: list[Result] = []
    for pi in range(total_pages):
        page_num = pi + 1
        had_surname = per_page_surname[pi]
        footer = per_page_footer[pi]
        ok = had_surname and footer == (page_num, total_pages)
        results.append(("E", ok,
                         f'page {page_num}/{total_pages}: surname '
                         f'{"present" if had_surname else "MISSING"}, footer {footer!r} '
                         f'(expected {(page_num, total_pages)})'))
    return results


def analyze(text: str, sections: list[Section], surname: str,
            headings_extra: tuple[str, ...] = (), statuses: Sequence[str] = (),
            declared_headings: Sequence[str] = ()) -> tuple[list[Result], int]:
    """Run all five checks. Returns (results, total_pages). `declared_headings`: the `[headings]` values, the only
    headings matched case-insensitively."""
    headings_set = {s["heading"] for s in sections} | set(headings_extra)
    nondated = frozenset(s["heading"] for s in sections if s.get("nondated", s["heading"] in NONDATED_HEADINGS)) \
        | set(headings_extra)
    text = _canonical_headings(text, set(declared_headings))
    pages_lines, stream, per_page_footer, per_page_surname = classify(text, headings_set, surname, statuses, nondated)
    total_pages = len(pages_lines)
    declared_counts = {s["heading"]: s["count"] for s in sections}
    results: list[Result] = []
    results += check_counts_and_chrono(stream, sections, headings_set, statuses, nondated)
    results += check_no_orphan_heading(stream, headings_set, declared_counts)
    results += check_no_straddle(pages_lines, headings_set, statuses)
    results += check_running_head(per_page_footer, per_page_surname, total_pages)
    return results, total_pages
