// FAMILY: color-band — colored masthead band, reversed-out name
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, unbreakable
// mark+value box, platform marks, generic icon sets).
#import "lib.typ": *
#let accent = rgb("#1f3a5f")    // hue A — the band + the heading bars
#let accent2 = rgb("#502d66")   // hue B — the dates + the list markers
// DUOTONE family (design.md § Duotone): the pair is validated together
// (far-analogous, +62°) — never mix hue A of one row with hue B of another.
// Coordinated palette: two accents + derived roles.
// soft = same hue lightened, for decorative hairlines only (never text).
// ink  = metadata gray biased 15% toward the accent hue (a pure neutral gray
//        next to a warm accent reads as a mismatch). dark = body ink, 8% biased.
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("Red Hat Text", "Noto Sans", "Liberation Sans")
#let dispf = ("Red Hat Display", "Noto Sans", "Liberation Sans")

// Solid icon style: filled, angular — matches this family's heavy register.
// White, reversed out of the band; the knockout detail is cut in the band hue.
#let ic-col = white
#let ic = icons-solid(ic-col, bg: accent)
#let mk = marks(ic-col)

#set page(paper: "us-letter", margin: (x: 1.5cm, top: 1.2cm, bottom: 1.2cm))
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.583em, spacing: 0.643em)

// device: heading reversed out of a solid accent bar, no rules at all
#let section(t, body, airy: false) = block(breakable: false,
  above: if airy { 12pt } else { 7pt }, below: 0pt)[
  #block(width: 100%, fill: accent, inset: (x: 6pt, y: 2.5pt))[
    #text(font: dispf, size: 11.5pt, weight: "bold", fill: white)[#upper(t)]
  ]
  #v(5pt)
  #body
]

#let job(role, org, dates, note) = entry(role, org, dates, note,
  date-st: it => text(size: 9pt, fill: accent2, weight: "bold", it),
  note-st: it => text(fill: muted, it))

// skills: label on its own line, items on the line below (two-line rows)
#let skill(cat, items) = srow(
  text(weight: "bold", size: 9.5pt)[#upper(cat)], items,
  brk: true, above: 6pt, below: 0pt)

#set list(marker: text(fill: accent2, weight: "bold")[•], indent: 10pt,
  spacing: 0.45em, body-indent: 6pt)

// header: full-width accent band (page 1 only, placed — takes no flow space)
#place(top + left, dx: -1.5cm, dy: -1.2cm,
  rect(width: 100% + 3cm, height: 3.0cm, fill: accent))
#block(above: 0pt, below: 13pt)[
  #text(font: dispf, size: 24pt, weight: "bold", fill: white)[Firstname Lastname]
  #v(-4pt)
  #text(size: 10.5pt, fill: white, weight: "medium")[Backend Software Developer — B.Sc. in Computer Science]
  #v(-4pt)
  #text(size: 9pt, fill: white)[
    #nb(ic.pin)[City, Region]
    #h(6pt) #nb(ic.tel)[#link("tel:+15555550100")[(555) 555-0100]]
    #h(6pt) #nb(mk.mail)[#link("mailto:me@example.com")[me\@example.com]]
    #h(6pt) #nb(mk.li)[#link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]]
    #h(6pt) #nb(mk.gh)[#link("https://github.com/handle")[github.com/handle]]
  ]
]

// ---------- Profile ----------
#section("Profile")[
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
// NOTE (this family, this page only, re-measured 2025-08): this date orphans to
// the end of the pdftotext (non-layout) stream when the descriptor below is
// SHORT, and does not when it is long enough to run the full measure. Measured
// at the real meta size (9pt), across both margins:
//     1.5cm + long  -> no orphan      1.4cm + long  -> no orphan
//     1.5cm + short -> ORPHAN         1.4cm + short -> ORPHAN
// So the x margin is irrelevant to this trap and the descriptor LENGTH is the
// whole cause. An earlier revision widened the measure to x: 1.4cm to "make the
// long descriptor fit"; that both broke the ≥1.5cm margin invariant (design.md §
// Invariants) and misdiagnosed the bug — at 9pt the long descriptor fits on one
// line at 1.5cm with room to spare. Keep the margin at 1.5cm and keep this
// descriptor LONG. Do not shorten it to satisfy line integrity: it does not wrap.
// This trap is position-dependent per ats.md; re-verify per rendered page and
// don't assume the fix transfers (on resume-pair-b.typ a month+year date instead
// of a bare year range was what held).
#section("Education")[
#job("Degree Name (Abbrev.)", "Institution", "2015 – 2019",
  "City · anchor unproven-but-real skills here (e.g. statistics-heavy coursework) · gloss local institutions for foreign readers")
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

// ---------- Soft skills: only with evidence drawn from this CV ----------
#section("Core Strengths")[
#skill("Label", "evidence drawn from the CV itself, never a bare adjective")
#skill("Mentoring", "e.g. \u{201c}onboarded two junior developers\u{201d} — only if a bullet above backs it")
#skill("Communication", "e.g. \u{201c}wrote the team’s API documentation\u{201d} — same rule")
]

// ---------- Languages (spell out the boolean-search words: "bilingual") ----------
#section("Languages")[
Bilingual English / French (fluent) #h(8pt)#text(fill: accent2)[•]#h(8pt) Third language (native)
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
