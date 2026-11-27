// FAMILY: clause-index — numbered-clause technical-standard document
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, unbreakable
// mark+value box, platform marks, generic icon sets, specialities line).
#import "../../lib.typ": *
// vertical rhythm: 1.000 as designed; a tuner stretches every pt gap through it
#let rhythm = 0.928
#let accent = rgb("#1d4ed8")    // cobalt — the clause numbers and the section hairline, nothing else
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("Public Sans", "PT Sans", "Noto Sans")
#let dispf = ("Schibsted Grotesk", "PT Sans", "Noto Sans")

// Line icons in the METADATA GRAY, never the accent: this family's accent has
// exactly one job (the numbers and the section hairline), so a coloured pin would be a third job.
#let ic-col = ink
#let ic = icons-line(ic-col)
#let mk = marks(ic-col)
#let ic = gate-icons(ic, mk)   // drawn icons follow marks' all-or-nothing

// GABARIT: dense, the specification-document register — 1.5cm margins, the
// widest measure of the roster, 10.5pt body, tight rhythm. Fill target derives
// from the 1.2cm bottom margin: (100 - 4.3) - 0..2%.
#set page(paper: "us-letter", margin: (x: 1.5cm, top: 1.2cm, bottom: 1.2cm))
#set page(..wd-page) if workday
// opt-in accent band (pick_design.py --band flips this): a text-free strip in the
// left margin, drawn in the page background (lib.typ accent-band)
#let band = false
// section-rule: how a section heading is underlined (vector line, no text):
//   "inline"      hairline fills the rest of the heading row (default)
//   "under"       full-width hairline under the heading
//   "under-short" bar under the number and title only
//   "none"        no rule (the original sober look)
// Total space under the heading is equal for all four values (measured, to 0.1pt).
#let section-rule = "inline"
#let section-rules = ("inline", "under", "under-short", "none")
#assert(section-rule in section-rules, message: "section-rule must be one of: " + section-rules.join(", ") + " (got " + repr(section-rule) + ")")
#set page(background: accent-band(accent)) if band
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.550em, spacing: 0.584em)

// DEVICE: an OUTDENTED CLAUSE NUMBER. The numbering-of-divisions convention of
// technical standards (ISO 2145, DIN 1421): the division number hangs in a
// fixed 20pt gutter, the title sits flush at the text edge, and the only
// ornament is one thin accent hairline (section-rule below), no bar, no fill,
// no panel. Nobody else numbers its sections.
//
// The number NEVER replaces the conventional heading stem — harvested
// counter-evidence: an ordinal used AS the label ("01" alone) costs the reader
// speed and costs the ATS its section classifier. "1 Experience" keeps both.
//
// Single-ROW grid, number cell first, so extraction stays number -> title ->
// body (verified: "1 Summary", "2 Skills & Tools" …).
#let clause = counter("clause")
#let sub = counter("sub")     // sub-clause index, reset by every section
#let section(t, body, airy: false) = block(width: 100%, breakable: false,
  above: if airy { 27pt * rhythm } else { 22pt * rhythm }, below: 0pt)[
  #clause.step()
  #sub.update(1)   // display() reads the value BEFORE this row’s step, so 1-based
  #let num = text(size: 12.5pt, weight: "bold", fill: accent, number-type: "lining",
    number-width: "tabular")[#context clause.display()]
  #let ttl = text(font: dispf, size: 12.5pt, weight: "bold", fill: dark)[#t]
  #if section-rule == "inline" [
    #grid(columns: (20pt, auto, 1fr), column-gutter: 0pt, align: (left + bottom, left + bottom, left + horizon),
      num, ttl, pad(left: 8pt, move(dy: 0.7pt, line(length: 100%, stroke: 1pt + accent))))
    #v(12pt * rhythm)
  ] else if section-rule == "under" [
    #grid(columns: (20pt, 1fr), column-gutter: 0pt, align: (left + bottom, left + bottom), num, ttl)
    #v(3pt * rhythm)
    #block(above: 0pt, below: 0pt)[#line(length: 100%, stroke: 1pt + accent)]
    #v(9pt * rhythm)
  ] else if section-rule == "under-short" [
    #box(stroke: (bottom: 1.5pt + accent), inset: (bottom: 3pt, right: 6pt))[#grid(columns: (20pt, auto), column-gutter: 0pt, align: (left + bottom, left + bottom), num, ttl)]
    #v(8.75pt * rhythm)
  ] else [
    #grid(columns: (20pt, 1fr), column-gutter: 0pt, align: (left + bottom, left + bottom), num, ttl)
    #v(12pt * rhythm)
  ]
  #block(above: 0pt, below: 0pt, width: 100%, body)
]

// dates right-flush, tabular figures (a standard document aligns its numerals);
// the institution/descriptor line under the entry anchors the date in the
// extraction (ats.md, orphaned-date trap)
#let job(role, org, dates, note) = entry(role, org, dates, note,
  date-st: it => text(size: 9pt, fill: muted, weight: "bold",
    number-width: "tabular", it),
  note-st: it => text(fill: muted, it), rhythm: rhythm)

// skills: a SUB-CLAUSE number. The row carries the section's own clause number
// with a sub-index ("2.1", "2.2" …) in the accent, then the label in bold, then
// the items. Nobody else numbers its skills rows, and the numbering is the same
// device as the section boundary rather than a second invention.
#let skill(cat, items) = srow(
  [#text(size: 8.5pt, weight: "bold", fill: accent, number-width: "tabular")[#context {
      sub.step(); clause.display(); [.]; sub.display() }]
   #text(weight: "bold")[#cat]], items)

#set list(marker: list-marker("dash", accent, bold: true), indent: 10pt,
  spacing: 0.679em, body-indent: 6pt)

// HEADER: NAME ROW, then title | contact. The name sits on its own row (header-two-row: the contact block never
// shares a y-band with it; OCR, y-sorting and grid extractors merge lines that do). The right cell is the contact
// block (2 lines, natural width, max 55% of the measure; also the photo slot). The left cell holds the role line, a
// REFERENCE ROW of small label/value pairs — the Bezugszeichenzeile of the German business-letter standard
// (DIN 676), where this family's header composition comes from — and the SPECIALITIES LINE: the one neutral family
// that carries one (core.md § Specialities line), set in the label register so it reads as a data row and not as
// a slogan. The reference row is sized to fit the left cell on one line beside the contact block.
#block(above: 0pt, below: 10pt * rhythm)[
  #let rcell(l, val) = [#text(size: 7pt, weight: "bold", fill: ink)[#upper(l)] #val]
  #header-two-row(
    [#text(font: dispf, size: 22pt, weight: "bold")[Firstname Lastname]],
    [#text(size: 10.5pt, weight: "medium")[[Target title, as in the facts or posting] — [Degree, if the facts state it]]
  #v(2pt * rhythm)
  // REFERENCE ROW — one flowing paragraph, never a grid of stacked cells.
  // MEASURED TRAPS: the left cell is the only place for these rows. Full width below the contact block, poppler
  // emitted LOCATION, AVAILABILITY, the whole contact block, then AUTHORIZATION (its right end shares an x-range
  // with the contact column), and beside a 4-line contact column MuPDF glued the last contact line to the
  // specialities line. As a single-ROW grid whose three cells each stacked
  // a label over its value, poppler emitted all three LABELS first and all
  // three VALUES after them, destroying the label↔value pairing the device
  // exists for. A single-ROW grid is safe when each cell is ONE line; the
  // moment a cell stacks two, the reader sweeps the row before it descends.
  #text(size: 8.5pt)[#rcell("Location", [\[City, Region\]]) #h(5pt)
    #rcell("Availability", [\[Two weeks’ notice\]]) #h(5pt)
    #rcell("Authorization", [\[Authorized to work\]])]
  #v(2pt * rhythm)
  // SPECIALITIES LINE: the skills the facts support, linear, NO letterspacing
  // (it extracts as "N E X T" and stops matching), each item boxed so it can
  // never break across a line end. Every item is CONTENT: SKILL.md rule 2
  // applies to it, in the most prominent position on the page.
  #text(size: 8.5pt, weight: "bold", fill: accent)[#specline(
    ("[SKILL]", "[SKILL]", "[SKILL]", "[SKILL]", "[SKILL]"),
    sep: [ · ])]],
    text(size: 9.5pt, fill: muted)[
      #contact-rows(2)#contact(ic.mail)[#link("mailto:me@example.com")[me\@example.com]] #h(8pt) #contact(ic.tel)[#link("tel:+15555550100")[(555) 555-0100]] \
      #contact(mk.web)[\[profile or portfolio — only if in the facts\]]],
    row-gutter: 3pt * rhythm, gutter: 10pt,
  )
]

// SECTION ORDER (this family's default): the hybrid/combination skeleton —
// SKILLS COME SECOND, straight after the summary and before the experience
// sections, with the full reverse-chronological history below. Sourced: the
// skills-forward order that recruiters accept is the hybrid format (summary +
// skills up top, then chronology), never a functional CV that replaces the
// chronology. A target market's own convention wins over this default
// (references/regional.md).

// ---------- Profile ----------
// Workday mode (--input workday=1): drops Profile/Summary, tracks the section name.
#let section = wd-section(section)
// Profile: only what the facts state (role, field, level, outcome); length follows
// the facts; no trait sentence.

// Tip: #box[*[term]*] keeps a fragile token unbroken.
#section("Summary")[
[Role and field, as the facts state them.] [Strongest verifiable fact from the
facts, with its number if the facts give one.] [One sentence the facts support,
with the field's key terms in *bold*.]
]

// ---------- Skills: a few rows, one per category the facts support, items as the facts word them (no gloss, no expansion); fewer rows when facts are thin ----------
#section("Skills & Tools")[
#skill("[Category from the facts]", "[item], [item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item]")
#skill("[Category from the facts]", "[item], [item], [item], [item], [item], [item]")
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
#section("Education")[
#job("[Credential, as printed]", "[Institution]", "[YYYY] – [YYYY]",
  "[City] · [one real fact the facts give: course, mention or grade] · [second fact the facts give, if any]")
]

// ---------- Languages: as the facts state them; "Bilingual" only if two are fluent/native ----------
// Optional section: keep it only per the Languages rule in references/steps/4-draft.md, otherwise delete it.
#section("Languages")[
[Language] ([level as stated])\u{2002}#box[#drawn-marker("mid", ink)\u{2002}[Language]] ([level as stated])
]
