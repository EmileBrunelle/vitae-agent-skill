// FAMILY: margin-index — classic marginalia (book typography, Bringhurst school)
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, unbreakable
// mark+value box, platform marks, generic icon sets).
#import "../../lib.typ": *
#let accent = rgb("#4a2f10")
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("STIX Two Text", "Libertinus Serif", "Noto Serif", "Liberation Serif")
#let dispf = bodyf

// this family carries no generic icons by principle — the
// platform marks are identifiers, not ornament (core.md).
#let ic-col = ink
#let mk = marks(ic-col)

#set page(paper: "us-letter", margin: (x: 1.5cm, top: 1.2cm, bottom: 1.2cm))
#set page(..wd-page) if workday
#set text(font: bodyf, size: 11pt, lang: "en", fill: dark, hyphenate: false,
  number-type: "old-style", number-width: "proportional")
#set par(justify: false, leading: 0.839em, spacing: 1.039em)

// device: NO rule, NO bar — the title hangs in the left margin column beside
// its own content. Single-ROW grid per section (safe: ats.md), title cell first
// so the extraction order stays heading → body.
#let section(t, body, airy: false) = block(breakable: false,
  above: if airy { 36pt } else { 31pt }, below: 0pt)[
  #if workday [
    // parse copy: title ABOVE the body, so the extraction order stays heading → body
    // (a margin column wraps the title and is read before the header contacts)
    #text(size: 10.5pt, weight: "bold", fill: accent)[#t]
    #v(3pt)
    #body
  ] else [
  #grid(columns: (2.5cm, 1fr), column-gutter: 12pt, align: (right + top, left + top),
    [#line(length: 100%, stroke: 1pt + accent)
     #v(3pt)
     #text(size: 10.5pt, weight: "bold", fill: accent)[#t]],
    body,
  )
  ]
]

// dates right-flush; the institution/descriptor line under the entry is what
// keeps the date anchored in the extraction (ats.md, orphaned-date trap)
#let job(role, org, dates, note) = entry(role, org, dates, note,
  date-st: it => text(size: 9pt, fill: muted, weight: "bold", it),
  note-st: it => text(fill: muted, it))

// skills: italic run-in label, no separator glyph at all — the italic/roman
// jump does the separating (nobody else uses italic as the skills device)
#let skill(cat, items) = srow(text(style: "italic")[#cat], items)

#set list(marker: drawn-marker("emdash", accent), indent: 9pt, spacing: 0.85em, body-indent: 6pt)

// header: name and role in the content column, contacts on one line under it;
// the margin column stays empty here (extraction keeps the name first)
#block(above: 0pt, below: 13pt)[
  #grid(columns: (2.5cm, 1fr), column-gutter: 12pt,
    [],
    [#text(font: dispf, size: 23pt, weight: "bold")[Firstname Lastname] \
     #v(-4pt)
     #text(size: 10.5pt, style: "italic")[[Target title, as in the facts or posting] — [Degree, if the facts state it]] \
     #v(-3pt)
     #text(size: 9pt, fill: muted)[#nb(mk.pin)[\[City, Region\]] #h(7pt) #nb(mk.phone)[#link("tel:+15555550100")[(555) 555-0100]]
       #h(7pt) #nb(mk.mail)[#link("mailto:me@example.com")[me\@example.com]] #h(7pt)
       #nb(mk.li)[#link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]] #h(7pt)
       #nb(mk.gh)[#link("https://github.com/handle")[github.com/handle]]]],
  )
]

// ---------- Profile ----------
// Workday mode (--input workday=1): drops Profile/Summary, tracks the section name.
#let section = wd-section(section)
// Profile: only what the facts state (role, field, level, outcome); length follows
// the facts; no trait sentence.

#section("Summary")[
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

// ---------- Education: linear one-line entry, NOT the grid job() shape ----------
// NOTE (this family, 2025-08 audit): the grid entry() orphaned this date to
// the end of the pdftotext extraction once the note was shortened to one
// line (core.md § Line integrity fix). Switched to `earlyline` (role,
// org+note, year all in one paragraph) per the known trap in ats.md — a
// bullet-less grid entry can orphan its date; the linear variant can't,
// since there is always text on both sides of the date in the same run.
#section("Education")[
#earlyline("[Credential, as printed]", "[Institution] — [City] · [fact, if any]", "[YYYY – YYYY, as stated]",
  year-st: it => text(size: 9pt, fill: muted, weight: "bold", it))
]

// ---------- Skills: a few rows, one per category the facts support, items as the facts word them (no gloss, no expansion); fewer rows when facts are thin ----------
#section("Expertise")[
#skill("[Category from the facts]", "[item], [item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item]")
]

// ---------- Languages: as the facts state them; "Bilingual" only if two are fluent/native ----------
#section("Languages")[
[Language] ([level as stated]) #h(8pt)#drawn-marker("dot", accent)#h(8pt) [Language] ([level as stated])
]
