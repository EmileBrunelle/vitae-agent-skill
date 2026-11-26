// FAMILY: swiss-grid — International Typographic Style
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, unbreakable
// mark+value box, platform marks, generic icon sets).
#import "../../lib.typ": *
// vertical rhythm: 1.000 as designed; a tuner stretches every pt gap through it
#let rhythm = 1.000
#let accent = rgb("#b3261e")
// Coordinated palette (monochrome harmony): one accent + derived roles.
// soft = same hue lightened, for decorative hairlines only (never text).
// ink  = metadata gray biased 15% toward the accent hue (a pure neutral gray
//        next to a warm accent reads as a mismatch). dark = body ink, 8% biased.
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("Liberation Sans", "Noto Sans")
#let dispf = bodyf

// this family carries no generic icons by principle — the
// platform marks are identifiers, not ornament (core.md).
#let ic-col = dark
#let mk = marks(ic-col)

#set page(paper: "us-letter", margin: (x: 1.5cm, top: 1.2cm, bottom: 1.2cm))
#set page(..wd-page) if workday
// opt-in accent band (pick_design.py --band flips this): a text-free strip in the
// left margin, drawn in the page background (lib.typ accent-band)
#let band = false
#set page(background: accent-band(accent)) if band
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.520em, spacing: 0.580em)

// device: heavy accent rule ABOVE the title, full width; nothing below
#let section(t, body, airy: false) = block(breakable: false,
  above: if airy { 20pt * rhythm } else { 15pt * rhythm }, below: 0pt)[
  #line(length: 100%, stroke: 2.5pt + accent)
  #v(4pt * rhythm)
  #text(font: dispf, size: 12.5pt, weight: "bold", fill: dark)[#t]
  #v(11pt * rhythm)
  #block(above: 0pt, below: 0pt, width: 100%, body)
]

#let job(role, org, dates, note) = entry(role, org, dates, note,
  date-st: it => text(size: 9pt, fill: muted, weight: "bold", it),
  note-st: it => text(fill: muted, it), rhythm: rhythm)

// skills: small uppercase run-in label (no tracking), then the items
#let skill(cat, items) = srow(text(size: 8.5pt, weight: "bold")[#upper(cat)], items)

#set list(marker: list-marker("square", dark, bold: true), indent: 10pt,
  spacing: 0.690em, body-indent: 6pt)

// header: ONE grid row — name/role left, contact column right (photo slot = right cell)
#block(above: 0pt, below: 11pt * rhythm)[
  #grid(columns: (1fr, auto), column-gutter: 14pt, align: (left + bottom, right + bottom),
    [#text(font: dispf, size: 24pt, weight: "bold")[Firstname Lastname] \
     #v(-3pt)
     #text(size: 10.5pt, weight: "medium")[[Target title, as in the facts or posting] — [Degree, if the facts state it]]],
    text(size: 9pt, fill: muted)[#contact-rows(5)#contact(mk.pin)[\[City, Region\]] \
      #contact(mk.phone)[#link("tel:+15555550100")[(555) 555-0100]] \
      #contact(mk.mail)[#link("mailto:me@example.com")[me\@example.com]] \
      #contact(mk.li)[#link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]] \
      #contact(mk.gh)[#link("https://github.com/handle")[github.com/handle]]],
  )
]

// ---------- Profile ----------
// Workday mode (--input workday=1): drops Profile/Summary, tracks the section name.
#let section = wd-section(section)
// Profile: only what the facts state (role, field, level, outcome); length follows
// the facts; no trait sentence.

#section("Profile")[
[Role and field, as the facts state them.] [Strongest verifiable fact from the facts, with its number if the facts give one.] [One sentence the facts support, with the field's key terms in *bold*.]
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

#job("[Role]", "[Employer]", "[Mon YYYY or YYYY, as stated] – [Mon YYYY or YYYY, as stated]",
  "[City] · [descriptor, only if stated] · [contract or mode, only if stated]")
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
]

// ---------- Off-target roles: separated, honest, never leading ----------
// Roles and bullets: only as many as the facts give; drop a role or section the facts don't support.
#section("Other Experience")[
#job("[Role]", "[Employer]", "[Mon YYYY or YYYY, as stated] – [Mon YYYY or YYYY, as stated]",
  "[City] · [descriptor, only if stated] · [contract or mode, only if stated]")
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
]

// ---------- Education: the SAME entry shape as the jobs (dates right-flush) ----------
// The institution+descriptor line under the entry is what keeps the date from
// being orphaned at the end of the extraction (verified: ats.md date trap).
#section("Education")[
#job("[Credential, as printed]", "[Institution]", "[Mon YYYY or YYYY, as stated] – [Mon YYYY or YYYY, as stated]",
  "[City] · [one real fact the facts give: course, mention or grade — or ask] · [second fact the facts give, if any]")
]

// ---------- Skills: a few rows, one per category the facts support, items as the facts word them (no gloss, no expansion); fewer rows when facts are thin ----------
#section("Technical Skills")[
#skill("[Category from the facts]", "[item], [item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item]")
]

// ---------- Languages: as the facts state them; "Bilingual" only if two are fluent/native ----------
#section("Languages")[
[Language] ([level as stated]) #h(8pt)#drawn-marker("dot", accent)#h(8pt) [Language] ([level as stated])
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
