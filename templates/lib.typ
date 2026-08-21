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
// Real brand/platform marks, from Font Awesome Free 6.7.2 path data —
// Icons: CC BY 4.0 (https://fontawesome.com/license/free), Copyright Fonticons,
// Inc. The path data is INLINED as an SVG string, so the document needs no
// assets dir, the mark is vector (it emits NO text — verified at the gate in
// every family) and its colour stays a PARAMETER instead of being baked into a
// file. A platform logo is a functional identifier of a contact channel, not
// ornament, so EVERY family carries these — including the three that carry no
// generic pin/phone icon by principle.
//
// Never an icon FONT: Font Awesome as a typeface leaks private-use codepoints
// into the extraction. Never emoji, never clipart.
//
// A mark at h: 7pt inside a 9pt line adds ~1pt of line height. On a page
// already at 96% fill that is enough to push the last unbreakable section over
// (measured) — re-run the fill loop after adding or resizing them.
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
#let phone-path = "M164.9 24.6c-7.7-18.6-28-28.5-47.4-23.2l-88 24C11.7 30.2 0 46 0 64C0 296.5 192.7 496 424 496c17.5 0 33.8-11.9 39.3-30.3l24-88c5.3-19.4-4.6-39.7-23.2-47.4l-96-40c-16.3-6.8-35.2-2.1-46.3 11.6l-40.6 49.5c-52.9-25.8-95.8-68.7-121.6-121.6l49.5-40.6c13.7-11.1 18.4-30 11.6-46.3l-40-96z"
#let phone-vb = "0 0 512 512"
#let pin-path = "M215.7 499.2C267 435 384 279.4 384 192C384 86 298 0 192 0S0 86 0 192c0 87.4 117 243 168.3 307.2c12.3 15.3 35.1 15.3 47.4 0zM192 128a64 64 0 1 1 0 128 64 64 0 1 1 0-128z"
#let pin-vb = "0 0 384 512"

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
