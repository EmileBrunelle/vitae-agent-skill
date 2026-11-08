# Contributing to vitae

Thanks for helping. This project is bilingual (English and French).

## Language

Issues, PR descriptions and review comments can be written in English or French. Files in the repository ([`SKILL.md`](SKILL.md), references, code, comments, commit messages) stay in English, except [`README.fr.md`](README.fr.md).

## What helps most

- **Field packs** — like [`references/fields/software-dev.md`](references/fields/software-dev.md), for other fields (nursing, finance, trades, ...).
- **Regional market files** — every country is verified individually, from a source. Never generalise one candidate's experience to a country.

## Culture: measured, not eyeballed

Every claim must be verifiable, with a source or a command that reproduces it. "It looks fine" is not evidence; a gate that passes is.

## Before opening a PR

Run from the repository root (needs `typst`, `pdftotext`, Python 3 with Pillow, pypdfium2 and pypdf, and the fonts in [`references/fonts.md`](references/fonts.md)):

1. Everything except spec validation, in one command:
   ```
   tests/run_all.sh            # add --quick for selftests + 3 templates
   ```
   It runs both self-tests, the 29 templates against their fill targets (`pick_design.FAMILIES[f]['page']['fill']`; `swiss-grid/resume-2page.typ` at `2 94 96`) and the spacing fixtures with their gates, on a scratch copy so the repo stays clean. It prints one `PASS`/`FAIL` line per check, keeps going after a failure and exits non-zero if any failed. Every line must be `PASS`. CI runs the same script on every PR and attaches the 29 PDFs and PNGs as an artifact.
2. Spec validation, from a directory named `vitae` (the validator requires the directory name to match the skill name):
   ```
   npx skills-ref validate .
   ```

## Branching

`main` always holds the latest released, tested version: `npx skills add/update` installs the default branch, so anything merged to `main` ships to every user at once. Fork, work on a topic branch, open the PR against `main`. PRs are merged at release time with the version bump and CHANGELOG entry, not one by one. There is no long-lived dev branch.

## Rules for templates

- The repo holds no symlinks (claude.ai rejects zips containing them, and Windows checkouts break them): family templates import the shared files by relative path (`#import "../../lib.typ": *`), so they compile only with `--root` on an ancestor (by hand, from the repo root: `typst compile --root . templates/families/<family>/resume.typ out.pdf`) — `verify.py` adds it for you. `pick_design.py --init` rewrites that import to `"lib.typ"` in the starter it copies out. Never add a symlink.
- A change to `templates/lib.typ` must keep the 29 templates pixel-identical, or the PR must say why not.

Python scripts must type-check with mypy (config in `mypy.ini`, run `python3 -m mypy`) and target Python 3.11 or later.

## Reference file format

Applies to `references/regional/**`, `references/certifications/**` and `references/fields/**`, except `*-common.md`, `overview.md` and stubs under 80 words (`tests/unit/test_reference_format.py` checks the mechanical rules).

- H1 is `# <Genre>: <Subject>`; genres: Market, Education, Regulated professions, Health professions, Academic, Outbound, Law, Field pack, Certifications, Foreign workers, Gulf nationalisation, Gulf credentials. Add a genre only if none fits.
- The first paragraph is `Loaded on demand when <trigger>.`, optionally followed by a `Read together with` sentence linking the parent file and at most one scope sentence.
- Market files open with `## At a glance` (bullets in this order when present: Paper, Photo, CV language, Personal data, Length, then others).
- Common section names when the topic exists: `## Protected titles`, `## Application package`, `## Personal data and law`; country-specific sections after.
- Every sourced fact carries its S### id, in the form `(Publisher, « Title », consulted YYYY-MM-DD, S###)` or plain S### where the sentence already names publisher, title and date. The date verb is `consulted`, never accessed, retrieved, read or consulté.
- No URLs in `references/` (they live in `docs/sources.md`).
- Confidence: a sourced fact carries its S###; an unsourced fact kept as a warning carries `LOW, unsourced`; an unchecked point carries `not checked`. No HIGH, MEDIUM, unverified, not sourced, bare LOW or LOW confidence.

## Where to edit

[`SKILL.md`](SKILL.md) is a slim entry point and `tests/run_all.sh` fails above 13000 bytes. Add or change step detail in `references/steps/N-<slug>.md` (academic mode in [`references/academic-mode.md`](references/academic-mode.md), traps in [`references/known-traps.md`](references/known-traps.md)); keep `SKILL.md` to the rules and the per-step skeleton. Every `references/`, `scripts/` or `templates/` path cited must exist (also gated).

- Markdown prose is not hard-wrapped: one paragraph or list item per line.

## Version bump

A user-visible change bumps all three together: `version:` in [`SKILL.md`](SKILL.md), the README badges (`assets/badges/status-beta.svg` and `statut-beta.svg`, regenerated from shields.io), and a [`CHANGELOG.md`](CHANGELOG.md) entry.
