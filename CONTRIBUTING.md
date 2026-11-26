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
   python -m pytest -q -n auto tests/integration    # add --quick for 3 templates and no fixtures; drop `-n auto` without pytest-xdist (slower, sequential)
   ```
   It runs both self-tests, the SKILL.md gates, the 29 templates against their fill targets (`pick_design.FAMILIES[f]['page']['fill']`; `swiss-grid/resume-2page.typ` at `2 94 96`), the `--doctor` simulations, the verify behaviour checks and the spacing fixtures with their gates (and that the fixtures match `tests/fixtures/gen.py`), on a scratch copy so the repo stays clean. It needs `pytest` (and `pytest-xdist` for `-n auto`); checks whose tool is missing are skipped with a reason. `--vitae-out DIR` keeps the template PDFs and PNGs in `DIR/pdf` and every check's log in `DIR/log` (default: a temp dir); Parallelism is pytest-xdist's: `-n auto` (or `-n N`), one scratch copy `DIR/work-<worker>` per worker, no `-n` = sequential. Every test must pass. CI runs the same command on every PR and attaches the 29 PDFs and PNGs as an artifact. Ruff, mypy and `tests/unit` are separate steps (`ruff check scripts tests evals`, `python -m mypy`, `python -m pytest -q -n auto tests/unit`).
   Before pushing, run it through `tests/ci_fonts.sh` (`tests/ci_fonts.sh python -m pytest -q -n auto tests/integration`): the host's fonts can differ from CI's (Fedora's Caladea is not Ubuntu's), which moves templates at the edge of the fill window. The script fetches the CI font set once into `~/.cache/vitae-ci-fonts` (pinned like `.github/actions/fonts`) and runs the command in `bwrap` with the host fonts hidden; it needs `bwrap` and `typst`.
2. Spec validation, from a directory named `vitae` (the validator requires the directory name to match the skill name):
   ```
   npx skills-ref validate .
   ```

### Mutation testing (local, not in CI)

`pip install mutmut` (3.8.1 used; into any env, it is not a dependency of the skill), then from the repository root (the wrapper is bash: WSL on Windows):

```
tests/mutmut.sh run --max-children 4     # ~3 min; then: tests/mutmut.sh results | show <mutant> | browse
```

The scope is `[tool.mutmut]` in `pyproject.toml`: `source_paths` (the modules to mutate, written `src/vitae/...`: mutmut only strips a leading `src.`, so `tests/mutmut.sh` links `src -> scripts` for the run) and `pytest_add_cli_args_test_selection` (the test files that run). To widen it, add the module to `source_paths` and the test files that import it to the selection. Survivors are either equivalent mutants (no behaviour change: case-insensitive regex keys, `encoding="UTF-8"`, unread initial values) or test gaps; kill the latter with a behaviour test, never one that mirrors the code. Current scope: `verify/review_record.py` (95 %), `verify/jsonout.py` (97 %), `verify/cv.py` (98 %), `verify/registry.py` (100 %); 1577 of 1628 mutants killed, 49 survivors and 2 timeouts (a mutant that loops forever). Every survivor left is equivalent: UTF-8 spelling variants of `encoding=` (`UTF-8`, `UTF-8-SIG`; a dropped `encoding=` is killed by `tests/unit/test_verify_locale.py`, which reads non-ASCII files under `LC_ALL=C -X utf8=0` in a subprocess), case-insensitive regex and field keys, no-op arguments (`split(None)`, `maxsplit`, `ensure_ascii=None`), and initial values that are overwritten before any read.

## Branching

`main` always holds the latest released, tested version: `npx skills add/update` installs the default branch, so anything merged to `main` ships to every user at once. Fork, work on a topic branch, open the PR against `main`. PRs are merged at release time with the version bump and CHANGELOG entry, not one by one. There is no long-lived dev branch.

## Rules for templates

- The repo holds no symlinks (claude.ai rejects zips containing them, and Windows checkouts break them): family templates import the shared files by relative path (`#import "../../lib.typ": *`), so they compile only with `--root` on an ancestor (by hand, from the repo root: `typst compile --root . templates/families/<family>/resume.typ out.pdf`) — `verify.py` adds it for you. `pick_design.py --init` rewrites that import to `"lib.typ"` in the starter it copies out. Never add a symlink.
- A change to `templates/lib.typ` must keep the 29 templates pixel-identical, or the PR must say why not.

Python scripts must type-check with mypy (config in `mypy.ini`, run `python3 -m mypy`) and target Python 3.11 or later: the minimum is the oldest maintained Python (3.11 today; `tomllib` requires it), and `typing_extensions` is for type checking only (imported under `TYPE_CHECKING`, never at run time).

## Reference file format

Applies to `references/regional/**`, `references/certifications/**` and `references/fields/**`, except `*-common.md`, `overview.md` and stubs under 80 words (`tests/unit/test_reference_format.py` checks the mechanical rules).

- H1 is `# <Genre>: <Subject>`; genres: Market, Education, Regulated professions, Health professions, Academic, Outbound, Law, Field pack, Certifications, Foreign workers, Gulf nationalisation, Gulf credentials. Add a genre only if none fits.
- The first paragraph is `Loaded on demand when <trigger>.`, optionally followed by a `Read together with` sentence linking the parent file and at most one scope sentence.
- Market files open with `## At a glance` (bullets in this order when present: Paper, Photo, CV language, Personal data, Length, then others).
- Scope sentences beyond those allowed in the first paragraph go in a `## Scope` section placed right after the first paragraph (after `## At a glance` in Market files, since At a glance must be the first H2).
- Common section names when the topic exists: `## Protected titles`, `## Application package`, `## Personal data and law`; country-specific sections after.
- Every sourced fact carries its S### id, in the form `(Publisher, « Title », consulted YYYY-MM-DD, S###)` or plain S### where the sentence already names publisher, title and date. The date verb is `consulted`, never accessed, retrieved, read or consulté. An optional publication or revision date goes before `consulted`, with no verb: `(Publisher, « Title », 2023-05-26, consulted 2026-11-07, S295)`. A source read only through a Wayback capture uses `snapshot YYYY-MM-DD` in place of `consulted YYYY-MM-DD`. When docs/sources.md records no consulted date for an entry, use `consulted 2026-11-07`, the verification date in its header; an undated source keeps `undated` before it.
- No URLs in `references/` (they live in `docs/sources.md`).
- Naming: a country with several files gets a folder `<country>/` (`market.md`, `education.md`, ...); a country with one file is `<country>.md`.
- Outbound guides (candidates from an origin applying abroad) live in an `outbound/` folder directly under the origin's folder, one file per DESTINATION, no `to-`/`outbound-` prefix (`quebec/outbound/france.md`). The shared file is `common.md`, or `<group>-common.md` when only some files of the folder share it (`india/outbound/europe-common.md`).
- An origin with a single outbound guide uses `<origin>/outbound.md` (`middle-east/near-east/outbound.md`). `test_outbound_naming` enforces the prefix ban and the genre-to-folder rule.
- Confidence: a sourced fact carries its S###; an unsourced fact kept as a warning carries `LOW, unsourced`; an unchecked point carries `not checked`. No HIGH, MEDIUM, unverified, not sourced, bare LOW or LOW confidence.

## Where to edit

[`SKILL.md`](SKILL.md) is a slim entry point and `tests/integration` fails above 13000 bytes. Add or change step detail in `references/steps/N-<slug>.md` (academic mode in [`references/academic-mode.md`](references/academic-mode.md), traps in [`references/known-traps.md`](references/known-traps.md)); keep `SKILL.md` to the rules and the per-step skeleton. Every `references/`, `scripts/` or `templates/` path cited must exist (also gated).

- Markdown prose is not hard-wrapped: one paragraph or list item per line.

## Version bump

A user-visible change bumps all three together: `version:` in [`SKILL.md`](SKILL.md), the README badges (`assets/badges/status-beta.svg` and `statut-beta.svg`, regenerated from shields.io), and a [`CHANGELOG.md`](CHANGELOG.md) entry.
