// FAMILY: swiss-grid — International Typographic Style — TWO-PAGE version
// ---------------------------------------------------------------------------
// This is the worked 2-page counterpart of resume.typ in this directory, built
// by following that file's own "2-page version recipe" comment block to the
// letter. It exists because "1-page and 2-page versions" is half of what this
// skill claims to do, and a claim nothing exercises is a claim nobody checked.
//
// Gate (both pages measured, from this directory):
//     python3 ../../../scripts/verify.py resume-2page.typ 2 94 96
//
// What makes this two pages rather than one is CONTENT, not air: a third
// on-target role, more bullets per role, a highlights block under the Profile,
// and sections a 1-page version has to drop (Selected Projects, Certifications).
// The anti-filler clause (SKILL.md rule 5) is the whole point — if the material
// for this does not exist, the honest deliverable is the 1-page version, not
// this one padded. Page 2 is never filled by opening the leading: a page whose
// rhythm is visibly double its neighbour's is the air rule 5 forbids. Rows that
// wrap are shortened (line integrity is a VISUAL check the gate cannot see,
// references/steps/6-verify.md) and the fill bought back with real content.
// ---------- Shared mechanics (templates/lib.typ) ----------
#import "../../lib.typ": *
// vertical rhythm: 1.000 as designed; a tuner stretches every pt gap through it
#let rhythm = 1.000
#let accent = rgb("#b3261e")
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("Nimbus Sans", "Liberation Sans", "Noto Sans")
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
#set par(justify: false, leading: 0.508em, spacing: 0.568em)

// device: heavy accent rule ABOVE the title, full width; nothing below
#let section(t, body, airy: false) = block(breakable: false,
  above: if airy { 20pt * rhythm } else { 15pt * rhythm }, below: 0pt)[
  #line(length: 100%, stroke: 2.5pt + accent)
  #v(4pt * rhythm)
  #text(font: dispf, size: 12.5pt, weight: "bold", fill: dark)[#t]
  #v(12pt * rhythm)
  #block(above: 0pt, below: 0pt, width: 100%, body)
]

#let job(role, org, dates, note) = entry(role, org, dates, note,
  date-st: it => text(size: 9pt, fill: muted, weight: "bold", it),
  note-st: it => text(fill: muted, it), rhythm: rhythm)

// skills: small uppercase run-in label (no tracking), then the items
#let skill(cat, items) = srow(text(size: 8.5pt, weight: "bold")[#upper(cat)], items)

#set list(marker: list-marker("square", dark, bold: true), indent: 10pt,
  spacing: 0.678em, body-indent: 6pt)

// header: name row, then a grid row — role left, 2-line contact block right (column = natural width, max 55%); contact never shares a y-range with the name. No photo is wired: a photo would take the right end of the name row
#block(above: 0pt, below: 11pt * rhythm)[
  #header-two-row(
    [#text(font: dispf, size: 24pt, weight: "bold")[Firstname Lastname]],
    [#text(size: 10.5pt, weight: "medium")[[Target title, as in the facts or posting] — [Degree, if the facts state it]]],
    text(size: 9pt, fill: muted)[#contact-rows(2)#contact(mk.pin)[\[City, Region\]] #h(10pt) #contact(mk.phone)[#link("tel:+15555550100")[(555) 555-0100]] #h(10pt) #contact(mk.mail)[#link("mailto:me@example.com")[me\@example.com]] \
      #contact(mk.web)[\[profile or portfolio — only if in the facts\]]],
    row-gutter: 10pt * rhythm,
  )
]

// ---------- Profile ----------
// Workday mode (--input workday=1): drops Profile/Summary, tracks the section name.
#let section = wd-section(section)
// Profile: only what the facts state (role, field, level, outcome); length follows
// the facts; no trait sentence.

#section("Profile")[
[Role and field, as the facts state them.] [Strongest verifiable fact from the facts, with its number if the facts give one.] [One sentence the facts support, with the field's key terms in *bold*.]

// recipe step 1: the highlights block — 2 LINEAR lines, never a grid (a grid
// extracts column-first and scrambles the reading order: ats.md).
#v(3pt * rhythm)
#text(size: 9.5pt)[
  – [Claim from the facts that a bullet below proves] #h(14pt) – [Second claim from the facts] \
  – [Third claim from the facts] #h(14pt) – [Fourth claim from the facts]
]
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
- [Action verb] [what, from the facts][, outcome, if stated].

#job("[Role]", "[Employer]", "[Mon YYYY or YYYY, as stated] – [Mon YYYY or YYYY, as stated]",
  "[City] · [descriptor, only if stated] · [contract or mode, only if stated]")
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

// ---------------------------------------------------------------------------
// recipe step 3: the page break is DELIBERATE and sits at the section boundary
// that leaves page 1 fullest (here after the off-target run). Never left to auto-flow: auto-flow picks a
// different boundary the moment a single bullet changes length, and then the
// page assignment is not reproducible. It also has to leave page 2 a real
// page's worth of content, bought with real material, not air.
#if not workday { pagebreak() }  // workday parse copy: one page (the last line of each page is dropped)

// The running head goes in the FLOW, right after the break — never in a page
// `header:` field, which many parsers skip entirely (lib.typ § runhead).
#if not workday { runhead(rhythm: rhythm)[Firstname Lastname — [Target title]][2][2] }  // no page 2 in the parse copy

// recipe step 4: #set text / #set par are document-GLOBAL, so page 2 is
// re-balanced locally here rather than by loosening the whole document. Page 2
// keeps a rhythm close to page 1's (never double it); the `airy` section spacing
// and short real bullets bring it to the target. Both pages are measured, and
// NOTE for the tuner: `verify.py --tune` edits only the FIRST par declaration
// and measures only the LAST page, so a two-declaration file like this one is
// balanced by hand — tune page 1 with the 1-page file, then set the second
// declaration here until page 2 lands in the same target.
#set par(justify: false, leading: 0.527em, spacing: 0.607em)
// the item gap follows page 2's leading (leading + 0.16em), so page 2 keeps wrapped line < bullet < entry
#set list(spacing: 0.697em)

// ---------- Education: the SAME entry shape as the jobs (dates right-flush) ----------
// The institution+descriptor line under the entry is what keeps the date from
// being orphaned at the end of the extraction (verified: ats.md date trap).
// The bullet under the entry is load-bearing for the SAME reason: a bullet-less
// grid entry at a page boundary re-orders its date to the end of the page's
// extraction stream (verify.py catches exactly this).
#section("Education", airy: true)[
#job("[Credential, as printed]", "[Institution]", "[Mon YYYY or YYYY, as stated] – [Mon YYYY or YYYY, as stated]",
  "[City] · [one real fact the facts give: course, mention or grade — or ask]")
- [Course or mention from the facts, only where it anchors a skill claimed above.]
- [Further course or mention from the facts.]
]

// ---------- Selected Projects: only if the facts give named work ----------
// The honest reason a CV goes to two pages is named, verifiable work that does
// not fit on one. It uses the SAME entry helper as the jobs, so the date lands
// in the same place and the extraction order stays identical (references/steps/6-verify.md).
// Delete the section when the facts name no project.
// Roles and bullets: only as many as the facts give; drop a role or section the facts don't support.
#section("Selected Projects", airy: true)[
#job("[Project name, as the facts give it]", "[Kind of project, as stated]", "[YYYY, as stated]",
  "[What it does in one clause, from the facts] · [link, if given]")
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].

#job("[Project name, as the facts give it]", "[Kind of project, as stated]", "[YYYY, as stated]",
  "[What it does in one clause, from the facts]")
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].

#job("[Project name, as the facts give it]", "[Kind of project, as stated]", "[YYYY, as stated]",
  "[What it does in one clause, from the facts]")
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
- [Action verb] [what, from the facts][, outcome, if stated].
]

// ---------- Skills: a few rows, one per category the facts support, items as the facts word them (no gloss, no expansion); fewer rows when facts are thin ----------
#section("Technical Skills", airy: true)[
#skill("[Category from the facts]", "[item], [item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item]")
]

// ---------- Certifications & professional development: only if the facts give them ----------
// Dated like everything else, and only where the certificate is real and
// current. Delete the section when the facts give none.
#section("Certifications & Professional Development", airy: true)[
#skill("[Category from the facts]", "[Issuing body] — [what, as printed], [year, as stated]")
#skill("[Category from the facts]", "[Item from the facts], [year, as stated]")
#skill("[Category from the facts]", "[Item from the facts], [year, as stated]")
]

// ---------- Languages: as the facts state them; "Bilingual" only if two are fluent/native ----------
// Optional section: keep it only per the Languages rule in references/steps/4-draft.md, otherwise delete it.
#section("Languages", airy: true)[
[Language] ([level as stated]) #h(8pt)#drawn-marker("dot", accent)#h(8pt) [Language] ([level as stated])
]
