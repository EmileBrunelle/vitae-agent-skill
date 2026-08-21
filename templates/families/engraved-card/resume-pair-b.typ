// FAMILY: engraved-card — engraved stationery / social-card typography
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, unbreakable
// mark+value box, platform marks).
#import "lib.typ": *
#let accent = rgb("#5c1f3a")    // garnet — the lozenges + the name rule
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("C059", "P052", "Nimbus Roman")
#let dispf = ("C059", "P052", "Nimbus Roman")

// No generic icon BY PRINCIPLE: engraving carried no ornament — a hairline was
// expensive to cut cleanly, a tint impossible, so the tradition put nothing on
// the card but type. The platform marks are still here (a platform logo is a
// functional identifier of a contact channel, not decoration), in the
// metadata gray so they never compete with the centred axis.
#let ic-col = ink
#let mk = marks(ic-col)

// GABARIT: the airiest of the roster. A card's value is its margin, so the
// horizontal measure comes down to 13.5cm. Body stays at 10.5pt: at 11pt the
// eight sections of the reference content no longer hold one page at this
// margin, and the margin is what carries this family — measured, not guessed.
// Fill target derives from the 2cm bottom margin: (100 - 7.2) - 0..2%.
#set page(paper: "us-letter", margin: (x: 2.0cm, top: 1.6cm, bottom: 1.6cm))
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.514em, spacing: 0.614em)

// DEVICE: a small accent LOZENGE (a rotated filled square — vector, emits no
// text) centred above a CENTRED title. The engraver's spot: one mark, dead
// centre, and nothing else. No rule, no bar, no panel, nothing full-width
// anywhere in the document. This is the only family on a centred axis, and the
// only one whose section titles are centred.
#let section(t, body, airy: false) = block(width: 100%, breakable: false,
  above: if airy { 20pt } else { 15pt }, below: 0pt)[
  // Two separate `align(center)` blocks, not one containing both: inside a
  // single centred block the mark and the title end up centred on their own
  // line boxes and drift apart on short titles (verified — "Languages" landed
  // 150px off the optical centre).
  #align(center, box(width: 5pt, height: 5pt,
    rotate(45deg, rect(width: 4.4pt, height: 4.4pt, fill: accent))))
  #v(2pt)
  #align(center, text(font: dispf, size: 12pt, weight: "semibold", fill: dark)[#t])
  #v(5pt)
  #body
]

// dates right-flush; the institution/descriptor line under the entry is what
// keeps the date anchored in the extraction (ats.md, orphaned-date trap)
#let job(role, org, dates, note) = entry(role, org, dates, note,
  role-st: it => text(size: 11.5pt, weight: "bold", it),
  date-st: it => text(size: 9.5pt, fill: muted, weight: "bold", it),
  note-st: it => text(fill: muted, it),
  meta-size: 9.5pt, above: 7pt, below: 3pt)

// skills: the label, then a FULL STOP, then the items — the engraved
// catalogue/trade-card convention, where the period was the separator because
// a rule or a colour was not available. Nobody else punctuates with a period.
#let skill(cat, items) = srow(text(weight: "semibold")[#cat.], items)

#set list(marker: text(fill: accent)[–], indent: 10pt, spacing: 0.45em,
  body-indent: 6pt)

// HEADER: fully CENTRED — the social-stationery lockup. Name, a short centred
// accent rule under it, the role line, then the contacts on one centred line.
// No photo slot: a centred card has no side cell, and that is the point.
#block(width: 100%, above: 0pt, below: 13pt)[
  #align(center)[
    #text(font: dispf, size: 23pt, weight: "bold")[Firstname Lastname]
    #v(1pt)
    #line(length: 56pt, stroke: 0.6pt + accent)
    #v(3pt)
    #text(size: 11pt, style: "italic")[Backend Software Developer — B.Sc. in Computer Science]
    #v(-1pt)
    #text(size: 9pt, fill: muted)[
      City, Region #h(7pt) #link("tel:+15555550100")[(555) 555-0100] #h(7pt)
      #nb(mk.mail)[#link("mailto:me@example.com")[me\@example.com]] #h(7pt)
      #nb(mk.li)[#link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]] #h(7pt)
      #nb(mk.gh)[#link("https://github.com/handle")[github.com/handle]]]
  ]
]

// SECTION ORDER (this family's default): the formal-classic skeleton —
// EDUCATION IS RAISED above the experience sections, the way a formal
// credential-led document is ordered. A target market's own convention wins
// over this default (references/regional.md).

// ---------- Profile ----------
#section("Summary")[
Role and degree in one clause, then the strongest verifiable fact (X years
shipping production code at A, B, C). One sentence covering the stack with
2-3 bolded keywords (*Python/Django*, *TypeScript*, #box[*CI/CD*] — box keeps
fragile tokens unbroken). One closing trait sentence, no clichés
("seeking opportunities…" is dead weight).
]

// ---------- Education: the SAME entry shape as the jobs (dates right-flush) ----------
// One date convention per document. The institution+descriptor line under the
// entry, plus a date run as WIDE as the others, are what keep this bullet-less
// entry's date from floating to the end of the extraction (ats.md).
#section("Education")[
#job("Degree Name (Abbrev.)", "Institution", "2015 – 2019",
  "City · anchor unproven-but-real skills here (statistics-heavy coursework)")
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

// ---------- Skills: 5-7 linear rows, every keyword defensible ----------
#section("Skills")[
#skill("Languages", "Python, TypeScript, SQL, JavaScript, Bash")
#skill("Backend & data", "Django, PostgreSQL, REST APIs, message queues")
#skill("Frontend", "React, accessibility-minded interface work")
#skill("Tools", "Git (version control), Docker, Linux")
#skill("Cloud & CI", "AWS (EC2, S3), continuous integration (CI/CD: GitHub Actions)")
#skill("Software quality", "unit and integration testing, test plans, code review")
#skill("Methodologies", "Agile / Scrum, technical documentation")
]

// ---------- Soft skills: DROPPED BY THIS FAMILY, on purpose ----------
// engraved-card ships `soft: None`: the engraved-card register is terse, and
// an evidence-line soft-skills section is the one section a formal card would
// not have carried. Dropping a section is a documented option of the label
// system (design.md § Section labels), not a fill trick — but it is also what
// buys this family its airy gabarit: with 2cm margins, eight sections of the
// reference content do not hold one page and seven do (measured both ways).

// ---------- Languages (spell out the boolean-search words: "bilingual") ----------
#section("Languages")[
Bilingual English / French (fluent)\u{2002}#box[#text(fill: ink)[·]\u{2002}Third] language (native)
]
