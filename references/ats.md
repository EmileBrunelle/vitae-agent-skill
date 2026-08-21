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
- **A double `#h()` around a coloured separator glyph isolates it as its own
  paragraph** (verified, 8 families' Languages line: `#h(8pt)#text(fill:
  …)[•]#h(8pt)`): the glyph's colour change plus the two function-based gaps
  make poppler emit "…(fluent)" / a blank line / "•" alone / a blank line /
  "Third language…" instead of one paragraph — even when the line never
  wraps. Real text spaces (a literal space or `\u{2002}`/`\u{2003}` em/en-space
  characters) around the glyph do not trigger this; `#h()` does, colour or
  not. Fix: drop the `#h()` pair, use real space characters, and — to
  guarantee the glyph can never end a line alone if the row ever does wrap —
  wrap the glyph and the word that follows it in one `#box[...]` (verified on
  `gutter-rail`, extended to text glyphs): `…(fluent)\u{2002}#box[#text(fill:
  accent)[•]\u{2002}Third] language (native)`.
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
  date orphaned at the very end of the extraction. Detect with the grep below.
  **Fix — keep the grid, add text after the date** (verified on the template
  in every family): what anchors the date is *something following it in the
  extraction order*, not the absence of the grid. So an education entry uses
  the SAME entry helper as the jobs (title + right-flushed date on the grid
  row, institution + descriptor on the line under it) and extracts as
  `Degree Name` / `2015 – 2019` / `Institution — City · …` — no floating year.
  **Two conditions, both required** (verified by bisection): (a) a line of text
  *after* the date in the emission order — the institution + descriptor line;
  and (b) a date run about as **wide** as the other right-flushed dates on the
  page.
  **Refinement, measured on `gutter-rail`, and it is what the
  "position-dependent" part actually is**: condition (a) is not "a line of text
  follows", it is **a line that reaches under the date's own x-range**. Same
  page, same entry, only the descriptor's face changed: in the 9pt body sans it
  ended at x=452.7 while the date ran x=493-569 — 40pt of clear air under the
  date, which stayed its own cluster and was emitted at the very end. The same
  descriptor in the 8pt mono reaches x=532.6, overlaps the date column, and the
  date extracts in place. Widening the *date* does not help
  (`"Sep 2015 – Jun 2019"` still floated); widening the *following line* does.
  So when a year floats, compare the two x-ranges (`pdftotext -bbox`) before
  touching anything else, and fix it with a longer or wider descriptor — never
  by un-aligning the date. `"2015 – 2019"` and `"Graduated 2019"` extract in place; a bare
  `"2019"` or `"Jun 2019"` is narrow enough to fall outside the date column's
  x-range, becomes its own cluster and is emitted at the very end (verified
  both ways, and one family reproduced it on a bare year while five others did
  not — treat the narrow form as unsafe everywhere, not as a per-family
  quirk). Degree years may stay year-only in *content* terms: write the study
  range, or prefix the year ("Graduated 2019"). The
  older workaround (re-rendering the entry as a linear
  `Degree, Institution — 2019 · City` line) is **retired**: it fixed the
  extraction and broke the page, putting that one date mid-line while every
  other date on the CV was flush right. One date convention per document
  (`design.md`). The trap is POSITION-DEPENDENT (verified): it can also hit a
  normal grid entry that lands last before a page break, and it moves when
  content shifts — so re-run the date grep after every layout change; if a
  year still floats, add a following line (a one-clause descriptor) to that
  entry rather than un-aligning its date.
- **Inline "chips" — the verdict is split** (verified, both halves on the same
  dense page: the `mono-technical` skills block, six rows, 8.5pt mono keys):
  a per-item `box(fill: …)` — the tinted-pill look — is **still banned,
  reproduced**: every box becomes its own text cluster and `pdftotext`
  interleaves them across rows (`LANGUAGES = Python` / `TypeScript SQL
  JavaScript Bash` / `BACKEND & DATA = Django` / `FRONTEND = React` /
  `PostgreSQL REST APIs message queues` / …) — labels torn from their values,
  items interleaved across rows. A per-item `highlight(fill: …)` is
  **verified safe**, same page, same density, same chips: the tint paints
  behind the same text run, no new box, one cluster —
  `LANGUAGES = Python, TypeScript, SQL, JavaScript, Bash` /
  `BACKEND & DATA = Django, PostgreSQL, REST APIs, message queues`,
  byte-identical to the plain linear row. Two conditions come with the proof:
  (a) keep the separators OUTSIDE the tint (`.map(chip).join([, ])`) — without
  them the words still extract but the item boundaries are gone and a keyword
  filter reads one long run; (b) a chipped multi-word token that wraps still
  splits (`… CI/CD: GitHub` / `Actions)`), the ordinary wrap rule — wrap
  fragile tokens in `#box[…]` as anywhere else. Calibration lesson: this
  failure does not reproduce on a short synthetic test page — a two-row test
  that fits one line each extracts cleanly both ways. It needs a real dense
  page (six rows, several wrapping, a right-flushed date column above) to
  appear, so "chips are fine, I tested it" on a toy page is worthless — test
  extraction on the real page. The safe primitive is `chip()` in
  `templates/lib.typ`; it is a creative-register device, not a default.
- **A RUN of painted segments — a "statusline" — is verified safe** (measured
  on `gutter-rail`, whose whole contact line is one): five contact items, each
  painted with `highlight` (`chip`), the gaps between them plain spaces, each
  mark+value pair wrapped in `nb`, extracted **byte-identically** to the
  unsegmented version of the same dense page — `diff` clean over the whole
  document. Three conditions, all already in the chip rules above: `highlight`
  and never `box(fill:)`; **plain spaces between segments, never `h()`**
  (explicit spacing beside a painted run tears it, same as a box); and the mark
  inside the pair's `nb`. Note what the paint does *not* cover: a vector mark is
  an inline image box and `highlight` paints behind a text run only, so the mark
  always sits in the gap before its field — visually it reads as the icon+value
  pairing of a bar module, and no construction puts it under the tint.
- **A full-width tinted PANEL per section ("a tile") is extraction-safe, and
  usually not worth it** (measured on `hard-edge`'s page shape): wrapping each
  section body in a `block(fill:, inset:, radius:)` left the reading order and
  every label↔value pair intact — the only diff was re-wrapping, from the
  narrower measure. What killed it was the page, not the parser: at
  `inset: (y: 7pt)` over eight sections it cost a full extra page. Available as
  a boundary device for a family that budgets for it.
- **Two tiles SIDE BY SIDE (a two-column grid of panels) — rejected, with the
  constat** (measured, `gutter-rail`, two sections in one grid row): the reading
  order did *not* scramble at that size — poppler emitted the left tile whole,
  then the right one — so this is not the classic two-column failure. It fails
  on the other rule: halving the measure makes every structured row inside the
  tiles **wrap**, which is line integrity failing by construction, and each
  wrapped row then extracts as two fragments (`label evidence drawn from the CV
  itself, never a` / `bare adjective`). The safe form of the same idea is the
  panel entry above: tiles at **full width, stacked, with gaps**.
- **Stacked cells inside a single-ROW grid break label↔value pairing**
  (verified): a "reference row" of three label/value pairs, built as a
  single-ROW grid whose each cell stacked a small bold LABEL over its VALUE,
  extracted as all three labels first and all three values after them
  (`LOCATION` / `AVAILABILITY` / `WORK AUTHORIZATION` / `City, Region` /
  `Two weeks' notice` / `Authorized to work`) — the pairing the device exists
  for, destroyed. This refines the single-ROW rule above: a single-row grid
  is safe **when each cell is ONE line**; the moment a cell stacks two lines,
  the extractor sweeps across the row before it descends and the pairs come
  apart. Fix: one flowing paragraph with run-in labels.
- **A full-width row under a two-zone header gets its right end pulled into
  the other zone** (verified): with the identity block left and the contact
  column right, a reference row spanning the full measure below them
  extracted as `LOCATION City, Region` / `AVAILABILITY Two weeks' notice` /
  *the whole contact column* / `AUTHORIZATION Authorized to work`. poppler
  clusters by column before it reads by line, so a device that spans under a
  two-zone header must stay INSIDE one of the zones. Fix: put the row in the
  left cell.
- **A bordered `box(stroke: …)` around the skills LABEL breaks like a chip
  does** (verified): the label in a hard-bordered box tore the first two
  labels off their values and emitted them at the END of the section
  (`… METHODOLOGIES Agile / Scrum` / `LANGUAGES` / `BACKEND & DATA`). Same
  separate-text-cluster failure as a box around each item — it is the BOX
  that breaks it, not the position. Fix: a painted label (`highlight`), which
  stays inside the paragraph's run.
- **`h(…)` next to a painted label breaks it the same way** (verified, same
  page shape): `srow([#stag(cat)#h(4pt)], items)` — an `h(4pt)` inserted to
  widen the gap between a `highlight`-painted label and its items — tore
  `LANGUAGES` and `MENTORING` off their values and emitted them at the end of
  their sections. Explicit spacing beside a `highlight` breaks the run exactly
  as a `box` does. Fix: shrink the `extent` so the field hugs the label and let
  the paragraph's own word space be the gap.
- **Hyphenated compounds that wrap fuse in extraction** (verified):
  "motion-capture" breaking at the hyphen extracts as "motioncapture", which
  a keyword filter will not match. Write the unhyphenated form or wrap the
  token in `#box[...]`.
- No `tracking`/letterspacing on any text an ATS must read — it extracts as
  "S O F T WA R E" and breaks section classification.
- Decorative vector icons are safe (no text emitted), but never encode
  information only in an icon. Same for the platform marks (LinkedIn, GitHub,
  mail, globe) inlined as SVG path data: verified in all fourteen families'
  extraction, they emit nothing — the readable URL beside them is what the
  parser reads. An icon FONT is the unsafe version: it leaks private-use
  codepoints into the extraction — never ship one, inline path data only.
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

## Harvested devices — verdicts

Device-level calls gathered from a survey of published CVs, template
galleries and recruiter commentary — flagged as harvested-from-the-wild,
not measured here, except where noted.

- **Specialities line** under the name (5-7 mastered skills, small caps,
  separator-joined): safe, plain text, high 30-second-scan value; verified in
  extraction as whole words with separators intact. NO letterspacing (extracts
  as `N E X T`). It is CONTENT: rule 2 of SKILL.md applies to every item on it.
- **Language proficiency as plain CEFR/ILR-coded text**
  (`French — conversational (B1)`) beats every graphic meter: progress bars,
  dot ratings and donut meters are frequently unreadable to extraction and
  are named by recruiters as a template tell. Prefer the words.
- **Condensed "Early career" line** for roles past the detailed decade: safe
  and recommended — the mechanic that makes it safe is role first and years
  last IN THE SAME paragraph, so text always precedes the date and the
  orphan-date trap above cannot fire (unlike a bullet-less grid entry).
- **Location + availability/timezone line**: safe when inline in the body
  flow; a real trap when placed in an actual page `header:`/`footer:` field,
  because many parsers skip those regions entirely — anything load-bearing
  there is a bug, not a device. Same for contact info and dates.
- **Monogram of initials**: safe as real TEXT inside a drawn box; a trap as
  an image or logo — an image-rendered monogram is invisible to extraction
  and leaves a hole where the identity should be.
- **QR code**: invisible to every extractor, useful only on a printed copy,
  and split reception from recruiters. Not a device this skill offers.
- **An ordinal used AS the section label** (`01` alone, replacing the word):
  costs the reader speed and costs the ATS its section classifier. A
  numbered family keeps the conventional stem beside the number
  (`1 Experience`).
- **Vertical timeline rail / sidebar dates outdented into the margin**: the
  two-column extraction failure under another name. Not offered.
- One harvested claim corrected by our own measurement: platform-logo
  contact rows are commonly flagged as an extraction risk, and that verdict
  is about **icon FONTS and image-rendered marks** — inlined SVG path data
  was verified to emit no text in every family, and the readable URL beside
  it is what the parser reads. Never let the mark be the only carrier of the
  information.

## Verification commands

One command in any POSIX shell: `scripts/verify.sh cv.typ EXPECTED_PAGES
[FILL_MIN FILL_MAX]` runs everything below plus the fill measurement and
exits non-zero on any failure. `scripts/verify.py --tune cv.typ PAGES
FILL_MIN FILL_MAX` runs a page-fill loop by bisection on
`#set par(leading:, spacing:)` and writes the winning values — it does NOT
replace the gate; run the gate after it. The individual checks:

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
