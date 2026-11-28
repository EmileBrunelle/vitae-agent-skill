// FAMILY: color-band — colored masthead band, reversed-out name
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, unbreakable
// mark+value box, platform marks, generic icon sets).
#import "../../lib.typ": *
// vertical rhythm: 1.000 as designed; a tuner stretches every pt gap through it
#let rhythm = 0.990
#let accent = rgb("#1f3a5f")    // hue A — the band + the heading bars
#let accent2 = rgb("#502d66")   // hue B — the dates + the list markers
// DUOTONE family (core.md § Duotone): the pair is validated together
// (far-analogous, +62°) — never mix hue A of one row with hue B of another.
// Coordinated palette: two accents + derived roles.
// soft = same hue lightened, for decorative hairlines only (never text).
// ink  = metadata gray biased 15% toward the accent hue (a pure neutral gray
//        next to a warm accent reads as a mismatch). dark = body ink, 8% biased.
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("Red Hat Text", "Noto Sans", "Liberation Sans")
#let dispf = ("Red Hat Display", "Noto Sans", "Liberation Sans")

// Solid icon style: filled, angular — matches this family's heavy register.
// White, reversed out of the band; the knockout detail is cut in the band hue.
#let ic-col = white
#let ic = icons-solid(ic-col, bg: accent)
#let mk = marks(ic-col)
#let ic = gate-icons(ic, mk)   // drawn icons follow marks' all-or-nothing

#set page(paper: "us-letter", margin: (x: 1.5cm, top: 1.2cm, bottom: 1.2cm))
#set page(..wd-page) if workday
// PDF/UA-1 needs a document title: the person's name. Fill it once here; the header below reuses it.
#let doc-name = "Firstname Lastname"
#set document(title: doc-name, author: doc-name)
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.583em, spacing: 0.637em)

// device: heading reversed out of a solid accent bar, no rules at all
#let section(t, body, airy: false) = block(breakable: false,
  above: if airy { 19pt * rhythm } else { 14pt * rhythm }, below: 0pt)[
  #block(width: 100%, fill: accent, inset: (x: 6pt, y: 2.5pt))[
    #text(font: dispf, size: 11.5pt, weight: "bold", fill: white)[#upper(t)]
  ]
  #v(8.5pt * rhythm)
  #block(above: 0pt, below: 0pt, width: 100%, body)
]

#let job(role, org, dates, note, expected: false) = entry(role, org, dates, note, expected: expected,
  date-st: it => text(size: 9pt, fill: accent2, weight: "bold", it),
  note-st: it => text(fill: muted, it), rhythm: rhythm)

// skills: label on its own line, items on the line below (two-line rows)
#let skill(cat, items) = srow(
  text(weight: "bold", size: 9.5pt)[#upper(cat)], items,
  brk: true, brk-gap: 2pt * rhythm, above: auto, below: 0pt)

#set list(marker: list-marker("dot", accent2, bold: true), indent: 10pt,
  spacing: 0.760em, body-indent: 6pt)

// header: full-width accent band (page 1 only) — lib.typ `masthead` grows with the text
#masthead(accent, rhythm: rhythm)[
  #text(font: dispf, size: 24pt, weight: "bold", fill: white)[#doc-name]
  #v(-4pt)
  #text(size: 10.5pt, fill: white, weight: "medium")[[Target title, as in the facts or posting] — [Degree, if the facts state it]]
  #v(0pt)
  #text(size: 9pt, fill: white)[
    #contact(ic.pin)[\[City, Region\]]
    #h(6pt) #contact(ic.tel)[#link("tel:+15555550100")[(555) 555-0100]]
    #h(6pt) #contact(mk.mail)[#link("mailto:me@example.com")[me\@example.com]]
    #h(6pt) #contact(mk.web)[\[profile or portfolio — only if in the facts\]]
  ]
]

// ---------- Profile ----------
// Workday mode (--input workday=1): drops Profile/Summary, tracks the section name.
#let section = wd-section(section)
// Profile: only what the facts state (role, field, level, outcome); length follows
// the facts; no trait sentence.

// Tip: #box[*[term]*] keeps a fragile token unbroken.
#section("Profile", summary: true)[
[Role and field, as the facts state them.] [Strongest verifiable fact from the
facts, with its number if the facts give one.] [One sentence the facts support,
with the field's key terms in *bold*.]
]

// ---------- Experience in the target field FIRST ----------
// Roles and bullets: only as many as the facts give; drop a role or section the facts don't support.
#section("[Target-field] Experience")[

#job("[Role]", "[Employer]", "[Mon YYYY or YYYY, as stated] – [Mon YYYY or YYYY, as stated, or present]",
  "[City] · [descriptor, only if the facts or the employer's site say it] · [contract or mode, only if stated]")
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].

#job("[Role]", "[Employer]", "[Mon YYYY or YYYY, as stated] – [Mon YYYY or YYYY, as stated]",
  "[City] · [descriptor, only if stated] · [contract or mode, only if stated]")
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].

#job("[Role]", "[Employer]", "[Mon YYYY or YYYY, as stated] – [Mon YYYY or YYYY, as stated]",
  "[City] · [descriptor, only if stated] · [contract or mode, only if stated]")
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
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
]

// ---------- Education: the SAME entry shape as the jobs (dates right-flush) ----------
// The institution+descriptor line under the entry is what keeps the date from
// being orphaned at the end of the extraction (verified: ats.md date trap).
// NOTE (this family, this page only, re-measured 2025-08): this date orphans to
// the end of the pdftotext (non-layout) stream when the descriptor below is
// SHORT, and does not when it is long enough to run the full measure. Measured
// at the real meta size (9pt), across both margins:
//     1.5cm + long  -> no orphan      1.4cm + long  -> no orphan
//     1.5cm + short -> ORPHAN         1.4cm + short -> ORPHAN
// So the x margin is irrelevant to this trap and the descriptor LENGTH is the
// whole cause. An earlier revision widened the measure to x: 1.4cm to "make the
// long descriptor fit"; that both broke the ≥1.5cm margin invariant (core.md §
// Invariants) and misdiagnosed the bug — at 9pt the long descriptor fits on one
// line at 1.5cm with room to spare. Keep the margin at 1.5cm and keep this
// descriptor LONG. Do not shorten it to satisfy line integrity: it does not wrap.
// This trap is position-dependent per ats.md; re-verify per rendered page and
// don't assume the fix transfers (on resume-pair-b.typ a month+year date instead
// of a bare year range was what held).
#section("Education")[
#job("[Credential, as printed]", "[Institution]", "[YYYY] – [YYYY]",
  "[City] · [one real fact the facts give: course, mention or grade] · [second fact the facts give, if any]")
]

// ---------- Skills: a few rows, one per category the facts support, items as the facts word them (no gloss, no expansion); fewer rows when facts are thin ----------
#section("Skills & Tools")[
#skill("[Category from the facts]", "[item], [item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item], [item], [item]")
]

// ---------- Languages: as the facts state them; "Bilingual" only if two are fluent/native ----------
// Optional section: keep it only per the Languages rule in references/steps/4-draft.md, otherwise delete it.
#section("Languages")[
[Language] ([level as stated]) #h(8pt)#drawn-marker("dot", accent2)#h(8pt) [Language] ([level as stated])
]

// ---------- 2-page version recipe ----------
// 1. Under Profile, optionally a highlights block: linear lines (never a grid),
//    "– item" chips separated by #h(14pt), only items that repeat nothing.
// 2. Fuller bullets (as many as the facts give per role), languages with the
//    levels as stated.
// 3. Place a deliberate #pagebreak() at the section boundary that leaves
//    page 1 fullest (typically after Education); page assignment must be
//    deterministic, never left to auto-flow.
// 4. Balance unequal pages: #set text/#set par are document-global — re-set
//    them locally after the #pagebreak(), and/or use section(..., airy: true)
//    on the sparse page. Re-run the fill measurement on EVERY page.
