---
name: vitae
description: Build ATS- and human-optimized résumés/CVs in Typst — exact page control (1-page and 2-page versions), no section ever split across pages, measured page fill, machine-parseable layout, regional and multilingual conventions, adversarial review loop, optional job-search guide. Use when the user asks to create, redesign, improve, translate, or tailor a CV/résumé, or to evaluate one against a job posting.
license: MIT
compatibility: Requires typst 0.13+, poppler-utils (pdftotext, pdfinfo), and Python 3 with Pillow. Run scripts/check_env.sh (POSIX shells) or scripts/check_env.ps1 (Windows 11+) to diagnose; pip-only fallback documented in references/ats.md.
metadata:
  author: EmileBrunelle
  version: "0.1"
  repository: https://github.com/EmileBrunelle/vitae-agent-skill
allowed-tools: Bash(typst:*) Bash(pdfinfo:*) Bash(pdftotext:*)
---

# vitae — résumés that survive both the ATS and the 30-second human scan

You are building a résumé that will be read twice: once by a parser, once by a tired
human giving it 30 seconds. Every decision below serves one of those two readers.
Work from facts only — a résumé is a legal-adjacent document about a real person.

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
   candidate. **This rule outranks every layout or convention guideline** —
   when "5-7 skill rows" or "month+year dates" would require padding or
   guessing, follow this rule and flag the gap instead.
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

0. **Check the environment.** Run `scripts/check_env.sh` (any POSIX shell — Linux, macOS, WSL/Git Bash) or
   `scripts/check_env.ps1` (Windows) — read-only doctors that print the exact
   install command per platform; get the user's go-ahead before running any
   install. Pick fonts from `typst fonts` output — never assume. After each
   compile, glance at stderr: a missing font only warns and silently falls back.
1. **Gather facts.** Source documents (old CV, LinkedIn, user answers). If a
   source is not plain text (`.docx`, an exported PDF), convert it first —
   `pdftotext` for PDFs, `pandoc -t markdown` for `.docx`, or ask the user to
   paste the text — and eyeball the converted output before extracting facts:
   reading binary or scrambled content invites hallucinated facts (rule 1).
   Build a
   fact sheet: identity, links, jobs (title, org, dates month+year, mode,
   bullets), education, skills, languages. Ask for gaps; never fill them
   yourself. If only a year is known, ask for months; keep year-only and flag
   it if the candidate cannot supply them.
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
   language. Audience heuristic (North-American markets): 1-page for startups,
   walk-ins and spontaneous applications; 2-pages for established companies and
   consulting firms. **A stricter regional norm from step 2 always wins** (e.g.
   France: 1 page; UK: 1 page early-career). When the regional standard asks
   for more pages than the honest content fills, scale typography and margins
   up rather than inventing content, and say so in your final message.
4. **Draft from the template.** Copy `templates/resume.typ`, load the field
   pack if one exists, keep the design system's invariants
   (`references/design.md`) but give the candidate their own look: pick a
   fresh combination of the free axes (accent, heading device, font pairing,
   header layout) from design.md — shipping the template's default
   combination is a defect, every candidate's CV must be distinguishable
   from every other one this skill produced.
   If your knowledge of Typst is shaky — and after ANY compile error, before
   retrying — read `references/typst-primer.md` (1 minute): it covers every
   construct the template uses and the exact errors agents actually hit;
   don't guess syntax, test with `typst eval`.
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
   violation, and it survives every mechanical check.
6. **Verify mechanically** (loop until all pass; re-run after EVERY edit).
   In any POSIX shell run the whole gate in one command —
   `scripts/verify.sh cv.typ EXPECTED_PAGES [FILL_MIN FILL_MAX]` — it exits
   non-zero if any check fails; never skip it after an edit. The individual
   checks (run these on bare Windows):
   - `typst compile cv.typ` then `pdfinfo cv.pdf | grep Pages` — exact count.
   - `python3 scripts/measure_fill.py page.png` on rendered PNGs — target per
     rule 5. Tune leading/spacing/section gaps, never `v(1fr)` canyons.
   - `pdftotext cv.pdf -` — reading order sane, no orphaned dates, skill lines
     intact. Full checklist and known extraction traps: `references/ats.md`.
   - Render PNGs and *look at them*: no ugly breaks, consistent apostrophes,
     no widows.
7. **Adversarial review.** Run `references/reviews.md`: 2-4 parallel reviewer
   subagents (recruiter 30-second scan, hiring manager of the field, ATS
   expert, plus one per target market segment with an invented but realistic
   posting). Spawn every reviewer with an explicit cheap model
   (`model: haiku` or `sonnet`) — a fan-out inheriting an expensive main-loop
   model burns quota fast. Give them rendered PNGs *and* sources. Apply only findings that
   survive cross-examination; findings demanding invented facts become
   questions for the user.
8. **Deliver.** PDFs plus `.typ` sources (one-minute retailoring per
   application is a selling point). Optional companions — build them with
   `references/companion-guide.md`: job-search guide, cover-letter templates,
   LinkedIn alignment checklist. Rule 1 applies to companions too: no salary
   range or market statistic without web verification, and label them
   indicative.

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
- One accent color doing six jobs stops signaling → titles + org names only.
- Full-width rule under every heading reads as 1997 → short accent bar +
  hairline.
