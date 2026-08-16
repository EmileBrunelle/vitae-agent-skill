# Companion job-search guide

An optional multi-page PDF delivered alongside the CVs. Offer it once the CVs
are final; it reuses their design tokens so the package reads as one system.

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
6. **Interview preparation** — the 8 near-certain screening questions with
   response angles, 5 STAR stories mapped to the candidate's real experiences
   (list the facts they must retrieve — never write the stories for them),
   technical topics by likelihood, questions to ask, salary ranges
   (web-verified, explicitly qualified as indicative), follow-up etiquette.
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
