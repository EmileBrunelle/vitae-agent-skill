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
// Real brand/platform marks, as inline SVG path data via Iconify: LinkedIn
// and GitHub from Simple Icons (CC0 1.0, no attribution required — the
// LinkedIn path is tag 13.19.0, the last one published under CC0 before
// LinkedIn's own brand-guideline enforcement had it withdrawn), email/website
// from Tabler Icons' filled set (MIT, (c) Paweł Kuna). The path data is
// INLINED as an SVG string: the document stays one self-contained file, the
// mark is vector (it emits NO text — verified in the extraction at the
// gate), and its colour is a parameter, not baked in.
// A platform logo is a functional identifier, not decoration, so EVERY family
// carries these; the families that carry no generic icons by principle
// (swiss-grid, humanist-quiet, margin-index) still carry no pin/phone icon.
#let pmark(d, vb, c, h: 7pt) = box(baseline: 0.5pt, image(
  bytes("<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"" + vb
    + "\"><path fill=\"" + c.to-hex() + "\" d=\"" + d + "\"/></svg>"),
  format: "svg", height: h))
#let li-path = "M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"
#let li-vb = "0 0 24 24"
#let gh-path = "M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"
#let gh-vb = "0 0 24 24"
#let mail-path = "M22 7.535v9.465a3 3 0 0 1 -2.824 2.995l-.176 .005h-14a3 3 0 0 1 -2.995 -2.824l-.005 -.176v-9.465l9.445 6.297l.116 .066a1 1 0 0 0 .878 0l.116 -.066l9.445 -6.297z M19 4c1.08 0 2.027 .57 2.555 1.427l-9.555 6.37l-9.555 -6.37a2.999 2.999 0 0 1 2.354 -1.42l.201 -.007h14z"
#let mail-vb = "0 0 24 24"
#let web-path = "M21.165 16a10 10 0 0 1 -8.434 5.973a1 1 0 0 0 .617 -.444a18 18 0 0 0 2.28 -5.528z M8.372 16a18 18 0 0 0 2.28 5.53a1 1 0 0 0 .616 .443a10 10 0 0 1 -8.433 -5.973z M13.57 16a16 16 0 0 1 -1.57 3.884a16 16 0 0 1 -1.57 -3.884 M8.034 10a18 18 0 0 0 0 4h-5.832a10 10 0 0 1 -.002 -4z M13.952 10a16 16 0 0 1 0 4h-3.904a16 16 0 0 1 0 -4z M21.8 10a10.05 10.05 0 0 1 -.002 4h-5.832c.149 -1.329 .149 -2.67 0 -4z M11.267 2.027a1 1 0 0 0 -.615 .444a18 18 0 0 0 -2.28 5.529h-5.54a10.01 10.01 0 0 1 8.334 -5.967z M12 4.116a16 16 0 0 1 1.57 3.885h-3.14c.34 -1.317 .85 -2.6 1.53 -3.817z M12.733 2.026a10.01 10.01 0 0 1 8.435 5.974h-5.54a18 18 0 0 0 -2.28 -5.53a1 1 0 0 0 -.517 -.414z"
#let web-vb = "0 0 24 24"
// One helper per mark, in the family's icon colour (`ic-col`), and each
// mark+value pair goes inside a #box[…~…] so the mark can never be orphaned
// at a line end.
#let m-mail = pmark(mail-path, mail-vb, ic-col)
#let m-li = pmark(li-path, li-vb, ic-col)
#let m-gh = pmark(gh-path, gh-vb, ic-col)
#let m-web = pmark(web-path, web-vb, ic-col)

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
    #h(6pt) #box[#m-mail~#link("mailto:me@example.com")[me\@example.com]]
    #h(6pt) #box[#m-li~#link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]]
    #h(6pt) #box[#m-gh~#link("https://github.com/handle")[github.com/handle]]
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
