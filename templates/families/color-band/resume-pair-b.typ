// FAMILY: color-band — colored masthead band, reversed-out name
#let accent = rgb("#1f3a5f")    // hue A — the band + the heading bars
#let accent2 = rgb("#502d66")   // hue B — the dates + the list markers
// DUOTONE family (design.md § Duotone): the pair is validated together
// (far-analogous, +62°) — never mix hue A of one row with hue B of another.
// Coordinated palette: two accents + derived roles.
// soft = same hue lightened, for decorative hairlines only (never text).
// ink  = metadata gray biased 15% toward the accent hue (a pure neutral gray
//        next to a warm accent reads as a mismatch). dark = body ink, 8% biased.
#let soft = color.mix((accent, 40%), (white, 60%))
#let ink = color.mix((luma(95), 85%), (accent, 15%))
#let muted = ink
#let dark = color.mix((luma(25), 92%), (accent, 8%))
#let bodyf = ("Noto Sans", "Liberation Sans")
#let dispf = ("Red Hat Display", "Noto Sans", "Liberation Sans")

// ---------- Contact icons: vector only, no text emitted (verified in extraction) ----------
// Solid style: filled, angular — matches this family's heavy register.
#let ic-col = white
#let ic-pin = box(baseline: 1.4pt, width: 6pt, height: 7.4pt)[
  #place(top + center, circle(radius: 2.6pt, fill: ic-col))
  #place(bottom + center, polygon(fill: ic-col, (0pt, 0pt), (4pt, 0pt), (2pt, 3.4pt)))]
#let ic-tel = box(baseline: 1.4pt, width: 6pt, height: 7.4pt)[
  #place(horizon + center, rect(width: 4.6pt, height: 7.6pt, fill: ic-col))
  #place(bottom + center, dy: -1pt, rect(width: 2.4pt, height: 0.9pt, fill: accent))]
#let ic-mail = box(baseline: 1.4pt, width: 8pt, height: 7.4pt)[
  #place(horizon + center, rect(width: 8pt, height: 6pt, fill: ic-col))
  #place(horizon + center, dy: -1.2pt, polygon(stroke: 1pt + accent, (0pt, 0pt), (4pt, 2.8pt), (8pt, 0pt)))]
#let ic-web = box(baseline: 1.4pt, width: 7.6pt, height: 7.4pt)[
  #place(horizon + center, circle(radius: 3.7pt, fill: ic-col))
  #place(horizon + center, line(length: 7.4pt, stroke: 0.9pt + accent))
  #place(horizon + center, ellipse(width: 3.6pt, height: 7.4pt, stroke: 0.9pt + accent))]

// ---------- Platform marks (contact line) ----------
// Same mechanism as every other family: `marks()` from lib.typ, reading the
// `icons.typ` that scripts/harvest_icons.py generates beside it at build time
// (the path data is third-party artwork and is NOT vendored in this repo).
// Selective import: this file keeps its own job()/chip devices.
// Each mark+value pair goes through `nb`, a #box[…~…] so the mark can never
// be orphaned at a line end — and `nb` drops the mark cleanly if the fetch
// failed, leaving the URL as plain text.
#import "lib.typ": marks, nb
#let mk = marks(ic-col)

#set page(paper: "us-letter", margin: (x: 1.5cm, top: 1.2cm, bottom: 1.2cm))
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.54em, spacing: 0.59em)

// device: heading reversed out of a solid accent bar, no rules at all
#let section(t, body, airy: false) = block(breakable: false,
  above: if airy { 10pt } else { 5pt }, below: 0pt)[
  #block(width: 100%, fill: accent, inset: (x: 6pt, y: 2.5pt))[
    #text(font: dispf, size: 11.5pt, weight: "bold", fill: white)[#upper(t)]
  ]
  #v(5pt)
  #body
]

#let job(role, org, dates, note) = block(above: 6pt, below: 3pt, sticky: true)[
  #grid(columns: (1fr, auto), align: (left + bottom, right + bottom),
    text(size: 11pt, weight: "bold")[#role],
    text(size: 9pt, fill: accent2, weight: "bold")[#dates],
  )
  #v(1.5pt)
  #text(size: 9pt)[#text(weight: "semibold")[#org]#if note != none [#text(fill: muted)[ — #note]]]
]

// skills: label on its own line, items on the line below (two-line rows)
#let skill(cat, items) = block(above: 6pt, below: 0pt)[
  #text(weight: "bold", size: 9.5pt)[#upper(cat)] \
  #items
]

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
    #box[#ic-pin~City, Region]
    #h(6pt) #box[#ic-tel~#link("tel:+15555550100")[(555) 555-0100]]
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
// NOTE (this family only): a bare 4-digit year in the date cell gets shuffled
// to the end of the pdftotext (non-layout) stream on this template's page —
// reproducible regardless of leading/spacing/sticky, tied to the isolated
// numeric-only run. A month+year token (as every job() entry above already
// uses) does not trigger it, so the date is written the same way here.
#section("Education")[
#job("Degree Name (Abbrev.)", "Institution", "Sep 2015 – May 2019",
  "City · relevant coursework noted · institution glossed for readers")
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
