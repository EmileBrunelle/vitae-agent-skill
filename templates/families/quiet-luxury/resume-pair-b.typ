// FAMILY: quiet-luxury — warm restrained minimalism (2020s "quiet luxury")
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, unbreakable
// mark+value box, platform marks, generic icon sets).
#import "../../lib.typ": *
// vertical rhythm: 1.000 as designed; a tuner stretches every pt gap through it
#let rhythm = 0.938
#let accent = rgb("#5c4632")
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("Noto Sans", "Liberation Sans")
#let dispf = ("Adwaita Sans", "Noto Sans", "Liberation Sans")

// ---------- Contact icons: vector only, no text emitted ----------
// Line style in the METADATA gray, not the accent: the accent is spent on
// organizations and the trailing rules, and nowhere else.
#let ic-col = ink
#let ic = icons-line(ic-col)
#let mk = marks(ic-col)
#let ic = gate-icons(ic, mk)   // drawn icons follow marks' all-or-nothing

#set page(paper: "us-letter", margin: (x: 1.6cm, top: 1.3cm, bottom: 1.2cm))
#set page(..wd-page-x(1.6cm)) if workday
// opt-in accent band (pick_design.py --band flips this): a text-free strip in the
// left margin, drawn in the page background (lib.typ accent-band)
#let band = false
#set page(background: accent-band(accent)) if band
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.536em, spacing: 0.597em)

// device: the title, then a SHORT hairline tick on its own baseline-centre —
// inline punctuation, not furniture. Never under the heading, never full width
// (a rule spanning the measure beside every title reads as word-processor
// furniture; measured and rejected).
#let section(t, body, airy: false) = block(breakable: false,
  above: if airy { 33pt * rhythm } else { 26pt * rhythm }, below: 0pt)[
  #text(font: dispf, size: 12.5pt, weight: "bold", fill: dark)[#t]
  #h(7pt)
  #box(baseline: -3pt, line(length: 34pt, stroke: 2pt + accent))
  #v(11pt * rhythm)
  #block(above: 0pt, below: 0pt, width: 100%, body)
]

// dates right-flush; the organization line under the entry anchors the date in
// the extraction (ats.md, orphaned-date trap). Organizations carry the accent.
#let job(role, org, dates, note) = entry(role, org, dates, note,
  date-st: it => text(size: 9pt, fill: muted, weight: "bold", it),
  org-st: it => text(weight: "semibold", fill: accent, it),
  note-st: it => text(fill: muted, it), rhythm: rhythm)

// skills: the label is set in the METADATA GRAY — colour, not weight or a
// glyph, does the separating. No colon, no dash, no bullet.
#let skill(cat, items) = srow(text(fill: ink, weight: "semibold")[#cat], items)

#set list(marker: list-marker("mid", dark), indent: 10pt, spacing: 0.774em, body-indent: 6pt)

// header: CONTACTS FIRST (a letterhead line), then the name, then the role —
// the reverse of every other family's header order.
#block(above: 0pt, below: 14pt * rhythm)[
  #text(size: 8.5pt, fill: muted)[
    #contact(ic.pin)[\[City, Region\]] #h(7pt) #contact(ic.tel)[#link("tel:+15555550100")[(555) 555-0100]]
    #h(7pt) #contact(mk.mail)[#link("mailto:me@example.com")[me\@example.com]] #h(7pt)
    #contact(mk.web)[\[profile or portfolio — only if in the facts\]]]
  #v(3pt * rhythm)
  #text(font: dispf, size: 22pt, weight: "bold")[Firstname Lastname]
  #v(-4pt)
  #text(size: 10.5pt, fill: ink)[[Target title, as in the facts or posting] — [Degree, if the facts state it]]
]

// ---------- Profile ----------
// Workday mode (--input workday=1): drops Profile/Summary, tracks the section name.
#let section = wd-section(section)
// Profile: only what the facts state (role, field, level, outcome); length follows
// the facts; no trait sentence.

#section("Professional Summary")[
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
]

// ---------- Education: same entry shape as the jobs (dates right-flush) ----------
#section("Education")[
#job("[Credential, as printed]", "[Institution]", "[Mon YYYY or YYYY, as stated] – [Mon YYYY or YYYY, as stated]",
  "[City] · [one real fact the facts give: course, mention or grade — or ask] · [second fact the facts give, if any], [third fact the facts give, if any]")
]

// ---------- Skills: a few rows, one per category the facts support, items as the facts word them (no gloss, no expansion); fewer rows when facts are thin ----------
#section("Skills & Tools")[
#skill("[Category from the facts]", "[item], [item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item]")
]

// ---------- Languages: as the facts state them; "Bilingual" only if two are fluent/native ----------
// Optional section: keep it only per the Languages rule in references/steps/4-draft.md, otherwise delete it.
#section("Languages")[
[Language] ([level as stated])\u{2002}#box[#drawn-marker("mid", ink)\u{2002}[Language]] ([level as stated])
]
