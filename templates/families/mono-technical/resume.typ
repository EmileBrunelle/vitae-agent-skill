// FAMILY: mono-technical — technical-documentation / spec-sheet aesthetic
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, unbreakable
// mark+value box, platform marks, generic icon sets).
#import "lib.typ": *
// DUOTONE family: two harmonised hues, each with its own job.
#let accent = rgb("#1f3a5f")    // hue A — STRUCTURE: heading marks, chip keylines
#let accent2 = rgb("#8f2d3f")   // hue B — DATA: dates, list markers, icons
#let pal = derive(accent)
#let soft = pal.soft
#let wash = color.mix((accent, 8%), (white, 92%))
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
// pool pair 1 of 2 verified at the gate: local faces first so the compile is
// warning-free (`typst fonts` check, references/design.md § font pools)
#let bodyf = ("Noto Sans", "Liberation Sans")
#let monof = ("Source Code Pro", "Adwaita Mono", "Noto Sans Mono")
#let dispf = monof

// ---------- Contact icons: vector only, no text emitted ----------
// Line style in hue B — the data hue, the same one that carries the dates.
#let ic-col = accent2
#let ic = icons-line(ic-col)
#let mk = marks(ic-col)

#set page(paper: "us-letter", margin: (x: 1.6cm, top: 1.25cm, bottom: 1.2cm))
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.651em, spacing: 0.771em)

// device: a filled hue-A square, then the title in the MONO face. No rules.
#let section(t, body, airy: false) = block(breakable: false,
  above: if airy { 25pt } else { 20pt }, below: 0pt)[
  #box(width: 6pt, height: 6pt, fill: accent, baseline: 0pt)
  #box(width: 3pt, height: 6pt, fill: accent2, baseline: 0pt)
  #h(5pt)
  #text(font: dispf, size: 11.5pt, weight: "bold", fill: dark)[#t]
  #v(4pt)
  #body
]

// dates in the MONO face, hue B, right-flush (tabular alignment is this
// family's signature); the organization line under the entry anchors the date
// in the extraction (ats.md, orphaned-date trap).
#let job(role, org, dates, note) = entry(role, org, dates, note,
  date-st: it => text(font: dispf, size: 8.5pt, fill: accent2, weight: "medium", it),
  note-st: it => text(fill: muted, it))

// skills: a spec-sheet KEY = VALUE row — mono key in hue A, the "=" in hue B,
// values in the body sans. Verified alternative to inline "chips": one box per
// item SCATTERS in pdftotext (each box becomes its own text cluster and the
// items interleave across rows) — see references/ats.md.
#let skill(cat, items) = srow([#text(font: dispf, size: 8.5pt, weight: "bold", fill: accent)[#upper(cat)] #text(font: dispf, size: 8.5pt, fill: accent2)[=]], items)

#set list(marker: box(width: 3pt, height: 3pt, fill: accent2, baseline: -0.5pt),
  indent: 10pt, spacing: 0.45em, body-indent: 7pt)

// header: name, role, then the contacts on ONE mono line (spec-sheet footer)
#block(above: 0pt, below: 12pt)[
  #text(size: 22pt, weight: "bold")[Firstname Lastname]
  #v(-4pt)
  #text(size: 10.5pt, weight: "medium")[Backend Software Developer — B.Sc. in Computer Science]
  #v(-2pt)
  #text(font: dispf, size: 8.5pt, fill: muted)[
    #nb(ic.pin)[City, Region] #h(6pt) #nb(ic.tel)[#link("tel:+15555550100")[(555) 555-0100]]
    #h(6pt) #nb(mk.mail)[#link("mailto:me@example.com")[me\@example.com]] #h(6pt)
    #nb(mk.li)[#link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]] #h(6pt)
    #nb(mk.gh)[#link("https://github.com/handle")[github.com/handle]]]
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

// ---------- Education: same entry shape as the jobs (dates right-flush) ----------
#section("Education")[
#job("Degree Name (Abbrev.)", "Institution", "2015 – 2019",
  "City · relevant coursework noted · institution glossed for readers, capstone in applied distributed systems")
]

// ---------- Skills: 5-7 linear rows, every keyword defensible ----------
#section("Technical Stack")[
#skill("Languages", "Python, TypeScript, SQL, JavaScript, Bash")
#skill("Backend & data", "Django, PostgreSQL, REST APIs, message queues")
#skill("Frontend", "React, accessibility-minded interface work")
#skill("Tools", "Git (version control), Docker")
#skill("Cloud & CI", "AWS (EC2 and S3), continuous integration (CI/CD: GitHub Actions)")
#skill("Software quality", "unit and integration testing, test plans, code review")
#skill("Methodologies", "Agile / Scrum, technical documentation")
]

// ---------- Soft skills: only with evidence drawn from this CV ----------
#section("Working Style")[
#par[#text(font: dispf, size: 8.5pt, weight: "bold", fill: accent)[LABEL] #h(2pt) evidence drawn from the CV itself, never a bare adjective]
#par[#text(font: dispf, size: 8.5pt, weight: "bold", fill: accent)[MENTORING] #h(2pt) e.g. \u{201c}onboarded two junior developers\u{201d} — only if a bullet above backs it]
#par[#text(font: dispf, size: 8.5pt, weight: "bold", fill: accent)[COMMUNICATION] #h(2pt) e.g. \u{201c}wrote the team’s API documentation\u{201d} — same rule]
]

// ---------- Languages (spell out the boolean-search words: "bilingual") ----------
#section("Languages")[
Bilingual English / French (fluent)\u{2002}#box[#text(fill: accent2)[·]\u{2002}Third] language (native)
]
