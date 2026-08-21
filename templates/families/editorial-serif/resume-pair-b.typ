// FAMILY: editorial-serif — contemporary editorial: serif display over a sans body
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, unbreakable
// mark+value box, platform marks, generic icon sets).
#import "lib.typ": *
#let accent = rgb("#1f3a5f")
// Coordinated palette (monochrome harmony): one accent + derived roles.
// soft = same hue lightened, for decorative hairlines only (never text).
// ink  = metadata gray biased 15% toward the accent hue (a pure neutral gray
//        next to a warm accent reads as a mismatch). dark = body ink, 8% biased.
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("Open Sans", "Noto Sans", "Liberation Sans")
#let dispf = ("Noto Serif", "Liberation Serif")

// Line icon style: thin stroke, rounded — belongs to this family's light
// register. Platform marks in the same colour.
#let ic-col = accent
#let ic = icons-line(ic-col)
#let mk = marks(ic-col)

#set page(paper: "us-letter", margin: (x: 1.5cm, top: 1.2cm, bottom: 1.2cm))
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.505em, spacing: 0.575em)

// device: short heavy accent bar 20 a large serif title (magazine kicker rule)
#let section(t, body, airy: false) = block(breakable: false,
  above: if airy { 18pt } else { 13pt }, below: 0pt)[
  #line(length: 46pt, stroke: 3.5pt + accent)
  #v(3pt)
  #text(font: dispf, size: 13pt, weight: "bold", fill: dark)[#t]
  #v(4pt)
  #body
]

// role in the display serif: the serif/sans jump does the hierarchy
#let job(role, org, dates, note) = entry(role, org, dates, note,
  date-st: it => text(size: 9pt, fill: muted, weight: "bold", it),
  note-st: it => text(fill: muted, it),
  role-st: it => text(font: dispf, size: 11.5pt, weight: "bold", it))

// skills: serif bold label, thin accent tick (vector), sans items
#let skill(cat, items) = srow([#text(font: dispf, size: 11pt, weight: "bold")[#cat] #box(width: 3pt, height: 3pt, fill: accent, baseline: -2pt)], items)

#set list(marker: text(fill: dark)[–], indent: 10pt, spacing: 0.45em, body-indent: 6pt)

// header: oversized serif name, then role line left / contact column right (photo slot)
#block(above: 0pt, below: 12pt)[
  #grid(columns: (1fr, auto), column-gutter: 14pt, align: (left + bottom, right + bottom),
    [#text(font: dispf, size: 25pt, weight: "bold")[Firstname Lastname] \
     #v(-2pt)
     #text(size: 10.5pt, fill: accent, weight: "semibold")[Backend Software Developer — B.Sc. in Computer Science]],
    text(size: 9pt, fill: muted)[#set par(leading: 0.42em); #nb(ic.pin)[City, Region] \
      #nb(ic.tel)[#link("tel:+15555550100")[(555) 555-0100]] \
      #nb(mk.mail)[#link("mailto:me@example.com")[me\@example.com]] \
      #nb(mk.li)[#link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]] \
      #nb(mk.gh)[#link("https://github.com/handle")[github.com/handle]]],
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

// ---------- Education: the SAME entry shape as the jobs (dates right-flush) ----------
// The institution+descriptor line under the entry is what keeps the date from
// being orphaned at the end of the extraction (verified: ats.md date trap).
#section("Education")[
#job("Degree Name (Abbrev.)", "Institution", "2015 – 2019",
  "City · relevant coursework noted · institution glossed for readers")
]

// ---------- Skills: 5-7 linear rows, every keyword defensible ----------
#section("Technical Skills")[
#skill("Languages", "Python, TypeScript, SQL, JavaScript, Bash")
#skill("Backend & data", "Django, PostgreSQL, REST APIs, message queues")
#skill("Frontend", "React, accessibility-minded interface work")
#skill("Tools & DevOps", "Git (version control), Docker, AWS (EC2, S3), continuous integration (CI/CD: GitHub Actions)")
#skill("Software quality", "unit and integration testing, test plans, code review")
#skill("Methodologies", "Agile / Scrum, technical documentation")
]

// ---------- Soft skills: only with evidence drawn from this CV ----------
#section("Core Strengths")[
#skill("Label", "evidence drawn from the CV itself, never a bare adjective")
#skill("Mentoring", "e.g. \u{201c}onboarded two junior developers\u{201d} — only if a bullet above backs it")
#skill("Communication", "e.g. \u{201c}wrote the team’s API documentation\u{201d} — same rule")
]

// ---------- Languages (spell out the boolean-search words: "bilingual") ----------
#section("Languages")[
Bilingual English / French (fluent)\u{2002}#box[#text(fill: accent)[•]\u{2002}Third] language (native)
]

// ---------- 2-page version recipe ----------
// 1. Under Profile, add a highlights block: 2 linear lines (never a grid),
//    two "– item" chips per line separated by #h(14pt).
// 2. Fuller bullets (3-4 per role), evidence-based "Core Strengths" lines
//    ("Label — evidence from this CV"), languages with levels.
// 3. Place a deliberate #pagebreak() at the section boundary that leaves
//    page 1 fullest (typically after Education); page assignment must be
//    deterministic, never left to auto-flow.
// 4. Balance unequal pages: #set text/#set par are document-global — re-set
//    them locally after the #pagebreak(), and/or use section(..., airy: true)
//    on the sparse page. Re-run the fill measurement on EVERY page.
