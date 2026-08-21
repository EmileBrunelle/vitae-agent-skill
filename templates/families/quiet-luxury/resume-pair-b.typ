// FAMILY: quiet-luxury — warm restrained minimalism (2020s "quiet luxury")
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, unbreakable
// mark+value box, platform marks, generic icon sets).
#import "lib.typ": *
#let accent = rgb("#5c4632")
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("Noto Sans", "Liberation Sans")
#let dispf = ("Adwaita Sans", "Noto Sans", "Liberation Sans")

// ---------- Contact icons: vector only, no text emitted ----------
// Line style in the METADATA gray, not the accent: the accent is spent on
// organizations and the trailing rules, and nowhere else.
#let ic-col = ink
#let ic = icons-line(ic-col)
#let mk = marks(ic-col)

#set page(paper: "us-letter", margin: (x: 1.6cm, top: 1.3cm, bottom: 1.2cm))
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.525em, spacing: 0.625em)

// device: the title, then a SHORT hairline tick on its own baseline-centre —
// inline punctuation, not furniture. Never under the heading, never full width
// (a rule spanning the measure beside every title reads as word-processor
// furniture; measured and rejected).
#let section(t, body, airy: false) = block(breakable: false,
  above: if airy { 27pt } else { 22pt }, below: 0pt)[
  #text(font: dispf, size: 12pt, weight: "semibold", fill: dark)[#t]
  #h(7pt)
  #box(baseline: -3pt, line(length: 34pt, stroke: 2pt + accent))
  #v(5pt)
  #body
]

// dates right-flush; the organization line under the entry anchors the date in
// the extraction (ats.md, orphaned-date trap). Organizations carry the accent.
#let job(role, org, dates, note) = entry(role, org, dates, note,
  date-st: it => text(size: 9pt, fill: muted, weight: "bold", it),
  org-st: it => text(weight: "semibold", fill: accent, it),
  note-st: it => text(fill: muted, it))

// skills: the label is set in the METADATA GRAY — colour, not weight or a
// glyph, does the separating. No colon, no dash, no bullet.
#let skill(cat, items) = srow(text(fill: ink, weight: "semibold")[#cat], items)

#set list(marker: text(fill: dark)[·], indent: 10pt, spacing: 0.45em, body-indent: 6pt)

// header: CONTACTS FIRST (a letterhead line), then the name, then the role —
// the reverse of every other family's header order.
#block(above: 0pt, below: 14pt)[
  #text(size: 8.5pt, fill: muted)[
    #nb(ic.pin)[City, Region] #h(7pt) #nb(ic.tel)[#link("tel:+15555550100")[(555) 555-0100]]
    #h(7pt) #nb(mk.mail)[#link("mailto:me@example.com")[me\@example.com]] #h(7pt)
    #nb(mk.li)[#link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]] #h(7pt)
    #nb(mk.gh)[#link("https://github.com/handle")[github.com/handle]]]
  #v(3pt)
  #text(font: dispf, size: 22pt, weight: "bold")[Firstname Lastname]
  #v(-4pt)
  #text(size: 10.5pt, fill: ink)[Backend Software Developer — B.Sc. in Computer Science]
]

// ---------- Profile ----------
#section("Professional Summary")[
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

// ---------- Education: same entry shape as the jobs (dates right-flush) ----------
#section("Education")[
#job("Degree Name (Abbrev.)", "Institution", "2015 – 2019",
  "City · relevant coursework noted · institution glossed for readers, capstone in applied distributed systems")
]

// ---------- Skills: 5-7 linear rows, every keyword defensible ----------
#section("Skills & Tools")[
#skill("Languages", "Python, TypeScript, SQL, JavaScript, Bash")
#skill("Backend & data", "Django, PostgreSQL, REST APIs, message queues")
#skill("Frontend", "React, accessibility-minded interface work")
#skill("Tools", "Git (version control), Docker")
#skill("Cloud & CI", "AWS (EC2, S3), continuous integration (CI/CD: GitHub Actions)")
#skill("Software quality", "unit and integration testing, test plans, code review")
#skill("Methodologies", "Agile / Scrum, technical documentation")
]

// ---------- Soft skills: only with evidence drawn from this CV ----------
#section("Working Style")[
#skill("Label", "evidence drawn from the CV itself, never a bare adjective")
#skill("Mentoring", "e.g. \u{201c}onboarded two junior developers\u{201d} — only if a bullet above backs it")
#skill("Communication", "e.g. \u{201c}wrote the team’s API documentation\u{201d} — same rule")
]

// ---------- Languages (spell out the boolean-search words: "bilingual") ----------
#section("Languages")[
Bilingual English / French (fluent)\u{2002}#box[#text(fill: ink)[·]\u{2002}Third] language (native)
]
