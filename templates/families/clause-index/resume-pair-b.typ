// FAMILY: clause-index — numbered-clause technical-standard document
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, unbreakable
// mark+value box, platform marks, generic icon sets, specialities line).
#import "../../lib.typ": *
// vertical rhythm: 1.000 as designed; a tuner stretches every pt gap through it
#let rhythm = 1.000
#let accent = rgb("#33475b")    // slate — the clause numbers, and nothing else
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("Public Sans", "PT Sans", "Noto Sans")
#let dispf = ("Schibsted Grotesk", "PT Sans", "Noto Sans")

// Line icons in the METADATA GRAY, never the accent: this family's accent has
// exactly one job (the numbers), so a coloured pin would be a third job.
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
#set page(background: accent-band(accent)) if band
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.550em, spacing: 0.630em)

// DEVICE: an OUTDENTED CLAUSE NUMBER. The numbering-of-divisions convention of
// technical standards (ISO 2145, DIN 1421): the division number hangs in a
// fixed 20pt gutter, the title sits flush at the text edge, and there is no
// rule, no bar, no fill, no panel anywhere in the document. Nobody else numbers
// its sections, and nobody else spends its accent only on numerals.
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
  #grid(columns: (20pt, 1fr), column-gutter: 0pt, align: (left + bottom, left + bottom),
    text(size: 12pt, weight: "bold", fill: accent, number-type: "lining",
      number-width: "tabular")[#context clause.display()],
    text(font: dispf, size: 12pt, weight: "bold", fill: dark)[#t])
  #v(12pt * rhythm)
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
  spacing: 0.733em, body-indent: 6pt)

// HEADER: TWO ZONES over a REFERENCE ROW. The identity block left, the contact
// block right (that right cell is also the photo slot), and under both a
// reference row of small label/value pairs — the Bezugszeichenzeile of the
// German business-letter standard (DIN 676), which is where this family's
// header composition comes from. Then the SPECIALITIES LINE: this is the one
// neutral family that carries one (core.md § Specialities line), set in the
// label register so it reads as a data row and not as a slogan.
#block(above: 0pt, below: 10pt * rhythm)[
  // The reference row and the specialities line live INSIDE the left zone, not
  // across the full width. MEASURED (new trap): a full-width row that crosses
  // the contact column's x-range gets its rightmost item pulled into the
  // contact cluster — the extraction came out
  // "LOCATION … / AVAILABILITY … / <the whole contact column> / AUTHORIZATION …".
  // poppler clusters by column before it reads by line, so a device that spans
  // under a two-zone header must stay inside one of the zones.
  #let rcell(l, val) = [#text(size: 7.5pt, weight: "bold", fill: ink)[#upper(l)] #val]
  #hrow(
    [#text(font: dispf, size: 22pt, weight: "bold")[Firstname Lastname] \
     #v(-3pt * rhythm)
     #text(size: 10.5pt, weight: "medium")[[Target title, as in the facts or posting] — [Degree, if the facts state it]]
     #v(2pt * rhythm)
     // REFERENCE ROW — one flowing paragraph, never a grid of stacked cells.
     // MEASURED TRAP (new): as a single-ROW grid whose three cells each stacked
     // a label over its value, poppler emitted all three LABELS first and all
     // three VALUES after them, destroying the label↔value pairing the device
     // exists for. A single-ROW grid is safe when each cell is ONE line; the
     // moment a cell stacks two, the reader sweeps the row before it descends.
     #text(size: 9pt)[#rcell("Location", [\[City, Region\]]) #h(9pt)
       #rcell("Availability", [\[Two weeks’ notice\]]) #h(9pt)
       #rcell("Authorization", [\[Authorized to work\]])]
     #v(2pt * rhythm)
     // SPECIALITIES LINE: the skills the facts support, linear, NO letterspacing
     // (it extracts as "N E X T" and stops matching), each item boxed so it can
     // never break across a line end. Every item is CONTENT: SKILL.md rule 2
     // applies to it, in the most prominent position on the page.
     #text(size: 8.5pt, weight: "bold", fill: accent)[#specline(
       ("[SKILL]", "[SKILL]", "[SKILL]", "[SKILL]", "[SKILL]"),
       sep: [ · ])]],
    text(size: 9pt, fill: muted)[
      #contact-rows(4)#contact(ic.mail)[#link("mailto:me@example.com")[me\@example.com]] \
      #contact(ic.tel)[#link("tel:+15555550100")[(555) 555-0100]] \
      #contact(mk.li)[#link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]] \
      #contact(mk.gh)[#link("https://github.com/handle")[github.com/handle]]],
    align-cells: (left + top, right + top), gutter: 16pt,
    above: 0pt, below: 0pt)
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
#section("Languages")[
[Language] ([level as stated])\u{2002}#box[#drawn-marker("mid", ink)\u{2002}[Language]] ([level as stated])
]
