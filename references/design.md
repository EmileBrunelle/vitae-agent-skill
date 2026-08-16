# Design system

Goal: modern (2020s), distinctive but sober, equally strong printed in grayscale.

## Invariants vs free axes — every candidate gets their own look

The rules in this file split in two. **Invariants** are the verified mechanics
and never change: single text column, unbreakable sections, no tracking,
linear skill lines, measured fill, one accent color doing few jobs.
**Free axes** are aesthetic choices — pick a fresh combination per candidate,
guided by their field and market (regulated/corporate → restrained navy/slate,
serif tolerated; creative-adjacent → warmer accent, more contrast in the
display font). **Never ship the template's own combination** (bordeaux
`#7d2231` + tick device + Carlito/Montserrat): it is the template's identity,
not the candidate's, and every unmodified copy makes all of them look
machine-made. Change at least the accent, the heading device, and one of
(font pairing, header layout).

The free axes:

1. **Accent color** — any hue at contrast ≥ 4.5:1 on white. Pre-validated
   (computed, not eyeballed): teal `#0e6862` · bordeaux `#7d2231` · navy
   `#1f3a5f` · forest `#1e5631` · indigo `#3b3486` · rust `#8c3b00` · plum
   `#5b2a5e` · slate `#33475b` · bronze `#6e4a1f` · petrol `#0f4c5c`.
   Other hues are fine — verify the ratio first (relative-luminance formula,
   1.05/(L+0.05) ≥ 4.5).
2. **Heading device** — accent tick beside the title · two-tone rule (short
   thick accent segment + hairline) · plain hairline with the title itself
   carrying the accent · bold dark title + short accent underline. All
   vector-only (no text emitted).
3. **Font pairing** — body + display from `typst fonts` output, humanist or
   geometric sans (or serif where the market expects it). Same family for
   both, weights doing the contrast, is also a valid, quieter choice.
4. **Header layout** — centered stack · name left with the contact block
   right-aligned (one grid ROW — extraction-safe) · name + subtitle left,
   contacts on one line below.
5. **Micro-choices** — list marker (`–`, `•`, `▪`), rule weights, name in
   bold vs semibold, muted tone (`luma(80-100)`).

Ten accents × four devices × pairings × headers ≈ hundreds of looks, all
inside the verified constraints. Derive the choice from the candidate
(field, market, personality that shows in the facts) — never random,
never the default.

## Tokens

- One accent color, dark enough to survive B&W photocopy (contrast ≥ 4.5:1 on
  white; e.g. deep teal `#0e6862`, deep bordeaux `#7d2231`). Used ONLY for:
  section titles, organization names, bullet markers, header subtitle.
  **The example colors above are illustrative, not a default — never reuse
  them across candidates** (verified: a second candidate shipped with the
  example teal and read as a clone of the first). Confirm the fresh palette
  with the user early — a color rejected after the build is wasted work.
- `muted` gray for metadata — keep it dark enough (`luma(90)`, ≥5:1) because
  dates/notes are the first thing lost in a bad photocopy.
- Fonts: a humanist/geometric sans pair — body + display for name/titles.
  Check availability with `typst fonts`; give a fallback list, e.g.
  `font: ("Carlito", "Noto Sans", "Liberation Sans")`. Serif
  (Times/New Computer Modern) reads dated to tech recruiters; use only if the
  target market expects it (academia, law).

## Structure primitives (see templates/resume.typ)

- `section(title, body)` = **one unbreakable block** (`block(breakable: false)`)
  containing title + rule + content. This is what guarantees "no section split
  across pages". A section taller than one page will overflow instead of
  splitting — restructure content instead.
- Section heading: uppercase, accent color, display font — **no letterspacing/
  `tracking`** (it breaks text extraction into "S O F T WA R E") — plus a
  restrained accent device: a small accent tick beside the heading + a thin
  hairline below (the template's treatment), or a two-tone rule (short thick
  accent segment 26-34pt + hairline to the margin). Either delimits clearly
  without the full-width-rule Word look; vector devices emit no text, so
  extraction is unaffected. Vary the device between candidates — two CVs from
  this skill shouldn't look like the same document.
- Job entry: line 1 = bold role (left) + bold muted dates (right, month+year
  range); line 2 = accent-semibold organization + muted descriptor
  ("City · what the employer is (1 clause) · contract type/mode").
- Skills / languages / soft skills: linear paragraphs
  `#text(weight:"semibold")[Category~:] items` — never grids (ATS) —
  with a non-breaking space before `:` in French.
- Soft skills only with evidence: `Label — evidence drawn from the CV itself`.
  Bare adjective lists get skipped by every reviewer.
- Icons: local SVG files via `image()` are ATS-safe (vector images emit no
  text). Official brand marks (LinkedIn "in", GitHub octocat) read far better
  than hand-drawn shapes — store them in an `assets/` dir with the fill color
  hardcoded (changing the accent means editing the SVGs too). Never use emoji
  or font glyphs as icons: they leak characters into the extraction.

## Page-fill tuning loop

Target (measured on the FULL page height, margins included — that is what
`measure_fill.py` reports): last ink row at **(100 − bottom-margin%) − 0..2%**.
Examples: 1.2 cm bottom margin on US Letter (27.94 cm) ≈ 4.3% → aim 94-96%;
2 cm on A4 (29.7 cm) ≈ 6.7% → aim 91-93%. Do NOT chase a literal "95-100%"
regardless of margins. The target applies to every page, including the last
page of a multi-page version. Anti-filler clause and regional page-count
priority: SKILL.md rules 5 and step 3. Measure, never eyeball:

```
typst compile cv.typ p{p}.png --format png --ppi 90
python3 scripts/measure_fill.py p*.png     # prints "ink from X% to Y%"
```

A decorative full-width band at the top of the page (page `background`) makes
ink start at 0% — normal; the fill target applies to the LAST ink row only.
The fill measurement does NOT catch internal holes — two checks users
actually demanded:
- **Internal-gap scan**: flag any all-white run taller than ~3.5% of page
  height inside the content area. Runnable check (per rendered PNG):
  `python3 -c "from PIL import Image;im=Image.open('p1.png').convert('L');w,h=im.size;px=im.load();rows=[any(px[x,y]<150 for x in range(int(w*.06),int(w*.94),4)) for y in range(int(h*.02),int(h*.97))];import itertools;print([sum(1 for _ in g) for k,g in itertools.groupby(rows) if not k])"`
  — any number > 0.035*h is a hole to fix.
- **Uniform section spacing**: one `above:` value for all sections of a
  document (`airy` only on sparse pages of multi-page versions); distribute
  extra space through global leading/spacing, never one oversized gap.

Tuning knobs, in order of preference (avoid `v(1fr)` stretchers — they create
visible canyons):
1. Body `leading` and par `spacing` (global rhythm; ±0.01-0.03em steps).
2. `section` `above` gap; a separate larger value for sparse pages
   (an `airy: true` variant) — but keep the delta between pages small or the
   document reads as two different documents.
3. List `spacing`, job-block `above/below`.
4. Real content (an extra legitimate bullet) beats any spacing trick.
5. Multi-page balancing: `#set text`/`#set par` are document-global — re-declare
   them locally after a `#pagebreak()` to give a sparser page its own rhythm
   without disturbing page 1.

On multi-page versions, decide the page break yourself (`#pagebreak()`) so page
assignment is deterministic, and re-run the loop after every content edit —
one wrapped line can cascade an unbreakable section onto a new page.

## Micro-typography checklist

- Typographic apostrophes (’) everywhere, including inside strings passed to
  helper functions (Typst smart quotes don't reach every context).
- Fragile tokens (`CI/CD`, version numbers) wrapped in `#box[...]` so they
  never break across lines. Calibration: this is for tokens that break *badly*
  (slashes, dots); multi-word phrases with natural space breakpoints don't
  need it. Caveat: markup like `#box`/`*bold*` only works in `[content]`
  arguments — inside a helper's `"string"` argument it renders literally;
  call helpers with `[brackets]` when markup is needed.
- Bold budget: ≤2 bold tech terms per bullet; never bold whole concept phrases.
- En dash `–` for ranges, em dash — for asides; consistent per language.
- Hyphenation off (`hyphenate: false`) — ragged right, no broken words.
