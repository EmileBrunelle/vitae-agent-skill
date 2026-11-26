// FAMILY: bold-display — geometric display, heavy weight contrast
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, unbreakable
// mark+value box, platform marks, generic icon sets).
#import "../../lib.typ": *
// vertical rhythm: 1.000 as designed; a tuner stretches every pt gap through it
#let rhythm = 1.000
#let accent = rgb("#8c3b00")    // hue A — the name, and nothing else
#let accent2 = rgb("#105a90")   // hue B — heading underlines, markers, icons
// DUOTONE family (core.md § Duotone): the pair is validated together
// (complementary) — never mix hue A of one row with hue B of another.
// Coordinated palette: two accents + derived roles.
// soft = same hue lightened, for decorative hairlines only (never text).
// ink  = metadata gray biased 15% toward the accent hue (a pure neutral gray
//        next to a warm accent reads as a mismatch). dark = body ink, 8% biased.
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("Adwaita Sans", "Noto Sans", "Liberation Sans")
#let dispf = ("Space Grotesk", "Noto Sans", "Liberation Sans")

// Solid icon style: filled, angular — matches this family's heavy register.
#let ic-col = accent2
#let ic = icons-solid(ic-col)
#let mk = marks(ic-col)
#let ic = gate-icons(ic, mk)   // drawn icons follow marks' all-or-nothing

#set page(paper: "us-letter", margin: (x: 1.5cm, top: 1.2cm, bottom: 1.2cm))
#set page(..wd-page) if workday
// opt-in accent band (pick_design.py --band flips this): a text-free strip in the
// left margin, drawn in the page background (lib.typ accent-band)
#let band = false
#set page(background: accent-band(accent)) if band
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.590em, spacing: 0.670em)

// device: oversized dark title over a heavy accent underline as wide as the title
#let section(t, body, airy: false) = block(breakable: false,
  above: if airy { 21.5pt * rhythm } else { 16.5pt * rhythm }, below: 0pt)[
  #box(inset: (bottom: 3pt), stroke: (bottom: 2.5pt + accent2))[
    #text(font: dispf, size: 13pt, weight: "bold", fill: dark)[#upper(t)]
  ]
  #v(10.5pt * rhythm)
  #block(above: 0pt, below: 0pt, width: 100%, body)
]

#let job(role, org, dates, note) = entry(role, org, dates, note,
  date-st: it => text(size: 9pt, fill: muted, weight: "bold", it),
  note-st: it => text(fill: muted, it), rhythm: rhythm)

// skills: bold label, wide gap, items — no separator punctuation at all
#let skill(cat, items) = srow(box[#text(weight: "bold")[#cat]#h(12pt)], items)

#set list(marker: list-marker("square", accent2, bold: true), indent: 10pt,
  spacing: 0.760em, body-indent: 6pt)

// header: oversized accent name left, contacts on one line below
#block(above: 0pt, below: 12pt * rhythm)[
  #text(font: dispf, size: 29pt, weight: "bold", fill: accent)[Firstname Lastname]
  #v(-3pt * rhythm)
  #text(size: 11pt, weight: "medium")[[Target title, as in the facts or posting] — [Degree, if the facts state it]]
  #v(-3pt * rhythm)
  #text(size: 9pt, fill: muted)[
    #contact-rows(2)#contact(ic.pin)[\[City, Region\]] #h(9pt) #contact(ic.tel)[#link("tel:+15555550100")[(555) 555-0100]]
    #h(9pt) #contact(mk.mail)[#link("mailto:me@example.com")[me\@example.com]] \
    #contact(mk.li)[#link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]]
    #h(9pt) #contact(mk.gh)[#link("https://github.com/handle")[github.com/handle]]
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
#section("Education")[
#job("[Credential, as printed]", "[Institution]", "[YYYY] – [YYYY]",
  "[City] · [one real fact the facts give: course, mention or grade] · [second fact the facts give, if any]")
]

// ---------- Skills: a few rows, one per category the facts support, items as the facts word them (no gloss, no expansion); fewer rows when facts are thin ----------
#section("Technical Stack")[
#skill("[Category from the facts]", "[item], [item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item], [item], [item]")
]

// ---------- Languages: as the facts state them; "Bilingual" only if two are fluent/native ----------
#section("Languages")[
[Language] ([level as stated])\u{2002}#box[#drawn-marker("dot", accent2)\u{2002}[Language]] ([level as stated])
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
