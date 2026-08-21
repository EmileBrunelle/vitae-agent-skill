# Design system

Goal: modern (2020s), distinctive but sober, equally strong printed in grayscale.

## Invariants — never change

Verified mechanics, identical in every family: single text column;
unbreakable sections; **section boundaries that read at arm's length —
measured, not eyeballed** (see below, and the gate FAILs on it); no
`tracking` on any text an ATS reads; skills as linear paragraphs, never data
grids; measured fill; body ≥ 10pt (target 10.5-11); section headings ≥ 1.15×
the body size; margins ≥ 1.5cm horizontal / ≥ 1.2cm vertical; every colour
pair at contrast `(L1+0.05)/(L2+0.05) ≥ 4.5`; no hue in the muddy band
(40-70°) on text; one accent doing few jobs; no trap from `ats.md`.

Everything *else* is a family attribute, and deliberately varies: the heading
device, the header composition, the skills-block shape, the accent role, the
icon style, the section labels, the **page gabarit** (margins, measure, body
size, derived fill target), the **default section order**, and whether the
family carries a **specialities line**. The mechanics are shared and validated
once — `templates/lib.typ`; the devices never are (§ Where the mechanics stop
and the devices start).

**Section separation is an invariant, not a preference.** A CV whose sections
do not detach from the intra-section rhythm fails, exactly like a CV with two
text columns. `scripts/verify.py` measures it on every rendered page: the
tallest internal white run must be **≥ 2.0× the median** internal white run
(`BOUNDARY_RATIO`), and a run taller than 3.5% of page height is a hole
unless it is a boundary (boundaries may reach 5%).

**The ratio is a FLOOR, not a target, and passing it is not the test.** The
floor is calibrated just under the families whose separation reads best —
measured at 90 ppi: `color-band` 2.33, `hard-edge` 3.12, `swiss-grid` 3.40,
`bold-display` 3.60. The counter-intuitive part is worth stating: those are
among the *lowest* white ratios of the roster, because their boundary is
carried by **ink** (a filled bar, a knocked-out black slab, a 2.5pt
rule, a heavy underline). White space is therefore a floor, never a score — a
family with no device needs far more than the floor (`humanist-quiet` 6.60,
`margin-index` 6.73-7.40). So every family clears the measurement **and** is
looked at: the boundary has to be obvious to the eye. A recipe that sits at
2.00 has no margin left — one content edit fails it — and a recipe at 6.00
with an ink device is over-separated; both were measured on `hard-edge` while
tuning it, and 3.00 is where it landed.

**The instrument has one blind spot, and a device can walk into it.** The scan
compares the boundary runs to the *intra-section* runs, so it needs
intra-section white to exist. A device that puts ink on **every row of the
section body** — a continuous vertical rule beside the text, a full-height
column ruler — deletes that comparison: measured on `gutter-rail`'s first
build, whose gutter rail was drawn at the text edge with the text indented past
it, the whole page yielded **10** white runs instead of ~60, median 21.5px,
tallest 27px, **ratio 1.26** — a FAIL on a page whose boundaries are in fact
bracketed by ink at both ends. Two consequences, and neither is "relax the
check": (1) the fix is to move the device **into the margin**, where a gutter
belongs anyway (`outset` instead of `inset`), so the text column's own rhythm is
measured honestly and the device's separation becomes a bonus the number
*understates* — the same build then measures 3.00; and (2) a dashed or dotted
version of that rail would have *passed* with a ratio near 8, because the dash
gaps become the median — that number would be a lie, and inflating the ratio
that way is the one manoeuvre this section forbids by name.

## The destination support — the print-safe build is canonical

Applies to **every** family, not to the expressive ones only. Nobody controls
what a recipient does with a PDF: it gets printed, photocopied, faxed by a
public-sector office, read on a phone. So the **light-background, print-safe
build is the CANONICAL one and it is the file that ships** — checked in
grayscale, not only in colour (`convert look.png -colorspace Gray`, or any
grayscale render: every device must still read).

A **screen-first build** — a full dark theme — is legitimate as a *supplement*,
on the explicit request of the candidate or user and for a controlled context (an
online portfolio, a personal site, a page whose only reader is a browser). It is
never the delivered file and never the default, and the agent does not propose
it as one.

The mechanics, when a screen build is asked for: **one source, two palettes**,
exactly like the 1-page/2-page pair. A `#let screen = false` toggle at the top
of the `.typ` switches the page fill and the palette; the devices, the geometry
and the content do not move. Two rules make it honest:

- **Re-derive, never invert.** Each hue keeps its hue and gets its *lightness*
  recomputed against the real background, and the contrast is recalculated with
  the general formula on that background — not on white. (This is what an
  institutional desktop's theme engine does, in OKLCH, rather than flipping a
  light theme; § gutter-rail names the source.) Verified on `gutter-rail`'s
  screen build over `#1b1d23`: hue A 7.29:1, hue B 6.14:1, body 13.70:1,
  metadata 8.37:1.
- **The gate does not transfer whole.** On a dark page the entire sheet is ink,
  so the fill measurement and the white-run separation scan have nothing to
  measure — `measure_fill` reports ink from 0% to 100% and finds no runs. The
  **canonical light build carries those two checks**; the screen build is
  validated for contrast on its real background and for extraction (verified
  byte-identical between the two builds of the same source — colour emits no
  text). Do not "tune" a dark build: tune the light one and toggle.

## Design families — every candidate gets their own look

**Do not "choose freely".** Measured: an agent told to pick freely
reconverges on the template's own look, so the first CV of every user of this
skill is the twin of all the others. The three markers that make CVs from
this skill recognizable as a batch are **(1)** UPPERCASE section headings
over a full-width accent rule, **(2)** a `Category: item, item` skills block,
**(3)** the accent applied to the same three places (role title, rules,
links). Each family below breaks all three differently.

**The final bar — non-recognition.** Every recipe, and every CV built from
one, is judged on this: *a recruiter who has already seen two CVs produced by
this skill must not be able to identify the third as coming from the same
tool.* Corollary, applied to the recipe itself: *if the page could pass for the
default template of a popular consumer tool — the most-used word-processor
CV template, the first theme of a résumé site — the recipe fails.* Second
corollary, and it applies to the expressive families in particular: **nor may
the page be identifiable as an existing brand.** A recipe that reproduces one
company's visual signature — its specific combination of border, shadow,
shape and palette — makes the candidate's CV look like a third party's
product, which is the same failure as looking like a template with a
different owner. Harvested case: `hard-edge` was read as one specific
code-learning platform's identity, because thick black border + zero-blur
offset shadow + tinted pill fields is not "neo-brutalism", it is the
neubrutalism **UI-component** dialect that brand ships. The fix is never to
abandon the current — it is to take another dialect of the same current
(there, the print/poster one: knockout type in solid black, no shadow, no
tint fields). Ask it per family: *could a reader name a company looking at
this page?* This is a
pass/fail test, not a matter of taste, and it is the reason the roster is
fourteen families deep rather than one good-looking template: quality does not
protect against a uniform look, only variance does. The Layout reviewer
checks it against the rendered pages (`references/reviews.md`).

The two named failure modes it is measured against live in
§ Anti-references: **Anti-Word-97** and **Anti-AI-slop**. There are exactly
two, they are named, and no third one is invented — a list of vague things to
avoid is how a bar becomes a mood.

Pick the family with `scripts/pick_design.py` (deterministic per candidate —
the 1-page, 2-page and translated versions then share one look) unless the
user names one explicitly. The template stays single: a family is a **recipe
applied on top of `templates/resume.typ`** — a handful of `#let`/`#set`
substitutions plus the header block.

Each family carries a **register** — `modern`, `neutral`, `classic` or
`creative` — and the script weights the pool with it: early-career candidates
default to the modern families, mid-career to modern and neutral, and senior to
neutral and classic; a conservative market drops the loud families whatever the
stage (`--conservative`; `--market` is documentation only, it changes nothing).
The default leans modern deliberately. Register is derived from the
fact sheet (years of experience, first job, seniority of the titles) and the
target market, **never** from age or any demographic datum. Whatever the
profile and the flags, the script widens the pool until **at least five
families** are eligible (`MIN_POOL`), so two candidates of the same profile
collide at worst one time in five. Widening is additive and stops the moment
five are eligible, so adding a constraint can never *widen* the pool.

**The `creative` register is never in the default pool.** Three families live
there (`hard-edge`, `avant-poster`, `gutter-rail`), and they are eligible only
when the target field resolves to creative in `DOMAIN_REGISTER`
(`scripts/pick_design.py`) or when the candidate or user asks explicitly
(`--creative`); a conservative target market caps them straight back out.
`gutter-rail` is the one whose lock is a *domain* rather than a taste: its
current is legible only to a software audience, so it takes a software/technical
field **plus** an explicit request for something expressive — the same
double-lock logic that keeps `mono-technical` off a general-business CV. They are filtered out *before* the
widening loop, so widening can never pull one in for an accountant. What they
buy is more typographic risk — a committed duotone, ample colour, a bold header
composition — under exactly the same gate as everything else: *beautiful **and**
parseable*, or it does not ship. Expressiveness there still lives in the
typography, the colour and the devices, **never in the structure**: single text
column, linear skills, clean extraction, all the ATS invariants holding exactly
as they do on an accountant's CV.

Every family below was built on the template, passed the gate with the values
stated, and had its rendering inspected — each one with **two different pairs
from its font pool**, to prove the register (not one lucky pair) is what holds.
The gate's fill target is the family's own, derived from its gabarit
(§ Gabarit), not a global 94-96%. **Those values were tuned on the template's
own filler content and on pair 1** — re-run the loop for real content, and after
any font swap; `scripts/verify.py --tune` does that loop by bisection instead of
by hand. Every pool member is open-licence; at least one per role is present in
a standard Linux font set — with one documented exemption, the *creative*
families' display pools, whose registers (a wonky heavy grotesque, a condensed
poster face, a dev-tooling UI grotesque) have no equivalent in a standard Linux
font set; their body pools do, and so does `gutter-rail`'s mono pool. The rest name their provenance (see § Font pools). Any font the recipient
lacks is listed in the hand-off with its package.

### Rules common to every family

**Section boundaries (the 30-second scan).** A section break must read as a
break at arm's length. Two requirements, both verified per family:

- **Spacing hierarchy, sharply stepped**: `section` gap ≫ job-entry gap
  (5-6pt) > list-item gap (0.45em) > line leading. The section gap is at
  least **2× the space between a heading and its own body** — the gap belongs
  to the boundary, not to the heading. Two documented exemptions, both
  measured: a family whose device is a *filled* shape may go **below** 2:1
  (`color-band` runs 7pt over 5pt = 1.4:1 and still measures the strongest
  boundary of the roster — the reversed bar is the boundary); and a family
  whose device is *nothing* needs 4:1 or more (`humanist-quiet` 26/4 = 6.5:1).
  A family whose heading sits *beside* its body has no heading→body gap at
  all and the ratio does not apply: `margin-index` puts the title in a 2.5cm
  margin column, so its whole boundary budget is the 30pt section gap plus
  the short accent rule above the title, and the white-run ratio below is the
  only measurement that governs it (7.40, the highest of the roster).
- **Measured, in the gate**: `scripts/verify.py` scans every rendered PNG
  (`measure_fill.gaps`) and FAILs when the tallest internal white run is
  under **2.0× the median** run, when any run exceeds **5% of page height**,
  or when a run over **3.5%** is not a boundary. That last clause is the
  pre-heading exemption: the white immediately above a section title is
  allowed to run to 5%, a hole in the middle of a section is not. Measured at
  90 ppi (max run / median run, max run as % of page height): `color-band`
  2.33 / 1.4%, `swiss-grid` 3.40 / 1.7%, `editorial-serif` 3.40 / 1.7%,
  `bold-display` 3.60 / 1.8%, `quiet-luxury` 3.85 / 2.5%, `mono-technical`
  4.00 / 2.4%, `humanist-quiet` 6.60 / 3.3%, `keyline-corporate` 7.25 / 2.9%,
  `margin-index` 7.40 / 3.7%. If the gap you want would overflow the page or
  open a canyon, take the space from the *intra*-section rhythm instead of
  adding to the gap — raising the contrast between the two is what makes the
  boundary read, not the absolute size of the gap.

**Line integrity — a structured line holds ONE line.** Harvested from a reader
looking at the rendered pages: *"it is better when nothing overflows onto the
line below — except in the Profile."* Two levels, and they are different kinds
of rule.

- **Hard, and it is checked by eye on the render (step 6 of `SKILL.md`).** A
  **structured** line never wraps. Structured means: every **skills / stack
  row**, the **education entry's descriptor line**, the **Languages line**, the
  **header and contact lines**, and the **specialities line**. These read as a
  list, so a wrapped second line reads as a broken list — and on the
  specialities line and the skills rows a wrapping separator run can also
  scatter in extraction (`ats.md`, `lib.typ` § specline). Three fixes, in
  order of preference: **more rows with fewer items each** (splitting one
  overlong row in two costs the page nothing — the wrapped line it replaces
  was already a second line), a **shorter label**, or the measure/size of the
  row. Never squeeze the body size to buy it.
- **Soft, and it is a drafting preference (step 5 of `SKILL.md`).** Experience
  **bullets** aim for one line wherever the honest content allows it — that is
  what the 30-second scan actually reads. Two lines are fine for a bullet that
  earns them; three means the bullet is two bullets. **Prose wraps freely**:
  the Profile/Summary is a paragraph and wrapping is its job. This is a rule
  for the real CV as much as for the demonstration content.

**The "too much like Word 97" test.** Every recipe must read as current, not
merely as clean. The failure mode to ban, by name: *if the page could have
come out of a 1990s-2000s word processor's default template, the recipe
fails.* Symptoms that trigger it:

- a thin full-width rule under every section heading (this absorbs the older
  "full-width rule reads as 1997" trap);
- a default-looking Times-ish serif used with no typographic intent;
- underlines on text that is not a link;
- default round bullets with no drawn character;
- uniformly tight leading with no spacing hierarchy;
- default border grays (`luma(180)`-ish hairlines used as furniture);
- clipart, ornaments, emoji.

Applied to the roster: no family uses a full-width hairline under a heading, the
serif family uses its serif as a display face over a sans body (not as body
Times), no family underlines non-link text, and the hierarchy rules above
forbid flat leading.

**Section labels are a fingerprint too.** Fourteen families that all say
"Profile / Technical Skills / Core Strengths" still read as one tool. Each
family therefore carries its **own default labels** (in
`FAMILIES[...]["labels"]`, `scripts/pick_design.py`), and the script draws a
variant per candidate from these pools:

| role | pool |
|---|---|
| profile | Profile · Summary · Professional Summary |
| skills | Technical Skills · Skills & Tools · Skills · Expertise · Technical Stack |
| soft skills | Core Strengths · Strengths · Working Style · *(dropped entirely)* |

No two families ship the same default *triple* — three of them used to default
to "Profile / Technical Skills / Core Strengths", which is the very fingerprint
this table exists to break; `pick_design.py --selftest` now asserts the fourteen
triples are distinct.

Hard limits, from `references/regional.md` § Section names and
`references/ats.md`: **Education**, **Languages** and the experience sections
keep their conventional stems (a qualifier after the stem is fine —
"Nursing Experience" — an exotic name is not), and every variant above is a
conventional stem in the North-American market file. In French the same
variance runs on the FR column of that table (Profil · Résumé de carrière;
Compétences techniques · Compétences et outils · Expertise) with the
non-breaking space before the colon. A market whose file names one convention
wins over the draw.

**Where the mechanics stop and the devices start.** `templates/lib.typ` holds
the shared MECHANICS and nothing else: the entry emission order that keeps a
date from floating to the end of the extraction, the one-paragraph skills row,
the unbreakable mark+value box, the platform marks as inline SVG, the two
generic icon sets, the single-ROW alignment grid, the palette derivation, the
painted chip, the specialities line, the condensed early-career line, the
page-2 running head. Each one is a verified answer to a trap in
`references/ats.md`, and each is validated **once** — re-implementing one per
family is how a fixed trap comes back — and it was: nine families each carried
their own hand-copied 50 lines of SVG path data and their own `job()` grid).

The DEVICES are never in the lib: heading devices, header compositions,
glyphs, colour roles, the *shape* of the skills row, the fonts. Mutualising one
of those rebuilds the attractor this whole system exists to break. A primitive
in the lib therefore never chooses a colour, a size or a face — it takes them
as parameters, or takes already-styled content. Consequence for delivery: the
hand-off is **two files**, the `.typ` and `lib.typ` beside it (Typst has no
bundler), or the lib inlined into the `.typ` before sending.

**Gabarit — density is a family attribute, not a global setting.** Two CVs from
this skill should differ at arm's length before a single word is read, and the
page geometry is the cheapest way to get that. Each family owns its margins,
its measure, its body size and — derived from the bottom margin, per the fill
rule — its own fill target (`page` in `FAMILIES`, `scripts/pick_design.py`):

| gabarit | margins (x / top / bottom) | body | fill target | families |
|---|---|---|---|---|
| dense | 1.5 / 1.2 / 1.2 cm | 10.5pt | 94-96% | `bold-display`, `clause-index`, `color-band`, `editorial-serif`, `humanist-quiet`, `keyline-corporate`, `swiss-grid` |
| dense, larger type | 1.5 / 1.2 / 1.2 cm | **11pt** | 94-96% | `margin-index` (a 15.5cm measure wants a bigger face, not a smaller one) |
| dense, hard | 1.6 / 1.3 / 1.3 cm | 10.5pt | 94-96% | `hard-edge` |
| dense, mono | 1.6 / 1.25 / 1.2 cm | 10.5pt | 94-96% | `mono-technical` |
| dense, quiet | 1.6 / 1.3 / 1.2 cm | 10.5pt | 94-96% | `quiet-luxury` |
| **uniform** | **1.5 / 1.5 / 1.5 cm** | 10.5pt | **93-95%** | `gutter-rail` — the only family whose margins are equal on all four sides, and the reason is its source: a tiling desktop's *outer gap* is one number applied to every edge |
| mid | 1.8 / 1.3 / 1.6 cm | 10.5pt | 92-94% | `avant-poster` (the margin is what its bars bleed into, so it has to be real) |
| airy | 2.0 / 1.6 / 1.6 cm | 10.5pt | 92-94% | `engraved-card` (a card's value is its margin) |

Two measured lessons from deriving these, both counter-intuitive:

- **Wide margins make a page harder to fill, not easier.** A narrow measure
  wraps more, so it produces *more* line height from the same content: at
  2.2cm margins and 11pt body, the reference content would not hold one page at
  any leading in range, while at 2.0cm and 10.5pt it does. Conversely a *dense*
  family with a very wide measure produces few wraps and under-fills, so it
  needs a generous rhythm to reach its target — `clause-index` legitimately
  sits at `leading 0.849em`, and that loose leading over a wide measure is
  exactly how a technical-standard document is set. Do not read a big leading
  as a mistake; read it against the measure.
- **The airy gabarit costs a section.** `engraved-card` ships `soft: None` — it
  drops the soft-skills section — and that is not a fill trick dressed up: with
  2cm margins, eight sections of the reference content do not hold one page and
  seven do (measured both ways), and a terse formal card is the one register
  that would not have carried an evidence-line strengths block anyway. When a
  gabarit and the honest content disagree, the page count or the section list
  gives way, never the type size or the margins (SKILL.md rule 5).

**Default section order is a family attribute too.** The skeleton is the last
thing left that all fourteen shared, and a shared skeleton reads as one tool
even under fourteen different skins. Each family declares an `order`
(`FAMILIES`, `scripts/pick_design.py`), and **a target market's own convention
always overrides it** (`references/regional.md`):

- *chronological* — profile, experience, other, education, skills, soft,
  languages: the nine original families.
- *skills-forward hybrid* — profile, **skills**, experience, other, education,
  soft, languages: `clause-index`, `hard-edge`, `gutter-rail`. Sourced, and
  bounded: the
  skills-forward order recruiters accept is the hybrid/combination format
  (summary + skills up top, full reverse chronology below), never a functional
  CV that *replaces* the chronology.
- *narrative-led* — profile, experience, other, education, **skills**, soft,
  languages: `avant-poster`. Its specialities line already carries the stack
  for the 30-second scan, so the detailed skills block does not need to lead.
- *credential-led* — profile, **education**, experience, other, skills,
  languages: `engraved-card`, the formal-classic skeleton, education raised and
  no soft-skills section.

**Header composition is a family attribute** — and it is the first thing on the
page, so it does more anti-clone work than any heading device. The fourteen
compositions in play: one grid ROW with a right-hand contact column
(`swiss-grid`, `editorial-serif`, `keyline-corporate`), a full-width reversed
band (`color-band`), left-aligned with contacts stacked under
(`humanist-quiet`), an oversized coloured name with wide-gap contact lines
(`bold-display`), name in the content column beside an empty margin
(`margin-index`), **contacts first** as a letterhead line (`quiet-luxury`), a
single monospace contact line (`mono-technical`), **fully centred**
(`engraved-card`), **two zones over a reference row** (`clause-index`), a
**monogram block** beside the name (`hard-edge`), a **full-bleed masthead
bar** (`avant-poster`), and a **statusline strip of painted segments** across the
top with the name under it (`gutter-rail`). Only families whose composition
has a right-hand cell take a photo, and only where the market expects one.

**The specialities line — a family trait, on four families.** Under the
name/title, the 5-7 mastered skills, set small, separator-joined: the
30-second scan gets the stack before it gets the prose, and retailoring per
application becomes one line to edit. Two independent real CVs converged on it,
and it recurs across published CVs and template galleries alike.

- **Four families carry one** — `avant-poster`, `bold-display`,
  `clause-index`, `hard-edge` (`spec` in `FAMILIES`). Not all fourteen: a
  device on every family is a new fingerprint for the tool, which is the exact
  opposite of the point.
- **Each styles it its own way**: case, separator and colour are the family's
  (`hard-edge` mono uppercase, pipe-separated, hue A; `avant-poster` display
  face, slash-separated, hue A; `bold-display` a drawn hue-B square as the
  separator; `clause-index` small bold accent, middot-separated).
- **It is content, not decoration.** SKILL.md rule 2 applies to every item on
  it — a skill with no experience bullet behind it is keyword stuffing in the
  most prominent position on the page.
- **Mechanics** (`lib.typ` § specline): linear emission, **no `tracking`**
  (letterspacing extracts as `N E X T` and stops matching), every item boxed so
  none can break across a line end. Verified in extraction as whole words with
  the separators intact.
- **Wrapping: a caution, not a prohibition.** A separator-joined run that wraps
  is a documented scatter risk (`ats.md`), so it was measured: pushed to 14
  items so it wrapped onto a second line, the line still extracted in order,
  separators intact, the wrapped remainder on its own contiguous line, and the
  section below it untouched. Keep it to 5-7 items anyway — that is the
  30-second-scan argument, not an extraction one — and re-read the extraction if
  it does wrap, since only one separator on one face was stress-tested.

**Where the devices come from: harvested, not imagined.** Every device in every
recipe below is traceable to a real page — a published CV, a design tradition
with a name and canonical practitioners, a template gallery's expressive
vocabulary — and never to "what would look creative here". This is a method,
not a courtesy: an agent inventing devices converges on the same three or four
obvious ones, which is the clone problem again one level up. So the loop is:
**search for real examples first, name the current or the source, extract the
concrete device (what is drawn, where, doing what job), check it against the
invariants — extraction first — then attribute it to one to three families as a
trait.** Never to all of them. A device that fails extraction goes into
`ats.md` with its measured failure instead of being quietly dropped; a device
that passes goes in with its proof. The same rule governs § Guided creation.

**One date convention per document.** Whatever the family, every date on the
page sits in the same place — the experience entries and the education entry
use the *same* entry helper, dates right-flushed. The old workaround for the
orphaned-date extraction trap (rendering the bullet-less education entry as a
linear "Degree, Institution — 2019 · City" line) is **retired**: it put that
one date mid-line while every other date was flush right. What actually fixes
the trap is (a) *text after the date in the extraction order* — the institution
+ descriptor line under the entry — and (b) a date run as **wide** as the other
right-flushed dates: `2015 – 2019` extracts in place, a bare `2019` does not.
The grid keeps the visual alignment either way (verified: `pdftotext` emits
degree → 2015 – 2019 → institution, no floating year). See
`references/ats.md`.

**Font pools, not fixed pairs.** A family owns a typographic *register*, not
two font names. Each declares 3-5 vetted faces per role (display / body) in
`scripts/pick_design.py` FONTS — **the single source of truth**, with the exact
family name as `typst fonts` reports it, the provenance (distro package or
Google Fonts), and the fallback chain; this file describes the registers and
never repeats the lists. `pick_design.py` draws the pair deterministically,
then checks local availability and prints the provenance of anything missing —
**never a silent fallback** (a missing font only *warns* in Typst and swaps
itself out, which turns a design into a bug with no error message). **A font
swap moves the fill**: every family is re-gated on a second pool pair. Of the
first nine, three passed untouched and six needed a re-tune (they spilled the
last unbreakable section onto page 2, and got it back through a
leading/spacing trim of 0.03-0.09em rather than a smaller section gap;
`margin-index`, whose rhythm is the coarsest, also had to give back 4pt of
section gap). All four new ones needed a re-tune on pair 2, and the moves were
LARGER (0.05-0.24em) — the tuner now does that loop by bisection, so budget one
`--tune` run per pair rather than a hand loop, and widen its bounds before
touching a device. One hard
rule across the roster: **no display face is shared by two families** — the
display face is half of a family's identity. Body faces may overlap.

**A width failure is a pool failure, not a tuning failure.** On a family whose
whole metadata register is monospaced, a *display* mono is disqualified by
measurement: `gutter-rail` drew Martian Mono for pair 2, passed the gate on it
(1 page, fill 95%, ratio 3.75) and still had to reject it, because at 8.5pt its
advance width runs ~25% over a document mono's and it broke **line integrity**
twice — the statusline strip wrapped onto a second line and the education
descriptor wrapped after "foreign". `--tune` cannot fix that: it moves leading,
and the row was too wide, not too tall. Red Hat Mono, Geist Mono and Noto Sans
Mono all hold both lines at the same size (verified by bbox). Check advance
width, not just legibility, for any face that will carry a structured line.

Vetting checklist — every candidate face must pass **all** of it before it
enters the dictionary:

1. legible at 10.5pt body / 8.5pt metadata, printed, not only on screen;
2. a complete weight set: regular + bold minimum, medium/semibold desirable;
3. real italics if the family's register uses italics (a synthesised oblique
   fails);
4. correct figures — lining or old-style *by design*, unambiguous 0/O and 1/l,
   and tabular figures where dates are right-flushed;
5. professional register: no fantasy, no display-only quirks in a body face;
6. licence verified free (SIL OFL / GPL+font exception / Apache) and the
   provenance recorded;
7. stable metrics — no missing glyphs for the target languages, no hinting
   collapse at small sizes;
8. and the roster rule: not already a *display* face of another family.

Enrichment by web search (allowed, but only on purpose): when the user
explicitly asks for something fresh, when no pool member fits the case, or
when a drawn face is unavailable locally, the agent **may** look for another
free face on the web — provided it (1) passes the checklist above, (2) is not
one of the over-used defaults (`Inter`, `Roboto`, `Montserrat`, `Lato`,
`Open Sans` — fine as *body* faces, but they bring no distinctiveness as a
*display* face), (3) respects the no-shared-display rule, and (4) is **added to
the FONTS dictionary** once it has passed the gate. Today's discovery is
tomorrow's pool. Without an explicit request or an availability problem: the
dictionary only, no search.

**Colour: harmonised mini-palettes, not lone hues.** An accent never travels
alone. Each family declares a harmony rule, and the recipe derives the rest
from the accent so a new hue follows the same logic:

```typst
#let soft = color.mix((accent, 40%), (white, 60%))     // hairlines only, never text
#let ink  = color.mix((luma(95), 85%), (accent, 15%))  // metadata gray, hue-biased
#let muted = ink
#let dark = color.mix((luma(25), 92%), (accent, 8%))   // body ink, barely biased
```

- **Why the bias**: a pure neutral gray beside a warm accent reads as a
  mismatch. 15% toward the accent hue is enough to harmonise and invisible as
  "a colour". Verified across the curated accents (every family's
  gamuts, deduplicated): derived `ink` lands at 6.43-7.31:1 on white, `dark` at
  16.64-17.42:1, and every accent itself at ≥ 6.0:1 (measured minimum
  6.11:1) — all above threshold.
- **Harmony rule per family**: `mono` (same hue lightened) for the restrained
  families, `analogous` (hue +24°, desaturated) for the mid ones,
  `complementary` (opposite hue, heavily desaturated, decorative hairlines
  only) for the most expressive. Harmonising *refines*; it never adds a
  visible second colour.
- **The not-flashy guardrail** — applies to every family, expressive ones
  included: accents are **deep and contained** — HSL lightness ≤ 42% and
  contrast ≥ 6:1 on white at the sober level. That excludes neons and
  pastels (both need high lightness) by construction. Every curated gamut
  below measures L 18-41%.
- **The muddy-hue veto** — no hue between **40° and 70°** (yellow through
  olive) on text or on small elements, at any level of the dial
  (`EXCLUDE_HUE` in `gen_palette.py`, enforced on hue A *and* hue B). The
  reason is perceptual, not arithmetic: a yellow has to be darkened hard to
  reach 6:1 on white, and a dark yellow is not gold, it is mustard — it reads
  as dirty at 9-11pt. Those hues are only acceptable as a large background
  flat, and no role in this palette is one. Dull gold/bronze/olive accents
  were removed from the curated gamuts for the same reason (`editorial-serif`
  and `keyline-corporate` lost `#6e4a1f` bronze, `bold-display` lost `#4e512a`
  olive, `mono-technical` lost `#664e2d` and `#66513c`); the dark browns that
  stayed (`#4a2f10` walnut, `#5c4632` bark) are chocolate and greige at
  L 18-28%, not gold. A family's expressiveness comes from **how widely
  it uses the colour** (a full band, heavy bars, oversized type), never from
  a louder hue: each accent must stay credible on a conservative employer's
  CV even when the family itself is an expressive one.
- **Generating beyond the curated gamuts**: `scripts/gen_palette.py` builds a
  harmonised palette from the family's rule and a deterministic seed, then
  *validates* every role against the general contrast formula on its real
  background and re-draws until it passes (selftest: 50 draws × 9 families ×
  3 dial levels, all roles above threshold). Three-step audacity dial:
  `sober` (default, the guardrail above), `expressive` (unlocked by a
  creative target field), `bold` (vivid hues — **only on the explicit request
  of the candidate or user, never inferred by the agent**). A conservative
  target market caps the dial back to sober and never raises it
  (`references/regional.md`). At every level the invariants hold: contrast
  validated, the accent keeps the role its family assigns it, extraction
  unaffected.

**Duotone — a second hue with a job, on six families.** Asking "is one
accent enough colour?" has one honest answer: on the sober families, yes —
monochrome *is* their character, and adding a hue to `swiss-grid` or
`quiet-luxury` would break the recipe, not enrich it. On the expressive and
modern side, a real second hue adds range without adding noise, and the
creative register is duotone by construction — a constructivist poster IS a
two-ink medium. Six families declare one: `color-band`, `bold-display`,
`mono-technical`, and all three creative families, `hard-edge`, `avant-poster`
and `gutter-rail`.
The rules are strict:

- **Roles, not decoration.** Hue A and hue B each own 1-2 *named* jobs, listed
  in the recipe, and never swap: e.g. A = the devices (band, bars, heading
  marks), B = the data (dates, markers, icons). A second hue sprinkled across
  icons *and* backgrounds *and* text is exactly the "cheap two-colour flyer"
  failure.
- **Hue B is subordinate.** Same dial ranges as A (the professional guardrail
  applies to *both* hues: HSL lightness inside the dial, contrast ≥ the level's
  minimum on white), drawn one notch calmer in saturation. Two co-equal
  saturated hues read as a template.
- **The pair comes from the harmony, not from taste**: complementary
  (hue +180°) for `bold-display`, `mono-technical`, `hard-edge` and
  `avant-poster`, split-complementary for `gutter-rail` (its hue A is always a
  blue or a violet, so the true complement lands in the red-brown band the
  § 14 hue veto excludes), far-analogous (+62°) for `color-band`.
  `gen_palette.py` derives and validates the pair in one draw and re-draws the
  whole palette if hue B fails its contrast — so an invalid pair can never be
  emitted. It now knows the same red-brown veto § 14 documents (hue B is
  vetoed on 10-35° in addition to the 40-70° yellow-olive zone), not just for
  the curated rows: when the mechanical +180°/+62° derivation lands hue B
  there, it is ROTATED off the band — never darkened or desaturated further,
  since it is exactly the low lightness the sober floor forces that turns
  that band brown (see § 14) — to the nearest hue that clears the band by a
  12° margin (1° past the edge still measured brown at floor saturation) and
  keeps ≥55° of separation from hue A; if no rotation clears both, the whole
  palette re-draws. Escaping the low edge lands hue B in wine/plum (blue
  overtakes green in the mix, off the brown axis entirely); escaping the high
  edge risks the 40-70° zone next door, so the low-edge escape is tried first.
  Verified on a rendered sample (gutter-rail and mono-technical, both
  seeded to draw a raw hue B in-band): the rotated hue reads as a chosen red
  ink in colour and as a distinct mid-gray in a grayscale render, in both the
  8.5pt statusline dates and the 8.5pt mono dates — no faded-toner brown. The
  curated A→B pairs in the recipes above are **paired by index**: never
  combine hue A of one row with hue B of another.
- **Grayscale**: both hues are deep by construction, so they converge in a B&W
  photocopy — never encode information in the *difference* between them (that
  rule already holds for a single accent).

**Creative fields.** For a candidate in a creative field the CV is itself a
portfolio piece, and the pool unlocks the **`creative` register** (`hard-edge`,
`avant-poster`, `gutter-rail`) on top of the expressive modern families. The expressiveness
lives in the **typography, the colour and the devices — never in the
structure**: single text column, linear skills, clean extraction, all the ATS
invariants hold exactly as they do on an accountant's CV. A creative field
also lifts the colour dial to `expressive`; a conservative target market caps
both the dial and the register straight back down.

**Contact icons — two different things, one rule each.**

*Generic icons* (map pin, phone handset) are a family attribute, not a global
feature. Where a family has them they are drawn in Typst from primitives
(`circle`, `rect`, `polygon`, `ellipse`, `line` composed inside a fixed-size
`box` with `place`) — no external files, so the template stays
self-contained, and no text is emitted (verified in the extraction of every
family). Both sets live in `templates/lib.typ` as `icons-line(c)` /
`icons-solid(c, bg: …)`, taking the colour as a parameter — the drawing is a
mechanic, the choice of style (or of none) is the family's. Two styles, each
belonging to its family's register: **line** (0.9pt stroke, rounded) and
**solid** (filled, angular). Four families carry no generic icon **by
principle** (`swiss-grid`, `humanist-quiet`, `margin-index`, `engraved-card`) —
that absence is itself the style choice. A fifth carries none for a **measured**
reason rather than a principled one: on `gutter-rail` the contact items sit in
8.5pt statusline segments, and at that size the 0.9pt stroked pin and handset
read as a "C" and a "[" — the vector detail collapses, while the solid path-data
marks stay legible. Where a generic icon would have to be that small, use
`mk.pin` / `mk.phone` and say so in the recipe.

*Platform marks* (email, LinkedIn, GitHub, a personal site) are in **every
family, including those four**: a platform logo is a functional identifier
of a contact channel, not ornament, and a recruiter scans for it. They are
real brand marks — LinkedIn and GitHub from Simple Icons (CC0 1.0, no
attribution required), email/phone/pin/website from Tabler Icons' filled set
(MIT) — provenance kept in a comment in the `.typ` — inlined as an SVG string via
`image(bytes(…), format: "svg")`, so the document stays ONE self-contained
file, the mark is vector (it emits no text — verified at the gate in every
family) and its colour is a parameter rather than baked into a file:

```typst
#let pmark(d, vb, c, h: 7pt) = box(baseline: 0.5pt, image(
  bytes("<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"" + vb
    + "\"><path fill=\"" + c.to-hex() + "\" d=\"" + d + "\"/></svg>"),
  format: "svg", height: h))
```

The *colour* is part of the family's accent budget, not a given: accent
(`editorial-serif`, `keyline-corporate`, `humanist-quiet` — where the links
are accent-coloured too, so a gray mark beside a teal value reads as a
mismatch), white on the band (`color-band`), hue B (`bold-display`,
`mono-technical`), metadata gray (`quiet-luxury`), body ink (`swiss-grid`,
whose purism forbids colour on the contact column), `ink` (`margin-index`,
`engraved-card`, `clause-index` — the last two because their accent budget is
spent elsewhere: on a centred lozenge, on the clause numbers), hue B
(`hard-edge`, `avant-poster`).
Each mark+value pair sits in a `#box[…~…]` so the mark can never be orphaned
at a line end. A mark at `h: 7pt` inside a 9pt line adds ~1pt of line height:
on a page already at 96% fill that is enough to push the last unbreakable
section over (measured on `swiss-grid` and `margin-index`) — re-run the
tuning loop after adding them. Never emoji, never clipart, never a font glyph
(an icon *font* would leak private-use characters into the extraction — the
path data does not).

**Sourcing a new icon later**: same recipe as above — inline path data from
Simple Icons (brand/platform logos, CC0) or Lucide/Tabler (generic icons,
ISC/MIT) via Iconify, pasted as a `d`/`viewBox` pair into `lib.typ` exactly
like `pmark`'s existing entries. Never an icon font: private-use codepoints
leak into the extraction (`references/ats.md`).

Shared to all families (deltas vs the template, applied once): the palette
block above, and note that the template's *body* hardcodes the accent in two
places — the organization name inside `job()` (which the education entry now
uses too) and the Languages separator `•`: keep them accent-coloured only in
the families whose accent role covers organization names, and make them
`dark`/`ink` elsewhere. On a duotone family the separator and the markers
belong to hue B, never hue A.

### 1. swiss-grid — International Typographic Style · register: neutral

Müller-Brockmann / Helvetica school: flush-left, objective, structure carried
by rules and size steps, never by colour on text.

- **Heading device**: 2.5pt accent rule **above** the title, full width,
  nothing below it. Title case, 12.5pt bold, `dark` — not accent.
- **Skills block**: small uppercase run-in label (8.5pt bold, **no
  tracking**), space, then the items — `LANGUAGES Python, TypeScript, …`.
  (A fixed-width label column was tried and rejected: at 70-82pt the labels
  either fuse with the values in extraction or wrap and interleave.)
- **Accent role**: the section rules only. No coloured text anywhere.
- **Icons**: the contact line is marked **all-or-nothing** (amended after a
  half-iconified line was found worse than either extreme: platform marks
  present but city/phone bare): every contact item carries a mark, city and
  phone included (`mk.pin` / `mk.phone`, added to `lib.typ` alongside the
  platform marks, same Tabler Icons provenance), all in the body ink,
  never in colour. No generic icon FONT and no colour on marks — that part of
  the original purism holds; only the "no mark on city/phone" half was the
  inconsistency.
- **Header**: one grid ROW — name 24pt bold + role line left, 5-line contact
  column right-aligned (photo slot = right cell).
- **Type**: one neo-grotesque for display *and* body. Pool (and provenance,
  and the fallback chain): `scripts/pick_design.py` FONTS `swiss-grid`.
- **Accents** (mono harmony): `#b3261e` swiss red · `#33475b` slate ·
  `#0f4c5c` petrol.
- **Verified**: leading `0.555em`, spacing `0.615em`, section `above` 13pt
  (18pt airy), 6pt after the title (2.2:1) → 1 page, fill 96%, white-run
  ratio 3.40 (tallest gap 1.7% of page height). Default labels: Profile /
  Technical Skills / Strengths.
- Markets: any; safe for conservative. Photo: yes.

### 2. editorial-serif — contemporary editorial · register: classic

The serif family of the roster, modernised: a **serif display face over a
sans body** — the pairing current editorial design actually uses — with the
hierarchy carried by a big size jump rather than by small caps. The dated
signals were removed deliberately: no all-serif setting, no small caps as
structure, and no hairline running to the margin on the title's baseline
(the most "academic paper" element of the earlier version).

- **Heading device**: a **short 46pt × 3.5pt accent bar above** the title
  (magazine kicker rule), then the title at 13pt bold `dark` in the display
  serif, title case. No full-width rule anywhere.
- **Skills block**: serif bold label, a 3pt accent square (vector mark, not a glyph),
  then the items in the sans — the serif/sans jump does the separating.
- **Accent role**: the kicker bars, the header role line, and the skills
  squares. Dates and organizations stay `ink`/`dark`.
- **Icons**: **line** style, accent, in the contact column; platform marks in
  the accent too.
- **Header**: one grid ROW — serif name 25pt bold + accent role line left,
  contact column right (photo slot = right cell). No rule.
- **Type**: serif display over a humanist sans body; body stays 10.5pt — the
  sans body is what keeps it out of the LaTeX register. Pool:
  `pick_design.py` FONTS `editorial-serif`.
- **Accents** (mono harmony): `#1f3a5f` navy · `#5b2a5e` plum · `#72191f`
  oxblood (bronze `#6e4a1f` was dropped: muddy at text sizes, see the
  muddy-hue veto).
- **Verified**: leading `0.55em`, spacing `0.63em`, section `above` 15pt
  (20pt airy), 3pt after the title (5.0:1) → 1 page, fill 96%, white-run
  ratio 3.40 (1.7% of page height). The boundary is carried by the kicker bar
  *plus* a 5:1 ratio; buying that air cost 0.07em of leading. Default labels:
  Summary / Technical Skills / Core Strengths.
- Markets: academia, law, finance, public sector, DACH, France. Safe for
  conservative. Photo: yes.

### 3. color-band — reversed-out masthead · register: modern

Brand/editorial current: a solid colour field carries the identity, the body
below is plain black-on-white.

- **Heading device**: heading reversed out **white on a solid accent bar**
  (full text-width block, `inset: (x: 6pt, y: 2.5pt)`), UPPERCASE 11.5pt
  bold. No rules anywhere in the document.
- **Skills block**: two-line rows — small uppercase bold label on its own
  line, items on the line below (verified: extraction keeps label and values
  adjacent).
- **Accent role** (DUOTONE, see § Duotone): hue **A** does backgrounds only —
  the header band and the heading bars; hue **B** does the dates and the list
  markers. No other coloured text anywhere.
- **Icons**: **solid** style in **white**, inside the band — platform marks
  in white too.
- **Header**: full-width band, `#place(top + left, dx: -1.5cm, dy: -1.2cm,
  rect(width: 100% + 3cm, height: 3.0cm, fill: accent))` — `place` takes no
  flow space, so the band lands on page 1 only (a page `background` would
  repeat it on page 2). Name 24pt bold white, role line and contacts white
  inside the band; photo slot = right of the band.
- **Type**: a contemporary brand sans with display and text cuts of one
  system. Pool: `pick_design.py` FONTS `color-band`.
- **Accents** (analogous harmony; hue A must also clear 4.5:1 against
  **white** text, not just on white). Validated A→B pairs, far-analogous
  (+62°), never mixed across rows: `#1f3a5f` navy → `#502d66` (11.0) ·
  `#1e5631` forest → `#2b4b5d` (9.3) · `#3b3486` indigo → `#733b6c` (8.2) ·
  `#0f4c5c` petrol → `#2c1a66` (14.5).
- **Verified**: leading `0.583em`, spacing `0.643em`, section `above` 7pt
  (12pt airy), 5pt after the title (1.4:1 — the *filled-device* exemption:
  the reversed bar is the boundary) → 1 page, fill 94%, white-run ratio 2.33
  (1.4% of page height), the lowest of the roster and still the boundary that
  reads best. Knife-edge on the template's content: +1pt of `above` spills to
  2 pages. Budget a re-tune.
- Markets: tech, startups, creative-adjacent, marketing. Not for
  conservative markets. Photo: yes.

### 4. humanist-quiet — restraint, no rules at all · register: neutral

Vignelli-school austerity: the device is the *absence* of a device;
whitespace and one size step do all the delimiting.

- **Heading device**: none. 13pt bold `dark` title case. With no device, the
  gap *is* the boundary — this family runs one of the largest section gaps of
  the roster (only `margin-index`, which also has no device, runs wider).
- **Skills block**: bulleted rows — accent `–` marker, semibold label, em
  dash, items, with `hanging-indent: 16pt` so wrapped lines align under the
  label (still one paragraph per row: extraction-safe).
- **Accent role**: the bullet markers (both lists and skills rows) and the
  links (`#show link: set text(fill: accent)`). Headings, roles,
  organizations and dates all stay `dark`/`ink`.
- **Icons**: all-or-nothing on the contact line (amended: city/phone were
  bare while the platform marks carried icons — worse than either extreme).
  Every contact item is marked, in the accent (its links are accent-coloured:
  a gray mark beside a teal value reads as a mismatch) — `mk.pin` / `mk.phone`
  added to `lib.typ` alongside the platform marks, same provenance. A family
  whose device is absence still marks its contact line consistently; the
  no-device principle governs the section headings, not this line.
- **Header**: name 23pt bold + role line left-aligned, contacts on two
  left-aligned lines below, no rule.
- **Type**: one humanist sans, display and body, nothing else. Pool:
  `pick_design.py` FONTS `humanist-quiet`.
- **Accents** (mono harmony): `#0e6862` teal · `#33475b` slate · `#8c3b00`
  rust.
- **Verified**: leading `0.545em`, spacing `0.645em`, section `above` 26pt
  (31pt airy), 4pt after the title (6.5:1) → 1 page, fill 96%, white-run
  ratio 6.60, tallest gap 3.3% of page height — over the 3.5% hole limit only
  a *boundary* may exceed, which is exactly what it is. With no device at all,
  this family buys its boundary in white and nothing else.
- Markets: any; safe for conservative. Photo: no.

### 5. keyline-corporate — contemporary corporate report · register: modern

*(Formerly `smallcaps-sober`, whose serif small caps read dated.)* The sober
family for professional services, rebuilt in a current register: an accent
keyline as the only device, an accent-labelled skills block, and a clean
grotesque throughout.

- **Heading device**: an accent **keyline down the left of the title** —
  `box(inset: (left: 11pt), stroke: (left: 4pt + accent))[…]`, which hugs
  the title's own height exactly. Title case 13pt bold `dark`. No rules
  anywhere in the document.
- **Skills block**: the **label itself carries the accent** (bold accent
  label, then the items in `dark`) — no colon, no separator glyph, no rule.
  Nobody else colours the skills label.
- **Accent role**: the heading keylines, the skills labels, and the dates.
  Headings, roles and organizations stay `dark`.
- **Icons**: **line** style, accent, in the contact column; platform marks in
  the accent too.
- **Header**: one grid ROW — name 24pt bold + role line left, contact column
  right (photo slot = right cell), closed by a `soft` hairline.
- **Type**: a clean grotesque; weight and size do the contrast, no second
  typeface needed. Pool: `pick_design.py` FONTS `keyline-corporate`.
- **Accents** (analogous harmony): `#33475b` slate · `#1f3a5f` navy ·
  `#0f4c5c` petrol · `#5b2a5e` plum (bronze `#6e4a1f` dropped — muddy-hue
  veto).
- **Verified**: leading `0.54em`, spacing `0.62em`, section `above` 23pt
  (28pt airy), 5pt after the title (4.6:1) → 1 page, fill 95%, white-run
  ratio 7.25 (2.9% of page height).
- Markets: law, finance, consulting, public sector, DACH. Safe for
  conservative. Photo: yes.

### 6. bold-display — geometric display, heavy contrast · register: modern

Avant-Garde-lineage display type: oversized geometric caps, big weight
jumps, colour spent on the name.

- **Heading device**: 13pt UPPERCASE `dark` display title over a **2.5pt
  accent underline as wide as the title itself** — `box(inset: (bottom: 3pt),
  stroke: (bottom: 2.5pt + accent))[…]`. A `line(length: 100%)` inside a box
  resolves to the *available* width and silently reproduces the banned
  full-width rule (verified) — use the box stroke.
- **Skills block**: bold title-case label, a 12pt gap, then the items — no
  colon, no dash, no punctuation; weight and space do the separating.
- **Accent role** (DUOTONE, see § Duotone): hue **A** is spent on the name
  (29pt) and nothing else; hue **B** carries the heading underlines, the list
  markers and the icons. Everything else `dark`/`ink`.
- **Icons**: **solid** style, hue **B**, on the contact lines — platform
  marks in hue B too.
- **Header**: oversized accent name left, role line below, contacts on two
  left-aligned lines with wide `#h(9pt)` gaps instead of separators.
- **Type**: a geometric display face for the name over a neutral sans body.
  With URW Gothic, `weight: "bold"` maps to URW Gothic Demi — verified
  rendering, not a fallback. Pool: `pick_design.py` FONTS `bold-display`.
- **Accents** (complementary harmony). Validated A→B pairs (hue B = the
  opposite hue, one notch calmer, contrast in brackets), never mixed across
  rows: `#8c3b00` rust → `#105a90` steel (7.3) · `#0e6862` teal → `#72191f`
  oxblood (11.2) · `#3b3486` indigo → `#7d3312` sienna (8.9 — olive `#4e512a` was
  dropped, its hue 65° sits inside the muddy band) · `#b3261e` red →
  `#1a6265` petrol (7.1).
- **Verified**: leading `0.536em`, spacing `0.616em`, section `above` 14pt
  (19pt airy), 6pt after the title (2.3:1) → 1 page, fill 94%, white-run
  ratio 3.60 (1.8% of page height). Its heavy underline carries the boundary,
  which is why it clears the floor on so little white. Default labels:
  Profile / Technical Stack / Core Strengths.
- Markets: tech, product, design-adjacent, startups. Not for conservative
  markets. Photo: no.

### 7. margin-index — classic marginalia · register: classic

Book typography (Bringhurst school), the second *classic* current and nothing
like `editorial-serif`: one text serif throughout, old-style figures, and the
section titles **hanging in the left margin beside their own content** instead
of sitting over it. There is no rule, bar or panel anywhere in the document.

- **Heading device**: a **short 2.5cm accent rule above the margin title**,
  the width of the margin column only — book furniture, never a rule under or
  beside the heading — and the title lives in a 2.5cm
  left column of a single-ROW `grid` (title cell first, so extraction stays
  heading → body; verified), right-aligned against the gutter, 10.5pt bold in
  the accent. Nobody else colours its section titles.
- **Skills block**: *italic* run-in label, then the items in roman — **no
  separator glyph at all**; the italic/roman jump does the separating.
- **Accent role**: the margin titles and the list markers (`—`). Roles,
  organizations and dates stay `dark`/`ink`.
- **Icons**: all-or-nothing on the contact line (amended: city/phone were
  bare while the platform marks carried icons — worse than either extreme).
  Every contact item rides the line marked, in `ink` — `mk.pin` / `mk.phone`
  added to `lib.typ` alongside the platform marks, same provenance.
  Marginalia still bolts no *decorative* ornament onto the page — the
  no-generic-icon principle governs headings and section devices, not
  whether the contact line is consistently marked.
- **Header**: name + italic role line in the *content* column, contacts on one
  line below it (the margin column stays empty, and is the photo slot when a
  market asks for one).
- **Type**: a text serif with real italics and old-style figures
  (`number-type: "old-style"` is part of the recipe, not decoration), one
  family for both roles. Pool: `pick_design.py` FONTS `margin-index`.
- **Accents** (mono harmony): `#4a2f10` walnut · `#1f3a5f` navy · `#5b2a5e`
  plum.
- **Verified**: body **11pt** (the measure is narrow — 15.5cm — so the type
  goes up, not down), leading `0.80em`, spacing `1.00em`, section `above` 30pt
  (35pt airy) → 1 page, fill 96%, white-run ratio 7.40, tallest gap 3.7% of
  page height (a boundary, so under the 5% ceiling and not a hole). No
  heading→body gap exists here — title and body share the grid row — so the
  2:1 ratio does not apply and the section gap plus the margin rule carry the
  whole boundary. Widest gaps of the roster: re-scan this family first after any
  content edit.
- Markets: academia, law, public sector, publishing, DACH, France. Safe for
  conservative. Photo: yes (margin column).

### 8. quiet-luxury — warm restrained minimalism · register: neutral

The 2020s “quiet luxury” current: warmth instead of neutrality, quality
signalled by typography and spacing rather than by structure. Distinct from
`swiss-grid` (which is mathematical) and from `humanist-quiet` (which removes
devices from a structured system) — this one has exactly one small device and
spends its colour on the employers.

- **Heading device**: the title, then a **short 34pt × 2pt accent tick** on its
  optical centre, in the accent — inline punctuation, not furniture. Measured
  and rejected on the way: a hairline running from the title out to the right
  margin, which reads as word-processor furniture beside every heading.
- **Skills block**: the label is set in the **metadata gray** (`ink`), the
  items in `dark` — *colour*, not weight or a glyph, does the separating. No
  colon, no dash, no bullet.
- **Accent role**: the organization names and the heading ticks. Nobody else
  puts the accent on the employers.
- **Icons**: **line** style in the **metadata gray**, never the accent — the
  accent has its two jobs already; the platform marks follow, in the same gray.
- **Header**: **contacts first** (a small gray letterhead line), then the
  name, then the role — the reverse of every other family's order. Photo slot
  = right cell of the header row.
- **Type**: one warm humanist sans, generous but unshowy, display and body.
  Pool: `pick_design.py` FONTS `quiet-luxury`.
- **Accents** (mono harmony): `#5c4632` bark · `#33475b` slate · `#0e6862`
  teal.
- **Verified**: leading `0.58em`, spacing `0.68em`, section `above` 20pt
  (25pt airy), 4pt after the title (5.0:1) → 1 page, fill 96%, white-run
  ratio 3.85 (2.5% of page height).
- Markets: any; safe for conservative; reads slightly senior/executive. Photo:
  yes.

### 9. mono-technical — technical-documentation aesthetic · register: modern

The spec-sheet / changelog current: monospace devices, tabular dates, high
information density. Real and current, but **concentrated in software,
engineering and data roles** — on a general-business or executive CV it reads
as costume. Second duotone family, and the one where the two hues are most
clearly split by job.

- **Heading device**: a 6pt filled **hue-A square** followed by a 3pt hue-B
  bar (a two-tone spec-sheet index mark), then the title in the
  **monospace** face, 11.5pt bold `dark`, title case. No rules anywhere.
  Monospace headings *look* letterspaced but carry no `tracking` — extraction
  verified clean (this is the one legal way to get that look).
- **Skills block**: a spec-sheet `KEY = VALUE` row — mono uppercase key in
  hue A, the `=` in hue B, the values in the body sans. **Verified failure on
  the way**: setting each item as an inline "chip" (`box` with a fill)
  scatters the block in `pdftotext` — every box becomes its own text cluster
  and items interleave across rows. Chips are banned everywhere, not only
  here (`ats.md`).
- **Accent role** (DUOTONE): hue **A** = the heading squares and the skills
  keys; hue **B** = the dates, the list markers and the icons.
- **Icons**: **line** style in hue **B** — the same hue that carries the
  data, platform marks included.
- **List marker**: a 3pt filled hue-B **square drawn as a box**, not a glyph —
  the only family whose marker emits no character at all.
- **Header**: name, role line, then the contacts on ONE monospace line.
- **Type**: a document-grade monospace for every device + a neutral sans body.
  Pool: `pick_design.py` FONTS `mono-technical`.
- **Accents** (complementary harmony). Validated A→B pairs: `#1f3a5f` navy →
  `#8f2d3f` crimson (8.0) · `#33475b` slate → `#8a2f2a` brick (8.3) ·
  `#0f4c5c` petrol → `#66291a` (11.1) · `#5b2a5e` plum → `#3c633a` (6.9). The
  first two replaced `#664e2d` and `#66513c`: a complemented navy lands on
  dull bronze, which is the muddiest thing this system can produce at 8.5pt.
- **Verified**: leading `0.651em`, spacing `0.771em`, section `above` 20pt
  (25pt airy), 4pt after the title (5.0:1) → 1 page, fill 94%, white-run
  ratio 4.00 (2.4% of page height).
- Markets: software, engineering, data, hardware, startups. Not for
  conservative markets, not for general business. Photo: no.

### 10. engraved-card — engraved stationery · register: classic

The engraved-letterhead and social-stationery tradition (the Crane-school
stationers, the conventions the etiquette manuals codified). Engraving made a
clean hairline expensive to cut and a tint impossible, so the page carries
almost no furniture: a **centred axis**, one quiet serif, wide margins, and a
single small mark. The third *classic* current and nothing like the other two —
`editorial-serif` is a magazine, `margin-index` is a book, this is a card.

- **Heading device**: a 4.4pt accent **lozenge** (a rotated filled square —
  vector, emits no text) centred above a **centred** title, 12pt semibold
  `dark` in the display serif, title case. The engraver's spot: one mark, dead
  centre. No rule, no bar, no panel, nothing full-width anywhere in the
  document. The only family on a centred axis and the only one whose section
  titles are centred.
- **Skills block**: the label, then a **full stop**, then the items —
  `Languages. Python, TypeScript, …` — the engraved catalogue/trade-card
  convention, where the period was the separator because a rule and a colour
  were not available. Nobody else punctuates with a period.
- **Accent role**: the section lozenges and the short rule under the name. Two
  jobs. Dates and organizations stay `ink`/`dark`.
- **Icons**: **no generic icon, by principle** — engraving bolted no ornament
  on. The platform marks ride the contact line in `ink`, never competing with
  the centred axis.
- **Header**: **fully centred** — name 23pt in the display serif, a 56pt
  centred accent **hairline** (0.6pt) under it, the italic role line, then the
  contacts on one centred line. No photo slot: a centred card has no side cell,
  and that is the point. The hairline is the point of the family: engraving
  made a clean thin line the expensive part, so 1.2pt over 34pt read as a
  stubby dash sitting on the name and 0.6pt over 56pt reads as an engraver's
  rule.
- **Section order**: *credential-led* — Summary, **Education**, target-field
  experience, other experience, Skills, Languages. Ships `soft: None`.
- **Type**: one quiet serif for display and body, engraved-letterform lineage.
  Pool: `pick_design.py` FONTS `engraved-card`.
- **Accents** (mono harmony): `#5c1f3a` garnet · `#2f4858` deep petrol ·
  `#3d3550` aubergine.
- **Gabarit**: the airiest — 2.0cm x, 1.6cm y, body 10.5pt, fill target
  **92-94%**.
- **Verified**: leading `0.556em`, spacing `0.656em`, section `above` 15pt
  (20pt airy), 5pt after the title → 1 page, fill 94%, white-run ratio 3.23.
  The centred title needed `block(width: 100%, breakable: false)`: a
  non-breakable block shrinks to its content, so `align(center)` inside it
  centred each title on its own section's widest line and the titles drifted up
  to 150px apart (`typst-primer.md`). **The header block needs the same
  `width: 100%`, and this is the family's worst failure mode when it is
  missing**: without it the whole lockup centred on the contact line (its
  widest line) and sat 42pt left of the centred section titles — the short
  rule under the name read as decentred while the titles read as centred, on
  the one family whose entire character is a centred axis (measured on the
  render: name axis at x=366 vs section axis at x=425, 100 ppi). The lozenge
  is drawn 4.4pt inside a 5pt box: `rotate` defaults to `reflow: false`, so
  the 6.2pt diagonal overflows the box visually at zero layout cost; at 3.5pt
  the mark read as a speck of dust rather than a lozenge.
- Markets: any; safe for conservative; reads formal. Photo: no.

### 11. clause-index — numbered-clause standard document · register: neutral

The numbering-of-divisions convention of technical standards and specification
documents (ISO 2145, DIN 1421), with a header borrowed from the German
business-letter standard's reference line (DIN 676). Its device is a **number**,
not a rule — distinct from `swiss-grid` (a rule above), `humanist-quiet` (no
device) and `quiet-luxury` (a tick beside).

- **Heading device**: an **outdented clause number** in tabular figures,
  hanging in a fixed 20pt gutter, in the accent; the title flush at the text
  edge, 12pt bold `dark`, title case. Single-ROW grid, number cell first, so
  extraction stays number → title → body. No rule, bar, fill or panel anywhere.
  Nobody else numbers its sections, and nobody else spends its accent only on
  numerals.
  **The number never replaces the conventional stem.** Harvested
  counter-evidence is explicit: an ordinal used *as* the label (`01` alone)
  costs the reader speed and costs the ATS its section classifier. `1
  Experience` keeps both, and the stem rule from `regional.md` still applies.
- **Skills block**: a **sub-clause number** — the section's own number with a
  sub-index (`2.1`, `2.2` …) in the accent, then the bold label, then the
  items. Nobody else numbers its skills rows, and the numbering is the same
  device one level down rather than a second invention.
- **Accent role**: the numbers, section and sub-clause. That is the whole
  budget — which is why the icons are gray here.
- **Icons**: **line** style in the **metadata gray**, never the accent; the
  platform marks follow, in the same gray.
- **Header**: **two zones over a reference row**. Identity block left (name
  22pt, role line), contact column right (also the photo slot), and inside the
  left zone a **reference row** of run-in label/value pairs — Location,
  Availability, Authorization — then the **specialities line** in the label
  register, so it reads as a data row and not as a slogan. The reference row
  and the specialities line stay *inside* the left zone deliberately: spanning
  the full measure under a two-zone header pulled the rightmost pair into the
  contact cluster in extraction (`ats.md`).
- **Section order**: *skills-forward hybrid* — Summary, **Skills & Tools**,
  target-field experience, other experience, Education, Strengths, Languages.
- **Type**: an institutional grotesque with tabular figures. Pool:
  `pick_design.py` FONTS `clause-index`.
- **Accents** (mono harmony): `#33475b` slate · `#1f3a5f` navy · `#0f4c5c`
  petrol.
- **Gabarit**: dense — 1.5cm x, 1.2cm y, body 10.5pt, fill **94-96%**. The
  widest measure of the roster, and the reason its leading is the loosest
  (§ Gabarit).
- **Verified**: leading `0.849em`, spacing `0.929em`, section `above` 22pt
  (27pt airy), 5pt after the title → 1 page, fill 96%, white-run ratio 2.89.
  Pair 2 needed a large rhythm move, not a device change: `0.609em / 0.689em`
  at the same 22pt gap → fill 96%, ratio 3.73. First attempt cut the section
  gap to 16pt instead and landed at ratio 2.00 — sitting on the floor — because
  the tuner's default search range (0.80-1.30× the current leading) was too
  narrow; widening the range was the right fix, and shrinking the boundary was
  not. Widen `--tune`'s bounds before touching a device.
- Markets: any; safe for conservative; reads engineering/institutional.
  Photo: yes (right cell).

### 12. hard-edge — neo-brutalist · register: **creative** (duotone)

The neo-brutalist current read from **print**, not from a component library:
flat solid fields, oversized knockout type in solid black, hard square corners,
and a heavy grotesque display against a monospace for every piece of metadata.
That grotesque/monospace split is the signature — without it the recipe is just
a black box.

**Which dialect, and why it matters (harvested).** This family used to be a
white **hard-bordered box** with a flat 2.5pt **offset block** behind it, plus
skills items in **tinted pill fields**. A reader named a specific
code-learning platform on sight. Thick black border + zero-blur offset shadow +
candy tint field is not "neo-brutalism" in general — it is the *neubrutalism
UI-component* dialect that several brands ship, and reproducing it makes the
CV look like a third party's product (§ The final bar — non-recognition, brand
clause). The print/poster dialect of the same current is where the family sits
now: black solid fields, knockout type, **no shadow anywhere, no tint fields**.
Note that this does not soften the § Anti-references rule the old version was
built on — a *blurred* offset shadow was always the slop tell; the finding is
that a flat one, in that specific combination, was a brand tell.

- **Heading device**: the title **knocked out of a hard black slab** — white
  UPPERCASE 11.5pt bold on `dark`, square corners, `inset: (x: 6pt, y: 2.5pt)`,
  the slab only as wide as its own title, so nothing is full-width anywhere in
  the document. Distinct from `color-band`, whose heading also reverses out:
  that one is a **full-text-width bar in the accent**, this is a
  **shrink-to-title slab in the body ink**. No border, no shadow, no
  `measure()` needed — `box(fill:)` shrinks to its content. The trap survives
  for anyone who reinstates a `rect` here: `rect(width: 100%)` inside a box
  resolves to the *available* width and silently reproduces the banned
  full-width bar (same trap as `line(length: 100%)`).
- **Skills block**: a **reversed-out tag**, then the items plain — the section
  slab's own shape one scale down, which is how this family repeats its
  vocabulary instead of inventing a second one. The tag is a **painted chip**
  (`highlight()`), not a `box`, and that is mechanical, not stylistic: a
  `box(stroke:)` around the *label alone* tore the first two labels off their
  values and emitted them at the END of the section on this very page shape
  (`ats.md`, `lib.typ` § chip). `highlight()` paints behind the same text run,
  so the row stays one text cluster and extracts byte-identically to a plain
  linear row. `extent: 1pt` so the field hugs its label, and the gap to the
  first item is the paragraph's **own word space** — **new verified trap**: an
  `h(4pt)` there, the obvious way to widen that gap, tore `LANGUAGES` and
  `MENTORING` off their values and emitted them at the END of their sections.
  Explicit spacing beside a `highlight` breaks the run exactly as a `box`
  does; a plain word space does not. The items carry **no tint** (see the
  dialect note above), and the soft-skills rows take the same shape.
- **Accent role** (DUOTONE): hue **A** owns *the identity* — the monogram
  block and the specialities line. Hue **B** owns *the data* — the dates, the
  list markers, the icons. The section slabs and the skills tags are `dark`,
  not accent: the structure of this family is black.
- **Icons**: **solid** style, hue B. Nothing in this family is rounded.
- **List marker**: a hard-bordered **outlined square**, drawn (emits no text) —
  the only outlined marker of the roster; `mono-technical`'s is filled.
- **Header**: **monogram + name**. A 1.15cm hard-bordered square holds the
  initials reversed out of hue A, the name 25pt beside it, the role line in the
  mono under it, then the **specialities line**, then one monospace contact
  line. The monogram is real **text** inside a drawn box, never an image: an
  image-rendered monogram is invisible to extraction and leaves a hole where
  the identity should be.
- **Section order**: *skills-forward hybrid*.
- **Type**: a heavy grotesque display + a neutral sans body + **a document mono
  for all metadata** — this family declares a third font role. Pool:
  `pick_design.py` FONTS `hard-edge`.
- **Accents** (complementary harmony). Validated A→B pairs, never mixed across
  rows: `#b3261e` red → `#0f4c5c` petrol · `#1e5631` forest → `#5c1f3a` garnet
  · `#3b3486` indigo → `#8c3b00` rust.
- **Gabarit**: dense, hard — 1.6cm x, 1.3cm y, body 10.5pt, fill **94-96%**.
- **Verified**: leading `0.786em`, spacing `0.876em`, section `above` 20pt
  (25pt airy), 6pt after the title → 1 page, fill 95%, white-run ratio 3.12.
  Tuning it is what produced the floor-is-not-a-target note in § Invariants:
  17pt of section gap measured 2.00 (at the floor, no margin left), 25pt
  measured 6.00 (over-separated for an ink device), 20pt landed at 3.00.
- Markets: design, product, creative-adjacent tech, startups. Never for
  conservative markets; not in the default pool. Photo: no.

### 13. avant-poster — constructivist poster · register: **creative** (duotone)

The constructivist poster tradition (the Lissitzky lineage): a **two-ink**
discipline — one colour plus black — flat geometric bars, type locked to a hard
axis. The two-ink constraint is also why this family
survives a photocopy: both hues are deep and nothing encodes information in the
difference between them.

- **Heading device**: a heavy 5pt hue-A **bar that bleeds off the left page
  edge** and stops at the section title, with the title set on the bar's **own
  line**, to its right. Not a rule above the title (`swiss-grid`), not a kicker
  over it (`editorial-serif`), not an underline below it (`bold-display`), not
  a keyline hugging its height (`keyline-corporate`), not a fill behind it
  (`color-band`): the bar is beside the title, on its baseline, and it runs off
  the page. **Nobody else lets a device leave the text block.** The bleed is a
  `place`d rect at `dx: -<x-margin>` — `place` takes no flow space and emits no
  text, so the bar costs nothing in layout and nothing in extraction.
- **Skills block**: the label in hue A, then a drawn 1.5pt × 8pt hue-B
  **divider bar** (a box: emits no text), then the items. The divider is the
  section device's own flat-bar vocabulary one scale down — a poster repeats
  its own shapes at different sizes instead of inventing a second language.
- **Accent role** (DUOTONE): hue **A** = the bleeding bars (masthead and
  sections). Hue **B** = the skills dividers, the markers, the icons, the
  dates.
- **Icons**: **solid** style, hue B — flat geometric shapes only.
- **List marker**: a filled hue-B **circle**, drawn (emits no text). The only
  circular marker of the roster: a constructivist page is bars and circles.
- **Header**: a **masthead bar composition** — a full-bleed hue-A bar across
  the top of page 1, the name 30pt in the condensed display under it, the role
  line, the **specialities line**, then the contacts. The bar is `place`d so it
  lands on page 1 only — a page `background` would repeat it on page 2.
  **No diagonal, and its removal is the harvested lesson of this family.** An
  earlier version placed a rotated hue-B bar top right and defended it as "the
  constructivist diagonal". A reader looked at the page and asked what it was
  for; there was no answer. That is the § Anti-AI-slop test failing on its one
  question — *does this element do work the reader can name?* A diagonal that
  sets an axis is a decision; a diagonal that only signals "constructivist" is
  decorative geometric confetti with a manifesto. The character is carried by
  the two elements that do work: the bars that bound the sections and leave the
  text block, and the committed two-ink discipline.
- **Section order**: *narrative-led* — Summary, target-field experience, other
  experience, Education, **Technical Stack**, Working Style, Languages.
- **Type**: a condensed grotesque display + a humanist sans body. Pool:
  `pick_design.py` FONTS `avant-poster`.
- **Accents** (complementary harmony). Validated A→B pairs, never mixed across
  rows: `#b3261e` red → `#1f3a5f` navy · `#8c3b00` rust → `#0e6862` teal ·
  `#72191f` oxblood → `#2f4858` petrol.
- **Gabarit**: mid — 1.8cm x, 1.3cm top, 1.6cm bottom, body 10.5pt, fill
  **92-94%**. The margin is what the bars bleed into, so it has to be real.
- **Verified**: leading `0.548em`, spacing `0.638em`, section `above` 15pt
  (20pt airy), 6pt after the title → 1 page, fill 93%, white-run ratio 3.00.
  The 93% is post-diagonal-removal and post-line-integrity: splitting the
  overlong `Tools & DevOps` row in two and shortening the education
  descriptor to one line cost one line net, which the band absorbs.
- Markets: design, art direction, motion, advertising, cultural sector. Never
  for conservative markets; not in the default pool. Photo: yes (right of the
  masthead).

### 14. gutter-rail — the themed developer environment · register: **creative** (duotone)

The "coordinated theme" practice of developer environments, read in **print**:
an editor's chrome (a gutter with its sign column, fold marks, a statusline of
segments) plus the tiling-desktop conventions (bar modules as discrete segments,
one uniform gap everywhere, ONE reserved accent for the live state). Its sources
are documented decisions, not screenshots: the light-theme lineage that
*Solarized Light* opened and the curated light palettes after it (Catppuccin
Latte, Gruvbox light, Rosé Pine Dawn, Tokyo Night Day) for the colour practice;
the opinionated-rice configs (an Omarchy-style Hyprland setup: every bar module
reset to a flat square, one accent hardcoded *outside* the theme system for
active modules) for the segment vocabulary; a curated-rice distro
(Archcraft-style: one "apply theme" action rewriting the colour tokens of every
chrome surface at once) for the coordination; and an institutional desktop
(COSMIC) for the two structural ideas that make it presentable — a single
corner-style token applied uniformly to every surface, and a **first-class light
theme whose accent is re-derived per surface (in OKLCH) rather than inverted
from the dark one**.

**Locked to software, twice.** Creative register *and* a domain lock: the
vocabulary only reads to an audience that lives in these tools, so it needs a
software/technical field **plus** an explicit request. On a general-business CV
it is costume, exactly like `mono-technical` (§ 9) — of which it is the opposite
side of the same coin: that one is the *document* a program produces, this one is
the *environment* the program runs in.

**What was deliberately NOT built**, because each one is what makes a page
identifiable as one product rather than as a current (§ The final bar): no dark
background (§ The destination support), no line numbers in the gutter (a run of
"1 2 3" pollutes the extraction, and this is the harvested reason the gutter here
carries *marks* and not numbers), no syntax colouring (the duotone budget is two
hues with jobs, not a theme), no tab bar, no minimap.

- **Heading device**: a **gutter rail** — a 0.9pt hue-A rule running down the
  **margin** beside the section, for exactly that section's own height and no
  further, with a 3.6pt hue-A **fold mark** sitting in the gutter beside the
  title (an editor's fold chevron / diff sign). Title flush left at the text
  edge, 12.5pt bold `dark` in the UI grotesque, title case. Nobody else runs a
  vertical rule beside body content: `keyline-corporate`'s keyline hugs the
  *title's* own height and carries no mark, `margin-index` puts a whole column
  in the margin and no rule at all. The rail's nameable job is that it marks the
  section's vertical **extent** — where a rail stops, the section has stopped —
  so the white between two rails is bracketed by ink at both ends, which is what
  lets this family sit near the separation floor.
  **The rail must be in the margin (`outset`), never at the text edge with the
  text indented (`inset`)** — that is a measured requirement and the reason is
  in § Invariants (the instrument's blind spot): the inset version blinds the
  gate's separation scan, ratio 1.26.
- **Skills block**: a **fold row** — a drawn 3.4pt hue-B fold triangle, then the
  key in **lowercase mono**, then the items in the body sans. Lowercase is the
  point: after thirteen families of uppercase, bold, italic and numbered labels
  it is the shape left unused, and an editor's own configuration keys are
  lowercase. No colon, no `=`, no separator glyph — face and case do the
  separating. Distinct from `mono-technical`'s `KEY = VALUE` (uppercase mono key,
  an `=` operator in hue B) and from `hard-edge`'s reversed-out tag.
- **Accent role** (DUOTONE, harvested split): hue **A** = *the chrome* — the
  gutter rails and the crumb marks. Hue **B** = *the live state* — the drawn
  marks (fold, change-bar, the Languages separator), the dates and the platform
  marks. The role split is the tradition's own: an opinionated rice reserves one
  accent, outside the theme system, for whatever is active. A 14% wash of hue A
  paints the statusline segments; a wash is a **surface**, not a colour job (same
  construction as `mono-technical`'s).
- **Icons**: **no generic pin/phone icon**, and for a measured reason rather than
  a principle (§ Contact icons): every mark in the statusline is a platform mark
  (`mk.pin` / `mk.phone` beside the four channel logos), in hue **B**. The line
  is marked all-or-nothing.
- **List marker**: a drawn 2pt × 5.4pt hue-B **vertical change-bar** — the sign
  an editor paints in its gutter for a modified line, and the rail's own shape one
  scale down (the family repeats its vocabulary instead of inventing a second
  one). Emits no text. The roster's other drawn markers are a filled square, an
  outlined square and a circle.
- **Header**: a **statusline strip** of painted segments across the top of the
  page — one segment per contact item, each on the theme surface, gaps between
  them — then the name 24pt in the UI grotesque and the role line under it. The
  contacts come *first*, like `quiet-luxury`'s letterhead line, but as a bar of
  discrete modules rather than a run of text.
  **The mechanics are the whole permission slip**: each segment is a painted
  `chip` (`highlight`), never a `box(fill:)`, the gaps are plain spaces
  (`sym.space.quad`) and never `h()`, and each mark+value pair goes through `nb`.
  Verified against the unsegmented version of the same page: **byte-identical
  extraction** (see § Structure primitives and `ats.md`). The marks ride in the
  gaps *before* their fields, because `highlight` paints behind a text run and
  not behind an inline image box — there is no construction that puts a vector
  mark under the paint, and it reads as the icon+value pairing a bar module has
  anyway. **Which half of the pair the `chip` wraps is therefore a rendering
  decision, not a formality**: `nb(mk.x, seg[value])` (mark outside, tint on the
  value only) is correct, and `seg[#nb(mk.x)[value]]` — the tint wrapped round
  the whole pair — is the bug it replaces. `highlight` starts its rectangle at
  the first *glyph*, so with the pair wrapped, `extent: 2.2pt` reached 2.2pt back
  into the image box and the paint edge **cut every mark in half**. Wrapping the
  value alone spends the same extent inside the pair's own non-breaking space
  (~5.1pt at 8.5pt mono): the tint clears the mark by ~2.9pt, and the mark stays
  grouped with its value because the gap to the *previous* segment
  (`sym.space.quad` less the extent) is the wider one. Extraction is unchanged
  either way — `nb`'s box is the same box — so this one is caught only by looking
  at the render at 300dpi, which is why SKILL.md step 6's LOOK pass now asks for a zoomed crop wherever paint meets a vector mark.
- **Family variant** (`variants` in `FAMILIES`, drawn by `pick_design.py`): the
  **square-vs-pill** binary of the source tradition — the default bar style is a
  rounded pill, the opinionated dialect resets every module to a flat square.
  ONE `seg-radius` value (0pt or 2.5pt) governs every painted surface at once,
  which is the institutional-desktop idea rather than a per-element decision. It
  is the only variant axis in the roster; a variant on every family would be one
  more thing all fourteen share.
- **Section order**: *skills-forward hybrid*.
- **Type**: a **UI grotesque** for the chrome (name, section titles) + a
  **document mono for the BUFFER** — every piece of machine state, i.e. the
  statusline segments, the dates, the employer descriptors and the skills keys,
  and nothing else — + a neutral sans body. The chrome/buffer split is what keeps
  this family off `mono-technical`'s ground, where the *headings* are mono. Second
  family to declare a third font role. Pool: `pick_design.py` FONTS
  `gutter-rail`, and see § Font pools for why a *display* mono is disqualified
  here.
- **Accents** (complementary harmony). The curated hue-A gamut is the harvested
  light-theme palette **darkened to this skill's guardrail** — and that
  adaptation is the finding, not a formality: of every accent in those five
  palettes, exactly one (Rosé Pine Dawn's pine `#286983`, 6.11 on white) already
  clears the sober 6:1 floor. The rest are tuned for a cream editor background at
  4-5:1 and have to come down 15-25 points of lightness at constant hue.
  Validated A→B pairs, never mixed across rows: `#286983` pine → `#6a2f4d`
  prune · `#174f78` deep blue (from Solarized's `#268bd2`) → `#983e6a` magenta
  (from Solarized's own `#d33682`) · `#4d2287` mauve (from Latte's `#8839ef`) →
  `#2e6b24` state-green (from Latte's own `#40a02b`) · `#7e3c07` amber-bark
  (from Gruvbox light's `#d65d0e`) → `#1b6a63` teal.
  **Hue B is DESATURATED and stepped away in lightness, and both halves of that
  are load-bearing** — measured on the rows this replaces. The first pair-1 hue
  B was `#8a2f2a` brick, drawn at pine's *own* saturation and lightness (both
  H·S53·L34-35): equal-energy complementaries with no hierarchy, so the red
  fought the pine instead of sitting under it, and the grayscale separation was
  only 1.36. Desaturating and stepping it fixed the hierarchy but kept the hue,
  and the hue was the remaining problem.
  **Hue B is now split-complementary, never the true complement, and the reason
  is a hue veto that the 40-70° exclusion does not cover: the red-brown band,
  ~10-35°.** Hue A here is a blue or a violet, so its 180° complement lands
  squarely in that band — which is how three of these four rows shipped a
  terracotta (`#743a25`, H16), a rust (`#9c4b11`, H26) and a sienna
  (`#814022`, H19). At the lightness the sober 6:1 floor forces (L≈30) a hue in
  that band is not a red, it is a **brown**: R > G > B with B lowest is the
  definition. And hue B in this family carries the page's *smallest* ink — the
  8.5pt mono dates, the 1.5pt × 5.4pt change-bar, the 3.4pt fold triangle — so
  it is exactly where a brown fails: measured on 300dpi crops of the date column
  and the Languages line, the terracotta dates read as **faded or degraded
  black**, like a printer low on toner, instead of as a second ink. This is a
  hue problem with no contrast fix, because raising the contrast is what makes it
  brown. Rotating hue B off the band solves it at zero cost to the harmony
  reading: the same 300dpi crop of `#6a2f4d` prune reads as a chosen colour,
  because B > G there keeps it off the brown axis. Prune is also the *harvested*
  answer rather than the arithmetic one — pine's own source palette (Rosé Pine
  Dawn) carries `love` `#b4637a`, and darkened to the guardrail it lands in this
  hue — so hue B is now derived the same way hue A is. Numbers, all four rows
  above both floors: prune 9.87 on white / **1.62** grayscale (was 8.84 / 1.45),
  magenta 6.50 / **1.33**, state-green 6.47 / **1.71**, teal 6.39 / **1.30**.
  Note the asymmetry the veto creates: a *state-green* hue B is impossible on
  pine (1.02 in grayscale — a mid green and a mid teal-blue are the same gray)
  and correct on mauve (1.71), because the floor that matters is a **luminance**
  one, not a hue one. Judged on the light build **and** on the grayscale render,
  in that order — the paper is the destination (§ The destination support), the
  editor vocabulary is only the aesthetic.
  **Monochrome was tested and rejected, on the render.** The obvious objection
  to any hue B here is that a real editor's chrome is monochrome, so the
  duotone is decoration; two builds answer it. Collapsing hue B onto pine puts
  **eight** roles on one hue (rails, crumb marks, the statusline wash, fold
  triangles, change-bars, the Languages separator, the six platform marks, the
  dates) — the § Tokens trap verbatim — and it hands the page's thinnest
  elements its *weakest* ink: pine is 6.11 on white, sitting on the floor, while
  hue B's whole job is small marks that want more contrast than the 0.9pt rails,
  not the same. Routing the dates to body ink instead is worse: right-aligned
  near-black dates stop being a register and start competing with the bold role
  title on their own baseline (visible in the 300dpi date crop). And the source
  tradition is not monochrome — an opinionated rice reserves **one** accent,
  outside the theme system, for whatever is live. Monochrome here is an editor
  with no cursor colour.
- **Gabarit**: uniform — 1.5cm on all four sides, body 10.5pt, fill **93-95%**.
- **Verified**: leading `0.761em`, spacing `0.851em`, section `above` 16pt (21pt
  airy), 4.5pt after the title → 1 page, fill 95%, white-run ratio 3.00. Pair 2
  (Instrument Sans / Red Hat Mono / Noto Sans, pill segments, mauve → state-green)
  needed leading `0.770em` / spacing `0.860em` → 1 page, fill 95%, ratio 3.75.
  Both re-verified after the hue-B revision and the segment fix above (same
  numbers; colour and paint geometry move no text).
  Default labels: Profile / Skills / Working Style. Also verified: the grayscale
  render (rails, segments, marks and dates all still read), and the screen-first
  build of the same source (§ The destination support).
- Markets: software, engineering, data, developer tooling, technical startups.
  Never for conservative markets, never for general business; not in the default
  pool. Photo: no.

### Reach

Curated, all of it validated: **14 families × font pair × accent** =
**645 side-by-side-distinguishable looks** (avant-poster 27, bold-display 36,
clause-index 27, color-band 36, editorial-serif 48, engraved-card 48,
gutter-rail 108, hard-edge 81, humanist-quiet 27, keyline-corporate 36,
margin-index 48, mono-technical 48, quiet-luxury 27, swiss-grid 48 —
`hard-edge` and `gutter-rail` count on three faces each, because both draw a
metadata monospace on top of display and body). `gutter-rail`'s square/pill
variant doubles its own row again, 108 → 216, so **753**; and **1506** counting
the two list markers, which is the weak axis. On top of that, and orthogonal to it:
**60 section-label combinations** per family (3 profile × 5 skills × 4
soft-skill options, one of which is dropping the section), **six** of the
fourteen families carrying a validated **duotone pair** instead of a single
hue, and past the curated gamuts `gen_palette.py` generating fresh harmonised
palettes — duotone pairs included — on demand.

And the axes added in this pass do not multiply the count so much as they make
two CVs differ *before a word is read*: **eight gabarits** (margins, measure,
body size, derived fill target), **three default section skeletons**,
**fourteen header compositions**, and a **specialities line** on four families
and not on the other ten.

The point is not the number, it is the *axes*: a family changes the three
clone markers at once, the gabarit changes the page's proportions, the order
changes its skeleton, the header changes the first thing seen, the font pool
changes the voice inside the family, the label pool changes the lexical
skeleton, and the palette changes the colour — "pick a fresh accent" moved
none of the others. The bar is the one stated at the top of § Design families:
a recruiter who has seen two of these must not recognise the third, and none
of them may read as a consumer tool's default template.

## Anti-references — two, named, with their tells

There are exactly **two** named failure modes, and no third gets invented: a
growing list of things to avoid stops being a test and becomes a mood. Both are
pass/fail against the rendered page.

**1. Anti-Word-97** — the full tell list is in § Rules common to every family
("The 'too much like Word 97' test"): a thin full-width rule under every
heading, a default Times-ish serif with no typographic intent, underlines on
non-link text, default round bullets, uniformly flat leading, default border
grays as furniture, clipart or ornaments. Question to answer with a *no*:
*could this page have come out of a 1990s word processor's default template?*

**2. Anti-AI-slop** — the recognizable generative aesthetic, and the newer of
the two risks, because it is what an agent asked to "make it look creative"
produces. Its tells, as they actually appear:

- **stacked or gaudy gradients**, and one specific habit: the diagonal
  indigo-to-purple wash that a popular CSS framework's default palette made
  ubiquitous. No gradient earns its place on a CV; a gradient also collapses in
  a grayscale photocopy.
- **blur and glow** — soft drop shadows everywhere, glows, rounded corners on
  everything. No family carries a drop shadow at all now: `hard-edge` used to
  carry a flat 0-blur one, and it came off for a different reason — it read as
  a brand (§ hard-edge, the dialect note). The rule stands either way: a
  shadow is at best a decision at 0 blur and always slop at 4pt.
- **fake-grunge or novelty display faces** standing in for typographic
  personality.
- **decorative geometric confetti** — floating dots, blobs, arcs, little
  triangles with no job. Also the faux-handmade overcorrection (doodles,
  scrapbook textures): the opposite cliché is still a cliché.
- **the unchosen default face** used as if it were a choice, and three
  identical rounded cards in a row with uniform padding.
- **maximalism with no hierarchy**: effects on every element, so nothing leads;
  and its twin, **symmetric centred everything**, where every block is centred
  because centring requires no decision.
- **fake data made to look like data**: skill meters, percentage bars, dot
  ratings, donut charts. A recruiter names these by themselves, and they are
  numbers with nothing behind them — which is also a rule-2 violation.

The test, and it is a single question per element: **does this element do work
the reader can name?** A monogram identifies. A bar bounds a section. A tint
groups items. A diagonal sets an axis — *if* a reader can say which axis;
`avant-poster`'s could not, and it came off (§ 13). Anything whose only job is
to *look creative* comes off the page. Audacity is a small number of **decisions** — one
monogram, one committed duotone, one strong composition — never an accumulation.

Two things deliberately absent from this list. There is **no anti-Canva**:
template galleries are a legitimate source of expressive vocabulary (colour
blocks, an integrated portrait, a monogram, a specialities line, categorised
skill groupings, tinted fields), and the constructions there that fail are
excluded by `ats.md` on measured technical grounds, not on taste. And there is
no ban on *boldness*: the creative register exists precisely so that a bold
page can be built and then be *proven* — the gate does not soften for it.

## Guided creation — the bespoke-family mode

A user may ask for something the roster does not have ("something like a
letterpress broadside", "match this studio's identity", "nothing on your
list"). That request is granted, not deflected — but it is composed, not
improvised. The frame:

1. **The scripts' draw is a coherent STARTING POINT, not a cage.** Run
   `pick_design.py` anyway: it gives a validated palette, a vetted font pair,
   a gabarit, an order and a set of labels that already agree with each other.
   Deviating from it is allowed, with judgment and with the reason stated in
   the hand-off, as long as the result stays inside its family's grammar or
   becomes a coherent new one — and re-passes the gate.
2. **Compose the primitives, and know WHY each one exists.** Building on
   `lib.typ` is not a convenience: each primitive is a verified answer to a
   measured trap, and the *reason* is the part that transfers. `entry` exists
   because a date with no text after it in the emission order floats to the end
   of the extraction. `srow` exists because a grid extracts column-by-column
   and a per-item box becomes its own text cluster. `nb` exists because a mark
   orphaned at a line end separates from its value. `specline` refuses
   `tracking` because letterspacing extracts as `N E X T`. `chip` uses
   `highlight` and not `box(fill:)` because only one of the two keeps the row
   in a single cluster. An agent that knows the *why* can invent a new shape
   safely; one that knows only the *how* reintroduces the trap in a new costume.
3. **Anchor it in a real current, found by search — this is mandatory.** Name
   the tradition, its canonical practitioners, and its concrete device
   inventory (what is drawn, where, doing what job), the way every recipe above
   does. § Where the devices come from is the method, and it governs bespoke
   work more than it governs the roster: with no roster entry to lean on, an
   unanchored agent falls straight back onto the four obvious devices.
4. **Name your first idea, then do something else.** The first composition that
   comes to mind is, by construction, the one *any* agent would produce for
   this brief — that is what "reconverges on the template" means. Write it down
   explicitly, then build the second or third idea instead. This is the single
   most effective anti-generic move available, and it costs one sentence.
5. **Check it against both anti-references**, element by element, with the
   "does this do nameable work?" question.
6. **The full gate, and the bar of non-recognition.** Two font pairs, the
   family's own derived fill target, the separation floor *and* an obvious
   boundary to the eye, clean extraction, the rendered page looked at. A
   bespoke family gets no discount: it is held to more than the roster, not
   less, because nothing about it has been validated before.
7. **A success generalises.** A bespoke family that passes the gate, has three
   clone markers distinct from all fourteen, a font pool with no shared display
   face, a harmonised gamut, its own labels, gabarit, order and header
   composition, gets written into § Design families and into
   `scripts/pick_design.py` — and the roster is fifteen. That loop is how this
   file got to fourteen, and it is the intended way for it to keep growing.

## Tokens

- One accent color, from the chosen family's gamut, dark enough to survive
  B&W photocopy (every gamut above is pre-computed at ≥ 6.5:1 on white).
  It does only the **two or three jobs that family assigns it** — spending it
  on titles *and* organizations *and* markers *and* the subtitle is how it
  stops signalling (and how every CV starts looking alike). On a **duotone**
  family the budget is per hue, and tighter: **1-2 jobs each**, hue B always
  subordinate to hue A. Confirm the colour
  with the user early — one rejected after the build is wasted work. A hue
  outside the gamuts is fine: compute the ratio first
  (`(L1+0.05)/(L2+0.05) ≥ 4.5`, L1 the lighter; `1.05/(L+0.05)` for the
  white-background case) and against the *actual* background — `color-band`
  puts white text on the accent, which is a different pair.
- `ink` (aliased as `muted`) for metadata — derived from the accent per the
  palette block above, and always ≥ 5:1 (measured 6.5-7.1:1 across the
  curated gamuts) because dates/notes are the first thing lost in a bad
  photocopy. `soft` is decorative only: never set text in it.
- Fonts: the family names the pair. Confirm availability with `typst fonts`
  before drafting and always ship a fallback chain — a missing font only
  *warns* and silently falls back, and a fallback without the needed feature
  (a font feature a recipe depends on, e.g. real `smcp`) turns a design into
  a bug with no error message. Prefer open-license fonts and note the package in the
  hand-off.
- Body text ≥ 10pt (target 10.5-11pt); section headings ≥ 1.15× the body
  size; margins ≥ 1.5cm horizontal, ≥ 1.2cm vertical. Never drop below these
  to reach the fill target — same logic as the anti-filler clause (SKILL.md
  rule 5): change the page count, not the type size or the margins.

## Structure primitives (see templates/lib.typ and templates/resume.typ)

The shared MECHANICS live in `templates/lib.typ`, imported with
`#import "lib.typ": *` — one implementation, validated once, each one a
verified answer to a trap in `references/ats.md`. The list, with the trap each
one closes (the *why* is the part that transfers — § Guided creation):

| primitive | what it is | the trap it closes |
|---|---|---|
| `entry` | the experience/education entry: role → date → org+descriptor line, on one grid row | a date with no text after it in the emission order floats to the end of the extraction |
| `srow` | the skills row: ONE paragraph, label then items (run-in, two-line or hanging) | a data grid extracts column-by-column; a fixed-width `#box` label fuses or interleaves |
| `chip` | a painted chip — `highlight`, never `box(fill:)`; `radius` is a passthrough so a family can shape a whole RUN of segments with one value | a box per item becomes its own text cluster and the rows interleave |
| `specline` | the specialities line, items boxed, no `tracking` | letterspacing extracts as `N E X T`; an item split at a line end stops matching |
| `nb` | mark + `~` + value inside a box | a mark orphaned at a line end separates from its value |
| `marks` / `pmark` | the platform logos as inlined SVG path data | an icon FONT leaks private-use codepoints into the extraction |
| `icons-line` / `icons-solid` | the two generic icon styles, colour as a parameter | — (drawn from primitives: emits no text, and no `assets/` dir to hand over) |
| `hrow` | the single-ROW alignment grid, right cell = the photo slot | multi-ROW data grids scramble order; single-row ones are safe *when each cell is one line* |
| `earlyline` | the condensed early-career line, role first and years last in one paragraph | a bullet-less entry orphans its date; text before the date cannot |
| `runhead` | the page-2 running head, placed IN THE FLOW | a page `header:`/`footer:` field is skipped outright by many parsers |
| `derive` | the harmonised palette from one accent | a pure neutral gray beside a warm accent reads as a mismatch |
| `photo` | a cropped header photo | — |

The DEVICES are not in the lib and never will be (§ Where the mechanics stop
and the devices start). What follows is how they are built on top:

- `section(title, body)` = **one unbreakable block** (`block(breakable: false)`,
  and `width: 100%` if anything inside it is centred — a non-breakable block
  otherwise shrinks to its content and `align(center)` centres on the block)
  containing title + rule + content. This is what guarantees "no section split
  across pages". A section taller than one page will overflow instead of
  splitting — restructure content instead.
- Section heading: case, colour and device all come from the chosen **family**
  — the one hard rule is **no letterspacing/`tracking`** (it breaks text
  extraction into "S O F T WA R E"). Whatever the device, it is vector-only
  (rules, bars, panels, lozenges emit no text) or a background fill, never a
  glyph. The template's own device (accent tick + full-width hairline under an
  UPPERCASE accent title) belongs to no family: shipping it is the defect this
  system exists to prevent.
- Job entry: line 1 = bold role (left) + bold muted dates (right, month+year
  range); line 2 = semibold organization + muted descriptor
  ("City · what the employer is (1 clause) · contract type/mode"). Whether
  the organization, the dates or neither carries the accent is the family's
  call. **Education uses this same helper** — one date convention per document
  — with a wide date run ("2015 – 2019"): see the date rule in § Rules common
  to every family.
- Skills / languages / soft skills: linear paragraphs, one per category —
  never grids (ATS). The *shape* of that paragraph is the family's second
  marker (run-in label, uppercase run-in, two-line, bulleted, middot, wide
  gap); `Category: items` is the template's and belongs to no family. In
  French, whatever the shape, a non-breaking space precedes a `:`.
  Three verified failure modes when inventing a new shape: a fixed-width label
  `#box` fuses the label with the values in extraction when the label fills
  it, and wraps-then-interleaves when it doesn't; any `·`/`•`-separated
  run of items that can wrap scatters; and inline **chips** (one
  `box(fill: …)` per item) scatter and interleave across rows — each box is
  its own text cluster (`ats.md`).
- Soft skills only with evidence: `Label — evidence drawn from the CV itself`.
  Bare adjective lists get skipped by every reviewer.
- Icons: vector only, and ATS-safe because vectors emit no text. Official
  brand marks (LinkedIn "in", GitHub octocat, the envelope, the globe) read far
  better than hand-drawn shapes — inline the path data as an SVG string
  (`image(bytes(…), format: "svg")`, § Contact icons) instead of shipping an
  `assets/` dir: one file to hand over, and the colour stays a parameter
  instead of being baked into the file. Never use emoji or font glyphs as
  icons: they leak characters into the extraction.

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
- **Internal-gap scan**, now part of the gate (`measure_fill.gaps`, judged in
  `verify.py`): every all-white run inside the content area is measured, and
  the limits are relative to the page height, never in pixels — `> 0.05*h` is
  a canyon whatever it sits next to, `> 0.035*h` is a hole unless it is a
  section boundary (a run ≥ 2× the median run). To look at the spectrum by
  hand: `python3 scripts/measure_fill.py p1.png` prints the median gap, the
  three biggest and the biggest as a % of page height.
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
