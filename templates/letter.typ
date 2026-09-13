// vitae letter template — one letter per job posting, never a generic one.
// Fill from the SAME cv.typ already generated for this posting: accent, font
// and the name/contact trio are copied, never retyped (SKILL.md, letter
// doctrine). Verify: python3 scripts/verify_letter.py letter.typ EMPLOYER "JOB TITLE"
//
// Visual coherence with the CV is a REDUCED letterhead, not a copy of the CV
// header: a one-page letter has no vertical budget for a full CV header.
//   - name ~14pt, in the CV's font
//   - contact info on ONE line of text (email · phone · city · LinkedIn), no icons
//   - one thin rule in the CV's accent colour
//   - ~2.5cm total
// Body: 11pt, ~1.4 line-height, blank line between paragraphs, no indent.
// No ornament, no columns, no icons anywhere in the letter.
//
// HAND-OFF IS TWO FILES, exactly like a CV: this .typ and lib.typ beside it —
// same hand-off convention as templates/resume.typ. A letter is prose, not
// entries/skills rows, so it draws nothing from lib.typ's mechanics today;
// the import stays so a letter dropped into a delivery folder behaves like
// every other .typ in this skill (same two-file dependency, same
// harvest_icons.py no-op if ever run there).
#import "lib.typ": *

// ---------- Tokens — copied from this posting's cv.typ, never re-derived ----------
#let accent = rgb("#7d2231")
#let font = ("Carlito", "Noto Sans", "Liberation Sans")
#let name = "Firstname Lastname"
#let contact = "me@example.com · (555) 555-0100 · City, Region · linkedin.com/in/handle"

// ---------- Letterhead (~2.5cm) ----------
#set page(paper: "us-letter", margin: (x: 2.7cm, top: 2.2cm, bottom: 2.2cm))
#set text(font: font, size: 11pt, lang: "en", hyphenate: false)
#set par(justify: false, leading: 0.68em, spacing: 1em)

#block(below: 14pt)[
  #text(size: 14pt, weight: "bold")[#name]
  #v(2pt)
  #text(size: 9.5pt, fill: luma(90))[#contact]
  #v(6pt)
  #line(length: 100%, stroke: 0.8pt + accent)
]

// ---------- Corps ----------
#text(size: 10.5pt)[September 13, 2026]
#v(10pt)

#text(size: 10.5pt)[
  Hiring Manager \
  Employer Name \
  Employer Address
]
#v(10pt)

#text(weight: "bold")[Re: Application for the Backend Software Developer position]
#v(10pt)

Dear Hiring Manager,

Paragraph 1 — why this employer specifically: a fact about their product,
mission or team drawn from the posting or public sources, tied to what draws
the candidate to apply here and not to a generic opening elsewhere.

Paragraph 2 — two or three proofs, each one a fact already on the CV /
`FAITS.md`, matched explicitly to a requirement named in the posting. Never a
claim that is not already verified for the CV.

Paragraph 3 — availability and a closing line inviting next steps, no
salary figure unless the posting asked for one.

#v(10pt)
Sincerely, \
#name
