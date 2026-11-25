// FAMILY: mono-technical — technical-documentation / spec-sheet aesthetic
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, unbreakable
// mark+value box, platform marks, generic icon sets).
#import "../../lib.typ": *
// DUOTONE family: two harmonised hues, each with its own job.
#let accent = rgb("#1f3a5f")    // hue A — STRUCTURE: heading marks, chip keylines
#let accent2 = rgb("#8f2d3f")   // hue B — DATA: dates, list markers, icons
#let pal = derive(accent)
#let soft = pal.soft
#let wash = color.mix((accent, 8%), (white, 92%))
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
// pool pair 1 of 2 verified at the gate: local faces first so the compile is
// warning-free (`typst fonts` check, references/design/core.md § font pools)
#let bodyf = ("Noto Sans", "Liberation Sans")
#let monof = ("Adwaita Mono", "Noto Sans Mono")
#let dispf = monof

// ---------- Contact icons: vector only, no text emitted ----------
// Line style in hue B — the data hue, the same one that carries the dates.
#let ic-col = accent2
#let ic = icons-line(ic-col)
#let mk = marks(ic-col)
#let ic = gate-icons(ic, mk)   // drawn icons follow marks' all-or-nothing

#set page(paper: "us-letter", margin: (x: 1.6cm, top: 1.25cm, bottom: 1.2cm))
#set page(..wd-page-x(1.6cm)) if workday
// opt-in accent band (pick_design.py --band flips this): a text-free strip in the
// left margin, drawn in the page background (lib.typ accent-band)
#let band = false
#set page(background: accent-band(accent)) if band
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.545em, spacing: 0.665em)

// device: a filled hue-A square, then the title in the MONO face. No rules.
#let section(t, body, airy: false) = block(breakable: false,
  above: if airy { 27pt } else { 22pt }, below: 0pt)[
  #box(width: 6pt, height: 6pt, fill: accent, baseline: 0pt)
  #box(width: 3pt, height: 6pt, fill: accent2, baseline: 0pt)
  #h(5pt)
  #text(font: dispf, size: 11.5pt, weight: "bold", fill: dark)[#t]
  #v(14pt)
  #block(above: 0pt, below: 0pt, width: 100%, body)
]

// dates in the MONO face, hue B, right-flush (tabular alignment is this
// family's signature); the organization line under the entry anchors the date
// in the extraction (ats.md, orphaned-date trap).
#let job(role, org, dates, note) = entry(role, org, dates, note,
  date-st: it => text(font: dispf, size: 8.5pt, fill: accent2, weight: "medium", it),
  note-st: it => text(fill: muted, it))

// skills: a spec-sheet KEY = VALUE row — mono key in hue A, the "=" in hue B,
// values in the body sans. Verified alternative to inline "chips": one box per
// item SCATTERS in pdftotext (each box becomes its own text cluster and the
// items interleave across rows) — see references/ats.md.
#let skill(cat, items) = srow([#text(font: dispf, size: 8.5pt, weight: "bold", fill: accent)[#upper(cat)] #text(font: dispf, size: 8.5pt, fill: accent2)[=]], items)

#set list(marker: box(width: 3pt, height: 3pt, fill: accent2, baseline: -0.5pt),
  indent: 10pt, spacing: 0.45em, body-indent: 7pt)

// header: name, role, then the contacts on ONE mono line (spec-sheet footer)
#block(above: 0pt, below: 12pt)[
  #text(size: 22pt, weight: "bold")[Firstname Lastname]
  #v(-4pt)
  #text(size: 10.5pt, weight: "medium")[[Target title, as in the facts or posting] — [Degree, if the facts state it]]
  #v(-2pt)
  #text(font: dispf, size: 8.5pt, fill: muted)[
    #nb(ic.pin)[\[City, Region\]] #h(6pt) #nb(ic.tel)[#link("tel:+15555550100")[(555) 555-0100]]
    #h(6pt) #nb(mk.mail)[#link("mailto:me@example.com")[me\@example.com]] #h(6pt)
    #nb(mk.li)[#link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]] #h(6pt)
    #nb(mk.gh)[#link("https://github.com/handle")[github.com/handle]]]
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

// ---------- Education: same entry shape as the jobs (dates right-flush) ----------
#section("Education")[
#job("[Credential, as printed]", "[Institution]", "[Mon YYYY or YYYY, as stated] – [Mon YYYY or YYYY, as stated]",
  "[City] · [one real fact the facts give: course, mention or grade — or ask] · [second fact the facts give, if any], [third fact the facts give, if any]")
]

// ---------- Skills: a few rows, one per category the facts support, items as the facts word them (no gloss, no expansion); fewer rows when facts are thin ----------
#section("Technical Stack")[
#skill("[Category from the facts]", "[item], [item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item]")
]

// ---------- Languages: as the facts state them; "Bilingual" only if two are fluent/native ----------
#section("Languages")[
[Language] ([level as stated])\u{2002}#box[#drawn-marker("mid", accent2)\u{2002}[Language]] ([level as stated])
]
