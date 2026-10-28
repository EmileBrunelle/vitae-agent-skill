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
- One-word employer names stayed empty in every layout; only a two-word name
  was recognised. 1 observation: hypothesis, not a rule.
- "present" does not tick "I currently work here".
- Location is filled from `City (Region)` for some jobs.
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

Remaining after F: most employers empty, one title still truncated, location
of job 1, "currently work here", every degree, one end date.

## Recommended recipe: two-file strategy

1. Build a parse-only copy of the CV: experience and education stacked one
   field per line (Employer / Title / Dates; School / Degree / Dates), NO
   Profile/Summary section, no city in education descriptors. Page count is
   irrelevant for this file.
2. Upload it to "Autofill with résumé". Fix by hand what remains: employers,
   truncated titles, location, "currently work here", end dates, degrees.
3. Delete it from the Résumé/CV attachment field and upload the real CV before
   submitting.

The real CV is never changed for Workday.

## Template support

The vitae templates have no Workday mode yet. Minimal change (guidance, not
implemented): a stack helper in `templates/lib.typ` that renders an entry's
fields one per line, plus a `sys.inputs` flag (e.g. `--input workday=1`) that
selects it and suppresses the Profile section and education cities. Build the
parse-only PDF from the same source with that flag.
