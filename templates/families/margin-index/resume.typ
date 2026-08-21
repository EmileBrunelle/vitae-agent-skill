// FAMILY: margin-index — classic marginalia (book typography, Bringhurst school)
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, unbreakable
// mark+value box, platform marks, generic icon sets).
#import "lib.typ": *
#let accent = rgb("#4a2f10")
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("STIX Two Text", "Libertinus Serif", "Noto Serif", "Liberation Serif")
#let dispf = bodyf

// this family carries no generic icons by principle — the
// platform marks are identifiers, not ornament (design.md).
#let ic-col = ink
#let mk = marks(ic-col)

#set page(paper: "us-letter", margin: (x: 1.5cm, top: 1.2cm, bottom: 1.2cm))
#set text(font: bodyf, size: 11pt, lang: "en", fill: dark, hyphenate: false,
  number-type: "old-style", number-width: "proportional")
#set par(justify: false, leading: 0.800em, spacing: 1.000em)

// device: NO rule, NO bar — the title hangs in the left margin column beside
// its own content. Single-ROW grid per section (safe: ats.md), title cell first
// so the extraction order stays heading → body.
#let section(t, body, airy: false) = block(breakable: false,
  above: if airy { 35pt } else { 30pt }, below: 0pt)[
  #grid(columns: (2.5cm, 1fr), column-gutter: 12pt, align: (right + top, left + top),
    [#line(length: 100%, stroke: 1pt + accent)
     #v(3pt)
     #text(size: 10.5pt, weight: "bold", fill: accent)[#t]],
    body,
  )
]

// dates right-flush; the institution/descriptor line under the entry is what
// keeps the date anchored in the extraction (ats.md, orphaned-date trap)
#let job(role, org, dates, note) = entry(role, org, dates, note,
  date-st: it => text(size: 9pt, fill: muted, weight: "bold", it),
  note-st: it => text(fill: muted, it),
  above: 5pt)

// skills: italic run-in label, no separator glyph at all — the italic/roman
// jump does the separating (nobody else uses italic as the skills device)
#let skill(cat, items) = srow(text(style: "italic")[#cat], items)

#set list(marker: text(fill: accent)[—], indent: 9pt, spacing: 0.45em, body-indent: 6pt)

// header: name and role in the content column, contacts on one line under it;
// the margin column stays empty here (extraction keeps the name first)
#block(above: 0pt, below: 13pt)[
  #grid(columns: (2.5cm, 1fr), column-gutter: 12pt,
    [],
    [#text(font: dispf, size: 23pt, weight: "bold")[Firstname Lastname] \
     #v(-4pt)
     #text(size: 10.5pt, style: "italic")[Backend Software Developer — B.Sc. in Computer Science] \
     #v(-3pt)
     #text(size: 9pt, fill: muted)[#nb(mk.pin)[City, Region] #h(7pt) #nb(mk.phone)[#link("tel:+15555550100")[(555) 555-0100]]
       #h(7pt) #nb(mk.mail)[#link("mailto:me@example.com")[me\@example.com]] #h(7pt)
       #nb(mk.li)[#link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]] #h(7pt)
       #nb(mk.gh)[#link("https://github.com/handle")[github.com/handle]]]],
  )
]

// ---------- Profile ----------
#section("Summary")[
Role and degree in one clause, then the strongest verifiable fact (X years
shipping production code at A, B, C). One sentence covering the stack with
2-3 bolded keywords (*Python/Django*, *TypeScript*, #box[*CI/CD*] — box keeps
fragile tokens unbroken). One closing trait sentence, no clichés
("seeking opportunities…" is dead weight).
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

// ---------- Education: linear one-line entry, NOT the grid job() shape ----------
// NOTE (this family, 2025-08 audit): the grid entry() orphaned this date to
// the end of the pdftotext extraction once the note was shortened to one
// line (design.md § Line integrity fix). Switched to `earlyline` (role,
// org+note, year all in one paragraph) per the known trap in ats.md — a
// bullet-less grid entry can orphan its date; the linear variant can't,
// since there is always text on both sides of the date in the same run.
#section("Education")[
#earlyline("Degree Name (Abbrev.)", "Institution — City · coursework glossed for readers", "2015 – 2019",
  year-st: it => text(size: 9pt, fill: muted, weight: "bold", it))
]

// ---------- Skills: 5-7 linear rows, every keyword defensible ----------
#section("Expertise")[
#skill("Languages", "Python, TypeScript, SQL, JavaScript, Bash")
#skill("Backend & data", "Django, PostgreSQL, REST APIs, message queues")
#skill("Frontend", "React, accessibility-minded interface work")
#skill("Tools", "Git (version control), Docker")
#skill("Cloud & CI", "AWS (EC2, S3), continuous integration (CI/CD: GitHub Actions)")
#skill("Software quality", "unit and integration testing, test plans, code review")
#skill("Methodologies", "Agile / Scrum, technical documentation")
]

// ---------- Soft skills: only with evidence drawn from this CV ----------
#section("Strengths")[
#skill("Label", "evidence drawn from the CV itself, never a bare adjective")
#skill("Mentoring", "e.g. \u{201c}onboarded two junior developers\u{201d} — only if a bullet above backs it")
#skill("Communication", "e.g. \u{201c}wrote the team’s API documentation\u{201d} — same rule")
]

// ---------- Languages (spell out the boolean-search words: "bilingual") ----------
#section("Languages")[
Bilingual English / French (fluent) #h(8pt)#text(fill: accent)[•]#h(8pt) Third language (native)
]
