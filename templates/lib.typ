// vitae — shared MECHANICS. Import with `#import "lib.typ": *`.
//
// WHAT BELONGS HERE and what does not is the whole point of this file:
//
//   MECHANICS live here — the constructs whose *correctness* was verified once
//   and must never be re-derived: the emission order that keeps a date from
//   floating to the end of the extraction, the one-paragraph skills row, the
//   unbreakable mark+value box, the platform marks as inline SVG, the
//   single-ROW alignment grid. Each one is a verified answer to a trap in
//   references/ats.md. Re-implementing one per family is how a fixed trap
//   comes back.
//
//   DEVICES DO NOT live here — section heading devices, header composition,
//   glyphs, colour roles, the *shape* of the skills row, the fonts. Those are
//   the property of each design family (references/design.md § Design
//   families). Mutualising them rebuilds the attractor this whole system
//   exists to break: every CV out of the skill would look like the same CV.
//   A primitive here therefore never chooses a colour, a size or a face — it
//   takes them as parameters, or takes already-styled content.
//
// The hand-off is TWO files: the .typ and this lib.typ beside it (Typst has no
// bundler). Ship both, or inline this file into the .typ before delivering.

// ---------------------------------------------------------------- geometry
// hrow — the single-ROW alignment grid. Safe for extraction (references/ats.md:
// the ban is on multi-ROW data grids); the right cell is also the photo slot in
// every family whose header has one. Used by `entry` and by header blocks.
#let hrow(a, b, cols: (1fr, auto), gutter: 14pt,
          align-cells: (left + bottom, right + bottom),
          above: auto, below: auto) = block(above: above, below: below,
  grid(columns: cols, column-gutter: gutter, align: align-cells, a, b))

// photo — a header photo, cropped to a box. Vector/raster image, emits no
// text. Only families whose header has a right-hand cell take one, and only
// where the target market expects one (references/regional.md).
#let photo(path, w: 2.6cm, radius: 0pt) = box(clip: true, radius: radius,
  image(path, width: w))

// nb — an unbreakable mark+value pair. The `~` is the non-breaking space: the
// mark can never be orphaned at a line end, and the box keeps the pair from
// being split. Every icon/logo beside a contact value goes through this.
#let nb(mark, value) = box[#mark~#value]

// ---------------------------------------------------------------- entries
// entry — the ONE experience/education entry mechanic, and the only place the
// emission order is decided:
//
//     role (left)  →  date (right, same grid ROW)  →  org + descriptor line
//
// Both verified conditions of the orphaned-date trap live in that order
// (references/ats.md): (a) a line of text comes AFTER the date in the emission
// order — the org/descriptor line below; (b) the caller passes a date run as
// WIDE as the others on the page ("2015 – 2019", never a bare "2019"). Never
// reorder the three, and never un-align a date to fix an extraction problem:
// one date convention per document.
//
// EDUCATION USES THIS SAME HELPER. A separate education shape is what put one
// date mid-line while every other date was flush right; that workaround is
// retired.
//
// Styling is injected as `it => …` functions so the family owns every visual
// decision (which element carries the accent, the sizes, the faces) while the
// order and the grid stay here. Defaults reproduce the neutral entry.
#let entry(role, org, dates, note,
           role-st: it => text(size: 11pt, weight: "bold", it),
           date-st: it => text(size: 9pt, weight: "bold", it),
           org-st: it => text(weight: "semibold", it),
           note-st: it => it,
           sep: [ — ], meta-size: 9pt, gap: 1.5pt,
           above: 6pt, below: 3pt) = block(
  above: above, below: below, sticky: true)[
  #grid(columns: (1fr, auto), align: (left + bottom, right + bottom),
    role-st(role), date-st(dates))
  #v(gap)
  #text(size: meta-size)[#org-st(org)#if note != none [#note-st([#sep#note])]]
]

// srow — the extraction-safe skills row: ONE paragraph per category, the label
// immediately followed by its items in the emission order. Verified failure
// modes this exists to avoid (references/ats.md): a multi-row grid extracts
// column-by-column and orphans every label; a fixed-width `#box` label column
// fuses label with values when the label fills it and wraps-then-interleaves
// when it doesn't; one `box(fill: …)` per item (the "chip" look) makes every
// box its own text cluster and the items interleave across rows.
//
// `label` is ALREADY-STYLED content — the shape of the row is the family's
// second clone marker and is never decided here. The three mechanical variants:
//   default        run-in: label and items on one flowing paragraph
//   brk: true      two-line: label alone on its line, items under it
//   hang: <len>    wrapped lines align under the label (bulleted rows)
// `above`/`below` given => the row becomes a block (needed for the two-line
// shape); left at `none` it stays a bare `par` and keeps par spacing.
#let srow(label, items, hang: 0pt, brk: false, above: none, below: none) = {
  let body = if brk { [#label \ #items] } else { [#label #items] }
  if above == none and below == none {
    par(hanging-indent: hang, body)
  } else {
    block(above: if above == none { auto } else { above },
          below: if below == none { auto } else { below },
      par(hanging-indent: hang, body))
  }
}

// specline — the SPECIALITIES LINE: the 5-7 mastered skills, set under the
// name/title in the header, before the profile. Two independent real CVs
// converged on this device; what it buys is that the 30-second scan gets the
// stack before it gets the prose, and retailoring per application becomes one
// line to edit.
//
// It is a FAMILY TRAIT, never universal — a device on all thirteen families is
// a new fingerprint for the tool, which is the opposite of the point. Only the
// families whose recipe declares it carry one, and each styles it its own way
// (case, separator, colour).
//
// It is CONTENT, not decoration: SKILL.md rule 2 applies to every item on it —
// a skill on the specialities line with no experience bullet behind it is
// keyword stuffing in the most prominent position on the page.
//
// The mechanics: emitted linearly, NO `tracking` (letterspacing extracts as
// "N E X T" and breaks the line for a keyword filter), and each item boxed so
// it can never be split across a line end. A separator run that WRAPS can
// scatter in extraction (references/ats.md) — keep it to one line: 5-7 short
// items, verified in the extraction at the gate.
#let specline(items, sep: [ · ], st: it => it) = st(items
  .map(i => box[#i])
  .join(sep))

// chip — a PAINTED chip: a tint drawn BEHIND a run of text that stays inside
// the paragraph's own text flow. This is the extraction-safe way to get the
// tinted-pill look, and the difference from the banned version is the whole
// point:
//
//   box(fill: …) per item  →  every box becomes its own text cluster.
//     Reproduced on a dense real page (mono-technical's skills block):
//       LANGUAGES = Python / TypeScript SQL JavaScript Bash /
//       BACKEND & DATA = Django / FRONTEND = React / PostgreSQL REST APIs …
//     — labels torn from their values, items interleaved across rows. BANNED.
//
//   highlight(fill: …) per item  →  the tint is painted behind the SAME run,
//     no new box, one cluster. Same page, same density, same chips:
//       LANGUAGES = Python, TypeScript, SQL, JavaScript, Bash
//       BACKEND & DATA = Django, PostgreSQL, REST APIs, message queues
//     — byte-identical to the plain linear row. VERIFIED SAFE.
//
// Two conditions come with the proof:
//  (a) keep the SEPARATORS OUTSIDE the tint (`.map(chip).join([, ])`). Without
//      them the words still extract, but the item boundaries are gone and a
//      keyword filter reads one long run.
//  (b) a chipped multi-word token that WRAPS still splits ("… CI/CD: GitHub" /
//      "Actions)") — the ordinary wrap rule, so wrap fragile tokens in
//      `#box[…]` exactly as anywhere else.
//
// It is a CREATIVE-register device, not a default: a chipped skills block is
// loud, and a family that already has a strong heading device does not need it.
// `radius` is a passthrough, not a design decision: a family that paints a RUN
// of segments needs one corner value for all of them at once (gutter-rail's
// square/pill variant is exactly that value), and the alternative — hand-rolling
// `highlight` inside the family — is how the banned `box(fill:)` gets
// reintroduced later by whoever next widens that gap.
#let chip(body, fill: none, extent: 2.5pt, radius: 0pt) = highlight(
  fill: fill, extent: extent, radius: radius, body)

// earlyline — the condensed "Early career" line: one role per line, no
// bullets, for the roles past the detailed decade of a long career. Harvested
// as a real convention (it protects the reader's attention budget rather than
// decorating). The mechanic that matters: the ROLE comes first and the years
// come last IN THE SAME PARAGRAPH, so there is always text before the date and
// the orphaned-date trap cannot fire — unlike a bullet-less grid entry.
#let earlyline(role, org, years, sep: [ · ], year-st: it => it) = par[
  #text(weight: "semibold")[#role]#sep#org#sep#year-st(years)]

// runhead — the running head for page 2+: the candidate's name and the page
// number, repeated at the top of the page. Harvested from academic-CV
// convention. It goes in the FLOW, immediately after the `#pagebreak()`, and
// NEVER in a page `header:` field — many parsers skip the header/footer
// regions entirely, so anything load-bearing put there is a bug, not a device.
#let runhead(name, n, total, st: it => text(size: 8.5pt, it)) = block(
  above: 0pt, below: 10pt,
  st[#name #h(1fr) #n / #total])

// ------------------------------------------------------- generic icons
// Contact icons drawn from Typst primitives — no external files, and they emit
// NO text (verified in every family's extraction). Two styles, each belonging
// to a family's register; a family may also carry NONE, which is itself the
// style choice (references/design.md § Contact icons). Both take the colour as
// a parameter: the icon colour is part of the family's accent budget.
//
// `icons-line(c)` — 0.9pt stroke, rounded. Returns (pin, tel, mail, web).
#let icons-line(c) = {
  let s = 0.9pt + c
  (
    pin: box(baseline: 1.4pt, width: 6pt, height: 7.4pt)[
      #place(top + center, circle(radius: 2.5pt, stroke: s))
      #place(bottom + center, polygon(fill: c, (0pt, 0pt), (3.6pt, 0pt), (1.8pt, 3pt)))],
    tel: box(baseline: 1.4pt, width: 6pt, height: 7.4pt)[
      #place(horizon + center, rect(width: 4.4pt, height: 7.4pt, radius: 1.2pt, stroke: s))
      #place(bottom + center, dy: -0.9pt, line(length: 2pt, stroke: 0.8pt + c))],
    mail: box(baseline: 1.4pt, width: 8pt, height: 7.4pt)[
      #place(horizon + center, rect(width: 8pt, height: 5.8pt, radius: 0.6pt, stroke: s))
      #place(horizon + center, dy: -1.1pt, polygon(stroke: s, (0pt, 0pt), (4pt, 2.6pt), (8pt, 0pt)))],
    web: box(baseline: 1.4pt, width: 7.4pt, height: 7.4pt)[
      #place(horizon + center, circle(radius: 3.6pt, stroke: s))
      #place(horizon + center, line(length: 7.2pt, stroke: 0.8pt + c))
      #place(horizon + center, ellipse(width: 3.4pt, height: 7.2pt, stroke: 0.8pt + c))],
  )
}

// `icons-solid(c, bg: …)` — filled, angular. `bg` is the knockout colour the
// inner detail is cut in: `white` on a white page, the band colour when the
// icons sit reversed out inside a filled band.
#let icons-solid(c, bg: white) = (
  pin: box(baseline: 1.4pt, width: 6pt, height: 7.4pt)[
    #place(top + center, circle(radius: 2.6pt, fill: c))
    #place(bottom + center, polygon(fill: c, (0pt, 0pt), (4pt, 0pt), (2pt, 3.4pt)))],
  tel: box(baseline: 1.4pt, width: 6pt, height: 7.4pt)[
    #place(horizon + center, rect(width: 4.6pt, height: 7.6pt, fill: c))
    #place(bottom + center, dy: -1pt, rect(width: 2.4pt, height: 0.9pt, fill: bg))],
  mail: box(baseline: 1.4pt, width: 8pt, height: 7.4pt)[
    #place(horizon + center, rect(width: 8pt, height: 6pt, fill: c))
    #place(horizon + center, dy: -1.2pt, polygon(stroke: 1pt + bg, (0pt, 0pt), (4pt, 2.8pt), (8pt, 0pt)))],
  web: box(baseline: 1.4pt, width: 7.6pt, height: 7.4pt)[
    #place(horizon + center, circle(radius: 3.7pt, fill: c))
    #place(horizon + center, line(length: 7.4pt, stroke: 0.9pt + bg))
    #place(horizon + center, ellipse(width: 3.6pt, height: 7.4pt, stroke: 0.9pt + bg))],
)

// ------------------------------------------------------- platform marks
// Real brand/platform marks, as inline SVG path data sourced via Iconify from
// their upstream icon sets (paths taken verbatim from each project's GitHub
// repo, not from memory):
//   li (LinkedIn): Simple Icons v13.19.0 path — CC0 1.0, no attribution
//     required. LinkedIn's mark was withdrawn from Simple Icons afterwards
//     over brand-guideline enforcement, not a licence change; the path used
//     here is the last one the project published under CC0
//     (github.com/simple-icons/simple-icons, tag 13.19.0).
//   gh (GitHub): Simple Icons, current — CC0 1.0, no attribution required
//     (github.com/simple-icons/simple-icons).
//   mail, web, phone, pin: Tabler Icons, "filled" set — MIT, © Paweł Kuna
//     (github.com/tabler/tabler-icons). mail and web are multiple non-
//     overlapping filled subpaths concatenated into one `d` (same visual
//     result as the separate `<path>` elements upstream, one `image` call).
// The path data is INLINED as an SVG string, so the document needs no assets
// dir, the mark is vector (it emits NO text — verified at the gate in every
// family) and its colour stays a PARAMETER instead of being baked into a
// file. A platform logo is a functional identifier of a contact channel, not
// ornament, so EVERY family carries these — including the three that carry no
// generic pin/phone icon by principle.
//
// Never an icon FONT: an icon typeface leaks private-use codepoints into the
// extraction. Never emoji, never clipart.
//
// Every mark below shares a 24x24 viewBox; `pmark` scales by `height` only,
// so each renders at the same height regardless of its own aspect ratio — no
// per-family rescaling needed when swapping icon sets.
//
// A mark at h: 7pt inside a 9pt line adds ~1pt of line height. On a page
// already at 96% fill that is enough to push the last unbreakable section over
// (measured) — re-run the fill loop after adding or resizing them.
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
#let phone-path = "M9 3a1 1 0 0 1 .877 .519l.051 .11l2 5a1 1 0 0 1 -.313 1.16l-.1 .068l-1.674 1.004l.063 .103a10 10 0 0 0 3.132 3.132l.102 .062l1.005 -1.672a1 1 0 0 1 1.113 -.453l.115 .039l5 2a1 1 0 0 1 .622 .807l.007 .121v4c0 1.657 -1.343 3 -3.06 2.998c-8.579 -.521 -15.418 -7.36 -15.94 -15.998a3 3 0 0 1 2.824 -2.995l.176 -.005h4z"
#let phone-vb = "0 0 24 24"
#let pin-path = "M18.364 4.636a9 9 0 0 1 .203 12.519l-.203 .21l-4.243 4.242a3 3 0 0 1 -4.097 .135l-.144 -.135l-4.244 -4.243a9 9 0 0 1 12.728 -12.728zm-6.364 3.364a3 3 0 1 0 0 6a3 3 0 0 0 0 -6"
#let pin-vb = "0 0 24 24"

// One call per family: `#let mk = marks(ic-col)` then `nb(mk.li, [..])`.
#let marks(c, h: 7pt) = (
  mail: pmark(mail-path, mail-vb, c, h: h),
  li: pmark(li-path, li-vb, c, h: h),
  gh: pmark(gh-path, gh-vb, c, h: h),
  web: pmark(web-path, web-vb, c, h: h),
  phone: pmark(phone-path, phone-vb, c, h: h),
  pin: pmark(pin-path, pin-vb, c, h: h),
)

// ------------------------------------------------------- palette derivation
// The harmonised mini-palette: an accent never travels alone. A pure neutral
// gray beside a warm accent reads as a mismatch, so the grays are biased
// toward the accent hue — 15% is enough to harmonise and invisible as "a
// colour". Contrast of every derived role was validated across the curated
// gamuts (ink 6.5-7.1:1 on white, dark 16.7-17.2:1).
// `soft` is DECORATIVE ONLY: never set text in it.
// scripts/gen_palette.py generates and validates palettes beyond the gamuts.
#let derive(accent) = (
  soft: color.mix((accent, 40%), (white, 60%)),
  ink: color.mix((luma(95), 85%), (accent, 15%)),
  dark: color.mix((luma(25), 92%), (accent, 8%)),
)
