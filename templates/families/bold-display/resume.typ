// FAMILY: bold-display — geometric display, heavy weight contrast
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, unbreakable
// mark+value box, platform marks, generic icon sets).
#import "lib.typ": *
#let accent = rgb("#8c3b00")    // hue A — the name, and nothing else
#let accent2 = rgb("#105a90")   // hue B — heading underlines, markers, icons
// DUOTONE family (design.md § Duotone): the pair is validated together
// (complementary) — never mix hue A of one row with hue B of another.
// Coordinated palette: two accents + derived roles.
// soft = same hue lightened, for decorative hairlines only (never text).
// ink  = metadata gray biased 15% toward the accent hue (a pure neutral gray
//        next to a warm accent reads as a mismatch). dark = body ink, 8% biased.
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("Adwaita Sans", "Noto Sans", "Liberation Sans")
#let dispf = ("Space Grotesk", "Noto Sans", "Liberation Sans")

// Solid icon style: filled, angular — matches this family's heavy register.
#let ic-col = accent2
#let ic = icons-solid(ic-col)
#let mk = marks(ic-col)

#set page(paper: "us-letter", margin: (x: 1.5cm, top: 1.2cm, bottom: 1.2cm))
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.536em, spacing: 0.616em)

// device: oversized dark title over a heavy accent underline as wide as the title
#let section(t, body, airy: false) = block(breakable: false,
  above: if airy { 19pt } else { 14pt }, below: 0pt)[
  #box(inset: (bottom: 3pt), stroke: (bottom: 2.5pt + accent2))[
    #text(font: dispf, size: 13pt, weight: "bold", fill: dark)[#upper(t)]
  ]
  #v(6pt)
  #body
]

#let job(role, org, dates, note) = entry(role, org, dates, note,
  date-st: it => text(size: 9pt, fill: muted, weight: "bold", it),
  note-st: it => text(fill: muted, it))

// skills: bold label, wide gap, items — no separator punctuation at all
#let skill(cat, items) = srow(box[#text(weight: "bold")[#cat]#h(12pt)], items)

#set list(marker: text(fill: accent2, weight: "bold")[▪], indent: 10pt,
  spacing: 0.45em, body-indent: 6pt)

// header: oversized accent name left, contacts on one line below
#block(above: 0pt, below: 12pt)[
  #text(font: dispf, size: 29pt, weight: "bold", fill: accent)[Firstname Lastname]
  #v(-3pt)
  #text(size: 11pt, weight: "medium")[Backend Software Developer — B.Sc. in Computer Science]
  #v(-1pt)
  // SPECIALITIES LINE — the 5-7 mastered skills, before the profile prose, so
  // the 30-second scan gets the stack first and retailoring per application is
  // one line. NO `tracking`: letterspacing extracts as "N E X T" and stops
  // matching. Each item boxed so none can break across a line end. Every item
  // is CONTENT — SKILL.md rule 2 applies to it in the most prominent position
  // on the page.
  #text(font: dispf, size: 8.5pt, weight: "bold", fill: accent2)[#specline(
    ("PYTHON", "DJANGO", "POSTGRESQL", "TYPESCRIPT", "REACT", "DOCKER", "CI/CD"),
    sep: [ #box(width: 3pt, height: 3pt, fill: accent2) ])]
  #v(-3pt)
  #text(size: 9pt, fill: muted)[
    #nb(ic.pin)[City, Region] #h(9pt) #nb(ic.tel)[#link("tel:+15555550100")[(555) 555-0100]]
    #h(9pt) #nb(mk.mail)[#link("mailto:me@example.com")[me\@example.com]] \
    #nb(mk.li)[#link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]]
    #h(9pt) #nb(mk.gh)[#link("https://github.com/handle")[github.com/handle]]
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
#section("Education")[
#job("Degree Name (Abbrev.)", "Institution", "2015 – 2019",
  "City · anchor unproven-but-real skills here (e.g. statistics-heavy coursework) · gloss local institutions for foreign readers")
]

// ---------- Skills: 5-7 linear rows, every keyword defensible ----------
#section("Technical Stack")[
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
Bilingual English / French (fluent)\u{2002}#box[#text(fill: accent2)[•]\u{2002}Third] language (native)
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
