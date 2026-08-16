// vitae template — fill the data, keep the system.
// Design rules: references/design.md · ATS rules: references/ats.md
// Verify after EVERY edit: scripts/verify.sh resume.typ 1 94 96

// ---------- Tokens ----------
#let accent = rgb("#7d2231")        // one accent, ≥4.5:1 on white, survives B&W
#let muted = luma(90)
#let dark = luma(30)

// Paper: "us-letter" (Canada/USA) or "a4" (most of the rest) — see regional.md
#set page(paper: "us-letter", margin: (x: 1.5cm, top: 1.2cm, bottom: 1.2cm))
// lang drives hyphenation/smart quotes: "en", "fr", "de"…
#set text(font: ("Carlito", "Noto Sans", "Liberation Sans"), size: 10pt,
  lang: "en", fill: dark, hyphenate: false)
// Primary fill-tuning knobs ↓ (±0.01-0.03em steps)
#set par(justify: false, leading: 0.65em, spacing: 0.74em)

// ---------- Primitives ----------
// One unbreakable block per section: never split across pages.
// `airy: true` = roomier rhythm for sparse pages of a multi-page version.
#let section(t, body, airy: false) = block(breakable: false,
  above: if airy { 19pt } else { 14pt }, below: 0pt)[
  #grid(columns: (auto, auto), column-gutter: 7pt, align: horizon,
    box(width: 4pt, height: 9pt, fill: accent),   // accent tick (vector: emits no text)
    text(font: ("Montserrat", "Noto Sans", "Liberation Sans"),
      size: 10.5pt, weight: "bold", fill: accent)[#upper(t)],
  )
  #v(3pt)
  #line(length: 100%, stroke: 0.7pt + luma(180))  // single thin hairline
  #v(5pt)
  #body
]

// Bold role + bold dark dates right; accent org + muted descriptor below.
#let job(role, org, dates, note) = block(above: 9pt, below: 4pt, sticky: true)[
  #grid(columns: (1fr, auto), align: (left + bottom, right + bottom),
    text(size: 11pt, weight: "bold")[#role],
    text(size: 9pt, fill: muted, weight: "bold")[#dates],
  )
  #v(1.5pt)
  #text(size: 9pt)[#text(fill: accent, weight: "semibold")[#org]#if note != none [#text(fill: muted)[ — #note]]]
]

// Linear skill line — NEVER a data grid (ATS extracts grids column-by-column).
// French: use [#cat~:] for the non-breaking space before the colon.
// Markup (*bold*, #box) inside items only works if you pass [content],
// e.g. #skill("Languages", [Python, *TypeScript*]) — a "string" renders it literally.
#let skill(cat, items) = par[#text(weight: "semibold")[#cat:] #items]

#set list(marker: text(fill: accent, weight: "bold")[–], indent: 10pt,
  spacing: 0.5em, body-indent: 6pt)

// ---------- Header (centered, no icons — parses clean everywhere) ----------
#align(center)[
  #text(font: ("Montserrat", "Noto Sans", "Liberation Sans"),
    size: 23pt, weight: "bold")[Firstname Lastname]
  #v(-2pt)
  // Unregulated role name + degree — the degree carries the signal legally.
  #text(size: 11pt, fill: accent, weight: "medium")[Backend Software Developer — B.Sc. in Computer Science]
  #v(-4pt)
  #text(size: 9.5pt, fill: muted)[
    City, Region
    #h(5pt)•#h(5pt) #link("tel:+15555550100")[(555) 555-0100]
    #h(5pt)•#h(5pt) #link("mailto:me@example.com")[me\@example.com] \
    #link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]
    #h(5pt)•#h(5pt) #link("https://github.com/handle")[github.com/handle]
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

// ---------- Education ----------
// Bullet-less entries followed by a paragraph section can orphan their date
// in pdftotext (verified). Run the date grep from references/ats.md; if a
// year floats loose, replace job() with a linear one-line entry for it.
#section("Education")[
#job("Degree Name (Abbrev.)", "Institution", "2019",
  "City · anchor unproven-but-real skills here (e.g. statistics-heavy coursework) · gloss local institutions for foreign readers")
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
Bilingual English / French (fluent) #h(8pt)#text(fill: accent)[•]#h(8pt) Third language (native)
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
