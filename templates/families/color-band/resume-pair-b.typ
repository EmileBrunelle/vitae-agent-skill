// FAMILY: color-band — colored masthead band, reversed-out name
#let accent = rgb("#1f3a5f")    // hue A — the band + the heading bars
#let accent2 = rgb("#502d66")   // hue B — the dates + the list markers
// DUOTONE family (core.md § Duotone): the pair is validated together
// (far-analogous, +62°) — never mix hue A of one row with hue B of another.
// Coordinated palette: two accents + derived roles.
// soft = same hue lightened, for decorative hairlines only (never text).
// ink  = metadata gray biased 15% toward the accent hue (a pure neutral gray
//        next to a warm accent reads as a mismatch). dark = body ink, 8% biased.
#let soft = color.mix((accent, 40%), (white, 60%))
#let ink = color.mix((luma(95), 85%), (accent, 15%))
#let muted = ink
#let dark = color.mix((luma(25), 92%), (accent, 8%))
#let bodyf = ("Noto Sans", "Liberation Sans")
#let dispf = ("Red Hat Display", "Noto Sans", "Liberation Sans")

// ---------- Contact icons: vector only, no text emitted (verified in extraction) ----------
// Solid style: filled, angular — matches this family's heavy register.
#let ic-col = white
#let ic-pin = box(baseline: 1.4pt, width: 6pt, height: 7.4pt)[
  #place(top + center, circle(radius: 2.6pt, fill: ic-col))
  #place(bottom + center, polygon(fill: ic-col, (0pt, 0pt), (4pt, 0pt), (2pt, 3.4pt)))]
#let ic-tel = box(baseline: 1.4pt, width: 6pt, height: 7.4pt)[
  #place(horizon + center, rect(width: 4.6pt, height: 7.6pt, fill: ic-col))
  #place(bottom + center, dy: -1pt, rect(width: 2.4pt, height: 0.9pt, fill: accent))]
#let ic-mail = box(baseline: 1.4pt, width: 8pt, height: 7.4pt)[
  #place(horizon + center, rect(width: 8pt, height: 6pt, fill: ic-col))
  #place(horizon + center, dy: -1.2pt, polygon(stroke: 1pt + accent, (0pt, 0pt), (4pt, 2.8pt), (8pt, 0pt)))]
#let ic-web = box(baseline: 1.4pt, width: 7.6pt, height: 7.4pt)[
  #place(horizon + center, circle(radius: 3.7pt, fill: ic-col))
  #place(horizon + center, line(length: 7.4pt, stroke: 0.9pt + accent))
  #place(horizon + center, ellipse(width: 3.6pt, height: 7.4pt, stroke: 0.9pt + accent))]

// ---------- Platform marks (contact line) ----------
// Same mechanism as every other family: `marks()` from lib.typ, reading the
// `icons.typ` that scripts/harvest_icons.py generates beside it at build time
// (the path data is third-party artwork and is NOT vendored in this repo).
// Selective import: this file keeps its own chip devices.
// Each header contact goes through `contact`, a #box[…~…] so the mark can never
// be orphaned at a line end (`nb` is the untagged form, for Languages and skills) — and it drops the mark cleanly if the fetch
// failed, leaving the URL as plain text.
#import "../../lib.typ": marks, nb, contact, ghost, drawn-marker, list-marker, workday, wd-section, wd-page, entry as wd-entry, srow, masthead
// vertical rhythm: 1.000 as designed; a tuner stretches every pt gap through it
#let rhythm = 0.987
#let mk = marks(ic-col)
// the hand-drawn pin/phone follow the marks' all-or-nothing rule (no mixed row)
#let ic-on(g) = if mk.mail == none { ghost } else { g }

#set page(paper: "us-letter", margin: (x: 1.5cm, top: 1.2cm, bottom: 1.2cm))
#set page(..wd-page) if workday
// PDF/UA-1 needs a document title: the person's name. Fill it once here; the header below reuses it.
#let doc-name = "Firstname Lastname"
#set document(title: doc-name, author: doc-name)
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.569em, spacing: 0.611em)

// device: heading reversed out of a solid accent bar, no rules at all
#let section(t, body, airy: false) = block(breakable: false,
  above: if airy { 19pt * rhythm } else { 14pt * rhythm }, below: 0pt)[
  #block(width: 100%, fill: accent, inset: (x: 6pt, y: 2.5pt))[
    #text(font: dispf, size: 11.5pt, weight: "bold", fill: white)[#upper(t)]
  ]
  #v(8pt * rhythm)
  #block(above: 0pt, below: 0pt, width: 100%, body)
]

// lib.typ's `entry` sets the head (role, date, org line) — its measured
// in-head spacing is what keeps the org line grouped with its own role.
#let job(role, org, dates, note) = wd-entry(role, org, dates, note,
  date-st: it => text(size: 9pt, fill: accent2, weight: "bold", it),
  note-st: it => text(fill: muted, it), rhythm: rhythm)

// skills: label on its own line, items on the line below (two-line rows)
#let skill(cat, items) = srow(
  text(weight: "bold", size: 9.5pt)[#upper(cat)], items,
  brk: true, brk-gap: 2pt * rhythm, above: auto, below: 0pt)

#set list(marker: list-marker("dot", accent2, bold: true), indent: 10pt,
  spacing: 0.748em, body-indent: 6pt)

// header: full-width accent band (page 1 only) — lib.typ `masthead` grows with the text
#masthead(accent, rhythm: rhythm)[
  #text(font: dispf, size: 24pt, weight: "bold", fill: white)[#doc-name]
  #v(-4pt)
  #text(size: 10.5pt, fill: white, weight: "medium")[[Target title, as in the facts or posting] — [Degree, if the facts state it]]
  #v(0pt)
  #text(size: 9pt, fill: white)[
    #contact(ic-on(ic-pin))[\[City, Region\]]
    #h(6pt) #contact(ic-on(ic-tel))[#link("tel:+15555550100")[(555) 555-0100]]
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
#section("Profile")[
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
// NOTE (this family only): a bare 4-digit year in the date cell gets shuffled
// to the end of the pdftotext (non-layout) stream on this template's page —
// reproducible regardless of leading/spacing/sticky, tied to the isolated
// numeric-only run. A month+year token (as every job() entry above already
// uses) does not trigger it, so the date is written the same way here.
#section("Education")[
#job("[Credential, as printed]", "[Institution]", "[YYYY] – [YYYY]",
  "[City] · [one fact the facts give: course, mention or grade] · [second fact the facts give, if any]")
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
