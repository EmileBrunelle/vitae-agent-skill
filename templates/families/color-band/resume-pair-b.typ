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
// Real brand/platform marks, drawn from Font Awesome Free 6.7.2 path data —
// Icons: CC BY 4.0 (https://fontawesome.com/license/free), Copyright Fonticons,
// Inc. The path data is INLINED as an SVG string: the document stays one
// self-contained file, the mark is vector (it emits NO text — verified in the
// extraction at the gate), and its colour is a parameter, not baked in.
// A platform logo is a functional identifier, not decoration, so EVERY family
// carries these; the families that carry no generic icons by principle
// (swiss-grid, humanist-quiet, margin-index) still carry no pin/phone icon.
#let pmark(d, vb, c, h: 7pt) = box(baseline: 0.5pt, image(
  bytes("<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"" + vb
    + "\"><path fill=\"" + c.to-hex() + "\" d=\"" + d + "\"/></svg>"),
  format: "svg", height: h))
#let li-path = "M100.28 448H7.4V148.9h92.88zM53.79 108.1C24.09 108.1 0 83.5 0 53.8a53.79 53.79 0 0 1 107.58 0c0 29.7-24.1 54.3-53.79 54.3zM447.9 448h-92.68V302.4c0-34.7-.7-79.2-48.29-79.2-48.29 0-55.69 37.7-55.69 76.7V448h-92.78V148.9h89.08v40.8h1.3c12.4-23.5 42.69-48.3 87.88-48.3 94 0 111.28 61.9 111.28 142.3V448z"
#let li-vb = "0 0 448 512"
#let gh-path = "M165.9 397.4c0 2-2.3 3.6-5.2 3.6-3.3.3-5.6-1.3-5.6-3.6 0-2 2.3-3.6 5.2-3.6 3-.3 5.6 1.3 5.6 3.6zm-31.1-4.5c-.7 2 1.3 4.3 4.3 4.9 2.6 1 5.6 0 6.2-2s-1.3-4.3-4.3-5.2c-2.6-.7-5.5.3-6.2 2.3zm44.2-1.7c-2.9.7-4.9 2.6-4.6 4.9.3 2 2.9 3.3 5.9 2.6 2.9-.7 4.9-2.6 4.6-4.6-.3-1.9-3-3.2-5.9-2.9zM244.8 8C106.1 8 0 113.3 0 252c0 110.9 69.8 205.8 169.5 239.2 12.8 2.3 17.3-5.6 17.3-12.1 0-6.2-.3-40.4-.3-61.4 0 0-70 15-84.7-29.8 0 0-11.4-29.1-27.8-36.6 0 0-22.9-15.7 1.6-15.4 0 0 24.9 2 38.6 25.8 21.9 38.6 58.6 27.5 72.9 20.9 2.3-16 8.8-27.1 16-33.7-55.9-6.2-112.3-14.3-112.3-110.5 0-27.5 7.6-41.3 23.6-58.9-2.6-6.5-11.1-33.3 2.6-67.9 20.9-6.5 69 27 69 27 20-5.6 41.5-8.5 62.8-8.5s42.8 2.9 62.8 8.5c0 0 48.1-33.6 69-27 13.7 34.7 5.2 61.4 2.6 67.9 16 17.7 25.8 31.5 25.8 58.9 0 96.5-58.9 104.2-114.8 110.5 9.2 7.9 17 22.9 17 46.4 0 33.7-.3 75.4-.3 83.6 0 6.5 4.6 14.4 17.3 12.1C428.2 457.8 496 362.9 496 252 496 113.3 383.5 8 244.8 8zM97.2 352.9c-1.3 1-1 3.3.7 5.2 1.6 1.6 3.9 2.3 5.2 1 1.3-1 1-3.3-.7-5.2-1.6-1.6-3.9-2.3-5.2-1zm-10.8-8.1c-.7 1.3.3 2.9 2.3 3.9 1.6 1 3.6.7 4.3-.7.7-1.3-.3-2.9-2.3-3.9-2-.6-3.6-.3-4.3.7zm32.4 35.6c-1.6 1.3-1 4.3 1.3 6.2 2.3 2.3 5.2 2.6 6.5 1 1.3-1.3.7-4.3-1.3-6.2-2.2-2.3-5.2-2.6-6.5-1zm-11.4-14.7c-1.6 1-1.6 3.6 0 5.9 1.6 2.3 4.3 3.3 5.6 2.3 1.6-1.3 1.6-3.9 0-6.2-1.4-2.3-4-3.3-5.6-2z"
#let gh-vb = "0 0 496 512"
#let mail-path = "M48 64C21.5 64 0 85.5 0 112c0 15.1 7.1 29.3 19.2 38.4L236.8 313.6c11.4 8.5 27 8.5 38.4 0L492.8 150.4c12.1-9.1 19.2-23.3 19.2-38.4c0-26.5-21.5-48-48-48L48 64zM0 176L0 384c0 35.3 28.7 64 64 64l384 0c35.3 0 64-28.7 64-64l0-208L294.4 339.2c-22.8 17.1-54 17.1-76.8 0L0 176z"
#let mail-vb = "0 0 512 512"
#let web-path = "M352 256c0 22.2-1.2 43.6-3.3 64l-185.3 0c-2.2-20.4-3.3-41.8-3.3-64s1.2-43.6 3.3-64l185.3 0c2.2 20.4 3.3 41.8 3.3 64zm28.8-64l123.1 0c5.3 20.5 8.1 41.9 8.1 64s-2.8 43.5-8.1 64l-123.1 0c2.1-20.6 3.2-42 3.2-64s-1.1-43.4-3.2-64zm112.6-32l-116.7 0c-10-63.9-29.8-117.4-55.3-151.6c78.3 20.7 142 77.5 171.9 151.6zm-149.1 0l-176.6 0c6.1-36.4 15.5-68.6 27-94.7c10.5-23.6 22.2-40.7 33.5-51.5C239.4 3.2 248.7 0 256 0s16.6 3.2 27.8 13.8c11.3 10.8 23 27.9 33.5 51.5c11.6 26 20.9 58.2 27 94.7zm-209 0L18.6 160C48.6 85.9 112.2 29.1 190.6 8.4C165.1 42.6 145.3 96.1 135.3 160zM8.1 192l123.1 0c-2.1 20.6-3.2 42-3.2 64s1.1 43.4 3.2 64L8.1 320C2.8 299.5 0 278.1 0 256s2.8-43.5 8.1-64zM194.7 446.6c-11.6-26-20.9-58.2-27-94.6l176.6 0c-6.1 36.4-15.5 68.6-27 94.6c-10.5 23.6-22.2 40.7-33.5 51.5C272.6 508.8 263.3 512 256 512s-16.6-3.2-27.8-13.8c-11.3-10.8-23-27.9-33.5-51.5zM135.3 352c10 63.9 29.8 117.4 55.3 151.6C112.2 482.9 48.6 426.1 18.6 352l116.7 0zm358.1 0c-30 74.1-93.6 130.9-171.9 151.6c25.5-34.2 45.2-87.7 55.3-151.6l116.7 0z"
#let web-vb = "0 0 512 512"
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
