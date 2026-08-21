---
name: vitae
description: Build ATS- and human-optimized résumés/CVs in Typst — exact page control (1-page and 2-page versions), no section ever split across pages, measured page fill, machine-parseable layout, regional and multilingual conventions, adversarial review loop, optional job-search guide. Use when the user asks to create, redesign, improve, translate, or tailor a CV/résumé, or to evaluate one against a job posting.
license: MIT
compatibility: Requires typst 0.13+ and Python 3 with Pillow. poppler-utils (pdftotext, pdfinfo) recommended, falls back to pypdf. Run python3 scripts/verify.py --doctor to diagnose. Optional - LibreOffice/soffice, only for editable copies (.docx/.odt) derived from the compiled PDF.
metadata:
  author: EmileBrunelle
  version: "0.2"
  repository: https://github.com/EmileBrunelle/vitae-agent-skill
allowed-tools: Bash(python3:*) Bash(typst:*) Bash(pdfinfo:*) Bash(pdftotext:*) Bash(sha256sum:*)
---

# vitae — résumés that survive both the ATS and the 30-second human scan

You are building a résumé that will be read twice: once by a parser, once by a tired
human giving it 30 seconds. Every decision below serves one of those two readers.
Work from facts only — a résumé is a legal-adjacent document about a real person.

**This skill's repo may be public.** Never commit candidate data: no names,
employers, facts, or anecdotes traceable to a person — every lesson gets
generalized before it lands in these files.

**Field-agnostic.** The method applies to any profession; software development is
the reference case. If `references/field-<target>.md` exists for the candidate's
field (e.g. `field-software-dev.md`), load it in step 4 — it layers market depth
on the generic method. Otherwise substitute the field everywhere, building the
substitutions from four questions: (a) what is this field's portfolio
equivalent (GitHub, licenses, publications, a case log)? (b) where do its real
keywords live — read 3-5 current postings on the target market's dominant job
board (web-search, don't guess)? (c) which titles are protected, per which
regulator (health, law, finance, engineering are all regulated somewhere — see
`references/regional.md` for the verification method, its list is not
exhaustive)? (d) who screens — recast the reviewer personas (recruiter stays;
"hiring manager" becomes head nurse, practice owner, …) and the section names
("Nursing Experience").

## Non-negotiable rules

1. **Never invent facts.** No metrics, technologies, dates, or achievements the
   candidate did not provide. Public facts about *employers* are fine. When a
   fact is missing, leave a placeholder and tell the user what to ask the
   candidate. Degree names and acronyms are facts too: never expand an
   acronym from memory — reuse the source's exact wording or the
   institution's official program name. Even in unattended/automatic mode
   with no round-trip available, never paper over a gap with plausible
   wording — the placeholder stays visible in the deliverable. **This rule
   outranks every layout or convention guideline** — when "5-7 skill rows" or
   "month+year dates" would require padding or guessing, follow this rule and
   flag the gap instead.
2. **Every listed keyword must be defensible in an interview.** A skill with no
   experience bullet behind it reads as keyword stuffing and contaminates the
   rest. Three honest options: demote it (skills list only, never in the
   profile/highlights), anchor it (e.g. "Java-intensive coursework" under
   Education — gives an interview answer, at the cost of advertising that it
   is academic only), or drop it entirely. Anchoring pays off when target
   postings list the skill as an "or"/nice-to-have; dropping is better when
   the tailored application gains nothing from the keyword.
3. **Résumé and online profiles must tell the same story.** Recruiters
   cross-check LinkedIn (and GitHub for developers) first: titles, dates,
   durations, stack. Flag any discrepancy to the user instead of silently
   picking a side.
4. **Respect protected professional titles.** Reserved titles exist in many
   fields and jurisdictions ("engineer" across Canada via provincial acts,
   "Ingenieur" in Germany/Austria, state-registered health professions, etc.).
   Degree names are always safe; job titles are not. See `references/regional.md`.
5. **No section may split across a page break, and every page is filled by
   measurement, not by eye.** Fill target (from `scripts/measure_fill.py`,
   measured on the full page height): last ink row at
   **(100 − bottom-margin%) − 0..2%** — e.g. ~94-96% for a 1.2 cm bottom margin
   on US Letter, ~91-93% for a 2 cm margin on A4. This applies to every page,
   including the last page of a multi-page version. **Anti-filler clause:** if
   hitting the target would require a non-substantial bullet or cramped
   spacing, the content does not honestly fill that pagination — change the
   page count instead of forcing it.

## Workflow

0. **Check the environment.** Run `python3 scripts/verify.py --doctor` (any
   platform) — a read-only dependency preflight that prints the exact install
   command per platform, official repos first; get
   the user's go-ahead before running any install. Fonts are **not** chosen by
   hand here: step 4's `pick_design.py` draws the pair from the chosen
   family's pool and checks it against `typst fonts` for you — never assume a
   face is installed, and never let its warning stand. Prefer open-license fonts (Google
   Fonts / SIL OFL) over pure system fonts: their provenance (the distro
   package name, or the Google Fonts link) is easy to document in the
   hand-off; bundle the font files themselves (`fonts/` dir +
   `typst compile --font-path`, or upload alongside the source on
   typst.app) only when the recipient cannot install fonts locally. After
   each compile, glance at stderr: a missing font only warns and silently
   falls back.
1. **Gather facts.** Source documents (old CV, LinkedIn, user answers).
   **Track provenance per fact** from the start, one tag per line
   (`- <fact> — src: original-cv|linkedin|user|verified-in-work`): a fact
   relayed by the person commissioning the CV is not a fact confirmed by
   the candidate. If a source is not plain text (`.docx`, an exported PDF),
   convert it first — `pdftotext` for PDFs, `pandoc -t markdown` for
   `.docx`, or ask the user to paste the text — and eyeball the converted
   output before extracting facts: reading binary or scrambled content
   invites hallucinated facts (rule 1). Build a fact sheet: identity,
   links, jobs (title, org, dates month+year, mode, bullets), education,
   skills, languages. Ask for gaps; never fill them yourself. If only a
   year is known, ask for months; keep year-only and flag it if the
   candidate cannot supply them — but first try the institution's known
   academic calendar to bound the months, confirmed by the user (the
   regional file lists known cases). LinkedIn PDF exports are unreliable
   artifacts (mixed languages, mojibake in place names, page markers):
   verify on the live profile before flagging "profile errors" to the user.
   Verify organizations' official name spelling on their own site — clubs
   and events especially. When two sources spell the same fact differently
   (diacritics, a degree's casing or wording), keep the most recent/
   authoritative source's wording and flag the discrepancy to the user —
   never merge silently; for credential names specifically, the issuing
   institution's official wording outranks recency. Application history
   needs precise verbs (applied ≠ was offered ≠ received). When the
   candidate has verifiable public work product (code repos, publications,
   a case log), check claims against it directly — strongest anchor
   available; the field pack gives the specifics.
2. **Pick region and language.** Infer a default from the source material —
   city/country in the header, phone country code, language and spelling
   variant, posting URLs — state it and confirm; never silently decide. The
   *target job market* always overrides where the candidate lives (a Montréal
   candidate applying to London jobs gets UK conventions).
   Load `references/regional.md` (router:
   universal rules + orientation matrix), then ONLY the target market's file
   in `references/regional/` (e.g. `north-america.md`, `france.md`) — don't
   load the other markets. Apply the language and spelling of the *job
   market*, not the user's chat language. If the market has no file, do not
   infer from training data — verify with a current source or ask, and label
   the assumption in the deliverable.
3. **Decide versions.** Default deliverables: a 1-page and a 2-page version per
   language, and both of them **print-safe (light background), which is the
   canonical build and the one that ships** — nobody controls whether the
   recipient prints or photocopies the PDF, so look at the render in grayscale
   too. A screen-first dark build is a *supplement* only, on explicit request
   and for a controlled context (a portfolio page): same source, palette
   toggle, contrast recomputed on the real background, and the fill/separation
   gate stays on the light build because a dark page is all ink
   (`references/design.md` § The destination support). Audience heuristic (North-American markets): 1-page for startups,
   walk-ins and spontaneous applications; 2-pages for established companies and
   consulting firms. **A stricter regional norm from step 2 always wins** (e.g.
   France: 1 page; UK: 1 page early-career). When the regional standard asks
   for more pages than the honest content fills, scale typography and margins
   up rather than inventing content, and say so in your final message.
   Versions are living: if the same posting type blocks two or more reviewed
   applications on framing alone (title, ordering) — not a one-off — build
   that dedicated variant once instead of prescribing repeated manual
   retailoring. Keep ONE canonical source tree; delivered copies are
   regenerated from it (companion-guide.md, Delivery package) — a
   hand-maintained working copy plus a hand-maintained delivery copy WILL
   drift.
4. **Draft from the template.** Copy `templates/resume.typ` **and
   `templates/lib.typ` beside it** (the hand-off is two files — Typst has no
   bundler; `lib.typ` holds the verified shared mechanics, the devices stay
   per-family), load the field pack if one exists, keep the design system's
   invariants (`references/design.md`). Once `pick_design.py` has named the
   family, read that family's **reference implementation** in
   `templates/families/<family>/resume.typ` — all fourteen are there, each one
   gate-passing, with `resume-pair-b.typ` beside it showing the same recipe on
   its second font pair. It is faster and safer to start from the family's own
   worked file than to rebuild its devices from prose.
   `templates/families/swiss-grid/resume-2page.typ` is the worked **2-page**
   example (deliberate break, `runhead`, both pages measured). For the look, do **not** choose freely
   — an agent choosing freely reconverges on the template's own combination and
   every candidate ends up with the same CV. Run:
   `python3 scripts/pick_design.py --name "<candidate>" --field <field>
   --market <market> --career early|mid|senior [--photo] [--conservative]
   [--creative]` and apply the design family it prints; add `--emit-typ` to get
   the ready-to-paste Typst preamble for the drawn recipe (palette, fonts,
   gabarit, icon lines, `#set` block) — it deliberately does **not** emit the
   devices, because those are the recipe. **`--market` is documentation only**
   — it is echoed in the report and changes nothing: a conservative market
   must be passed as `--conservative` (the `--field` table also flips it on by
   itself for law, finance, accounting, insurance, government…).
   Build it by following that family's recipe in
   `references/design.md` § Design families (heading device, skills-block
   shape, accent role, contact icons, platform marks, header composition,
   verified leading/spacing/`above`). **Fourteen families in four registers**,
   and the pool is widened until at least **five** are eligible for any
   profile. The `creative` register (`hard-edge`, `avant-poster`, `gutter-rail`)
   is **never in the default pool**: it is unlocked by a creative target field or
   by `--creative` (an explicit request from the candidate or user, never
   inferred), and a conservative market caps it straight back out.
   `gutter-rail` carries a second lock on top: its current only reads to a
   software audience, so it needs a technical field **plus** the explicit ask. A creative family is
   held to the *same* gate as every other — "beautiful **and** parseable" is
   the whole bar, and it does not soften.
   The script also draws the
   **secondary parameters**, all of which are part of the anti-clone system —
   apply them, don't re-choose: the **font pair** from that family's pool
   (`FONTS` in the script is the single source of truth; it checks local
   availability and prints the provenance of anything missing — never let a
   font warning stand; two families also draw a third face, a metadata
   monospace), the **section labels** (the lexical skeleton is a fingerprint
   too), the list marker, on a **duotone** family the second hue with its own
   named jobs, and three things that change the page before a word is read:
   the family's **gabarit** (its own margins, body size and *derived* fill
   target — do not assume 94-96%), its **default section order** (a target
   market's convention always overrides it), and whether it carries a
   **specialities line** (four families do; on those, every item on that line
   is content and rule 2 applies to it in the most prominent position on the
   page). Where a family declares its own **variant** axis (one does), apply the
   drawn variant too. A different font pair shifts the fill: re-run the tuning loop with
   `scripts/verify.py --tune cv.typ PAGES FILL_MIN FILL_MAX`, which bisects
   `#set par(leading:, spacing:)` instead of you guessing — the printed
   leading/spacing is a starting point. If `--tune` says the target is
   unreachable, widen its bounds before you touch any device — the bounds are
   two positional arguments after `FILL_MAX`, e.g.
   `scripts/verify.py --tune cv.typ 1 88 96 0.45 1.40`. A losing search leaves
   the file untouched, so a failed `--tune` never costs you the family's own
   rhythm.
   Fresh fonts beyond the pool: only on the user's explicit request, or when
   nothing in the pool is available — then follow design.md § Font pools
   (vetting checklist, no over-used display defaults, add the winner back into
   `FONTS` once it passed the gate). The draw is deterministic per candidate,
   so the 1-page, 2-page and translated versions share one look. The user may
   override with an explicit family or their own combination — an explicit
   choice always wins; silence does not. Without python3, use the POSIX
   fallback in the script's docstring (`sha256sum` + modulo over the eligible
   families in alphabetical order, then the family's default accent and
   marker) — same family, default secondary parameters.
   **Derive `--career` from the fact sheet** — years of experience, whether
   this is a first job, the seniority of the titles — and the market from
   step 2's regional file and the employer type. **Never from age, birth year,
   graduation year used as an age proxy, or any other demographic datum**: the
   skill does not ask for age and does not infer from it (anti-discrimination
   conventions). The default is `early`, which leans modern.
   **Colour audacity dial** (`--audacity`, and `scripts/gen_palette.py`):
   default `sober`. It is raised only on the explicit request of the candidate
   or user — never inferred by the agent from anything about the person or
   their workplace — and a conservative target market caps it back down
   (`references/regional.md`); a market never raises it.
   Shipping the template's own combination (bordeaux `#7d2231`, accent tick +
   full-width hairline under an UPPERCASE accent title, `Category: items`,
   Carlito body + Montserrat headings) is a defect — Montserrat is also one of
   the over-used faces design.md bans as a *display* face, which is one more
   reason the template's look is a starting point and never a deliverable. The bar the result must clear is
   design.md's **non-recognition** test: a recruiter who has seen two CVs from
   this skill must not recognise the third, and no page may pass for a consumer
   tool's default template.
   Before writing any job title onto the page, check each title in the fact
   sheet against the protected titles in `references/regional.md` and the
   target market's file — the wording on the source CV does not by itself
   authorize reusing a reserved title.
   Read `references/typst-primer.md` (1 minute) before drafting, and again
   after ANY compile error, before retrying: it covers every construct the
   template uses and the exact errors agents actually hit; don't guess
   syntax, test with `typst eval`. If the primer doesn't cover the error,
   don't try random variants — consult up-to-date documentation by whatever
   means are available (web search for the official Typst docs, a docs MCP
   if one is configured) and fold the lesson back into the primer.
   Structure notes: the "target-field experience / other professional
   experience" split exists only to keep an off-track role from leading the
   page — when every job is on target, use a single experience section.
   For French output, change the `skill()` helper to `#cat~:` (non-breaking
   space before the colon). Employer descriptor line under each role;
   evidence-based soft-skill lines instead of bare adjective lists.
   Long careers (15+ years): condense old roles into one "Early career"
   block — one line per role (title, org, years), no bullets, linear entry
   variant — and detail only the recent decade; if honest content still
   overflows 2 pages and the market tolerates it (academic, DACH +
   attachments), a third page beats cramming. Career changers with under ~1
   year in the target field: lead with an evidence-anchored skills/projects
   section before the chronological timeline instead of letting an off-track
   role lead the page.
5. **Write bullets.** Action verb first (mood/tense per region; current role in
   present tense in every tense-based convention), one strong keyword bolded
   per bullet (max two), no authority inflation: *led / owned / guaranteed*
   only where the candidate truly had final responsibility — otherwise
   *contributed / collaborated / strengthened*. Contribution verbs survive
   interviews; inflated ones die there. Before moving on, diff every bullet
   against the fact sheet: any number, technology, mechanism, or hedge
   ("environ", "~") that differs from what the candidate said gets reverted
   or flagged — embellishing while rephrasing is the most common rule-1
   violation, and it survives every mechanical check. **Aim each bullet at one
   line** wherever the honest content allows it — that is what the 30-second
   scan reads; two lines are fine for a bullet that earns them, three means
   the bullet is two bullets. Prose (the Profile) wraps freely: that is its
   job. The hard half of this rule — structured lines never wrap — is checked
   on the render in step 6 (design.md § Line integrity).
6. **Verify mechanically** (loop until all pass; re-run after EVERY edit).
   Run the MECHANICAL subset in one command — `scripts/verify.sh cv.typ
   EXPECTED_PAGES [FILL_MIN FILL_MAX]` (POSIX wrapper, two lines, execs
   into verify.py) on Linux/macOS/WSL/Git Bash, or `python scripts/verify.py
   cv.typ EXPECTED_PAGES [FILL_MIN FILL_MAX]` directly on bare Windows — it
   exits non-zero if any check fails; never skip it after an edit. **Paste
   the gate's full output verbatim into the session before delivering** —
   this is the anti-circumvention check: a summary ("gate passed") is not
   proof, and a result that was never run cannot be pasted. Either way, the
   items further down this list (contrast recompute, date order, the
   fact-sheet diff, the visual look) are never covered by the script and
   stay manual:
   - `typst compile cv.typ` then `pdfinfo cv.pdf | grep Pages` — exact count.
   - `python3 scripts/measure_fill.py page.png` on rendered PNGs — target per
     rule 5, and it is the **family's own** target, derived from the family's
     bottom margin (94-96% for the dense gabarits, 92-94% for the airy ones):
     `pick_design.py` prints it. `verify.py --tune` reaches it by bisection. Tune leading/spacing/section gaps, never `v(1fr)` canyons. The
     same script reports the white-gap spectrum the gate judges: section
     boundaries must be the tallest internal white runs and measure ≥ 2× the
     median run, no run may pass 5% of page height, and a run over 3.5% is a
     hole unless it is a boundary (design.md § Invariants).
   - `pdftotext cv.pdf -` — reading order sane, no orphaned dates, skill lines
     intact, and dates within each section in reverse-chronological order.
     Full checklist and known extraction traps: `references/ats.md`.
   - Recompute the contrast of the accent as actually rendered (not the
     hex you intended) against its background, with design.md's formula —
     must still clear 4.5:1.
   - Diff every bullet against the fact sheet again — step 5's check, but the
     drafting agent self-checking once is not enough; re-verify it here.
     (The hiring manager's fact diff in step 7's review is the third
     checkpoint — deliberate, not drift.)
   - Confirm the document actually carries the design family that
     `pick_design.py` drew (or the family the user imposed explicitly): the
     family's heading device, its skills-block shape, its accent role, its
     contact-icon style, its font pair, its **gabarit** (margins, body size and
     the fill target derived from them), its **section order** and its
     specialities line if it has one — not just the accent. Re-run the script
     with the same arguments and diff its output against the `.typ`. None of the three
     clone markers may survive: UPPERCASE headings over a full-width accent
     rule, a `Category: items` skills block, accent on role title + rules +
     links.
   - Render PNGs and *look at them*: no ugly breaks, consistent apostrophes,
     no widows, body text comfortably readable at printed size, accent
     crisp against white and still legible converted to grayscale.
     Wherever a **painted surface meets a vector mark** (a chip or badge beside
     an icon), crop that band at 300dpi (`pdftoppm -r 300 -png -x -y -W -H`) and
     look again: a tint edge slicing through an icon is invisible at page scale
     and no gate check can see it (measured on `gutter-rail`'s statusline —
     design.md § 14, Header).
   - **Line integrity** (design.md § Line integrity): on the render, no
     **structured** line wraps onto a second line — every skills/stack row,
     the education entry's descriptor line, the Languages line, the
     header/contact lines, the specialities line. Fix by splitting one row
     into two with fewer items each (preferred — it costs the page nothing),
     by shortening the label, or by the row's measure. Prose and bullets are
     step 5's business, not this check's.
     This one is a **visual** check on the PNG (the LOOK pass above), not a
     gate check: `verify.py` cannot see a wrap and will pass a file that has one.
   - **Non-recognition, brand clause** (design.md § The final bar): look at
     the page and ask *could a reader name a company from this?* A recipe
     that reproduces one brand's signature combination of border, shadow,
     shape and palette fails the bar exactly as a stock template does.
   - **One date convention per document**: every date on the page sits where
     the family puts it — the education entry uses the same entry helper as
     the jobs, and its date is a *wide* run ("2015 – 2019", not a bare
     "2019", which drops out of the date column in extraction:
     `references/ats.md`). A date placed differently from the others is a bug,
     not a variant.
7. **Adversarial review.** Never deliver without this pass — a mechanical
   PASS is not a review. Run `references/reviews.md`: 3 core reviewers plus
   one per target market segment (recruiter 30-second scan, hiring manager of
   the field, ATS expert, plus one per segment with an invented but realistic
   posting) — the market-segment reviewers are part of this FIRST pass, not
   an optional later round. Spawn every reviewer with an explicit cheap model
   (`model: haiku` or `sonnet`) — a fan-out inheriting an expensive main-loop
   model burns quota fast. Give them rendered PNGs *and* sources. Apply only
   findings that survive cross-examination; findings demanding invented
   facts become questions for the user. After applying findings, go back
   through step 6 before delivering. Once that final PASS holds, write the
   manifest: `sha256sum *.typ > .vitae-manifest` — the trigger for the
   external-edit trap below.
8. **Deliver.** PDFs plus `.typ` sources (one-minute retailoring per
   application is a selling point). For a hand-off to the candidate, build
   the self-contained archive per `references/companion-guide.md`'s Delivery
   package section (rebuild/package scripts, README, final fact-sheet
   validation step). When the person commissioning the CV is not the
   candidate:
   - Every deliverable aimed at the candidate (guide, README, emails, file
     and asset names) is written in the candidate's language, never the
     requester's.
   - Questions for the candidate are diffed against the fact sheet before
     sending (never ask what is already known), rephrased in plain language
     (never a raw reviewer finding), kept short, and sent in the candidate's
     language.
   - Do not hand off the final package while open questions could still
     change its content.

   Optional companions — build them with `references/companion-guide.md`:
   job-search guide, cover-letter templates, LinkedIn alignment checklist.
   Rule 1 applies to companions too: no salary range or market statistic
   without web verification, and label them indicative.


## Known traps (each verified empirically; details live in the references)

- Multi-row data grids, and single lines of `•`-separated items that wrap,
  both scatter fragments in extraction → linear paragraphs / bulleted lists
  (`references/ats.md`).
- Letterspacing (`tracking`) on headings extracts as "S O F T WA R E" → none
  on ATS-read text; single-row alignment grids are safe, data grids are not.
- Year-only dates break ATS duration math → month+year ranges (unless the
  candidate truly cannot supply months — rule 1 wins, flag it).
- A `job()`-style entry with no bullets can orphan its date at the end of the
  extraction → check with the grep in `ats.md`; use a linear one-line entry
  variant if it happens.
- Typst markup (`#box`, `*bold*`) inside a helper's *string* argument renders
  literally → pass content in `[brackets]` when markup is needed.
- `#`, `$`, `[`, `]`, `~`, `@` in generated prose are Typst syntax → escape.
- Straight + curly apostrophes mixed (strings passed to helpers bypass smart
  quotes) → normalize to typographic ones everywhere.
- One line added to a full page cascades an unbreakable section and changes
  the page count → re-verify after every edit.
- One accent color doing six jobs stops signaling → only the two or three
  jobs the chosen family assigns it; on a duotone family, **1-2 jobs per hue**
  and hue B stays subordinate (design.md § Duotone).
- Full-width accent rule under every UPPERCASE heading reads as 1997 *and* is
  clone marker #1 → use the family's device.
- "Pick a fresh accent/combination" does not work: an agent told to choose
  freely reconverges on the template's look, and the first CV of every user of
  this skill comes out a twin of all the others (this is why
  `scripts/pick_design.py` and design.md's families exist). Same failure one
  level up when the user asks for something off-roster: follow design.md
  § Guided creation — anchor the composition in a real design current found by
  SEARCH, name your first idea and then build a different one, and hold the
  result to the full gate. Devices come from harvested real examples, never
  from the agent's imagination. The clone signature
  is three markers at once — UPPERCASE heading + full-width accent rule,
  `Category: items` skills, accent on role title + rules + links.
- A fixed-width `#box` label column in the skills block fuses label with
  values in extraction when the label fills it, and wraps + interleaves when
  it doesn't (verified both ways) → use one of the family shapes. Any **box**
  around skills content breaks the same way — one `box(fill:…)` per item (the
  chip look) *and* a single `box(stroke:…)` around the label alone both tore
  the rows apart on a dense page. But a **painted** chip is safe: `highlight()`
  puts the tint behind the same text run, no new box, and the row extracts
  byte-identically to a plain linear row — keep the separators outside the tint
  (`references/ats.md`, `templates/lib.typ` § chip). The failure does NOT
  reproduce on a short synthetic page: test extraction on the real one.
- A **single-ROW** alignment grid is safe only while each cell is ONE line: a
  cell stacking a label over its value made every label extract before every
  value. And a full-width row *under* a two-zone header gets its right end
  pulled into the other zone — poppler clusters by column before it reads by
  line (verified both, `references/ats.md`).
- Contact info, dates or an availability line placed in a page `header:` /
  `footer:` field: many parsers skip those regions outright. Keep everything
  load-bearing in the flow. Same verdict for a monogram rendered as an image,
  a QR code, and any skill/language meter drawn as a bar or a dot rating.
- A bullet-less entry's date floats to the end of the extraction unless BOTH
  hold: text follows it in emission order (the institution/descriptor line)
  and the date run is as wide as the other right-flushed dates (verified).
- A `line(length: 100%)` inside a `box` resolves to the *available* width, not
  the box content's — a "short underline" silently becomes a full-width rule.
  Use `box(stroke: (bottom: ...))`, or `context measure()` to size a drawn
  shape to its own text (verified).
- `block(breakable: false)` shrinks to its CONTENT width, so `align(center)`
  inside it centres on the block and not on the page — centred section titles
  drifted up to 150px apart. Add `width: 100%` (verified).
- A recipe that depends on a font feature needs it in the whole fallback
  chain: `#smallcaps` on a font without real `smcp` renders as plain text with
  no warning at all (verified: Libertinus Serif, Noto Serif, STIX Two Text,
  New Computer Modern and Montserrat have it; Open Sans, Caladea and
  Liberation Serif do not).
- Section boundaries that don't read at arm's length — an INVARIANT, and the
  gate FAILs on it: the section gap must be ≥ 2× the heading-to-body gap AND
  sharply stepped above the job-entry gap — raising the *contrast* between
  the two, not the absolute gap (which overflows the page or opens a canyon).
  Measured on the render: tallest internal white run ≥ 2× the median. A
  family whose device carries ink (a filled bar, a heavy rule) legitimately
  sits near that floor; a family with no device needs 4:1 or more. See
  design.md § Invariants and § Rules common to every family.
- Two named anti-references, both pass/fail against the rendered page
  (design.md § Anti-references — there are exactly two, no third gets
  invented). **Anti-Word-97**: thin full-width rule under every heading,
  default Times-ish serif, underlined non-link text, default round bullets,
  flat leading, default border grays, ornaments. "Could this have come out of a
  1990s word processor's default template?" must be answerable with no.
  **Anti-AI-slop**, the risk when an agent is asked to "make it look creative":
  stacked or gaudy gradients, blur and glow, fake-grunge display faces,
  decorative geometric confetti, the unchosen default face, maximalism with no
  hierarchy, symmetric-centred everything, and fake data made to look like data
  (skill meters, dot ratings, donut charts — also a rule-2 violation). The test
  is one question per element: *does this element do work the reader can name?*
  Audacity is a small number of decisions, never an accumulation. There is no
  anti-Canva: template galleries are a legitimate source of expressive
  vocabulary, and the constructions there that fail are excluded by `ats.md` on
  measured technical grounds, not on taste.
- A neutral gray beside a warm accent reads as a mismatch → derive `ink` from
  the accent (design.md § colour), don't drop in `luma(90)`.
- Hyphenated compounds that wrap ("motion-capture") extract fused; the
  orphan-date trap is position-dependent and moves when content shifts
  (see ats.md — re-grep dates after every layout change).
- A `.vitae-manifest` mismatch at session start (or any known edit by another
  tool/session) voids every previous PASS → re-run the verify gate on every
  version and the cross-file consistency audit (`references/reviews.md`)
  before re-delivering.
