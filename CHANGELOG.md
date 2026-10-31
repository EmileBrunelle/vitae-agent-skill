# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/). Newest first. Versions are the `version:` in `SKILL.md`; hashes point to the release commit.

## 0.7.5 - 2026-10-31

- `verify.py` WARNs when a bullet restates its own entry's descriptor line in the experience and projects sections (the note argument of the entry call, split on ` · `, `|` and commas; in projects also the second argument, the description; the employer is never compared; a descriptor segment needs at least 2 content words; English and French stop words) (a run wrote "Go + SQLite REST service" and then "Built the service in Go with SQLite" to fill the page); it fires when a bullet covers at least half of a descriptor segment's content words and at least two of them, one WARN per bullet, never a FAIL. Calibrated at zero hits on every shipped template and fixture.

## 0.7.4 - 2026-10-31

- `verify.py` WARNs when the top-level body text size is above 11pt (shipped templates stay at 10.5-11pt): a run raised the body to 12pt to reach the fill target, which pads the page with type size instead of facts and inverts the heading/role/meta hierarchy (template sizes are absolute pt). The `--tune` under-fill message and `references/steps/4-tune.md` now say that raising the body size is the same padding, not an alternative.

## 0.7.3 - 2026-10-31

- The leading-ratio WARN threshold drops from 2.00 to 1.95: a real run at leading 1em with 0.5em bullet spacing (ratio exactly 2.00) still read double-spaced; the shipped templates max out at 1.89.
- `verify.py` WARNs when the summary or profile repeats two or more figures already in the experience or project bullets (padding by repetition, which the anti-filler clause forbids); one headline figure is fine, and years, GPAs, dates, phone numbers, code and URLs are ignored.
- Contact icons are all-or-nothing across drawn and harvested icons: `lib.typ` gains `gate-icons()`, so when the harvest is blocked the drawn pin, phone and mail icons disappear with the harvested ones instead of leaving a mixed row (17 family templates and `pick_design.py` output patched, plus color-band's own drawn icons). Line height is kept, so the fill does not move.
- `verify.py` recognises the 0.7.2 `lib.typ` and three earlier releases as known stale copies.
- `docs/models.md`: Claude Code on the web row added; the older vitae that loaded in a first cloud attempt came from the cloud environment, not the repository.

## 0.7.2 - 2026-10-31

- `verify.py` WARNs when the body leading is more than 2x the bullet spacing (prose reads double-spaced next to single-line bullets; seen on three platforms; the absolute 1.00em WARN missed a 0.94em case); the threshold is 2.00 and the shipped templates max out at 1.89.
- `docs/models.md`: Antigravity CLI (`agy`) row added.

## 0.7.1 - 2026-10-30

- Gate fixes: the `~` check ignores raw blocks, block comments and `$math$` and now catches `*~25 users*`; the leading WARN reads `#set par(leading: ...)` in any argument order and in pt, ignoring ones scoped inside a `#let` / `#show`; a CV importing `../../lib.typ` is told to change the import and copy `lib.typ` next to `cv.typ`; the text-only icons WARN fires only when the default kit is incomplete; the doctor offline hint names `aarch64` on arm64.
- Family templates no longer rely on symlinks: the 28 `lib.typ` / `icons.typ` symlinks are removed and each family imports `../../lib.typ` by relative path, so the repo zips cleanly for claude.ai and checks out on Windows. Compiling a family template by hand now needs `--root .` from the repo root (`verify.py` adds it itself); `pick_design.py --init` rewrites the import to `"lib.typ"` in the starter it copies out.
- `verify.py` WARNs when the body paragraph leading is above 1.00em (it reads as double-spaced); shipped templates stay at 0.96em or less.
- `verify.py --doctor` prints an offline route when `typst` is missing and the sandbox has no network: download the abi3 wheel on another machine, upload it, then `pip install --no-index <wheel>`.
- The gate now FAILs on an unescaped word-initial `~` in content text (Typst turns it into a silent non-breaking space); write `\~` for a literal tilde.
- Contact icons are all-or-nothing: if only some of the marks were harvested, none are drawn (with a WARN on the partial harvest), so a row never mixes icons and bare text.
- `pick_design.py --init`: starter section headings use the drawn labels, and a drawn `soft=None` leaves no soft-skills section in the starter.
- README (en/fr): new "Built like software, not like a template" paragraph under the intro — facts file as single source of truth, test gate and adversarial review before delivery.
- `scripts/look.py`: with `--per-item`, an item whose response is cut off at `--max-tokens` (`finish_reason=length`) is now a `FAIL <id> — inconclusive (truncated at <n> tokens)` and the run continues with the remaining items (exit 1 as for any FAIL) instead of aborting with exit 2; a single-call truncation still exits 2, with an explicit `inconclusive: output truncated at <n> tokens` message. New `--temperature FLOAT` (default 0, unchanged), `--top-p FLOAT` and `--top-k INT` (LM Studio extension), the last two sent only when given.
- Visual pass is now a delivery precondition (step 8) and can no longer be skipped silently: `references/look-checklist.md` is rewritten as 15 scoped items (page / pages / crops) for `look.py --per-item`; four-route fallback in step 6 and the layout reviewer (self, vision subagent, any OpenAI-compatible vision endpoint remote or local via `scripts/look.py`, user); route 3 report value is `other-model <model>`, and step 8 accepts only the clean `look.py` line (a FAIL run prints `<label>: FAIL other-model <m> (<n> items: L…)` instead, which does not pass); "redesign" is defined for the layout review; required `Visual pass:` / `Layout review:` report lines; the compatibility note is corrected (pypdfium2 runs the text gates).
- `verify.py --render --crops`: 300 ppi crops of solid-fill bands and vector icons (`<stem>-p<N>-<fill|icon><n>.png`, <=8 per page, dropped bands named on stderr), both backends. A plain `--render` (without `--crops`) clears stale crops of the same stem, as does a re-render; icon detection no longer reports bullets, glyph fragments and letter chips (candidates are ranked by ink before the 8/page cap); real contact icons are no longer dropped (solid phone glyphs are kept, the mail icon is matched one no-break space from its value; a filled LinkedIn or mail mark beside its text, or in a text-free row of marks, is kept; measured recall 16/16 across the 8 icon families and 126/126 on an independent 140-mark set built by the reviewer (was 113/140), incl. a held-out icon kit 42/42); repeated same-shape decorations (same-size bullets, heading squares, dividers ×3+) are ignored (16 false positives → 0, unchanged; mixed-size bullets and dividers repeated twice can still be cropped); the paper is read from the innermost uniform ring, so a dark page under a white card, or a frame stroked at the page edge, no longer becomes one whole-page fill; a large sidebar no longer becomes a whole-page fill.
- `scripts/look.py`: stdlib-only vision route (OpenAI-compatible /chat/completions; remote, LM Studio, ollama), one PASS|FAIL line per checklist item, exit 0/1/2. Hardening: conflicting duplicate verdicts, truncated or unclosed-`<think>` output and `finish_reason=length` fail closed (exit 2 with a `--max-tokens` hint); tolerant answer formats (numbered, `L1: PASS`, tables, `L01`); PNG and size checks; `--label`, `--list-models`; new `--per-item` mode (one fresh request per checklist item, routed by scope; one call per page for `page` items). A FAIL run prints `<label>: FAIL other-model <m> (<n> items: L…)` instead of the clean line. Checklist scope tags select the crop type explicitly (`crops:fill`, `crops:icon`; plain `crops` = all), falling back to pages when no crop of that type exists. PNGs from several stems, duplicate or misnamed PNGs (nothing is sent), or an invalid `--base-url`, exit 2; `--per-item` makes page items × pages + other items calls.
- Review fixes: CI pins typst-py separately (0.15.0, no 0.15.1 on PyPI); `--facts` year-crossing ranges and FR month abbreviations; doctor never prints OK after a DEGRADED; `--text`/`--render` clear error on a corrupt PDF.
- `--doctor`: typst-py is probed by running it (`BROKEN` if it fails); typst older than 0.15 is `DEGRADED` (the fill targets are calibrated on 0.15); `TYPST_FONT_PATHS` is passed to typst-py as `font_paths`; a pip-only environment reports `OK (Python)`; typst-py compile warnings are no longer dropped. With poppler or pypdfium2 but no `pypdf`, it prints `DEGRADED  pypdf: not installed` naming the tiny-text check that will not run (no `OK (Python)` in that case); the pip-only install line is now `pip install typst pypdfium2 Pillow pypdf`. New `tests/run_all.sh` case `doctor-no-pypdf`.
- `verify.py --render <pdf> [--out DIR] [--ppi N]` writes one `<stem>-p<N>.png` per page (pypdfium2 or pdftoppm, 150 ppi by default) and `verify.py --text <pdf>` prints the text the gates read, so the agent instructions no longer name pdftotext / pdftoppm. `--facts` no longer flags `Jul 2019` against `juillet – août 2019`.
- Docs: README banner for AI agents; pip-only install line; step 6 uses `verify.py --render`; `allowed-tools` gains `cp`.
- CI: new `pure-python` job (typst-py + pypdfium2 + pypdf, no typst CLI, no poppler) runs `tests/run_all.sh`; `tests/backend_equiv.py` compares gate verdicts, page count and fill across poppler / pdfium and typst CLI / typst-py (BENCH); `fixtures/render.sh` falls back to typst-py; the CI fonts live in a composite action.
- `verify.py` / `verify_letter.py`: with no poppler on PATH but `pypdfium2` importable, every poppler-backed check (page count, ATS text, word boxes, hidden-text and text-clip gates, group proximity and date adjacency, ink gap raster, metadata, attachments) runs on pdfium instead of being skipped or degraded to pypdf (which splits words: "EDUCA TION"). `preflight()` now returns the backend (`"poppler" | "pdfium" | "pypdf" | None`) in place of the `use_poppler` bool; poppler stays preferred and its output is unchanged. pdfium is close to poppler, not identical: on every template invocation and `--gates` fixture of `tests/run_all.sh` the verdicts agree, but the measured numbers differ slightly (see the next two bullets for the known differences). The pdfium text is cut into lines at wide same-baseline gaps and read in an approximation of poppler's reading order; `tests/compare_backends.py` prints the per-fixture line counts of both (on the 14 fixtures: line sequence identical on 8, same set of lines on 10, 630 of poppler's 642 lines found verbatim in pdfium's, at most 5 lines apart, the same words everywhere; poppler's own line cutting is not purely geometric, so the counts cannot be made exact; the test fails below 85% of lines found or on any difference in words). `--doctor` prints `OK    pdf: pypdfium2 <ver> (...)`; `verify_academic.py` still needs poppler (`pdftotext -layout`). New `tests/run_all.sh` case `doctor-pdfium`.
- pdfium vs poppler, right-to-left text: pdfium extracts Arabic and Hebrew in logical order, poppler in visual (reversed) order, so the needle / facts verdicts can differ on Arabic CVs; pdfium is the more correct of the two. Nothing is normalised between them.
- pdfium vs poppler, hard-edge: the pdfium word boxes and raster put every band uniformly about 1 px (at 300 ppi) lower than poppler's; the mean group-proximity ratio delta is +0.013 (pdfium slightly more lenient: `gates/hard-edge` 0.85 on poppler, 0.88 on pdfium). No threshold was changed for it.
- pdfium fallback fixes: the date-adjacency reading order now reads a right-flushed date after the lines of its entry at any distance (up to the next dated head), unless a line under it overlaps its x-range, as poppler does (measured on poppler: role, org, date at every head-to-org gap from 4 to 200 pt, heads of 9 to 18 pt; a Typst grid `[Senior Engineer],[2019]` over an org line used to pass on pdfium and FAIL on poppler; selftest layouts at 12 to 150 pt and with a bold head and a date of one size); blocks sort by baseline row, not box top; the x-height band search skips a rule row (an em dash) instead of counting it as an empty row (gap-next on `humanist-quiet/resume` read 10.8 pt on pdfium against 8.6 pt on poppler, now 8.6 on both; on the 29 templates and 14 fixtures the poppler output is byte-identical, no other difference was measured); `pdf_backend()` selects pypdfium2 / pypdf only when they import, and a skipped gate names the real reason instead of `pdftotext not found`; one off-page FAIL on pdfium instead of two. Known limitation: when dated entries are stacked closely (3-6 pt) or chained through an undated entry, pdfium reads the first date at the end, so the date-adjacency FAIL message may name extra entries; the verdict is identical to poppler on every layout tested.
- typst without the CLI: when the `typst` Python package (typst-py with `Compiler.query`/`.eval` and `Fonts`) is importable, `verify.py` runs date adjacency, group proximity, duplicate names, the `--selftest` typst gates and the design font check through it instead of skipping them (same output as the CLI; CLI behaviour unchanged when present), and `--doctor` prints `OK    typst <ver> (Python API: compile, query, fonts)`. An old or stub module without `Compiler.query` stays `DEGRADED`. `pick_design.py` falls back to `typst.Fonts`.
- `verify.py` year-only WARN rewritten: it now says to KEEP the range year-only when the facts file has no month and report the gap, and never to invent or estimate months (it used to read as "month+year both ends", which pushed a model to make months up to silence it).
- Drawn fill target: `pick_design.py --init` / `--emit-typ` write `// vitae: pages=N fill=A-B` as line 1 of `cv.typ`. When the family is known (`// FAMILY:` banner in the first 3 lines, else the `families/` directory) `verify.py` takes the drawn target from `pick_design.FAMILIES[family]["page"]["fill"]`, never from the header, so deleting or editing the header changes nothing; a banner with a missing or disagreeing header prints `WARN  cv.typ header disagrees with family ...` naming the expected value. The header (line 1 only) is used only when no family is known. No FILL args = the drawn target. FILL_MIN below it is allowed but prints `WARN  fill target lowered below drawn target A-B` and repeats it on the `PASS (fill target lowered: A-B → X-Y)` line. Non-integer fill or page arguments (`94.5`, `9x`) now exit non-zero with `FAIL  fill args must be integers` instead of a ValueError traceback (also for `--tune`).
- New `verify.py cv.typ PAGES [FILL_MIN FILL_MAX] --facts facts.md`: WARNs `not in facts file: "<token>"` for each year, month+year, number, capitalized name (multi-word, single mid-sentence word, all-caps acronym such as UQAM or AWS) in the CV text absent from the facts file. A capitalized sequence is looked up whole first; only a sentence-start action verb from an explicit EN/FR list (and prepositions such as "From") is dropped from its head, so "Analyst — Globex Corp" no longer passes on "Corp" alone. Case, accents, spacing, number formats, company suffixes (Inc., Ltée, Corp., LLC, SA, SAS, GmbH), "%" = "percent" = "pour cent" and links (à, au, aux, of, the, and, et) are normalized; phone numbers are ignored; "Python 3.12" against facts "3.11" still WARNs. `references/steps/6-verify.md` gives the command and says every such WARN is removed or confirmed, never reworded away. Selftest and two `tests/run_all.sh` cases (`drawn-header`, `lowered-fill-warns`) cover it. When the facts file and the CV are in different languages (EN vs FR stopword ratio), it prints one `INFO  facts file is <lang>, CV is <lang>: coverage limited to dates, numbers and acronyms` line and checks only years, month+year, numbers, all-caps acronyms and letter+digit tokens, so translated titles ("Software Developer" vs "Développeur logiciel") no longer WARN and steer a model to delete real facts; same-language behaviour is unchanged.
- `verify.py --doctor` no longer reports pip-only fallbacks (typst Python API without the CLI, pypdf without poppler, poppler without pdftoppm, fewer than MIN_POOL design families installed) as `OK`: it prints `DEGRADED`, names the checks that are skipped (date adjacency, group proximity, hidden-text, design font availability) or indicative (ATS extraction), and gives install routes including no-root ones (typst static binary into `~/.local/bin`, poppler via micromamba), each with a pure-Python `urllib` variant for sandboxes where shell curl/wget are refused. Exit code unchanged (0). README.md / README.fr.md no longer claim `pip install typst pypdf Pillow` covers everything; `references/steps/0-env.md` tells the agent to report DEGRADED before promising a verified CV.
- CI: runner back to `ubuntu-latest` (currently Ubuntu 24.04), reverting the `ubuntu-26.04` pin from 0.7.0. CI pins mypy 2.4.1; the 8 pre-existing mypy errors in `verify.py` are fixed.
- Docs: Markdown no longer hard-wrapped (one paragraph or list item per line); text unchanged.

## 0.7.0 - 2026-10-30

- Context diet: `SKILL.md` goes from 46,647 B (~11.7k tokens, read whole by every model in measured runs) to under 10 KB. It keeps the frontmatter, the preamble and non-negotiable rules 0-5 verbatim, plus a rule that `scripts/` are run, never opened, and `templates/lib.typ` is copied with `cp`, never read or rewritten. Each step 0-8 is a short skeleton pointing to `references/steps/N-<slug>.md` ("read now, before doing anything for this step"); the step bodies moved there verbatim (plus `4-tune`, `6-tune` and `8-companions` sub-files). Academic mode is now `references/academic-mode.md` and Known traps `references/known-traps.md`. No rule changed.
- Motivation, measured: run8d (GPT-OSS) read `lib.typ` whole, rewrote it from memory and failed; Gemini and Qwen read the `verify.py` source instead of running it.
- `tests/run_all.sh` gains two gates: `SKILL.md` <= 13000 bytes, and every `references/`, `scripts/` or `templates/` path cited in `SKILL.md` and the moved files exists. Contributors add detail to the step files, not to `SKILL.md`.
- Scripts: full type annotations and TypedDicts across all 7 scripts, checked by mypy (`mypy.ini`, `python_version = 3.11`) in CI and in `tests/run_all.sh` (SKIP when mypy isn't installed). Manual argv parsing replaced by `argparse` in `verify.py`, `verify_academic.py`, `verify_letter.py`, `harvest_icons.py` and `measure_fill.py`; the CLI is unchanged (verified against the golden outputs of 0.6.12). Minor: `verify.py --gates --root` with no value prints usage instead of a traceback; `--root=DIR` is accepted.
- Python >= 3.11 is now declared (`tomllib`); README badge added.
- CI: Python matrix 3.11 + latest 3.x; runner pinned to `ubuntu-26.04` (was `ubuntu-latest`); actions bumped to their Node 24 majors (checkout v7, setup-python v7, cache v6, upload-artifact v7), which removes the Node 20 deprecation warnings.

## 0.6.12 - 2026-10-30 (`385a732`)

- `tests/run_all.sh` runs the self-tests, the 29 templates against their fill targets and the spacing fixtures with their gates in one command; a GitHub Actions workflow runs it on every PR and push to `main` and attaches the PDFs.
- `verify.py --tune` caps upward leading at 1.10em and spacing at 1.24em (largest shipped 0.96em / 1.075em plus 15%), clamping and reporting any wider range passed. An under-filled page now FAILs with content advice (add a real fact, ask the user, never invent or pad) instead of "widen the range"; over-full behaviour unchanged.
- `verify.py`, `verify_academic.py` and `verify_letter.py` FAIL hidden text: any word pdftotext extracts whose box has under 1.5:1 WCAG contrast against its background (white-on-white, background-coloured, under a shape, hidden keyword layers such as brilliant-cv's), a box under 4pt, or a box crossing the page edge (with pypdf, runs placed wholly off the page, by geometry). WARNs on contrast under 3:1, text set under 5pt (real font size via pypdf; superscripts exempt), stuffed Keywords/Title/Author/Subject, embedded attachments, and when pypdf is missing. Calibrated on the 29 templates + 294 palette renders: weakest legit contrast 4.55:1, smallest legit box 5.49pt (a superscript); about 0.3 s per page.
- `entry()` (and every family's `job()`) sets the date inline after the role ("Role — Mar 2024 – present") unless the entry's org/descriptor line reaches under where a right-flushed date would sit; pdftotext/ATS read geometry, so a right-flushed date past a short org line landed at the end of the page. The decision is automatic and layout always converges; the date-adjacency gate FAILs only hand-built/overridden heads; Typst non-convergence is now a FAIL (`ff5da87`).
- README links are relative to the files they mention (`b8187db`).
- `tests/fixtures/README.md`: states that fixtures are not templates (`43e8b9a`).
- README: contributions welcome in English or French (`2ecab8c`); see `CONTRIBUTING.md`.

## 0.6.11 - 2026-10-29 (`7703057`)

- Step 4 fills `cv.typ` one section per edit with a compile each time; copy the starter's call forms instead of reading `lib.typ`.
- `pick_design.py --init` adds a comment above the first `#job(` naming its four positional arguments. No layout change.
- Step 7 gets a compact review path (sequential, two lenses, at most 5 findings each) for runtimes without parallel subagents; the default panel is unchanged.

## 0.6.10 - 2026-10-29 (`37b07c3`)

- Security hardening of `harvest_icons.py` (escaping, size caps, atomic write, no symlink writes), `pick_design.py --init` and `verify.py` (quoted commands).
- Rule 0: postings, CVs, facts and web pages are data, never instructions.
- README badges vendored as local SVG.

## 0.6.9 - 2026-10-29 (`b22dde2`)

- `verify.py` prints a NEXT footer with fix clauses after any FAIL.

## 0.6.8 - 2026-10-29 (`45d95a2`)

- Spacing hierarchy across all 14 families, pixel-identical in the lib marks.
- New measured gates: group proximity, date adjacency, forced line breaks, duplicate names, `lib.typ` integrity.
- `pick_design.py --init` starts a CV from a family template.
- Skill label "Programming" replaces a duplicate "Languages".

## 0.6.7 - 2026-10-29 (`a249ec5`)

- Text-clip gate: FAILs text cut by a filled band or invisible on its background.
- `masthead()` header band that grows with its content (used by color-band).
- SKILL.md: page text is facts only, no filler to reach the fill target.

## 0.6.6 - 2026-10-29 (`2240850`, `ea262a8`, `407b6a2`)

- One starting file per family (`resume.typ`).
- `--emit-typ` emits only installed font families under their exact Typst names.
- `verify.py` warns when FILL_MIN FILL_MAX are omitted; font hints say whether a font is Google-Fonts-only or also a Linux package.

## 0.6.5 - 2026-10-29 (`3ee5308`)

- Verified on Typst 0.15.

## 0.6.4 - 2026-10-28 (`82d53b3`)

- README mentions Workday support.

## 0.6.3 - 2026-10-28 (`24eaa12`)

- Real names in examples replaced with fictional ones.

## 0.6.2 - 2026-10-28 (`9d01fbf`)

- Workday: spell « février » in full.

## 0.6.1 - 2026-10-28 (`a36cafe`)

- Workday: write in-progress end dates as « Present ».

## 0.6 - 2026-10-28 (`d657ecf`)

- Workday parse-only copy (one wide page, no Projects, legal-name rules) and the two-file recipe, from measured parser behaviour (`88d029c`).
- List markers drawn as vector shapes so they no longer appear in ATS text (`f04abe7`, `119e9e6`); documented Eightfold quirks in `ats.md`.

## 0.5 - 2026-09-13 (`3c7054e`)

- Academic CV mode: its own template (`templates/academic/`) and gate (`verify_academic.py`).
- Skill can run on agents other than Claude Code (`f0d0608`).
- 2026-09-14: "no section split across a page break" is measured, not stated (`42b89a9`); French README added (`036baa8`).
- 2026-10-28 (`81c0288`): gates for year-only date ranges and degree tokens next to non-completion markers; `--all` infers 2-page files from names.

## 0.4 - 2026-09-13 (`137cf0e`)

- Section-separation gate sees more devices (rules beside text, etc.).

## 0.3 - 2026-09-13 (`c9cf7c7`)

- Cover letter shipped.

## 0.2 - 2026-08-21 (`701bd8f`)

- Anti-clone design system: 14 families in four registers, deterministic per-candidate draw (`pick_design.py`), generative palettes (`gen_palette.py`).
- Cross-platform gate `verify.py` (doctor, fill tuner, separation floor).
- Southeast Asia regional file (`82a9d67`); Maghreb added 2026-09-13 (`c8794c7`).
- 2026-09-13: section separation measured rather than described (`1de1251`); brand marks fetched at build time (`08c847e`).

## 0.1 - 2026-08-16 (`65c03bc`)

- First release (beta): ATS- and human-optimized résumé skill for Typst, with measured page fill, exact page control, regional conventions, adversarial review loop and field packs. Hardened the same day (`4fa49c8`).
