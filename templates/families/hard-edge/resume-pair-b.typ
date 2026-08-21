// FAMILY: hard-edge — neo-brutalist hard borders + monospace metadata
// REGISTER: creative (never in the default pool — design.md § The creative
// register: unlocked by a creative target field or an explicit request, capped
// back out by a conservative market).
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, painted chips,
// unbreakable mark+value box, platform marks, generic icon sets, specialities).
#import "lib.typ": *
#let accent = rgb("#b3261e")    // hue A — the monogram block + the specialities line
#let accent2 = rgb("#0f4c5c")   // hue B — the dates, the markers, the icons
// DUOTONE family (design.md § Duotone): the pair is validated together —
// never mix hue A of one row with hue B of another.
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("Noto Sans", "Public Sans", "Liberation Sans")
#let dispf = ("Hanken Grotesk", "Familjen Grotesk", "Noto Sans")
// THIRD font role, and it is this family's voice as much as the display face:
// every piece of METADATA — dates, employer descriptors, the specialities line,
// the contact line — is set in the monospace. That grotesque/monospace split is
// the neo-brutalist signature; without it the recipe is just a bordered box.
#let monof = ("DejaVu Sans Mono", "Fira Mono", "Noto Sans Mono")

// Solid icon style: filled, angular — nothing in this family is rounded.
#let ic-col = accent2
#let ic = icons-solid(ic-col)
#let mk = marks(ic-col)

// GABARIT: dense — 1.6cm margins, a wide measure, 10.5pt body. Fill target
// derives from the 1.3cm bottom margin: (100 - 4.7) - 0..2%.
#set page(paper: "us-letter", margin: (x: 1.6cm, top: 1.3cm, bottom: 1.3cm))
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.749em, spacing: 0.839em)

// DEVICE: the title KNOCKED OUT of a hard black slab, the slab only as wide as
// its own title — nothing full-width anywhere in the document. Square corners,
// no border, no shadow.
//
// This is the PRINT expression of the neo-brutalist current (extensive black
// for solid fields, oversized knockout type), deliberately not the web-UI
// dialect of it. The earlier version was a white bordered box with a 2.5pt
// flat offset block behind it — thick black border + zero-blur offset + a
// candy tint field is the "sticker card" vocabulary of the neubrutalism UI
// trend, and a reader recognized it as one specific brand's identity
// (§ Rules common to every family — the non-recognition bar covers brands too).
// Same current, different dialect, and the grotesque/monospace split still
// carries the family.
//
// Distinct from `color-band`, whose heading also reverses out: that one is a
// FULL-TEXT-WIDTH bar in the ACCENT; this is a shrink-to-title slab in the
// body ink. `box(fill:)` shrinks to its content, so no `measure()` is needed —
// but note the trap if a `rect` is ever reinstated here: `rect(width: 100%)`
// inside a box resolves to the AVAILABLE width and silently reproduces the
// banned full-width bar (same trap as `line(length: 100%)` — verified).
#let section(t, body, airy: false) = block(width: 100%, breakable: false,
  above: if airy { 25pt } else { 20pt }, below: 0pt)[
  #box(fill: dark, inset: (x: 6pt, y: 2.5pt),
    text(font: dispf, size: 11.5pt, weight: "bold", fill: white)[#upper(t)])
  #v(6pt)
  #body
]

// Dates and the employer descriptor in the MONO face — the metadata register.
// The descriptor line under the entry is what keeps the date anchored in the
// extraction (ats.md, orphaned-date trap).
#let job(role, org, dates, note) = entry(role, org, dates, note,
  role-st: it => text(font: dispf, size: 11pt, weight: "bold", it),
  date-st: it => text(font: monof, size: 8.5pt, fill: accent2, weight: "medium", it),
  note-st: it => text(font: monof, size: 8pt, fill: muted, it),
  meta-size: 9pt)

// SKILLS: a REVERSED-OUT TAG, then the items plain. The tag is the section
// slab's own shape one scale down — the family repeats its own shapes instead
// of inventing a second language.
//
// The tag is a PAINTED chip (`highlight`), not a `box`, and that is mechanical,
// not stylistic. MEASURED on this very page shape (ats.md, lib.typ § chip): the
// label set in a bordered `box(stroke:)` tore the first two labels off their
// values and emitted them at the END of the section ("… METHODOLOGIES Agile /
// Scrum … / LANGUAGES / BACKEND & DATA"). A box around the label is the same
// separate-text-cluster failure as a box around each item. `highlight` paints
// the field behind the same text run, so the row stays one text cluster and
// extracts byte-identically to a plain linear row.
//
// The ITEMS carry no tint. They used to be chips in a 22% tint of hue A; a
// row of tinted pills is the highlighter-field look of the neubrutalism UI
// trend, and together with the offset shadow it is what made the page
// recognizable as a specific brand. Black slab, plain items: the same current,
// read from print instead of from a component library.
// The tag hugs its label: `extent: 1pt`, and the gap to the first item is the
// paragraph's OWN word space. VERIFIED TRAP: an `h(4pt)` between the tag and
// the items — the obvious way to widen that gap — tore `LANGUAGES` and
// `MENTORING` off their values and emitted them at the end of the section, the
// same separate-text-cluster failure as a `box` around the label. Explicit
// spacing next to a `highlight` breaks the run; a plain word space does not.
#let stag(cat) = chip(
  text(font: monof, size: 8pt, weight: "bold", fill: white)[#upper(cat)],
  fill: dark, extent: 1pt)
#let skill(cat, items) = srow(stag(cat), items, above: 5pt, below: 0pt)
#let sskill(cat, items) = skill(cat, items)

// List marker: a hard-bordered SQUARE OUTLINE, drawn (emits no text). Nobody
// else uses an outlined marker — mono-technical's is filled.
#set list(marker: box(width: 4pt, height: 4pt, baseline: -0.5pt,
    stroke: 1pt + accent2), indent: 10pt, spacing: 0.45em, body-indent: 7pt)

// HEADER: MONOGRAM + TWO ZONES. A hard-bordered square holds the initials
// reversed out of hue A, the name sits beside it, then the specialities line
// and a single monospace contact line. The monogram is real TEXT inside a drawn
// box — never an image: harvested counter-evidence says an image-rendered
// monogram is invisible to extraction, and the initials are then a hole in the
// document where the name should be.
#block(above: 0pt, below: 12pt)[
  #hrow(
    [#box(baseline: 12pt, width: 1.15cm, height: 1.15cm, fill: accent,
       stroke: 1.4pt + dark, inset: 0pt)[
       #align(center + horizon, text(font: dispf, size: 17pt, weight: "bold",
         fill: white)[FL])]
     #h(9pt)
     #box(baseline: 12pt)[
       #text(font: dispf, size: 25pt, weight: "bold")[Firstname Lastname] \
       #v(-5pt)
       #text(font: monof, size: 9pt, fill: muted)[Backend Software Developer — B.Sc. in Computer Science]]],
    [], cols: (auto, 1fr), gutter: 0pt,
    align-cells: (left + top, left + top), above: 0pt, below: 5pt)
  // SPECIALITIES LINE — the 5-7 mastered skills, in hue A, mono, uppercase,
  // pipe-separated. NO `tracking`: letterspacing extracts as "N E X T" and
  // stops matching. Each item boxed, so none can break across a line end.
  // Every item is CONTENT: SKILL.md rule 2 applies to it in the most prominent
  // position on the page — a specialities line is not a decoration strip.
  #text(font: monof, size: 8.5pt, weight: "bold", fill: accent)[#specline(
    ("PYTHON", "DJANGO", "POSTGRESQL", "TYPESCRIPT", "REACT", "DOCKER", "CI/CD"),
    sep: [ | ])]
  #v(2pt)
  #text(font: monof, size: 8.5pt, fill: muted)[
    #nb(ic.pin)[City, Region] #h(7pt)
    #nb(ic.tel)[#link("tel:+15555550100")[(555) 555-0100]] #h(7pt)
    #nb(mk.mail)[#link("mailto:me@example.com")[me\@example.com]] #h(7pt)
    #nb(mk.li)[#link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]] #h(7pt)
    #nb(mk.gh)[#link("https://github.com/handle")[github.com/handle]]]
]

// SECTION ORDER (this family's default): SKILLS SECOND, straight after the
// profile — the hybrid order a technical/creative audience reads first, with
// the full reverse-chronological history below it. A target market's own
// convention wins over this default (references/regional.md).

// ---------- Profile ----------
#section("Profile")[
Role and degree in one clause, then the strongest verifiable fact (X years
shipping production code at A, B, C). One sentence covering the stack with
2-3 bolded keywords (*Python/Django*, *TypeScript*, #box[*CI/CD*] — box keeps
fragile tokens unbroken). One closing trait sentence, no clichés
("seeking opportunities…" is dead weight).
]

// ---------- Skills: 5-7 linear rows, every keyword defensible ----------
#section("Technical Stack")[
#skill("Languages", "Python, TypeScript, SQL, JavaScript, Bash")
#skill("Backend & data", "Django, PostgreSQL, REST APIs, message queues")
#skill("Frontend", "React, accessibility-minded interface work")
#skill("Tools & DevOps", "Git (version control), Docker, AWS (EC2 and S3), continuous integration")
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
  "City · anchor unproven-but-real skills here · gloss local institutions for foreign readers")
]

// ---------- Soft skills: only with evidence drawn from this CV ----------
#section("Strengths")[
#sskill("Label", "evidence drawn from the CV itself, never a bare adjective")
#sskill("Mentoring", "onboarded two junior developers — only if a bullet above backs it")
]

// ---------- Languages (spell out the boolean-search words: "bilingual") ----------
#section("Languages")[
Bilingual English / French (fluent)\u{2002}#box[#text(fill: accent2)[|]\u{2002}Third] language (native)
]
