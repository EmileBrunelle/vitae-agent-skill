// FAMILY: avant-poster — constructivist poster, two-ink discipline
// REGISTER: creative (never in the default pool — design.md § The creative
// register: unlocked by a creative target field or an explicit request, capped
// back out by a conservative market).
// ---------- Shared mechanics (templates/lib.typ) ----------
// Devices below stay this family's own; only the verified MECHANICS come from
// the lib (entry emission order, extraction-safe skills row, unbreakable
// mark+value box, platform marks, generic icon sets, specialities line).
#import "lib.typ": *
#let accent = rgb("#b3261e")    // hue A — the bleeding bars (masthead + sections)
#let accent2 = rgb("#1f3a5f")   // hue B — the diagonal, the dividers, markers, icons
// DUOTONE family (design.md § Duotone). The constructivist poster is a
// TWO-INK medium by construction — one colour plus black — which is also why
// this family survives a grayscale photocopy: both hues are deep, and nothing
// on the page encodes information in the difference between them.
#let pal = derive(accent)
#let soft = pal.soft
#let ink = pal.ink
#let muted = ink
#let dark = pal.dark
#let bodyf = ("Public Sans", "Fira Sans", "Noto Sans")
#let dispf = ("Big Shoulders Display", "Chivo", "Noto Sans")

// Solid icon style: filled, angular — flat geometric shapes only, hue B.
#let ic-col = accent2
#let ic = icons-solid(ic-col)
#let mk = marks(ic-col)

// GABARIT: mid — 1.8cm margins, 10.5pt body. The margin is what the bars bleed
// into, so it has to be real. Fill target derives from the 1.6cm bottom margin:
// (100 - 5.7) - 0..2%.
#let mx = 1.8cm
#set page(paper: "us-letter", margin: (x: mx, top: 1.3cm, bottom: 1.6cm))
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.503em, spacing: 0.593em)

// DEVICE: a heavy hue-A BAR THAT BLEEDS OFF THE LEFT PAGE EDGE and stops at the
// section title, with the title set on the bar's OWN LINE, to its right. Not a
// rule above the title (swiss-grid), not a kicker over it (editorial-serif),
// not an underline below it (bold-display), not a keyline hugging its height
// (keyline-corporate), not a fill behind it (color-band): the bar is beside the
// title, on its baseline, and it runs off the page. Nobody else lets a device
// leave the text block.
//
// The bleed is a `place`d rect at dx: -mx — `place` takes no flow space and
// emits no text, so the bar costs nothing in the layout and nothing in the
// extraction.
#let section(t, body, airy: false) = block(width: 100%, breakable: false,
  above: if airy { 20pt } else { 15pt }, below: 0pt)[
  #box(width: 100%, height: 13pt)[
    #place(horizon + left, dx: -mx,
      rect(width: mx + 30pt, height: 5pt, fill: accent))
    #place(horizon + left, dx: 38pt,
      text(font: dispf, size: 12.5pt, weight: "bold", fill: dark)[#upper(t)])
  ]
  #v(6pt)
  #body
]

// dates right-flush in hue B; the organization line under the entry anchors the
// date in the extraction (ats.md, orphaned-date trap)
#let job(role, org, dates, note) = entry(role, org, dates, note,
  role-st: it => text(font: dispf, size: 11.5pt, weight: "bold", it),
  date-st: it => text(size: 9pt, fill: accent2, weight: "bold", it),
  note-st: it => text(fill: muted, it))

// skills: the label in hue A, then a drawn hue-B DIVIDER BAR (a box: emits no
// text), then the items. The divider is the same flat-bar vocabulary as the
// section device, one notch down — a poster repeats its own shapes at
// different scales instead of inventing a second language.
#let skill(cat, items) = srow(
  [#text(font: dispf, weight: "bold", fill: accent)[#cat]
   #box(width: 1.5pt, height: 8pt, baseline: 1pt, fill: accent2)], items)

// List marker: a filled hue-B CIRCLE, drawn (emits no text). The only circular
// marker of the roster — a constructivist page is bars and circles.
#set list(marker: box(width: 3.4pt, height: 3.4pt, baseline: -0.6pt,
    circle(radius: 1.7pt, fill: accent2)),
  indent: 10pt, spacing: 0.45em, body-indent: 7pt)

// HEADER: A MASTHEAD BAR COMPOSITION. A full-bleed hue-A bar across the top of
// page 1, the name oversized under it, a rotated hue-B bar placed top-right
// (the constructivist diagonal — the one place this family allows an angle,
// because a diagonal in the text block would fight the single column), the role
// line, the specialities line, then the contacts.
//
// Both bars are `place`d, so they land on page 1 only: a page `background`
// would repeat them on page 2 (verified on color-band).
#place(top + left, dx: -mx, dy: -1.3cm,
  rect(width: 100% + 2 * mx, height: 0.5cm, fill: accent))
// The diagonal sits BELOW the masthead bar and fully inside the page: placed
// over it, the two shapes collide at the trim edge and read as an accident
// rather than a decision (looked at, not guessed).
#block(above: 0pt, below: 11pt)[
  #text(font: dispf, size: 30pt, weight: "bold")[Firstname Lastname]
  #v(-6pt)
  #text(size: 10.5pt, weight: "medium", fill: accent2)[Backend Software Developer — B.Sc. in Computer Science]
  #v(-1pt)
  // SPECIALITIES LINE — the 5-7 mastered skills, in the display face, hue A,
  // bar-separated. NO `tracking`: letterspacing extracts as "N E X T" and stops
  // matching. Each item boxed, so none can break across a line end. Every item
  // is CONTENT: SKILL.md rule 2 applies to it in the most prominent position on
  // the page.
  #text(font: dispf, size: 9pt, weight: "bold", fill: accent)[#specline(
    ("PYTHON", "DJANGO", "POSTGRESQL", "TYPESCRIPT", "REACT", "DOCKER", "CI/CD"),
    sep: [ \/ ])]
  #v(1pt)
  #text(size: 9pt, fill: muted)[
    #nb(ic.pin)[City, Region] #h(8pt)
    #nb(ic.tel)[#link("tel:+15555550100")[(555) 555-0100]] #h(8pt)
    #nb(mk.mail)[#link("mailto:me@example.com")[me\@example.com]] #h(8pt)
    #nb(mk.li)[#link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]] #h(8pt)
    #nb(mk.gh)[#link("https://github.com/handle")[github.com/handle]]]
]

// SECTION ORDER (this family's default): the narrative-led skeleton — profile,
// then the full chronology, then EDUCATION BEFORE SKILLS, with the skills row
// block near the end. The specialities line in the header already carries the
// stack for the 30-second scan, so the detailed skills block does not need to
// come first. A target market's own convention wins over this default
// (references/regional.md).

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
#section("Education")[
#job("Degree Name (Abbrev.)", "Institution", "2015 – 2019",
  "City · anchor unproven-but-real skills here (statistics-heavy coursework, thesis on distributed systems)")
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
#section("Working Style")[
#skill("Label", "evidence drawn from the CV itself, never a bare adjective")
#skill("Mentoring", "e.g. \u{201c}onboarded two junior developers\u{201d} — only if a bullet above backs it")
]

// ---------- Languages (spell out the boolean-search words: "bilingual") ----------
#section("Languages")[
Bilingual English / French (fluent)\u{2002}#box[#text(fill: accent2)[\/]\u{2002}Third] language (native)
]
