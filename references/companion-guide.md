# Companion job-search guide

An optional multi-page PDF delivered alongside the CVs. Offer it once the CVs
are final; it reuses their design tokens so the package reads as one system.

## Voice and boundaries

- **Write for a smart junior peer.** No hand-holding of the obvious (a
  developer knows to match the posting's language); keep the genuinely
  non-obvious (public-sector merit criteria, ATS mechanics, extraction
  traps). The failure mode is oscillating between assuming genius and
  assuming idiocy — calibrate once and hold it.
- **Never mention the requester.** When a friend/parent commissions the
  package, the guide belongs to the candidate — the requester's name, tools,
  or testimonials don't appear in it.
- **Never script disclosure of medical or personal reasons** for a career
  gap. Default interview script = neutral ("pause for personal reasons, now
  fully resolved" + the comeback story). Naming a burnout/illness is the
  candidate's optional choice — present it as such, never as the script.
- **Don't expose employer internals** that reflect poorly (aging hardware,
  budget constraints, internal tooling gaps) in the CV or the guide. Keep
  the resourcefulness story generic ("built the local server infrastructure
  from scratch under tight budget") — naming the embarrassing detail helps
  nobody and can burn the reference.
- Salary figures in the target market's notation (`79 000 $` in Québec, not
  "79 000 dollars"); verify recommended events actually admit non-students
  before listing them (university career fairs often don't).

## Structure that tested well (adapt chapters to the field)

1. **Synthesis & strategy** — positioning in one sentence, priority targets,
   what to avoid, which CV version to send where (table), green/yellow/red
   flags to spot in postings, pre-application checklist, classic pitfalls,
   timeline.
2. **Target-employer directory** — real, verified employers grouped by
   segment, 1 line each: what they do, why this candidate matches, practical
   hint. End with "how to find more" (local directories, alumni networks).
3. **LinkedIn & professional brand** — profile fixes (CV↔LinkedIn consistency
   first), ready-to-paste headlines, an "About" template built only from the
   fact sheet, skills to pin, discreet open-to-work settings if employed,
   recommendation-request template.
4. **Portfolio plan** (field-dependent) — one concrete showcase project with a
   weekly plan, the perfect README/case-study structure, profile hygiene.
5. **Cover letters & application process** — when a letter matters, a full
   template whose key paragraph defuses the candidate's main red flag,
   spontaneous-application email, networking message, tracking system,
   channels ranked by effectiveness, realistic weekly cadence.
6. **Interview preparation** — the hiring process shape per employer type
   (studio / SME / bank / consulting / public-sector merit boards), the 8
   near-certain screening questions with response angles, technical-test
   prep by format (algorithm drills, take-home, live pairing), 5 STAR
   stories mapped to the candidate's real experiences (list the facts they
   must retrieve — never write the stories for them), technical topics by
   likelihood, the AI-tools question, salary negotiation basics, questions
   to ask, what never to say, before/during/after logistics, salary ranges
   (web-verified, explicitly qualified as indicative), follow-up etiquette.
   Same depth expectation applies to cover letters: several targeted
   templates beat one generic one, plus a 10-minute personalization
   checklist and the classic fatal errors.
7. **Professional-title question** if relevant (licensing pathways: worth it
   or not, what is legal to write) — see regional.md.

## Authoring at scale (multi-agent)

- One chapter per parallel subagent, spawned with an explicit cheap model
  (`model: haiku` or `sonnet`) — up to 7 chapters inheriting an expensive
  main-loop model is a quota incident. Each gets: the candidate fact sheet
  (immutable, "invent nothing"), the chapter outline, and a STRICT output
  format: `## ` sections, `### ` subsections, `- ` bullets, `*bold*`, no
  tables, no code blocks, no emojis. That format converts mechanically.
- Chapters citing the outside world (employer lists, salary ranges) must
  web-verify and still be labeled "starting points, revalidate when applying".
- Templates written in the candidate's voice (letters, About) contain claims
  the candidate must validate — list them explicitly in your final message.

## Verdict tables and layout

- Simulated-posting verdicts: at most THREE clearly-labeled, color-coded
  levels (e.g. Yes — apply now / Possible — retailor first / Later — unlock
  action X first). Five shades of "limite" read as noise; every negative
  verdict must point at its unlock action.
- Guides under ~20 pages skip the table of contents — it steals a page and
  crowds the first chapter.
- Force a page break per chapter only when chapters are page-sized; a
  restructure into fewer, denser chapters beats 15 half-empty ones. Sticky
  headings (no forced break) work until the user wants clean chapter starts —
  ask which they prefer when the rendering shows the trade-off.

## Assembly (markdown → Typst)

- Convert: `## ` → `= `, `### ` → `== `; escape in body lines: `#` `$` `[`
  `]` `~` `@` (Typst syntax); keep `*bold*` as-is.
- One document: CV design tokens + `#show heading` rules (level 1 = chapter
  style + `pagebreak(weak: true)`), title page, then
  `#outline(title: [...], depth: 1)` — depth 1: a level-2 outline of a
  15-page guide overflows its page and looks worse than it helps.
- Footer with document name + page number.
- Verify like a CV: compile, check the page count is sane, render a few pages
  and look at them (TOC balance, no orphan headings). Fill targets do NOT
  apply to the guide — normal document rhythm is fine.
- After every edit round, re-check internal cross-references: chapter
  numbers cited in prose ("see chapter 4") silently rot when chapters are
  merged or reordered — grep every "chapitre/chapter N" against the real
  heading list, including in the delivery README.

## Derived editable formats

If the candidate needs an editable copy, GENERATE it from the Typst source —
never hand-maintain a second copy; a hand-maintained editable file and the
canonical `.typ` source will drift. Pandoc has no Typst reader, so route
through a direct conversion of the compiled PDF (`soffice --convert-to docx
cv.pdf`). This is lossy (layout, fonts, spacing shift) — the derived copy
needs an eyeball pass against the PDF before it ships.
Default to `.docx`: the format with real compatibility across mobile,
Google Docs, and WPS. Offer `.odt` only when the candidate's own tooling is
known and specifically calls for it. Never deliver both at once — if the
candidate edits one and sends the other, the two silently diverge. Warn the
candidate that the derived copy does not repass the full verification grid
(step 6/7) — treat it as a one-way export, not a parallel deliverable.

## Delivery package (when the user hands the dossier to the candidate)

- Ship a self-contained archive: ready-to-send PDFs (each pre-named to the
  neutral `Firstname_Lastname_CV.pdf` inside a per-variant folder), sources,
  fonts/assets, the verification scripts, and a README.
- Include a one-command `rebuild.sh` (compile + verify + copy into the
  ready-to-send folder) driven by a small variant manifest (variant name →
  source file → expected pages → output folder; verify.sh needs the page
  count per variant), and a `package.sh` = rebuild everything + archive —
  regeneration must not require remembering the toolchain.
- The README explains: which CV to send where (and why 1-page vs 2-page),
  what the typesetting tool is and why it was chosen, the methodology that
  makes the CVs solid (fact sheet, ATS verification, measured fill,
  adversarial reviews), install instructions for the candidate's OS, and —
  when AI tooling built the package — an honest transparency note.
- Archive format follows the recipient's platform (tar.gz for a Linux user,
  zip otherwise).
- **Final README step: the candidate validates the fact sheet line by line
  before the first application** (provenance tracked since step 1 makes this
  a checklist, not a re-interview). In the delivered copy, provenance tags
  use generic roles only — the "never mention the requester" rule applies to
  the fact sheet too.
