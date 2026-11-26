// FAMILY: hard-edge — neo-brutalist hard borders + monospace metadata
// REGISTER: creative (never in the default pool — core.md § The creative
// register: unlocked by a creative target field or an explicit request, capped
// back out by a conservative market).
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, painted chips,
// unbreakable mark+value box, platform marks, generic icon sets, specialities).
#import "../../lib.typ": *
#let accent = rgb("#b3261e")    // hue A — the monogram block + the specialities line
#let accent2 = rgb("#0f4c5c")   // hue B — the dates, the markers, the icons
// DUOTONE family (core.md § Duotone): the pair is validated together —
// never mix hue A of one row with hue B of another.
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("Public Sans", "Noto Sans", "Liberation Sans")
#let dispf = ("Familjen Grotesk", "Hanken Grotesk", "Noto Sans")
// THIRD font role, and it is this family's voice as much as the display face:
// every piece of METADATA — dates, employer descriptors, the specialities line,
// the contact line — is set in the monospace. That grotesque/monospace split is
// the neo-brutalist signature; without it the recipe is just a bordered box.
#let monof = ("Fira Mono", "DejaVu Sans Mono", "Noto Sans Mono")

// Solid icon style: filled, angular — nothing in this family is rounded.
#let ic-col = accent2
#let ic = icons-solid(ic-col)
#let mk = marks(ic-col)
#let ic = gate-icons(ic, mk)   // drawn icons follow marks' all-or-nothing

// GABARIT: dense — 1.6cm margins, a wide measure, 10.5pt body. Fill target
// derives from the 1.3cm bottom margin: (100 - 4.7) - 0..2%.
#set page(paper: "us-letter", margin: (x: 1.6cm, top: 1.3cm, bottom: 1.3cm))
#set page(..wd-page-x(1.6cm)) if workday
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.529em, spacing: 0.619em)

// DEVICE: the title KNOCKED OUT of a hard black slab, the slab only as wide as
// its own title — nothing full-width anywhere in the document. Square corners,
// no border, no shadow.
//
// This is the PRINT expression of the neo-brutalist current (extensive black
// for solid fields, oversized knockout type), deliberately not the web-UI
// dialect of it. The earlier version was a white bordered box with a 2.5pt
// flat offset block behind it — thick black border + zero-blur offset + a
// candy tint field is the "sticker card" vocabulary of the neubrutalism UI
// trend, and a reader recognized it as one specific brand's identity
// (§ Rules common to every family — the non-recognition bar covers brands too).
// Same current, different dialect, and the grotesque/monospace split still
// carries the family.
//
// Distinct from `color-band`, whose heading also reverses out: that one is a
// FULL-TEXT-WIDTH bar in the ACCENT; this is a shrink-to-title slab in the
// body ink. `box(fill:)` shrinks to its content, so no `measure()` is needed —
// but note the trap if a `rect` is ever reinstated here: `rect(width: 100%)`
// inside a box resolves to the AVAILABLE width and silently reproduces the
// banned full-width bar (same trap as `line(length: 100%)` — verified).
#let section(t, body, airy: false) = block(width: 100%, breakable: false,
  above: if airy { 26.5pt } else { 21.5pt }, below: 0pt)[
  #box(fill: dark, inset: (x: 6pt, y: 2.5pt),
    text(font: dispf, size: 11.5pt, weight: "bold", fill: white)[#upper(t)])
  #v(12.5pt)
  #block(above: 0pt, below: 0pt, width: 100%, body)
]

// Dates and the employer descriptor in the MONO face — the metadata register.
// The descriptor line under the entry is what keeps the date anchored in the
// extraction (ats.md, orphaned-date trap).
#let job(role, org, dates, note) = entry(role, org, dates, note,
  role-st: it => text(font: dispf, size: 11pt, weight: "bold", it),
  date-st: it => text(font: monof, size: 8.5pt, fill: accent2, weight: "medium", it),
  note-st: it => text(font: monof, size: 8pt, fill: muted, it),
  meta-size: 9pt)

// SKILLS: a REVERSED-OUT TAG, then the items plain. The tag is the section
// slab's own shape one scale down — the family repeats its own shapes instead
// of inventing a second language.
//
// The tag is a PAINTED chip (`highlight`), not a `box`, and that is mechanical,
// not stylistic. MEASURED on this very page shape (ats.md, lib.typ § chip): the
// label set in a bordered `box(stroke:)` tore the first two labels off their
// values and emitted them at the END of the section ("… [LABEL] [items] …
// [LABEL] [items] … / [LABEL]"). A box around the label is the same
// separate-text-cluster failure as a box around each item. `highlight` paints
// the field behind the same text run, so the row stays one text cluster and
// extracts byte-identically to a plain linear row.
//
// The ITEMS carry no tint. They used to be chips in a 22% tint of hue A; a
// row of tinted pills is the highlighter-field look of the neubrutalism UI
// trend, and together with the offset shadow it is what made the page
// recognizable as a specific brand. Black slab, plain items: the same current,
// read from print instead of from a component library.
// The tag hugs its label: `extent: 1pt`, and the gap to the first item is the
// paragraph's OWN word space. VERIFIED TRAP: an `h(4pt)` between the tag and
// the items — the obvious way to widen that gap — tore two labels
// off their values and emitted them at the end of the section, the
// same separate-text-cluster failure as a `box` around the label. Explicit
// spacing next to a `highlight` breaks the run; a plain word space does not.
#let stag(cat) = chip(
  text(font: monof, size: 8pt, weight: "bold", fill: white)[#upper(cat)],
  fill: dark, extent: 1pt)
#let skill(cat, items) = srow(stag(cat), items, above: auto, lift: 2pt, below: 0pt)
#let sskill(cat, items) = skill(cat, items)

// List marker: a hard-bordered SQUARE OUTLINE, drawn (emits no text). Nobody
// else uses an outlined marker — mono-technical's is filled.
#set list(marker: bullet-marked(box(width: 4pt, height: 4pt, baseline: -0.5pt,
    stroke: 1pt + accent2)), indent: 10pt, spacing: 0.732em, body-indent: 7pt)

// HEADER: MONOGRAM + TWO ZONES. A hard-bordered square holds the initials
// reversed out of hue A, the name sits beside it, then the specialities line
// and a single monospace contact line. The monogram is real TEXT inside a drawn
// box — never an image: harvested counter-evidence says an image-rendered
// monogram is invisible to extraction, and the initials are then a hole in the
// document where the name should be.
#block(above: 0pt, below: 12pt)[
  #hrow(
    [#box(baseline: 12pt, width: 1.15cm, height: 1.15cm, fill: accent,
       stroke: 1.4pt + dark, inset: 0pt)[
       #align(center + horizon, text(font: dispf, size: 17pt, weight: "bold",
         fill: white)[FL])]
     #h(9pt)
     #box(baseline: 12pt)[
       #text(font: dispf, size: 25pt, weight: "bold")[Firstname Lastname] \
       #v(-5pt)
       #text(font: monof, size: 9pt, fill: muted)[[Target title, as in the facts or posting] — [Degree, if the facts state it]]]],
    [], cols: (auto, 1fr), gutter: 0pt,
    align-cells: (left + top, left + top), above: 0pt, below: 5pt)
  // SPECIALITIES LINE — the mastered skills, in hue A, mono, uppercase,
  // pipe-separated. NO `tracking`: letterspacing extracts as "N E X T" and
  // stops matching. Each item boxed, so none can break across a line end.
  // Every item is CONTENT: SKILL.md rule 2 applies to it in the most prominent
  // position on the page — a specialities line is not a decoration strip.
  #text(font: monof, size: 8.5pt, weight: "bold", fill: accent)[#specline(
    ("[ITEM]", "[ITEM]", "[ITEM]", "[ITEM]", "[ITEM]", "[ITEM]", "[ITEM]"),
    sep: [ | ])]
  #v(2pt)
  #text(font: monof, size: 8.5pt, fill: muted)[
    #contact(ic.pin)[\[City, Region\]] #h(7pt)
    #contact(ic.tel)[#link("tel:+15555550100")[(555) 555-0100]] #h(7pt)
    #contact(mk.mail)[#link("mailto:me@example.com")[me\@example.com]] #h(7pt)
    #contact(mk.li)[#link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]] #h(7pt)
    #contact(mk.gh)[#link("https://github.com/handle")[github.com/handle]]]
]

// SECTION ORDER (this family's default): SKILLS SECOND, straight after the
// profile — the hybrid order a technical/creative audience reads first, with
// the full reverse-chronological history below it. A target market's own
// convention wins over this default (references/regional.md).

// ---------- Profile ----------
// Workday mode (--input workday=1): drops Profile/Summary, tracks the section name.
#let section = wd-section(section)
// Profile: only what the facts state (role, field, level, outcome); length follows
// the facts; no trait sentence.

// Tip: #box[*[term]*] keeps a fragile token unbroken.
#section("Profile")[
[Role and field, as the facts state them.] [Strongest verifiable fact from the
facts, with its number if the facts give one.] [One sentence the facts support,
with the field's key terms in *bold*.]
]

// ---------- Skills: a few rows, one per category the facts support, items as the facts word them (no gloss, no expansion); fewer rows when facts are thin ----------
#section("Technical Stack")[
#skill("[Category from the facts]", "[item], [item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item]")
]

// ---------- Experience in the target field FIRST ----------
// Roles and bullets: only as many as the facts give; drop a role or section the facts don't support.
// Present tense for a current role; the verb the facts support, not a bigger one.
#section("[Target-field] Experience")[

#job("[Role]", "[Employer]", "[Mon YYYY or YYYY, as stated] – [Mon YYYY or YYYY, as stated, or present]",
  "[City] · [descriptor, only if the facts or the employer's site say it] · [contract or mode, only if stated]")
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].

#job("[Role]", "[Employer]", "[Mon YYYY or YYYY, as stated] – [Mon YYYY or YYYY, as stated]",
  "[City] · [descriptor, only if stated] · [contract or mode, only if stated]")
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].

#job("[Role]", "[Employer]", "[Mon YYYY or YYYY, as stated] – [Mon YYYY or YYYY, as stated]",
  "[City] · [descriptor, only if stated] · [contract or mode, only if stated]")
- [Action verb] [what, from the facts][, outcome, if stated].
]

// ---------- Off-target roles: separated, honest, never leading ----------
// Roles and bullets: only as many as the facts give; drop a role or section the facts don't support.
#section("Other Experience")[
#job("[Role]", "[Employer]", "[Mon YYYY or YYYY, as stated] – [Mon YYYY or YYYY, as stated]",
  "[City] · [descriptor, only if stated] · [contract or mode, only if stated]")
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
]

// ---------- Education: the SAME entry shape as the jobs (dates right-flush) ----------
#section("Education")[
#job("[Credential, as printed]", "[Institution]", "[YYYY] – [YYYY]",
  "[City] · [one real fact the facts give: course, mention or grade — or ask] · [second fact the facts give, if any]")
]

// ---------- Languages: as the facts state them; "Bilingual" only if two are fluent/native ----------
#section("Languages")[
[Language] ([level as stated])\u{2002}#box[#text(fill: accent2)[|]\u{2002}[Language]] ([level as stated])
]
