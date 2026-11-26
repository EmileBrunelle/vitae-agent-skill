# Drawing rules — choosing among families, drafting a new one, vetting a font

Read this file only when the draft needs it: `--creative` or a creative target field, an explicit request for a look the roster does not have (bespoke family), a face outside the pool (font vetting), or the reasoning behind the anti-clone draw. Every ordinary draft runs on [`core.md`](core.md) plus the family file `pick_design.py` prints, and never needs this file.

## Why the draw exists (anti-clone)

**Do not "choose freely".** Measured: an agent told to pick freely reconverges on the template's own look, so the first CV of every user of this skill is the twin of all the others. The three markers that make CVs from this skill recognizable as a batch are **(1)** UPPERCASE section headings over a full-width accent rule, **(2)** a `Category: item, item` skills block, **(3)** the accent applied to the same three places (role title, rules, links). Each family recipe (`references/design/families/`) breaks all three differently.

The template's own combination (bordeaux `#7d2231`, accent tick + full-width hairline under an UPPERCASE accent title, `Category: items`, Carlito body + Montserrat headings) is clone marker #1, #2 and #3 at once. Shipping it is a defect: Montserrat is also one of the over-used faces § Font vetting bans as a *display* face, so the template's look is a starting point and never a deliverable. The bar the result must clear is the non-recognition test in [`core.md`](core.md) § The final bar: a recruiter who has seen two CVs from this skill must not recognise the third, and no page may pass for a consumer tool's default template.

An agent choosing freely reconverges on the template's own combination, so every candidate would end up with the same CV; this is why the family, the font pair, the section labels, the gabarit, the section order and the header composition are drawn by `pick_design.py` (deterministic per candidate) and applied, never re-chosen. A creative family is held to the same gate as every other: "beautiful **and** parseable" is the whole bar and it does not soften.

## Registers, roster and the widening rule

Each family carries a **register** — `modern`, `neutral`, `classic` or `creative` — and the script weights the pool with it: early-career candidates default to the modern families, mid-career to modern and neutral, and senior to neutral and classic; a conservative market drops the loud families whatever the stage (`--conservative`; `--market` is documentation only, it changes nothing). The default leans modern deliberately. Register is derived from the fact sheet (years of experience, first job, seniority of the titles) and the target market, **never** from age or any demographic datum. Whatever the profile and the flags, the script widens the pool until **at least five families** are eligible (`MIN_POOL`), so two candidates of the same profile collide at worst one time in five. Widening is additive and stops the moment five are eligible, so adding a constraint can never *widen* the pool.

**Family roster** (`id — register`; the register column `scripts/pick_design.py` weights by):

- avant-poster — creative
- bold-display — modern
- clause-index — neutral
- color-band — modern
- editorial-serif — classic
- engraved-card — classic
- gutter-rail — creative
- hard-edge — creative
- humanist-quiet — neutral
- keyline-corporate — modern
- margin-index — classic
- mono-technical — modern
- quiet-luxury — neutral
- swiss-grid — neutral

## The “too much like Word 97” test

Every recipe must read as current, not merely as clean. The failure mode to ban, by name: *if the page could have come out of a 1990s-2000s word processor's default template, the recipe fails.* Symptoms that trigger it:

- a thin full-width rule under every section heading (this absorbs the older "full-width rule reads as 1997" trap);
- a default-looking Times-ish serif used with no typographic intent;
- underlines on text that is not a link;
- default round bullets with no drawn character;
- uniformly tight leading with no spacing hierarchy;
- default border grays (`luma(180)`-ish hairlines used as furniture);
- clipart, ornaments, emoji.

Applied to the roster: no family uses a full-width hairline under a heading, the serif family uses its serif as a display face over a sans body (not as body Times), no family underlines non-link text, and the spacing-hierarchy rules in [`core.md`](core.md) § Rules common to every family forbid flat leading.

## Font vetting — a face outside the pool

**A width failure is a pool failure, not a tuning failure.** On a family whose whole metadata register is monospaced, a *display* mono is disqualified by measurement: `gutter-rail` drew Martian Mono for pair 2, passed the gate on it (1 page, fill 95%, ratio 3.75) and still had to reject it, because at 8.5pt its advance width runs ~25% over a document mono's and it broke **line integrity** twice — the statusline strip wrapped onto a second line and the education descriptor wrapped after "foreign". `--tune` cannot fix that: it moves leading, and the row was too wide, not too tall. Red Hat Mono, Geist Mono and Noto Sans Mono all hold both lines at the same size (verified by bbox). Check advance width, not just legibility, for any face that will carry a structured line.

Vetting checklist — every candidate face must pass **all** of it before it enters the dictionary:

1. legible at 10.5pt body / 8.5pt metadata, printed, not only on screen;
2. a complete weight set: regular + bold minimum, medium/semibold desirable;
3. real italics if the family's register uses italics (a synthesised oblique fails);
4. correct figures — lining or old-style *by design*, unambiguous 0/O and 1/l, and tabular figures where dates sit in columns;
5. professional register: no fantasy, no display-only quirks in a body face;
6. licence verified free (SIL OFL / GPL+font exception / Apache) and the provenance recorded;
7. stable metrics — no missing glyphs for the target languages, no hinting collapse at small sizes;
8. and the roster rule: not already a *display* face of another family.

Enrichment by web search (allowed, but only on purpose): when the user explicitly asks for something fresh, when no pool member fits the case, or when a drawn face is unavailable locally, the agent **may** look for another free face on the web — provided it (1) passes the checklist above, (2) is not one of the over-used defaults (`Inter`, `Roboto`, `Montserrat`, `Lato`, `Open Sans` — fine as *body* faces, but they bring no distinctiveness as a *display* face), (3) respects the no-shared-display rule, and (4) is **added to the FONTS dictionary** once it has passed the gate. Today's discovery is tomorrow's pool. Without an explicit request or an availability problem: the dictionary only, no search.

## Reach

Curated, all of it validated: **14 families × font pair × accent** = **645 side-by-side-distinguishable looks** (avant-poster 27, bold-display 36, clause-index 27, color-band 36, editorial-serif 48, engraved-card 48, gutter-rail 108, hard-edge 81, humanist-quiet 27, keyline-corporate 36, margin-index 48, mono-technical 48, quiet-luxury 27, swiss-grid 48 — `hard-edge` and `gutter-rail` count on three faces each, because both draw a metadata monospace on top of display and body). `gutter-rail`'s square/pill variant doubles its own row again, 108 → 216, so **753**; and **1506** counting the two list markers, which is the weak axis. On top of that, and orthogonal to it: **15 section-label combinations** per family (3 profile × 5 skills; the soft-skills section is not drawn, it is added only when the facts give evidence), **six** of the fourteen families carrying a validated **duotone pair** instead of a single hue, and past the curated gamuts `gen_palette.py` generating fresh harmonised palettes — duotone pairs included — on demand.

And the axes added in this pass do not multiply the count so much as they make two CVs differ *before a word is read*: **eight gabarits** (margins, measure, body size, derived fill target), **three default section skeletons**, **fourteen header compositions**, and a **specialities line** on four families and not on the other ten.

The point is not the number, it is the *axes*: a family changes the three clone markers at once, the gabarit changes the page's proportions, the order changes its skeleton, the header changes the first thing seen, the font pool changes the voice inside the family, the label pool changes the lexical skeleton, and the palette changes the colour — "pick a fresh accent" moved none of the others. The bar is the one stated at the top of [`core.md`](core.md) § Design families (“The final bar”): a recruiter who has seen two of these must not recognise the third, and none of them may read as a consumer tool's default template.

## Anti-references — two, named, with their tells

There are exactly **two** named failure modes, and no third gets invented: a growing list of things to avoid stops being a test and becomes a mood. Both are pass/fail against the rendered page.

**1. Anti-Word-97** — the full tell list is in § The “too much like Word 97” test above: a thin full-width rule under every heading, a default Times-ish serif with no typographic intent, underlines on non-link text, default round bullets, uniformly flat leading, default border grays as furniture, clipart or ornaments. Question to answer with a *no*: *could this page have come out of a 1990s word processor's default template?*

**2. Anti-AI-slop** — the recognizable generative aesthetic, and the newer of the two risks, because it is what an agent asked to "make it look creative" produces. Its tells, as they actually appear:

- **stacked or gaudy gradients**, and one specific habit: the diagonal indigo-to-purple wash that a popular CSS framework's default palette made ubiquitous. No gradient earns its place on a CV; a gradient also collapses in a grayscale photocopy.
- **blur and glow** — soft drop shadows everywhere, glows, rounded corners on everything. No family carries a drop shadow at all now: `hard-edge` used to carry a flat 0-blur one, and it came off for a different reason — it read as a brand ([`families/hard-edge.md`](families/hard-edge.md), the dialect note). The rule stands either way: a shadow is at best a decision at 0 blur and always slop at 4pt.
- **fake-grunge or novelty display faces** standing in for typographic personality.
- **decorative geometric confetti** — floating dots, blobs, arcs, little triangles with no job. Also the faux-handmade overcorrection (doodles, scrapbook textures): the opposite cliché is still a cliché.
- **the unchosen default face** used as if it were a choice, and three identical rounded cards in a row with uniform padding.
- **maximalism with no hierarchy**: effects on every element, so nothing leads; and its twin, **symmetric centred everything**, where every block is centred because centring requires no decision.
- **fake data made to look like data**: skill meters, percentage bars, dot ratings, donut charts. A recruiter names these by themselves, and they are numbers with nothing behind them — which is also a rule-2 violation.

The test, and it is a single question per element: **does this element do work the reader can name?** A monogram identifies. A bar bounds a section. A tint groups items. A diagonal sets an axis — *if* a reader can say which axis; `avant-poster`'s could not, and it came off ([`families/avant-poster.md`](families/avant-poster.md)). Anything whose only job is to *look creative* comes off the page. Audacity is a small number of **decisions** — one monogram, one committed duotone, one strong composition — never an accumulation.

Two things deliberately absent from this list. There is **no anti-Canva**: template galleries are a legitimate source of expressive vocabulary (colour blocks, an integrated portrait, a monogram, a specialities line, categorised skill groupings, tinted fields), and the constructions there that fail are excluded by [`ats.md`](../ats.md) on measured technical grounds, not on taste. And there is no ban on *boldness*: the creative register exists precisely so that a bold page can be built and then be *proven* — the gate does not soften for it.

## Guided creation — the bespoke-family mode

A user may ask for something the roster does not have ("something like a letterpress broadside", "match this studio's identity", "nothing on your list"). That request is granted, not deflected — but it is composed, not improvised. The frame:

1. **The scripts' draw is a coherent STARTING POINT, not a cage.** Run `pick_design.py` anyway: it gives a validated palette, a vetted font pair, a gabarit, an order and a set of labels that already agree with each other. Deviating from it is allowed, with judgment and with the reason stated in the hand-off, as long as the result stays inside its family's grammar or becomes a coherent new one — and re-passes the gate.
2. **Compose the primitives, and know WHY each one exists.** Building on `lib.typ` is not a convenience: each primitive is a verified answer to a measured trap, and the *reason* is the part that transfers. `entry` exists because a date with no text after it in the emission order floats to the end of the extraction. `srow` exists because a grid extracts column-by-column and a per-item box becomes its own text cluster. `nb` exists because a mark orphaned at a line end separates from its value. `specline` refuses `tracking` because letterspacing extracts as `N E X T`. `chip` uses `highlight` and not `box(fill:)` because only one of the two keeps the row in a single cluster. An agent that knows the *why* can invent a new shape safely; one that knows only the *how* reintroduces the trap in a new costume.
3. **Anchor it in a real current, found by search — this is mandatory.** Name the tradition, its canonical practitioners, and its concrete device inventory (what is drawn, where, doing what job), the way every family recipe does. [`references/icons.md`](../icons.md) § Where the devices come from is the method, and it governs bespoke work more than it governs the roster: with no roster entry to lean on, an unanchored agent falls straight back onto the four obvious devices.
4. **Name your first idea, then do something else.** The first composition that comes to mind is, by construction, the one *any* agent would produce for this brief — that is what "reconverges on the template" means. Write it down explicitly, then build the second or third idea instead. This is the single most effective anti-generic move available, and it costs one sentence.
5. **Check it against both anti-references**, element by element, with the "does this do nameable work?" question.
6. **The full gate, and the bar of non-recognition.** Two font pairs, the family's own derived fill target, the separation floor *and* an obvious boundary to the eye, clean extraction, the rendered page looked at. A bespoke family gets no discount: it is held to more than the roster, not less, because nothing about it has been validated before.
7. **A success generalises.** A bespoke family that passes the gate, has three clone markers distinct from all fourteen, a font pool with no shared display face, a harmonised gamut, its own labels, gabarit, order and header composition, becomes a new `references/design/families/<id>.md` plus a `FAMILIES` entry in `scripts/pick_design.py` — and the roster is fifteen. That loop is how the roster got to fourteen, and it is the intended way for it to keep growing.
