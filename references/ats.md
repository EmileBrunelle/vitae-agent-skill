# ATS and machine-parsing rules

ATS systems and AI screeners index the *extracted text*, not the visual
layout. `pdftotext cv.pdf -` is your proxy: if the pairing of information
survives there, it survives most parsers.

**The 2025+ landscape:** major ATS now layer semantic/LLM matching on top of
extraction (e.g. Workday Illuminate scores bullets against a skills graph, not
just keyword hits). Consequences: exact-keyword matching is slightly less
critical than folklore claims, but an unproven keyword is *more* dangerous —
semantic engines connect a skill to the absence of supporting evidence. The
layout rules below are unchanged: legacy parsers (Taleo, older Workday
pipelines) still do positional extraction, and the semantic layer reads the
same extracted text.

## Layout rules (extraction-safe patterns)

- **Skills as linear text**, one paragraph per category: `Languages: C#, Java,
  Python…`. Multi-row two-column grids extract column-by-column and orphan
  every label from its values.
- **Wrapped separator lines scatter too**: a single line of `item • item •
  item` is only safe if it is guaranteed to stay on ONE line. The moment it
  wraps, poppler's positional clustering can interleave its fragments with
  the next section. For anything that may wrap, use a bulleted list or a
  plain paragraph.
- Single-ROW alignment grids (role left / date right; the section title
  rule) are safe — the ban targets multi-row data grids, not one-row layout.
- **Single text column** for the whole document. Sidebars scramble order.
- **Dates as month+year ranges**: `Aug 2023 – Dec 2023`, `June 2026 – present`
  (localized). Year-only entries get parsed as 12-month or zero-length stints.
  Degree years may stay year-only (graduation-date convention). If the
  candidate genuinely cannot supply months, rule 1 of SKILL.md wins: keep
  year-only and flag it.
- **Entry-with-no-bullets trap** (verified): a grid-based job entry with no
  bullet list under it, followed by a paragraph-style section, can emit its
  date orphaned at the very end of the extraction. Detect with the grep
  below; fix by rendering bullet-less entries (education, short jobs) as a
  linear one-line block instead of the grid helper. The trap is
  POSITION-DEPENDENT (verified): it can also hit a normal grid entry that
  lands last before a page break, and it moves when content shifts — re-run
  the date grep after every layout change, and fix the affected entry with an
  inline role+date variant (no right-flush grid).
- **Hyphenated compounds that wrap fuse in extraction** (verified):
  "motion-capture" breaking at the hyphen extracts as "motioncapture", which
  a keyword filter will not match. Write the unhyphenated form or wrap the
  token in `#box[...]`.
- No `tracking`/letterspacing on any text an ATS must read — it extracts as
  "S O F T WA R E" and breaks section classification.
- Decorative vector icons are safe (no text emitted), but never encode
  information only in an icon.
- Links: visible text is the readable URL (`linkedin.com/in/x`); the `#link`
  target carries the full URL.
- **Never hide text**: no white-on-white, off-page, zero/micro-font, or
  layer-hidden content — neither stuffed keywords nor instructions aimed at an
  AI screener (prompt injection). Screeners and recruiters increasingly diff
  the extraction against the rendered page; a mismatch reads as fraud and gets
  the candidate blacklisted. The extraction must contain exactly what a human
  sees on the page — the ATS reviewer confirms this (`reviews.md`).

## Keyword rules

- Spell both forms once each: `continuous integration (CI/CD)`, `version
  control (Git)` — boolean searches hit either.
- Include the literal words recruiters search: "bilingual" / « bilingue »,
  the degree name, job-title synonyms.
- 5-7 skill rows is the sweet spot **when the candidate honestly has that
  many categories** — with fewer defensible categories, use fewer rows;
  SKILL.md rule 1 outranks any layout guideline. 8+ near-empty rows read as
  padding.
- A keyword in skills but absent from every experience bullet is a liability
  (SKILL.md rule 2): anchor, demote, or drop. Mechanical check: grep each
  skill item against the extracted bullet text — every 0-hit item must map
  to a deliberate demote/anchor decision, not an oversight.

## Verification commands

One command in any POSIX shell: `scripts/verify.sh cv.typ EXPECTED_PAGES
[FILL_MIN FILL_MAX]` runs everything below plus the fill measurement and
exits non-zero on any failure. The individual checks:

```
pdfinfo cv.pdf | grep Pages          # exact page count
pdftotext cv.pdf - | less            # reading order, label↔value pairing
pdftotext cv.pdf - | grep -n "20[0-9][0-9]"   # every date attached to its entry?
```

Red flags in the extraction: a lone year floating at the end (grid entry
without bullets — see trap above), skill labels grouped apart from their
values, spaced-out headings ("S O F T WA R E"), fragments of one line
interleaved into the next section (wrapped separator line).

Without poppler (e.g. bare Windows): page count = number of files produced by
`typst compile cv.typ p{p}.png`, or `pypdf`:
`python3 -c "import pypdf,sys; print(len(pypdf.PdfReader(sys.argv[1]).pages))" cv.pdf`.
For text extraction `pypdf` is a *degraded* fallback: verified on a real CV,
it injects spurious spaces inside words ("FORMA TION") that poppler does not —
indicative only; poppler's `pdftotext` is the reference extractor.

Without a typst binary at all: `pip install typst` ships no CLI but the
Python API compiles both formats (verified):
`python3 -c "import typst; typst.compile('cv.typ', output='cv.pdf')"` and
`typst.compile('cv.typ', output='p.png', format='png')` for the fill check.

## Human-scan rules (the other 30 seconds)

- First screen-height: name, target title, profile with the core stack
  bolded, start of the most relevant experience.
- Off-target current role → split sections so target-field experience leads
  (see SKILL.md step 4; skip the split when every job is on target).
- Dates right-aligned, bold, dark: recency is the most-checked datum.
- 1-page vs 2-page is an audience *and region* decision, not a content
  decision — regional norms win (SKILL.md step 3).
- **File name of the sent PDF**: `Firstname_Lastname_CV.pdf` (localized
  equivalent) — no accents, spaces, or version suffixes; some ATS uploaders
  choke on non-ASCII names and recruiters see the filename.
- Never include "References available upon request" — dated filler in every
  market; keep a separate reference list ready instead.
