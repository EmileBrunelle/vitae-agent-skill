// FAMILY: clause-index — numbered-clause technical-standard document
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, unbreakable
// mark+value box, platform marks, generic icon sets, specialities line).
#import "lib.typ": *
#let accent = rgb("#33475b")    // slate — the clause numbers, and nothing else
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("PT Sans", "Public Sans", "Noto Sans")
#let dispf = ("PT Sans", "Schibsted Grotesk", "Noto Sans")

// Line icons in the METADATA GRAY, never the accent: this family's accent has
// exactly one job (the numbers), so a coloured pin would be a third job.
#let ic-col = ink
#let ic = icons-line(ic-col)
#let mk = marks(ic-col)

// GABARIT: dense, the specification-document register — 1.5cm margins, the
// widest measure of the roster, 10.5pt body, tight rhythm. Fill target derives
// from the 1.2cm bottom margin: (100 - 4.3) - 0..2%.
#set page(paper: "us-letter", margin: (x: 1.5cm, top: 1.2cm, bottom: 1.2cm))
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.849em, spacing: 0.929em)

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
  above: if airy { 27pt } else { 22pt }, below: 0pt)[
  #clause.step()
  #sub.update(1)   // display() reads the value BEFORE this row’s step, so 1-based
  #grid(columns: (20pt, 1fr), column-gutter: 0pt, align: (left + bottom, left + bottom),
    text(size: 12pt, weight: "bold", fill: accent, number-type: "lining",
      number-width: "tabular")[#context clause.display()],
    text(font: dispf, size: 12pt, weight: "bold", fill: dark)[#t])
  #v(5pt)
  #body
]

// dates right-flush, tabular figures (a standard document aligns its numerals);
// the institution/descriptor line under the entry anchors the date in the
// extraction (ats.md, orphaned-date trap)
#let job(role, org, dates, note) = entry(role, org, dates, note,
  date-st: it => text(size: 9pt, fill: muted, weight: "bold",
    number-width: "tabular", it),
  note-st: it => text(fill: muted, it))

// skills: a SUB-CLAUSE number. The row carries the section's own clause number
// with a sub-index ("2.1", "2.2" …) in the accent, then the label in bold, then
// the items. Nobody else numbers its skills rows, and the numbering is the same
// device as the section boundary rather than a second invention.
#let skill(cat, items) = srow(
  [#text(size: 8.5pt, weight: "bold", fill: accent, number-width: "tabular")[#context {
      sub.step(); clause.display(); [.]; sub.display() }]
   #text(weight: "bold")[#cat]], items)

#set list(marker: text(fill: accent, weight: "bold")[–], indent: 10pt,
  spacing: 0.45em, body-indent: 6pt)

// HEADER: TWO ZONES over a REFERENCE ROW. The identity block left, the contact
// block right (that right cell is also the photo slot), and under both a
// reference row of small label/value pairs — the Bezugszeichenzeile of the
// German business-letter standard (DIN 676), which is where this family's
// header composition comes from. Then the SPECIALITIES LINE: this is the one
// neutral family that carries one (design.md § Specialities line), set in the
// label register so it reads as a data row and not as a slogan.
#block(above: 0pt, below: 10pt)[
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
     #v(-3pt)
     #text(size: 10.5pt, weight: "medium")[Backend Software Developer — B.Sc. in Computer Science]
     #v(2pt)
     // REFERENCE ROW — one flowing paragraph, never a grid of stacked cells.
     // MEASURED TRAP (new): as a single-ROW grid whose three cells each stacked
     // a label over its value, poppler emitted all three LABELS first and all
     // three VALUES after them, destroying the label↔value pairing the device
     // exists for. A single-ROW grid is safe when each cell is ONE line; the
     // moment a cell stacks two, the reader sweeps the row before it descends.
     #text(size: 9pt)[#rcell("Location", [City, Region]) #h(9pt)
       #rcell("Availability", [Two weeks’ notice]) #h(9pt)
       #rcell("Authorization", [Authorized to work])]
     #v(2pt)
     // SPECIALITIES LINE: the 5-7 mastered skills, linear, NO letterspacing
     // (it extracts as "N E X T" and stops matching), each item boxed so it can
     // never break across a line end. Every item is CONTENT: SKILL.md rule 2
     // applies to it, in the most prominent position on the page.
     #text(size: 8.5pt, weight: "bold", fill: accent)[#specline(
       ("PYTHON", "DJANGO", "POSTGRESQL", "TYPESCRIPT", "REACT", "DOCKER", "CI/CD"),
       sep: [ · ])]],
    text(size: 9pt, fill: muted)[
      #nb(ic.mail)[#link("mailto:me@example.com")[me\@example.com]] \
      #nb(ic.tel)[#link("tel:+15555550100")[(555) 555-0100]] \
      #nb(mk.li)[#link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]] \
      #nb(mk.gh)[#link("https://github.com/handle")[github.com/handle]]],
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
#section("Summary")[
Role and degree in one clause, then the strongest verifiable fact (X years
shipping production code at A, B, C). One sentence covering the stack with
2-3 bolded keywords (*Python/Django*, *TypeScript*, #box[*CI/CD*] — box keeps
fragile tokens unbroken). One closing trait sentence, no clichés
("seeking opportunities…" is dead weight).
]

// ---------- Skills: 5-7 linear rows, every keyword defensible ----------
#section("Skills & Tools")[
#skill("Languages", "Python, TypeScript, SQL, JavaScript, Bash")
#skill("Backend & data", "Django, PostgreSQL, REST APIs, message queues")
#skill("Frontend", "React, accessibility-minded interface work")
#skill("Tools & DevOps", "Git (version control), Docker, AWS (EC2, S3), continuous integration (CI/CD: GitHub Actions)")
#skill("Software quality", "unit and integration testing, test plans, code review")
#skill("Methodologies", "Agile / Scrum, technical documentation")
]

// ---------- Experience in the target field FIRST ----------
#section("Software Development Experience")[

#job("Current Role Title", "Employer", "Mar 2024 – present",
  "City · what the employer is, in one clause · full-time, hybrid")
- Current role in the present tense — every tense convention agrees on that.
- Action verb first; one bolded tech (*Python (Django)*); outcome or scope,
  no invented numbers.
- Contribution verbs (collaborated, strengthened, participated) unless the
  candidate truly owned the outcome — inflated verbs die in interviews.

#job("Earlier Role", "Employer 2", "Jul 2021 – Feb 2024",
  "City · descriptor · full-time, on-site")
- Month+year date ranges always — year-only breaks ATS duration math.
- One strong keyword bolded per bullet, two at most — a wall of bold is none.
]

// ---------- Off-target roles: separated, honest, never leading ----------
#section("Other Professional Experience")[
#job("Off-Target Earlier Role", "Employer 3", "Sep 2019 – Jun 2021",
  "City · descriptor · part-time alongside studies")
- Keep 1-2 transferable bullets; the section label does the explaining.
]

// ---------- Education: the SAME entry shape as the jobs (dates right-flush) ----------
#section("Education")[
#job("Degree Name (Abbrev.)", "Institution", "2015 – 2019",
  "City · anchor unproven-but-real skills here (e.g. statistics-heavy coursework) · gloss local institutions for foreign readers")
]

// ---------- Soft skills: only with evidence drawn from this CV ----------
#section("Strengths")[
#skill("Label", "evidence drawn from the CV itself, never a bare adjective")
#skill("Mentoring", "e.g. \u{201c}onboarded two junior developers\u{201d} — only if a bullet above backs it")
]

// ---------- Languages (spell out the boolean-search words: "bilingual") ----------
#section("Languages")[
Bilingual English / French (fluent)\u{2002}#box[#text(fill: ink)[·]\u{2002}Third] language (native)
]
