// FAMILY: swiss-grid — International Typographic Style — TWO-PAGE version
// ---------------------------------------------------------------------------
// This is the worked 2-page counterpart of resume.typ in this directory, built
// by following that file's own "2-page version recipe" comment block to the
// letter. It exists because "1-page and 2-page versions" is half of what this
// skill claims to do, and a claim nothing exercises is a claim nobody checked.
//
// Gate (both pages measured, from this directory):
//     python3 ../../../scripts/verify.py resume-2page.typ 2 94 96
//
// What makes this two pages rather than one is CONTENT, not air: a third
// on-target role, 3-4 bullets per role instead of 2-3, a highlights block under
// the Profile, evidence lines in Strengths, and the two sections a 1-page
// version has to drop entirely (Selected Projects, Certifications). The
// anti-filler clause (SKILL.md rule 5) is the whole point — if the material for
// this does not exist, the honest deliverable is the 1-page version, not this
// one padded.
//
// Measured while building it, because the numbers are the argument — fill of
// page 1 / page 2 for each candidate break position:
//     after Software Development Experience -> 67% / 77%   (both starved)
//     after Other Professional Experience   -> 82% / 62%
//     after Education                       -> 95% / 49%   <- chosen
// Page 2's 49% was then fixed by adding REAL sections, NOT by opening the
// leading: the leading that would have carried 49% to 95% was 1.12em against
// page 1's 0.665em, and a page whose rhythm is visibly double its neighbour's
// is exactly the air rule 5 forbids. Final rhythm 0.665em / 0.900em — page 2
// airier per recipe step 4, without reading as a different document.
// Two structured Strengths rows wrapped at the first passing configuration.
// They were SHORTENED (line integrity is a VISUAL check the gate cannot see,
// SKILL.md step 6) and the 4 points of fill that cost were bought back with two
// more one-line rows — again content, not leading.
// ---------- Shared mechanics (templates/lib.typ) ----------
#import "lib.typ": *
#let accent = rgb("#b3261e")
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("Nimbus Sans", "Liberation Sans", "Noto Sans")
#let dispf = bodyf

// this family carries no generic icons by principle — the
// platform marks are identifiers, not ornament (design.md).
#let ic-col = dark
#let mk = marks(ic-col)

#set page(paper: "us-letter", margin: (x: 1.5cm, top: 1.2cm, bottom: 1.2cm))
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.665em, spacing: 0.725em)

// device: heavy accent rule ABOVE the title, full width; nothing below
#let section(t, body, airy: false) = block(breakable: false,
  above: if airy { 18pt } else { 13pt }, below: 0pt)[
  #line(length: 100%, stroke: 2.5pt + accent)
  #v(4pt)
  #text(font: dispf, size: 12.5pt, weight: "bold", fill: dark)[#t]
  #v(6pt)
  #body
]

#let job(role, org, dates, note) = entry(role, org, dates, note,
  date-st: it => text(size: 9pt, fill: muted, weight: "bold", it),
  note-st: it => text(fill: muted, it))

// skills: small uppercase run-in label (no tracking), then the items
#let skill(cat, items) = srow(text(size: 8.5pt, weight: "bold")[#upper(cat)], items)

#set list(marker: text(fill: dark, weight: "bold")[▪], indent: 10pt,
  spacing: 0.45em, body-indent: 6pt)

// header: ONE grid row — name/role left, contact column right (photo slot = right cell)
#block(above: 0pt, below: 11pt)[
  #grid(columns: (1fr, auto), column-gutter: 14pt, align: (left + bottom, right + bottom),
    [#text(font: dispf, size: 24pt, weight: "bold")[Firstname Lastname] \
     #v(-3pt)
     #text(size: 10.5pt, weight: "medium")[Backend Software Developer — B.Sc. in Computer Science]],
    text(size: 9pt, fill: muted)[#nb(mk.pin)[City, Region] \
      #nb(mk.phone)[#link("tel:+15555550100")[(555) 555-0100]] \
      #nb(mk.mail)[#link("mailto:me@example.com")[me\@example.com]] \
      #nb(mk.li)[#link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]] \
      #nb(mk.gh)[#link("https://github.com/handle")[github.com/handle]]],
  )
]

// ---------- Profile ----------
#section("Profile")[
Role and degree in one clause, then the strongest verifiable fact (X years
shipping production code at A, B, C). One sentence covering the stack with
2-3 bolded keywords (*Python/Django*, *TypeScript*, #box[*CI/CD*] — box keeps
fragile tokens unbroken). One closing trait sentence, no clichés
("seeking opportunities…" is dead weight).

// recipe step 1: the highlights block — 2 LINEAR lines, never a grid (a grid
// extracts column-first and scrambles the reading order: ats.md).
#v(3pt)
#text(size: 9.5pt)[
  – Scope claim that a bullet below proves #h(14pt) – Second scope claim, same rule \
  – Stack claim naming the two load-bearing technologies #h(14pt) – Ownership claim
]
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
- Fourth bullet is where the 2-page version earns its second page: the detail
  a 1-page cut would drop, not a restatement of the three above.

#job("Earlier Role", "Employer 2", "Jul 2021 – Feb 2024",
  "City · descriptor · full-time, on-site")
- Month+year date ranges always — year-only breaks ATS duration math.
- One strong keyword bolded per bullet, two at most — a wall of bold is none.
- Migration, integration or refactor work stated as scope and constraint, with
  the technology named once (*PostgreSQL*) and no invented percentage.
- Cross-team work described by what it produced (a documented interface, a
  runbook), never as "excellent communication skills".

#job("First Role in the Field", "Employer 3", "Aug 2020 – Jun 2021",
  "City · descriptor · full-time, on-site")
- The role that starts the on-target run: the tense goes past, the verbs stay
  contribution verbs, the scope stays small and true.
- One bullet on the tooling learned in anger (*Docker*, CI) — a first job's
  honest value is what it taught, stated as work done and not as a course list.
]

// ---------- Off-target roles: separated, honest, never leading ----------
#section("Other Professional Experience")[
#job("Off-Target Earlier Role", "Employer 4", "Sep 2019 – Jun 2021",
  "City · descriptor · part-time alongside studies")
- Keep 1-2 transferable bullets; the section label does the explaining.
- Second bullet only where the transfer is real (a reporting tool built, a
  process documented) — the section exists to be honest about the gap years,
  not to re-argue them into the target field.
]

// ---------- Education: the SAME entry shape as the jobs (dates right-flush) ----------
// The institution+descriptor line under the entry is what keeps the date from
// being orphaned at the end of the extraction (verified: ats.md date trap).
// The bullet under the entry is load-bearing for the SAME reason: a bullet-less
// grid entry at a page boundary re-orders its date to the end of the page's
// extraction stream (verify.py catches exactly this).
#section("Education")[
#job("Degree Name (Abbrev.)", "Institution", "2015 – 2019",
  "City · relevant coursework noted · institution glossed for readers")
- Coursework worth naming only where it anchors a skill claimed above
  (statistics, algorithms, databases) — never the full transcript.
]

// ---------------------------------------------------------------------------
// recipe step 3: the page break is DELIBERATE and sits at the section boundary
// that leaves page 1 fullest — after the on-target experience run here. Never
// left to auto-flow: auto-flow picks a different boundary the moment a single
// bullet changes length, and then the page assignment is not reproducible.
// It also has to leave page 2 a real page's worth of content: this break put
// only Skills/Strengths/Languages on page 2 at first and measured 49% fill,
// which is the 2-page version failing its own rule 5 rather than passing it —
// hence the two extra sections below.
#pagebreak()

// The running head goes in the FLOW, right after the break — never in a page
// `header:` field, which many parsers skip entirely (lib.typ § runhead).
#runhead[Firstname Lastname — Backend Software Developer][2][2]

// recipe step 4: #set text / #set par are document-GLOBAL, so page 2 is
// re-balanced locally here rather than by loosening the whole document. Page 2
// carries the shorter sections, so it gets the airier rhythm and the `airy`
// section spacing; page 1 keeps the tighter one. Both pages are measured, and
// NOTE for the tuner: `verify.py --tune` edits only the FIRST par declaration
// and measures only the LAST page, so a two-declaration file like this one is
// balanced by hand — tune page 1 with the 1-page file, then set the second
// declaration here until page 2 lands in the same target.
#set par(justify: false, leading: 0.900em, spacing: 1.000em)

// ---------- Selected Projects: the section a 1-page version cannot afford ----------
// This is the honest reason a CV goes to two pages: named, verifiable work that
// does not fit. It uses the SAME entry helper as the jobs, so the date lands in
// the same place and the extraction order stays identical — a projects section
// with its own bespoke shape is a second date convention (SKILL.md step 6).
#section("Selected Projects", airy: true)[
#job("Project Name", "open source · 40+ stars", "2024",
  "what it does in one clause · *Python*, *PostgreSQL* · link in the header")
- One bullet on the problem it solves, one on the part that was hard. A project
  with no stated difficulty reads as a tutorial follow-along.

#job("Second Project", "internal tool, released with permission", "2023",
  "what it does in one clause · *TypeScript*, *React*")
- Scope and users ("used by the four-person support team"), never a star count
  standing in for adoption.
- One line on what it was built with and what it replaced — a tool that
  replaced a spreadsheet is a stronger claim than one that replaced nothing.
]

// ---------- Skills: 5-7 linear rows, every keyword defensible ----------
#section("Technical Skills", airy: true)[
#skill("Languages", "Python, TypeScript, SQL, JavaScript, Bash")
#skill("Backend & data", "Django, PostgreSQL, REST APIs, message queues, Redis")
#skill("Frontend", "React, accessibility-minded interface work")
#skill("Tools & DevOps", "Git (version control), Docker, AWS (EC2, S3), continuous integration (CI/CD: GitHub Actions)")
#skill("Software quality", "unit and integration testing, test plans, code review")
#skill("Methodologies", "Agile / Scrum, technical documentation, incident review")
#skill("Observability", "structured logging, metrics dashboards, alert triage")
]

// ---------- Soft skills: only with evidence drawn from this CV ----------
// The 2-page version states the evidence inline ("Label — evidence"), which is
// the form the 1-page version has to compress away.
#section("Strengths", airy: true)[
#skill("Mentoring", "onboarded two junior developers — the Current Role bullet above is the evidence")
#skill("Communication", "wrote and maintained the team’s API documentation, cited in the Earlier Role bullets")
#skill("Ownership", "carried the migration named above from proposal through to the post-deploy review")
#skill("Debugging", "the incident-review line in Methodologies is where this was learned, not a claim on its own")
#skill("Code review", "reviewed the payments service daily for two years — the Earlier Role bullets record it")
#skill("Documentation", "the runbook named in the Earlier Role bullets — written once, kept current")
]

// ---------- Certifications & professional development ----------
// Dated like everything else, and only where the certificate is real and
// current — an expired cloud badge listed undated is a liability in interview.
#section("Certifications & Professional Development", airy: true)[
#skill("Certification", "Issuing Body — earned 2024, valid to 2027 (credential ID on request)")
#skill("Course", "named course with the institution and the year, only where it backs a skill row above")
#skill("Community", "the talk given or the meetup organised, with the year — evidence for Communication above")
#skill("In progress", "a certification actually being studied for, with the sitting date — never a wish list")
]

// ---------- Languages (spell out the boolean-search words: "bilingual") ----------
// Levels stated, per the recipe — the 1-page version drops them to one line.
#section("Languages", airy: true)[
Bilingual English / French #h(8pt)#text(fill: accent)[•]#h(8pt) English (fluent) #h(8pt)#text(fill: accent)[•]#h(8pt) French (native) #h(8pt)#text(fill: accent)[•]#h(8pt) Third language (intermediate)
]
