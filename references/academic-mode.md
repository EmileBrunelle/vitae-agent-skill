# Academic mode

**Academic mode** applies when the document is an academic CV (SKILL.md states the switch); load [`references/fields/academic.md`](fields/academic.md) for the genre knowledge (sections, regional conventions, funding agencies, disciplines). It **replaces rule 5 and step 4 of SKILL.md, it does not relax them** — it has its own measured invariants, checked by `scripts/verify_academic.py`. The replacement invariant in one line: **the atom is the entry, not the section** — "no entry straddles a page break" stands in for "no section is ever split." One neutral gabarit, from `templates/academic/`; no family draw and no palette generation. Everything else in SKILL.md (rules 0-4, steps 0-3 and 5-8) still applies.

## Data source: structured file alongside FAITS.md

`FAITS.md` keeps its usual role: identity, appointments, education, and anything needing a provenance tag discussed with the candidate — same discipline as the skill's rule 1 (no fact without a source). It carries more weight here than in industry mode: an invented publication is not embellishment, it is research misconduct. Every publication entry additionally needs a public, verifiable identifier (DOI, arXiv ID, or publisher URL) — this is exactly the "what's the portfolio equivalent in this field?" question the skill already asks for any field.

The 200+ enumerated entries (publications, talks, grants, supervision, service) do not belong in `FAITS.md` line by line — they belong in a structured data file, readable by both the template engine and any future verification tooling without adding a dependency (TOML is a reasonable choice: readable natively by Typst's `toml()` and by Python's stdlib `tomllib`). Each entry should carry:
- `date` (mandatory — the first of the two invariants in [`fields/academic.md`](fields/academic.md)),
- `src` — the same provenance convention as `FAITS.md`,
- the fields the funding agencies ask for (role, amount, currency, period, peer-review status, author order, DOI/identifier).

This data file, not the rendered document, is the source of truth for section counts and ordering — any correctness check must compare the rendered output back against this file, never read the rendered output alone and call that verification.

## Correctness properties this genre must satisfy

These are properties a correct academic CV has, stated as rules for whoever builds or reviews this document — not a description of any particular checking tool.

- **A. Counts round-trip.** For every section, the number of entries declared in the data source equals the number of entries the rendered document actually shows. This is the single most valuable property: it catches an entry swallowed at a page break, broken list numbering, column interleaving on extraction, or a duplicated entry — and it verifies the document's actual purpose (a committee counts 25 articles; the document had better show 25). Where entries are numbered (common in math/CS, `[25]`, `[24]`…), the numbering must also be contiguous and monotonic.
- **B. Strict reverse chronology per section.** The sequence of years in each section is non-increasing, after a declared-length prefix of undated entries ("submitted," "forthcoming"). This is the most common real defect on a CV maintained by hand over many years, and it is a genuine failure, not a style preference — declare the prefix length explicitly for any section that is legitimately chronological in the other direction; never guess it.
- **C. No orphaned section heading at the bottom of a page.** The last line of content on a page is never a section or sub-section heading; a heading is always followed by at least two lines of its own entries on the same page.
- **D. No entry split across a page break.** The first line of content on every page (running head excluded) is either a section heading or the start of a new dated entry — never the continuation of one. This is the honest replacement for "no section ever split," applied at the entry level instead of the section level. It costs a last page that sometimes ends 1-3 lines short — with no fill target (see below), that cost is free.
- **E. Running head and pagination beyond 2 pages.** Every page carries the candidate's surname and "page n of N." An academic dossier gets printed, stapled, photocopied, and passed around a committee one page at a time — unlike an ATS-scanned industry résumé, there is no parser here that skips header/footer regions, so this is safe and expected in this genre even though the skill's industry-mode rule warns against putting anything load-bearing in a header/footer.

**What is measured and reported, never turned into a failure:** page count, last-page fill, prose-vs-list ratio, a per-section entry-count table (useful to the candidate too, as a quantitative summary of their own dossier).

## What does not apply here

- Fixed page-count targets, a paired 1-page/2-page deliverable.
- Keyword/ATS rules, action-verb bullet conventions.
- Any design system or visual-boldness dial — the single neutral gabarit above is the goal here, not variety.
- The job-search companion guide — out of scope for this genre.
- **There is no fill target, not even a floor on the last page — dropped, not loosened.** A last page that ends short because the next entry didn't fit is correct, not under-filled — there is no number here that anything could be measured against.
- **Prose-to-list ratio is not a pass/fail check.** It varies legitimately by discipline (humanities produce more prose) and by target (a descriptive agency CV can be 100% prose).
- **No section-boundary spacing checks** (the kind of device-quorum or whitespace-ceiling checks industry mode runs at section boundaries). This genre's atom is the entry, not the section boundary; those checks have no matching population here.
- **"Every entry is dated" is not a standalone text-extraction check.** On extracted text alone there's no reliable way to tell where one entry ends and the next begins. This requirement lives at the data-source level instead (the date field is mandatory there) and is verified through property A, by count, not by scanning raw text for year-like tokens.

## Gate (step 6)

At step 6, academic CVs are checked with `scripts/verify_academic.py` (run it, never open it) instead of the family-diff and fill checks of [`6-verify.md`](steps/6-verify.md).

The gate reads no word of any language. An entry that starts with a status word instead of a year ("In press", "Sous presse") is recognised only if the data file declares the word in `[meta] entry_status`, as a case-insensitive whole word (or words; list every inflection you print: Soumis, Soumise...), never guessed; with none declared only a year starts an entry, and a section with `undated_prefix` above 0 FAILs rather than miscounting. The `[counts]` check looks for each declared section's heading as the template prints it (English). A CV that prints other headings declares them in an optional `[headings]` table, with the same keys and nesting as `[counts]` (`education = "Formation"`, `[headings.publications]` `journal = "Articles de revues"`), matched as a literal, case-insensitive whole line; `affiliations` may also be declared for the extra "Affiliations and languages" heading; any other unknown key FAILs naming it. A counted section whose heading is not found is a plain FAIL naming that heading and saying to declare it under `[headings]`; no language is guessed or reported.
