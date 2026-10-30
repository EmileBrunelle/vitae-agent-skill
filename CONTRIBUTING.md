# Contributing to vitae

Thanks for helping. This project is bilingual (English and French).

## Language

Issues, PR descriptions and review comments can be written in English or French. Files in the repository (`SKILL.md`, references, code, comments, commit messages) stay in English, except `README.fr.md`.

## What helps most

- **Field packs** — like [`references/field-software-dev.md`](references/field-software-dev.md), for other fields (nursing, finance, trades, ...).
- **Regional matrix rows** — every country is verified individually, from a source. Never generalise one candidate's experience to a country.

## Culture: measured, not eyeballed

Every claim must be verifiable, with a source or a command that reproduces it. "It looks fine" is not evidence; a gate that passes is.

## Before opening a PR

Run from the repository root (needs `typst`, `pdftotext`, Python 3 with Pillow and pypdf, and the fonts in [`references/fonts.md`](references/fonts.md)):

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

- Never edit `templates/families/*/lib.typ`: they are symlinks to `templates/lib.typ`.
- A change to `templates/lib.typ` must keep the 29 templates pixel-identical, or the PR must say why not.

Python scripts must type-check with mypy (config in `mypy.ini`, run `python3 -m mypy`) and target Python 3.11 or later.

## Where to edit

`SKILL.md` is a slim entry point and `tests/run_all.sh` fails above 13000 bytes. Add or change step detail in `references/steps/N-<slug>.md` (academic mode in `references/academic-mode.md`, traps in `references/known-traps.md`); keep `SKILL.md` to the rules and the per-step skeleton. Every `references/`, `scripts/` or `templates/` path cited must exist (also gated).

- Markdown prose is not hard-wrapped: one paragraph or list item per line.

## Version bump

A user-visible change bumps all three together: `version:` in `SKILL.md`, the README badges (`assets/badges/status-beta.svg` and `statut-beta.svg`, regenerated from shields.io), and a [`CHANGELOG.md`](CHANGELOG.md) entry.

## En français

Les issues, descriptions de PR et commentaires de revue peuvent être en français ou en anglais; les fichiers du dépôt restent en anglais (sauf `README.fr.md`). Les contributions les plus utiles sont les packs de domaine et les lignes de la matrice régionale, chaque pays vérifié séparément à la source. Tout doit être mesuré et vérifiable. Avant une PR : les deux `--selftest`, les 29 gabarits contre leurs cibles de remplissage, les fixtures avec `verify.py --gates`, et `npx skills-ref validate .`. Ne modifiez jamais les `lib.typ` des familles (liens vers `templates/lib.typ`). `main` contient toujours la dernière version publiée et testée (`npx skills` installe la branche par défaut) : forkez, travaillez sur une branche thématique, ouvrez la PR vers `main`; les PR sont fusionnées à la publication, avec le changement de version, sans branche dev durable. Le détail des étapes va dans `references/steps/`, jamais dans `SKILL.md` (limite de 13000 octets vérifiée par `tests/run_all.sh`). Une version change `SKILL.md`, les badges et `CHANGELOG.md` ensemble.
