// FAMILY: humanist-quiet — Vignelli-style restraint, no rules anywhere
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, unbreakable
// mark+value box, platform marks, generic icon sets).
#import "../../lib.typ": *
// vertical rhythm: 1.000 as designed; a tuner stretches every pt gap through it
#let rhythm = 1.000
#let accent = rgb("#0e6862")
// Coordinated palette (monochrome harmony): one accent + derived roles.
// soft = same hue lightened, for decorative hairlines only (never text).
// ink  = metadata gray biased 15% toward the accent hue (a pure neutral gray
//        next to a warm accent reads as a mismatch). dark = body ink, 8% biased.
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("Noto Sans", "Liberation Sans")
#let dispf = ("Cantarell", "Noto Sans", "Liberation Sans")

// this family carries no generic icons by principle — the
// platform marks are identifiers, not ornament (core.md).
#let ic-col = accent
#let mk = marks(ic-col)

#set page(paper: "us-letter", margin: (x: 1.5cm, top: 1.2cm, bottom: 1.2cm))
#set page(..wd-page) if workday
// opt-in accent band (pick_design.py --band flips this): a text-free strip in the
// left margin, drawn in the page background (lib.typ accent-band)
#let band = false
#set page(background: accent-band(accent)) if band
// PDF/UA-1 needs a document title: the person's name. Fill it once here; the header below reuses it.
#let doc-name = "Firstname Lastname"
#set document(title: doc-name, author: doc-name)
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.560em, spacing: 0.655em)
#show link: set text(fill: accent)

// device: none — whitespace and a size/weight step do all the delimiting
#let section(t, body, airy: false) = block(breakable: false,
  above: if airy { 28pt * rhythm } else { 21pt * rhythm }, below: 0pt)[
  #text(font: dispf, size: 13pt, weight: "bold", fill: dark)[#t]
  #v(14pt * rhythm)
  #block(above: 0pt, below: 0pt, width: 100%, body)
]

#let job(role, org, dates, note) = entry(role, org, dates, note,
  date-st: it => text(size: 9pt, fill: muted, weight: "bold", it),
  note-st: it => text(fill: muted, it),
  above: 11pt, rhythm: rhythm)

// skills: bulleted rows, accent marker, em-dash label (hanging indent aligns wraps)
#let skill(cat, items) = srow([#drawn-marker("dash", accent, bold: true)#h(6pt)#text(weight: "semibold")[#cat] —], items, hang: 16pt)

#set list(marker: list-marker("dash", accent, bold: true), indent: 10pt,
  spacing: 0.765em, body-indent: 6pt)

// header: name + subtitle left, contacts on two left-aligned lines below
#block(above: 0pt, below: 12pt * rhythm)[
  // Header lines keep a tight pitch whatever the body leading: poppler splits a looser
  // contact row into one line per item or reads its second line before the first.
  #set par(leading: 0.451em, spacing: 0.546em)
  #text(font: dispf, size: 23pt, weight: "bold")[#doc-name]
  #v(-3pt)
  #text(size: 10.5pt)[[Target title, as in the facts or posting] — [Degree, if the facts state it]]
  #v(-4pt)
  #text(size: 9pt, fill: muted)[
    #contact-rows(2)#contact(mk.pin)[\[City, Region\]] #h(5pt)#drawn-marker("mid", auto)#h(5pt) #contact(mk.phone)[#link("tel:+15555550100")[(555) 555-0100]]
    #h(5pt)#drawn-marker("mid", auto)#h(5pt) #contact(mk.mail)[#link("mailto:me@example.com")[me\@example.com]] \
    #contact(mk.web)[\[profile or portfolio — only if in the facts\]]
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
- [Action verb] [what, from the facts][, outcome, if stated].
]

// ---------- Education: the SAME entry shape as the jobs (dates right-flush) ----------
// The institution+descriptor line under the entry is what keeps the date from
// being orphaned at the end of the extraction (verified: ats.md date trap).
#section("Education")[
#job("[Credential, as printed]", "[Institution]", "[YYYY] – [YYYY]",
  "[City] · [one real fact the facts give: course, mention or grade — or ask] · [second fact the facts give, if any]")
]

// ---------- Skills: a few rows, one per category the facts support, items as the facts word them (no gloss, no expansion); fewer rows when facts are thin ----------
#section("Skills")[
#skill("[Category from the facts]", "[item], [item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item]")
]

// ---------- Languages: as the facts state them; "Bilingual" only if two are fluent/native ----------
// Optional section: keep it only per the Languages rule in references/steps/4-draft.md, otherwise delete it.
#section("Languages")[
[Language] ([level as stated]) #h(8pt)#drawn-marker("dot", accent)#h(8pt) [Language] ([level as stated])
]

// ---------- 2-page version recipe ----------
// 1. Under Profile, optionally a highlights block: linear lines (never a grid),
//    "– item" chips separated by #h(14pt), only items that repeat nothing.
// 2. Fuller bullets (as many as the facts give per role), languages with
//    the levels as stated.
// 3. Place a deliberate #pagebreak() at the section boundary that leaves
//    page 1 fullest (typically after Education); page assignment must be
//    deterministic, never left to auto-flow.
// 4. Balance unequal pages: #set text/#set par are document-global — re-set
//    them locally after the #pagebreak(), and/or use section(..., airy: true)
//    on the sparse page. Re-run the fill measurement on EVERY page.
