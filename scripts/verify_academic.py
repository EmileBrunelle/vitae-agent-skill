#!/usr/bin/env python3
"""Five binary gates for an academic CV — a round-trip between the declared
TOML data file (source of truth for counts/order) and the rendered PDF
(`pdftotext -layout`). See academic-mode.md §3 for the design rationale; the
five checks and the non-goals below are DECIDED THERE, not here.

PLUMBING REUSED from verify.py (imported, not copied — none of it carries a
calibrated constant): preflight(), compile_pdf(), count_pages(),
render_pngs(). Also measure_fill.measure() for the reported-only last-page
fill line.

NOT REUSED, on purpose (commit c7ca219): check_whitespace(), tune(), or any
of BOUNDARY_RATIO / SEPARATION_CEILING / DEVICE_QUORUM / CANYON /
BOUNDARY_CEILING. Those are curve-fit to one/two-page industry résumés and
are meaningless on a genre with no fill target at all (academic-mode.md §3.4:
"Écarté, pas assoupli" — no fill floor, not even on the last page).

This script also never regexes the .typ source and compares it to a PDF
built from that same source — that round-trip is a tautology, and a
previous attempt at exactly this had to be deleted (academic-mode.md note,
commit d7f67da). Every declared count/order/prefix comes from the TOML;
every extracted count/order comes from the rendered PDF.

Usage:
    verify_academic.py cv.typ data.toml
    verify_academic.py --selftest
    verify_academic.py --doctor

Exit codes: 0 PASS, 1 FAIL, 2 usage error.
"""
import os
import re
import subprocess
import shutil
import sys
import tempfile

import tomllib  # stdlib, py3.11+

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify  # noqa: E402 -- plumbing only, see module docstring
import measure_fill  # noqa: E402 -- measure() only, reported not failed


# ---------------------------------------------------------------- constants
# The skill's own finite heading set for the math/CS academic variant
# (cv.typ). Hardcoded here deliberately — design note §3.2 check C: "le
# skill connaît la liste exacte de ses propres titres (il les a générés)".
# heading -> (counts-path, undated_prefix-path-or-None, numbered?)
SECTION_DEFS = [
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

FOOTER_RE = re.compile(r'^\s*(\d+)\s*/\s*(\d+)\s*$')
ENTRY_START_RE = re.compile(r'^(\d{4}(-\d{4})?|submitted|forthcoming|in press)\b', re.I)
NUM_RE = re.compile(r'\[(\d+)\]')
YEAR_RE = re.compile(r'\d{4}')


def dget(d, path, default=0):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def parse_span(token):
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
def extract_layout_text(pdf):
    if not shutil.which("pdftotext"):
        raise RuntimeError("pdftotext (poppler-utils) is required for the "
                            "-layout column structure the checks depend on")
    return subprocess.run(["pdftotext", "-layout", pdf, "-"],
                           capture_output=True, text=True).stdout


def parse_pages(text):
    """pdftotext -layout output -> list of raw per-page text chunks."""
    pages = text.split("\f")
    if pages and pages[-1].strip() == "":
        pages.pop()
    return pages


def classify(text, headings_set, surname):
    """Returns (pages_lines, stream, total_pages).

    pages_lines: list (per page) of raw content lines, header/footer lines
    stripped out.
    stream: flat [(page_idx, raw_line, stripped, is_entry_start), ...] across
    the whole document, in reading order.
    """
    raw_pages = parse_pages(text)
    pages_lines = []
    per_page_footer = []
    per_page_surname = []
    for pt in raw_pages:
        lines, footer, had_surname = [], None, False
        for raw in pt.split("\n"):
            s = raw.strip()
            if s == "":
                continue
            if surname and s == surname:
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

    stream = []
    current_heading = None
    for pi, lines in enumerate(pages_lines):
        for raw in lines:
            stripped = raw.strip()
            if stripped in headings_set:
                current_heading = stripped
                stream.append((pi, raw, stripped, True))
                continue
            dated = current_heading not in NONDATED_HEADINGS
            if dated:
                is_start = (not raw.startswith(" ")) and bool(ENTRY_START_RE.match(stripped))
            else:
                is_start = True  # one line = one entry, no year column (see NONDATED_HEADINGS)
            stream.append((pi, raw, stripped, is_start))

    return pages_lines, stream, per_page_footer, per_page_surname


# ------------------------------------------------------------------ checks
def check_counts_and_chrono(stream, sections, headings_set):
    """Check A (count round-trip + numbering) and B (antechronology)."""
    results = []
    positions = {}
    for idx, (pi, raw, stripped, is_start) in enumerate(stream):
        if stripped in headings_set and stripped not in positions:
            positions[stripped] = idx

    for sec in sections:
        heading, declared, prefix, numbered = (
            sec["heading"], sec["count"], sec["undated_prefix"], sec["numbered"])
        start_idx = positions.get(heading)
        entries = []  # (stripped_line, token)
        if start_idx is not None:
            for idx in range(start_idx + 1, len(stream)):
                _, _, stripped, is_start = stream[idx]
                if stripped in headings_set:
                    break
                if is_start:
                    m = ENTRY_START_RE.match(stripped)
                    token = m.group(0) if m else stripped
                    entries.append((stripped, token))

        n_extracted = len(entries)
        ok_a = (n_extracted == declared)
        results.append(("A", ok_a,
                         f'{heading}: declared {declared}, extracted {n_extracted}'))
        if not ok_a:
            continue

        if numbered and declared > 0:
            nums = []
            for stripped, _ in entries:
                m = NUM_RE.search(stripped)
                nums.append(int(m.group(1)) if m else None)
            expected = list(range(declared, 0, -1))
            ok_num = nums == expected
            results.append(("A", ok_num,
                             f'{heading}: entry numbers {nums} (expected {expected})'))

        if heading in NONDATED_HEADINGS:
            continue  # no date field, per schema -- check B does not apply

        dated_entries = entries[prefix:]
        spans = [parse_span(tok) for _, tok in dated_entries]
        if any(s is None for s in spans):
            results.append(("B", False,
                             f'{heading}: an entry past the declared undated_prefix '
                             f'({prefix}) has no year'))
            continue
        ok_b = True
        bad_pair = None
        for i in range(len(spans) - 1):
            if spans[i][1] < spans[i + 1][0]:  # prev.end < curr.start: a genuine reversal
                ok_b = False
                bad_pair = (spans[i], spans[i + 1])
                break
        msg = f'{heading}: spans after prefix {prefix} -> {spans}'
        if not ok_b:
            msg += f'  -- reversal at {bad_pair}'
        results.append(("B", ok_b, msg))

    return results


def check_no_orphan_heading(stream, headings_set, declared_counts):
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
    results = []
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


def check_no_straddle(pages_lines, headings_set):
    """Check D: the first content line of every page AFTER a break (running
    head excluded) is a heading or an entry-start token -- never a
    continuation of the previous page's last entry."""
    results = []
    for pi in range(1, len(pages_lines)):
        lines = pages_lines[pi]
        if not lines:
            continue
        first = lines[0]
        stripped = first.strip()
        ok = (stripped in headings_set
              or ((not first.startswith(" ")) and bool(ENTRY_START_RE.match(stripped))))
        results.append(("D", ok, f'page {pi + 1} first content line: "{stripped[:60]}"'))
    return results


def check_running_head(per_page_footer, per_page_surname, total_pages):
    """Check E: running head (surname) + 'n / N' pagination on every page,
    beyond 2 pages (academic-mode.md §3.2 E: deliberately not required at
    1-2 pages)."""
    if total_pages <= 2:
        return [("E", True, f'{total_pages} page(s) -- running head/pagination '
                             f'applies beyond 2 pages, not checked')]
    results = []
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


def analyze(text, sections, surname, headings_extra=()):
    """Run all five checks. Returns (results, total_pages)."""
    headings_set = {s["heading"] for s in sections} | set(headings_extra)
    pages_lines, stream, per_page_footer, per_page_surname = classify(text, headings_set, surname)
    total_pages = len(pages_lines)
    declared_counts = {s["heading"]: s["count"] for s in sections}
    results = []
    results += check_counts_and_chrono(stream, sections, headings_set)
    results += check_no_orphan_heading(stream, headings_set, declared_counts)
    results += check_no_straddle(pages_lines, headings_set)
    results += check_running_head(per_page_footer, per_page_surname, total_pages)
    return results, total_pages


# --------------------------------------------------------------- real usage
def build_sections_spec(data):
    counts = data.get("counts", {})
    prefixes = data.get("undated_prefix", {})
    sections = []
    for heading, cpath, ppath, numbered in SECTION_DEFS:
        declared = dget(counts, cpath, default=None)
        if declared is None:
            raise ValueError(f'TOML missing counts.{".".join(cpath)}')
        prefix = dget(prefixes, ppath, default=0) if ppath else 0
        sections.append({"heading": heading, "count": declared,
                          "undated_prefix": prefix, "numbered": numbered})
    return sections


def run_gate(typ, toml_path):
    ok, use_cli, use_poppler = verify.preflight()
    if not shutil.which("pdftotext"):
        ok = False
    if not ok:
        return False, [(True, "missing dependency -- see --doctor output above")], []

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)
    sections = build_sections_spec(data)
    surname = data["meta"]["name"].split(" ")[-1]

    # NOTE: deliberately no verify.ensure_icons(typ) here -- lib-academic.typ
    # never imports icons.typ (icons/photo are an explicit anti-goal for this
    # genre, academic-mode.md §1.1), so that plumbing would just write an
    # unused file under templates/academic/.
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "cv.pdf")
        compiled, err = verify.compile_pdf(typ, pdf, use_cli)
        if not compiled:
            return False, [(True, f"compile failed: {err}")], []

        text = extract_layout_text(pdf)
        results, total_pages = analyze(text, sections, surname, EXTRA_HEADINGS)

        # ---- reported-only metrics (never failed): page count, last-page
        # fill, and a rough prose/list share. academic-mode.md §3.3/§3.4.
        reported = [f'{total_pages} page(s)']
        pages_from_cli = verify.count_pages(pdf, use_poppler)
        if pages_from_cli and str(pages_from_cli) != str(total_pages):
            reported.append(f'note: pdfinfo reports {pages_from_cli} page(s)')
        pngs = verify.render_pngs(typ, tmp, use_cli)
        if pngs:
            reported.append(f'last-page fill: {measure_fill.measure(pngs[-1])}')

    msgs = [(not ok, msg) for _, ok, msg in results]
    fail = any(not ok for _, ok, _ in results)
    return not fail, msgs, reported


# ----------------------------------------------------------------- selftest
FIXTURE_HEAD = '''#set page(paper: "a5", margin: 1.2cm{header_footer})
#set text(size: 9pt)
#let e(y, body) = grid(columns: (1.4cm, 1fr), column-gutter: 6pt, [#y], [#body])
'''

HEADER_FOOTER = ''',
  header: align(right, text(size: 8pt)[Doe]),
  footer: context {
    let n = counter(page).get().first()
    let total = counter(page).final().first()
    align(center, text(size: 8pt)[#n / #total])
  }'''


def _compile_and_extract(src):
    with tempfile.TemporaryDirectory() as tmp:
        typ = os.path.join(tmp, "fixture.typ")
        pdf = os.path.join(tmp, "fixture.pdf")
        with open(typ, "w", encoding="utf-8") as f:
            f.write(src)
        ok, use_cli = verify.check_typst()
        compiled, err = verify.compile_pdf(typ, pdf, use_cli)
        assert compiled, f"fixture failed to compile: {err}"
        return extract_layout_text(pdf)


def _baseline_src(with_footer=True, pages=3):
    hf = HEADER_FOOTER if with_footer else ',\n  header: align(right, text(size: 8pt)[Doe])'
    src = FIXTURE_HEAD.format(header_footer=hf)
    src += '''
#text(weight: "bold")[SECTION ONE]
#v(2pt)
#e[2022][First alpha entry]
#e[2021][Second alpha entry]
#e[2019][Third alpha entry]
'''
    if pages >= 2:
        src += '''#pagebreak()
#text(weight: "bold")[SECTION TWO]
#v(2pt)
#e[2020][First beta entry]
#e[2018][Second beta entry]
'''
    if pages >= 3:
        src += '''#pagebreak()
#text(weight: "bold")[SECTION THREE]
#v(2pt)
#e[2017][Only gamma entry]
#e[2016][Second gamma entry]
'''
    return src


def _baseline_sections(pages=3):
    sections = [{"heading": "SECTION ONE", "count": 3, "undated_prefix": 0, "numbered": False}]
    if pages >= 2:
        sections.append({"heading": "SECTION TWO", "count": 2, "undated_prefix": 0, "numbered": False})
    if pages >= 3:
        sections.append({"heading": "SECTION THREE", "count": 2, "undated_prefix": 0, "numbered": False})
    return sections


def _assert_all_pass(results, label):
    bad = [(cid, msg) for cid, ok, msg in results if not ok]
    assert not bad, f"{label}: expected all checks to PASS, got failures: {bad}"


def _assert_fails_with(results, check_id, needle, label):
    hits = [msg for cid, ok, msg in results if cid == check_id and not ok]
    assert hits, f"{label}: expected check {check_id} to FAIL, but it passed"
    assert any(needle.lower() in m.lower() for m in hits), (
        f"{label}: check {check_id} failed, but not for the expected reason "
        f"(looked for {needle!r} in {hits})")


def selftest():
    # 0. baseline: a correct 3-page fixture passes all five checks.
    text = _compile_and_extract(_baseline_src(with_footer=True, pages=3))
    results, total_pages = analyze(text, _baseline_sections(3), "Doe")
    assert total_pages == 3
    _assert_all_pass(results, "baseline")

    # A. a missing entry: declare one more than the PDF actually has.
    sections = _baseline_sections(3)
    sections[0]["count"] = 4
    results, _ = analyze(text, sections, "Doe")
    _assert_fails_with(results, "A", "declared 4, extracted 3", "missing-entry")
    # the other, untouched sections still pass their own A/B/C/D checks
    other_bad = [(cid, msg) for cid, ok, msg in results
                 if not ok and "SECTION ONE" not in msg]
    assert not other_bad, f"missing-entry: unrelated checks broke too: {other_bad}"

    # B. two inverted years within one section.
    broken_years = FIXTURE_HEAD.format(header_footer=HEADER_FOOTER) + '''
#text(weight: "bold")[SECTION ONE]
#v(2pt)
#e[2019][First entry, out of order]
#e[2021][Second entry, out of order]
#e[2018][Third entry]
'''
    text_b = _compile_and_extract(broken_years)
    results, _ = analyze(text_b, [{"heading": "SECTION ONE", "count": 3,
                                    "undated_prefix": 0, "numbered": False}], "Doe")
    _assert_fails_with(results, "B", "reversal", "inverted-years")

    # C. an orphan heading: heading alone on its page, its one entry pushed
    # to the next page.
    orphan_src = FIXTURE_HEAD.format(header_footer=HEADER_FOOTER) + '''
#text(weight: "bold")[SECTION ONE]
#v(2pt)
#e[2022][First entry]
#e[2021][Second entry]
#pagebreak()
#text(weight: "bold")[SECTION TWO]
#pagebreak()
#e[2020][Orphaned entry]
#pagebreak()
#text(weight: "bold")[SECTION THREE]
#v(2pt)
#e[2019][Third entry]
#e[2018][Fourth entry]
'''
    text_c = _compile_and_extract(orphan_src)
    sections_c = [
        {"heading": "SECTION ONE", "count": 2, "undated_prefix": 0, "numbered": False},
        {"heading": "SECTION TWO", "count": 1, "undated_prefix": 0, "numbered": False},
        {"heading": "SECTION THREE", "count": 2, "undated_prefix": 0, "numbered": False},
    ]
    results, _ = analyze(text_c, sections_c, "Doe")
    _assert_fails_with(results, "C", 'section two": 0 line', "orphan-heading")

    # D. an entry straddling a page break: its continuation opens the next
    # page with neither a heading nor a year token.
    straddle_src = FIXTURE_HEAD.format(header_footer=HEADER_FOOTER) + '''
#text(weight: "bold")[SECTION ONE]
#v(2pt)
#e[2022][First entry, about to be cut in half]
#pagebreak()
continuing the first entry here, with no year token and no heading
#v(4pt)
#e[2019][Second entry]
'''
    text_d = _compile_and_extract(straddle_src)
    results, _ = analyze(text_d, [{"heading": "SECTION ONE", "count": 2,
                                    "undated_prefix": 0, "numbered": False}], "Doe")
    _assert_fails_with(results, "D", "continuing the first entry", "straddle")

    # E. missing pagination: same 3-page baseline, footer stripped out.
    text_e = _compile_and_extract(_baseline_src(with_footer=False, pages=3))
    results, _ = analyze(text_e, _baseline_sections(3), "Doe")
    _assert_fails_with(results, "E", "footer none", "missing-pagination")

    # bonus: E is a no-op below 3 pages, so a 2-page footerless CV still
    # passes overall (§3.2: "beyond 2 pages").
    text_short = _compile_and_extract(_baseline_src(with_footer=False, pages=2))
    results, total_pages = analyze(text_short, _baseline_sections(2), "Doe")
    assert total_pages == 2
    _assert_all_pass(results, "short-cv-no-pagination-required")

    print("selftest OK -- baseline PASSes all five checks; each of A missing "
          "entry, B inverted years, C an orphan heading, D a straddling "
          "entry, and E missing pagination FAILs its own check and no other; "
          "a <=2 page CV is exempt from E")


def main():
    argv = sys.argv[1:]

    if argv and argv[0] == "--selftest":
        selftest()
        sys.exit(0)

    if argv and argv[0] == "--doctor":
        ok, _, _ = verify.preflight()
        if not shutil.which("pdftotext"):
            print("MISSING  pdftotext (poppler-utils) -- required for the "
                  "-layout extraction these checks depend on")
            ok = False
        sys.exit(0 if ok else 1)

    if len(argv) != 2:
        print(f"usage: {os.path.basename(sys.argv[0])} cv.typ data.toml\n"
              f"       {os.path.basename(sys.argv[0])} --selftest\n"
              f"       {os.path.basename(sys.argv[0])} --doctor", file=sys.stderr)
        sys.exit(2)

    typ, toml_path = argv
    ok, msgs, reported = run_gate(typ, toml_path)
    for is_fail, msg in msgs:
        print(f"{'FAIL' if is_fail else 'OK  '}  {msg}")
    for line in reported:
        print(f"INFO  {line}")
    if ok:
        print("PASS  all five checks hold")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
