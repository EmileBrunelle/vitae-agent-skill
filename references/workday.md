# Workday (myworkdayjobs) — measured résumé-parser behaviour

Measured 2026-10-28 on ONE tenant (a Canadian financial institution, `wd10` host), 7 test
uploads of the same CV (baseline T0, variants A-F). None of this is checkable
statically, so `verify.py` has no gate for it; treat it as a post-upload
checklist. Overlap with the Eightfold section of `ats.md` is deliberate
(same family of defects, different fixes).

## Scope and version

- `wdN` in the URL is the data-centre pod (WD10 = Canada), NOT a product
  version. Workday is single-version SaaS with two releases a year, so the
  parser should be the same for every employer.
- Form configuration (required fields, degree picklist contents) does vary per
  employer. Expect the parse to match; expect the form around it to differ.
- 1 tenant measured: re-test when a new release lands or on a second tenant.

## Test protocol

- Delete the application, then start a NEW one for every test. Resuming the old
  one keeps fields from the previous parse.
- Upload through "Autofill with résumé" (do not submit). Screenshot the
  Experience and Education forms (title, employer, dates, description; school,
  degree, dates, field of study).
- Change one thing per test file against the baseline.

## Measured behaviours

Experience
- One line `Title — Employer · dates`: the employer after the em dash is lost
  and titles are truncated (a two-word title cut to its first word).
- Reordering to `Employer — Title · dates` does not help: Workday puts the
  FIRST segment into Job Title and drops the rest. The single line is the
  problem, not the order.
- One field per line (Employer / Title / Dates) fixes titles, start dates and
  a job that was missing altogether.
- Everything before the first recognised employer (the Profile/Summary) is
  pasted into job 1's description, and an institution named in it (a
  university) is taken as job 1's employer.
- Most employers stayed empty in every layout and format. The one employer
  that was recognised may simply be in Workday's company database. 1
  observation: hypothesis, not a rule.
- Only the English « Present » (capital P) marks a job as in progress (rule 6);
  « présent », « aujourd'hui », « à ce jour » do not tick "I currently work here".
- Location is filled from `City (Region)` for some jobs (always for in-progress ones, rule 6).
- Trailing sections (projects) may be swallowed into the last job's
  description.

Education
- Education on one line drops a school.
- A city-only descriptor (`City (Region) · N weeks`) becomes a phantom school
  and shifts that entry's dates.
- A year-only range may collapse (2026-2026 for a programme ending next year).
- No degree is ever selected from the picklist, in any variant.

## Results

| Test | Change vs baseline | Result | Pages |
|---|---|---|---|
| T0 | none (one-line entries, profile, city in descriptors) | employers lost, titles cut, a job missing, a school missing, phantom school, no degree | 2 |
| A | `Employer — Title · dates` | no gain, worse: first segment became Title | 2 |
| B | experience on 3 lines | titles, start dates, missing job fixed; 1 employer filled (the two-word one) | 3 |
| C | education on 3 lines, no city | phantom school gone, missing school back, dates fixed; no degree | 3 |
| D | T0 minus city in education descriptors only | phantom school and date fixed; missing school NOT back | 2 |
| E | B + C | gains cumulative; job 1 description = profile text, employer = the university | 3 |
| F | E minus Profile | job 1 employer no longer the university; description correct. Best | 3 |
| T_G | F's content uploaded as plain text (.txt) | parsed identically to F | - |
| T_H | F plus explicit key-value labels ("Employer:", "Period:") | WORSE: dates lost, schools dropped. Never label | - |
| T_I | F's content, same CV in ENGLISH (parse-only layout) | employers filled (2 of 3 small companies), two-word title kept intact, "currently work here" ticked for "present" jobs; but non-US credential names dropped as schools (5 to 2), one employer line glued to the previous job's description (phantom job titled with the next meta line's city) | - |
| T_J | T_I with the Education section swapped for the same entries in French (heading still "Education") | ZERO schools recognised; the whole French education block dumped into the last job's description; employers shifted (a school name became the last job's employer) | - |

Language (T_I, T_J, measured 2026-10-28): in English Workday filled employers
(2 of 3 small local companies), kept a two-word title intact (French: truncated
to one word) and ticked "currently work here" for "present" jobs, none of which
it ever did in French in any layout or format. English has its own defect:
non-US credential names (regional diplomas, "Undergraduate coursework") are
dropped as schools, and an employer line after a long bullet list can be glued
to the previous job's description. Workday parses the document in ONE language:
never mix languages inside the parse copy (T_J). For a non-English CV, expect
employers to stay empty. T_H: labels make it worse, never label fields.

T_G (historical, before the legal-name fix of rule 1 below): the remaining defects
(most employers empty, a title truncated, Degree never filled) looked like Workday
entity recognition rather than PDF reading, so no FORMAT or LAYOUT change fixed
them. Content did: the full legal name filled Company 4/4 (rule 1), and
"degree, program" lines brought Field of study to 3/5 (rule 2). Degree itself
stays 0/5. The PDF stays the recommended parse copy.

Remaining after F and the rule 1-2 fixes: some titles truncated, location of job 1,
"currently work here", every Degree, one end date, and employers left empty when
no legal name is given.

## Recommended recipe: two-file strategy

0. Build the parse-only copy in the language of the POSTING, entirely in that
   one language (sections, headings, entries). One copy per posting language.

1. Build a parse-only copy of the CV: experience and education stacked one
   field per line (Employer / Title / Dates; School / Degree / Dates), NO
   Profile/Summary section, no city in education descriptors. Page count is
   irrelevant for this file.
2. Upload it to "Autofill with résumé". Fix by hand what remains: employers,
   truncated titles, end dates, degrees (location and "currently work here" are automatic
   for in-progress jobs, rule 6: check them).
3. Delete it from the Résumé/CV attachment field and upload the real CV before
   submitting.

The real CV is never changed for Workday.

## Template support

Every template (`templates/resume.typ`, each family's `resume*.typ`) has a
built-in parse-only mode, selected by a `sys.inputs` flag:

    typst compile --input workday=1 resume.typ resume-workday.pdf

With the flag, each `entry` is stacked one field per line (Employer / Title /
Dates; education School / Degree / Dates) followed by the descriptor line and
bullets, the Profile/Summary section is omitted, and a leading city is dropped
from education descriptors. Volunteer/involvement sections keep the
normal entries; a Projects section is DROPPED (rule 3). The page is pinned to
a 40cm-wide, one-page-tall layout (rules 4-5). Without the flag the output is unchanged.

Section titles are normalised (lowercase, accents stripped, spaces collapsed)
and matched against built-in lists in EN, FR, DE, ES, IT, PT (profile/objective:
Profil, Sommaire, Objective, Personal Statement, Executive Summary, Objectif,
Kurzprofil, Perfil, Profilo...; education: Formation, Etudes, Ausbildung, Formacion,
Formazione, Formacao...; keep: Volunteer Work, Leadership, Benevolat, Implications,
Engagement, Ehrenamt, Voluntariado, Volontariato... Projects/Projets are NOT kept:
they are dropped, see rule 3). Profile and keep titles match exactly; education
titles also match as a whole-word stem, so compound titles ("Education &
Certifications", "Education et formation", "Formation et certifications") count
as education. A title in none
of them is not matched (profile kept, education city kept): add it with comma
lists, `--input workday-omit="Mon profil"`, `--input workday-edu="..."`,
`--input workday-keep="..."` (normalised the same way, added to the lists).
A title given as content is matched on its plain text. A projects title
(`projects`, `projets`, `projekte`, ...) is dropped unless it is also given to
`--input workday-keep="..."`, which keeps it as plain entries.

City stripping in education descriptors only removes the first " · " segment
when it has a place shape: letters, spaces and `.'-`, FOLLOWED BY ", Region"
or " (Region)", at most 40 chars, no digits. "Toronto, Ontario · 5 weeks" and
"Montréal (Québec) · …" are stripped; "Honours · …", "Cum laude · …" and
"GPA 3.8 · …" are kept. Limit: a bare city with no region ("Montréal · …") is
kept, and an all-letter "X, Y" phrase that is not a place would be stripped. Other limits: the section name is never reset, so an
entry placed between sections inherits the previous section's kind; the
margin-index `earlyline` only acts on a string `org` split on " — ". The mechanics are in
`templates/lib.typ` (`workday`, `entry`, `wd-section`); each template's one hook
is `#let section = wd-section(section)`. Notes given as Typst content (not a string) are never city-stripped. Academic CV template: not covered.

## Parse-copy rules from the second measurement round (real tenant, 2026-10)

Source: the CV author's test log (lots 2-3, variants L1/L6b/L11/L12 and the final
recipe). Status: V = verified by upload on one tenant, T = template behaviour
(built and checked in every family), C = content rule (not template-enforceable).

1. (V, C) Employer as the FULL LEGAL NAME with its suffix ("Acme Inc.", "Acme inc.",
   "Acme Ltd") filled the Company field 4/4; without it, most stayed empty. Doc-only:
   ask the user for each legal name and use it in the parse copy only (the real CV keeps
   the usual name). Pitfalls:
   - Never append a suffix blindly. Map EACH employer to its confirmed legal name and
     leave non-companies (a personal project listed as an entry, e.g. "Recipe-Planner",
     a school, a freelance activity) untouched.
   - The legal name is NOT translated. An English parse copy uses the registered name
     ("Fabrication Exemple inc.", not "Example Manufacturing inc.") unless the user confirms
     an English registered version.
   The template implements no suffix logic: if a mapping is ever automated it must be an
   explicit user-supplied list, never `org + " Inc."`.
2. (V, C) Education line "degree, program" ("Baccalauréat, informatique"): Field of
   study filled 3/5 vs 0/5 (Degree itself stays 0/5). Dates must stay textual/year-based: numeric MM/YYYY dates were
   REJECTED and killed Field of study. Field of study is a closed per-tenant list with
   fuzzy matching: there is no universal label, check each by hand.
3. (V, T) Projects section: no Workday field; it was swallowed into the last job's
   description. Dropped from the parse copy by default; `workday-keep` overrides.
4. (V, T; L11 relevé DOM-verified) Job descriptions are copied as the physical PDF lines, so the parse copy is a
   40cm-wide page: every bullet is one line (zero mid-sentence breaks verified). LIMIT:
   40cm holds ~240 characters per line at body size; a longer bullet wraps and Workday
   splits it mid-sentence. After building, check that no bullet wrapped (`pdftotext
   -layout`: every bullet one line) — if one did, shorten it (best: a 240-char bullet is
   too long for the human CV too) or raise the width in `wd-page-x`. `width: auto` was
   tried and rejected: `100%`/`fr` columns collapse in 10 of 15 families. The
   header stays at Letter content width, otherwise the right-hand contact column is read
   AFTER the experience. Check reading order with `pdftotext` in DEFAULT mode, not only
   `-raw`. (margin-index puts its section title above the body in this mode for the
   same reason.)
5. (V for the drop, observed on a capture only for the fix, not DOM-verified) Workday
   DROPS THE LAST LINE OF EACH PAGE (seen in L7/L10/L11); the fix, a single
   page of free height (`height: auto`, template behaviour; read on a capture in L12), is not DOM-checked. Typst gotcha: `set` inside `if {}` is
   block-scoped, so families use `#set page(..wd-page) if workday` right after their
   `#set page(...)`. A family with a manual `#pagebreak()` must skip it in workday mode, and its running
   head (`runhead`) too (swiss-grid `resume-2page` does).
   Rule 4's wd-page assumes US Letter; a family with side margin x != 1.5cm passes it
   (`wd-page-x(x)`), so the header keeps its own content width.

6. (V, T; L13/L16/L17, DOCX and PDF autofill, one tenant: a financial-sector employer, 2026-10-28) An
   in-progress job is recognised ONLY when its end is written « Present » (English,
   capital P). Then Workday fills Location from the descriptor line, ticks "I currently
   work here" and leaves End date empty. With « présent », « aujourd'hui », « à ce jour »
   it leaves Location empty, never ticks the box and invents an end date = the current
   month. (With a past end date Location was filled, L16: it is the in-progress parsing.)
   Template: in workday mode, stacked Job/Education entries rewrite a trailing present-type
   word in a string date run to « Present » (`wd-present` in `lib.typ`; en present/current/now,
   fr présent/aujourd'hui/à ce jour/en cours, es actualidad/presente, pt atual/presente,
   it presente/oggi, de heute/derzeit; case-insensitive, end of string). Volunteer/keep
   sections and content-typed dates are left untouched. The real CV keeps its own language.
7. (V) Location punctuation is stripped: « Montréal (Québec) » and « Montréal, Québec »
   both become « Montréal Québec ». Nothing to do.
8. (V) LinkedIn URL: filled from the PDF, empty from a DOCX even with a real hyperlink: one
   more reason the PDF parse copy is the default (PDF value DOM-verified, L18/L19).
9. (V, T; L18/L19, a financial-sector tenant, PDF) Month names: French « févr. » is not recognised and
   falls back to January; the full « février » is read as 2 (workday mode rewrites it).
   « janv. », « mars », « avr. », « juin », « sept. » are read correctly; « déc. » is
   untested. An ENGLISH month in a French copy (« Feb 2014 – Present ») breaks the whole
   date line: dates empty, line pushed into the description — keep months in the
   copy's language (only « Present » is the exception, rule 6).

Also: one language per parse copy (T_J), and the two-file strategy above.

### Manual checklist after Autofill

Never filled or unreliable, always check: Degree (never filled), Field of study,
end year of an in-progress program, start/end MONTHS (rule 9), Languages, Skills.
For in-progress jobs, Location and "I currently work here" are automatic with « Present »
(rule 6): just check them. Location and the box stay manual for finished jobs and for
a parse copy whose date was typed as content.
