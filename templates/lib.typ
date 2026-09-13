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
//   li (LinkedIn), gh (GitHub): Bootstrap Icons 13.21.0 — MIT, no
//     attribution required (github.com/twbs/icons).
//     LinkedIn's mark is served but flagged `hidden` upstream: it was
//     withdrawn over brand-guideline enforcement, NOT a licence change, so
//     the MIT grant on the published path is irrevocable. Consequence:
//     that one mark no longer tracks LinkedIn's logo and may be purged from
//     the set — the refresh below prints a NOTE when it happens.
// Refreshing these is a COMMAND, not an edit to this file: when a brand
// changes its mark, run
//     python3 scripts/harvest_icons.py bi li=linkedin,gh=github \
//         --update templates/lib.typ
// which rewrites the pairs below in place from the live Iconify API, then
// look at the render — a new path can shift the mark's optical weight at 7pt
// even when the licence and the gate are unchanged. The data stays INLINE
// because Typst makes no network request at compile time and the deliverable
// must build on typst.app with no assets directory.
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

#let li-path = "M0 1.146C0 .513.526 0 1.175 0h13.65C15.474 0 16 .513 16 1.146v13.708c0 .633-.526 1.146-1.175 1.146H1.175C.526 16 0 15.487 0 14.854zm4.943 12.248V6.169H2.542v7.225zm-1.2-8.212c.837 0 1.358-.554 1.358-1.248c-.015-.709-.52-1.248-1.342-1.248S2.4 3.226 2.4 3.934c0 .694.521 1.248 1.327 1.248zm4.908 8.212V9.359c0-.216.016-.432.08-.586c.173-.431.568-.878 1.232-.878c.869 0 1.216.662 1.216 1.634v3.865h2.401V9.25c0-2.22-1.184-3.252-2.764-3.252c-1.274 0-1.845.7-2.165 1.193v.025h-.016l.016-.025V6.169h-2.4c.03.678 0 7.225 0 7.225z"
#let li-vb = "0 0 16 16"
#let gh-path = "M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59c.4.07.55-.17.55-.38c0-.19-.01-.82-.01-1.49c-2.01.37-2.53-.49-2.69-.94c-.09-.23-.48-.94-.82-1.13c-.28-.15-.68-.52-.01-.53c.63-.01 1.08.58 1.23.82c.72 1.21 1.87.87 2.33.66c.07-.52.28-.87.51-1.07c-1.78-.2-3.64-.89-3.64-3.95c0-.87.31-1.59.82-2.15c-.08-.2-.36-1.02.08-2.12c0 0 .67-.21 2.2.82c.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82c.44 1.1.16 1.92.08 2.12c.51.56.82 1.27.82 2.15c0 3.07-1.87 3.75-3.65 3.95c.29.25.54.73.54 1.48c0 1.07-.01 1.93-.01 2.2c0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8"
#let gh-vb = "0 0 16 16"
#let mail-path = "M22 7.535v9.465a3 3 0 0 1 -2.824 2.995l-.176 .005h-14a3 3 0 0 1 -2.995 -2.824l-.005 -.176v-9.465l9.445 6.297l.116 .066a1 1 0 0 0 .878 0l.116 -.066l9.445 -6.297z M19 4c1.08 0 2.027 .57 2.555 1.427l-9.555 6.37l-9.555 -6.37a2.999 2.999 0 0 1 2.354 -1.42l.201 -.007h14z"
#let mail-vb = "0 0 24 24"
#let web-path = "M21.165 16a10 10 0 0 1 -8.434 5.973a1 1 0 0 0 .617 -.444a18 18 0 0 0 2.28 -5.528z M8.372 16a18 18 0 0 0 2.28 5.53a1 1 0 0 0 .616 .443a10 10 0 0 1 -8.433 -5.973z M13.57 16a16 16 0 0 1 -1.57 3.884a16 16 0 0 1 -1.57 -3.884 M8.034 10a18 18 0 0 0 0 4h-5.832a10 10 0 0 1 -.002 -4z M13.952 10a16 16 0 0 1 0 4h-3.904a16 16 0 0 1 0 -4z M21.8 10a10.05 10.05 0 0 1 -.002 4h-5.832c.149 -1.329 .149 -2.67 0 -4z M11.267 2.027a1 1 0 0 0 -.615 .444a18 18 0 0 0 -2.28 5.529h-5.54a10.01 10.01 0 0 1 8.334 -5.967z M12 4.116a16 16 0 0 1 1.57 3.885h-3.14c.34 -1.317 .85 -2.6 1.53 -3.817z M12.733 2.026a10.01 10.01 0 0 1 8.435 5.974h-5.54a18 18 0 0 0 -2.28 -5.53a1 1 0 0 0 -.517 -.414z"
#let web-vb = "0 0 24 24"
#let phone-path = "M9 3a1 1 0 0 1 .877 .519l.051 .11l2 5a1 1 0 0 1 -.313 1.16l-.1 .068l-1.674 1.004l.063 .103a10 10 0 0 0 3.132 3.132l.102 .062l1.005 -1.672a1 1 0 0 1 1.113 -.453l.115 .039l5 2a1 1 0 0 1 .622 .807l.007 .121v4c0 1.657 -1.343 3 -3.06 2.998c-8.579 -.521 -15.418 -7.36 -15.94 -15.998a3 3 0 0 1 2.824 -2.995l.176 -.005h4z"
#let phone-vb = "0 0 24 24"
#let pin-path = "M18.364 4.636a9 9 0 0 1 .203 12.519l-.203 .21l-4.243 4.242a3 3 0 0 1 -4.097 .135l-.144 -.135l-4.244 -4.243a9 9 0 0 1 12.728 -12.728zm-6.364 3.364a3 3 0 1 0 0 6a3 3 0 0 0 0 -6"
#let pin-vb = "0 0 24 24"

// ---- Alternative mark sets for mail/web/phone/pin (drawn per candidate by
// scripts/pick_design.py so the small glyphs stop being a shared fingerprint;
// LinkedIn/GitHub stay Bootstrap Icons in every set — a brand logo is a
// functional identifier, not a style). Harvested at authoring time with
// scripts/harvest_icons.py from the Iconify API — the same data the npm icon
// packages publish. Inline is the preferred form (keeps the hand-off at two
// files); an assets dir shipped alongside is an acceptable alternative.
// Phosphor — MIT (https://github.com/phosphor-icons/core/blob/main/LICENSE)
// harvested via Iconify API (https://api.iconify.design), set version 2.1.1 — same data as the npm package
#let ph-envelope_simple_fill-body = "<path fill=\"currentColor\" d=\"M224 48H32a8 8 0 0 0-8 8v136a16 16 0 0 0 16 16h176a16 16 0 0 0 16-16V56a8 8 0 0 0-8-8m-8 144H40V74.19l82.59 75.71a8 8 0 0 0 10.82 0L216 74.19z\"/>"
#let ph-envelope_simple_fill-vb = "0 0 256 256"
#let ph-globe_fill-body = "<path fill=\"currentColor\" d=\"M128 24a104 104 0 1 0 104 104A104.12 104.12 0 0 0 128 24m78.36 64h-35.65a135.3 135.3 0 0 0-22.3-45.6A88.29 88.29 0 0 1 206.37 88Zm9.64 40a87.6 87.6 0 0 1-3.33 24h-38.51a157.4 157.4 0 0 0 0-48h38.51a87.6 87.6 0 0 1 3.33 24m-88-85a115.3 115.3 0 0 1 26 45h-52a115.1 115.1 0 0 1 26-45m-26 125h52a115.1 115.1 0 0 1-26 45a115.3 115.3 0 0 1-26-45m-3.9-16a140.8 140.8 0 0 1 0-48h59.88a140.8 140.8 0 0 1 0 48Zm50.35 61.6a135.3 135.3 0 0 0 22.3-45.6h35.66a88.29 88.29 0 0 1-58 45.6Z\"/>"
#let ph-globe_fill-vb = "0 0 256 256"
#let ph-phone_fill-body = "<path fill=\"currentColor\" d=\"M231.88 175.08A56.26 56.26 0 0 1 176 224C96.6 224 32 159.4 32 80a56.26 56.26 0 0 1 48.92-55.88a16 16 0 0 1 16.62 9.52l21.12 47.15v.12A16 16 0 0 1 117.39 96c-.18.27-.37.52-.57.77L96 121.45c7.49 15.22 23.41 31 38.83 38.51l24.34-20.71a8 8 0 0 1 .75-.56a16 16 0 0 1 15.17-1.4l.13.06l47.11 21.11a16 16 0 0 1 9.55 16.62\"/>"
#let ph-phone_fill-vb = "0 0 256 256"
#let ph-map_pin_fill-body = "<path fill=\"currentColor\" d=\"M128 16a88.1 88.1 0 0 0-88 88c0 75.3 80 132.17 83.41 134.55a8 8 0 0 0 9.18 0C136 236.17 216 179.3 216 104a88.1 88.1 0 0 0-88-88m0 56a32 32 0 1 1-32 32a32 32 0 0 1 32-32\"/>"
#let ph-map_pin_fill-vb = "0 0 256 256"
// Bootstrap Icons — MIT (https://github.com/twbs/icons/blob/main/LICENSE.md)
// harvested via Iconify API (https://api.iconify.design), set version 1.13.1 — same data as the npm package
#let bi-envelope_fill-body = "<path fill=\"currentColor\" d=\"M.05 3.555A2 2 0 0 1 2 2h12a2 2 0 0 1 1.95 1.555L8 8.414zM0 4.697v7.104l5.803-3.558zM6.761 8.83l-6.57 4.027A2 2 0 0 0 2 14h12a2 2 0 0 0 1.808-1.144l-6.57-4.027L8 9.586zm3.436-.586L16 11.801V4.697z\"/>"
#let bi-envelope_fill-vb = "0 0 16 16"
#let bi-globe-body = "<path fill=\"currentColor\" d=\"M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8m7.5-6.923c-.67.204-1.335.82-1.887 1.855A8 8 0 0 0 5.145 4H7.5zM4.09 4a9.3 9.3 0 0 1 .64-1.539a7 7 0 0 1 .597-.933A7.03 7.03 0 0 0 2.255 4zm-.582 3.5c.03-.877.138-1.718.312-2.5H1.674a7 7 0 0 0-.656 2.5zM4.847 5a12.5 12.5 0 0 0-.338 2.5H7.5V5zM8.5 5v2.5h2.99a12.5 12.5 0 0 0-.337-2.5zM4.51 8.5a12.5 12.5 0 0 0 .337 2.5H7.5V8.5zm3.99 0V11h2.653c.187-.765.306-1.608.338-2.5zM5.145 12q.208.58.468 1.068c.552 1.035 1.218 1.65 1.887 1.855V12zm.182 2.472a7 7 0 0 1-.597-.933A9.3 9.3 0 0 1 4.09 12H2.255a7 7 0 0 0 3.072 2.472M3.82 11a13.7 13.7 0 0 1-.312-2.5h-2.49c.062.89.291 1.733.656 2.5zm6.853 3.472A7 7 0 0 0 13.745 12H11.91a9.3 9.3 0 0 1-.64 1.539a7 7 0 0 1-.597.933M8.5 12v2.923c.67-.204 1.335-.82 1.887-1.855q.26-.487.468-1.068zm3.68-1h2.146c.365-.767.594-1.61.656-2.5h-2.49a13.7 13.7 0 0 1-.312 2.5m2.802-3.5a7 7 0 0 0-.656-2.5H12.18c.174.782.282 1.623.312 2.5zM11.27 2.461c.247.464.462.98.64 1.539h1.835a7 7 0 0 0-3.072-2.472c.218.284.418.598.597.933M10.855 4a8 8 0 0 0-.468-1.068C9.835 1.897 9.17 1.282 8.5 1.077V4z\"/>"
#let bi-globe-vb = "0 0 16 16"
#let bi-telephone_fill-body = "<path fill=\"currentColor\" fill-rule=\"evenodd\" d=\"M1.885.511a1.745 1.745 0 0 1 2.61.163L6.29 2.98c.329.423.445.974.315 1.494l-.547 2.19a.68.68 0 0 0 .178.643l2.457 2.457a.68.68 0 0 0 .644.178l2.189-.547a1.75 1.75 0 0 1 1.494.315l2.306 1.794c.829.645.905 1.87.163 2.611l-1.034 1.034c-.74.74-1.846 1.065-2.877.702a18.6 18.6 0 0 1-7.01-4.42a18.6 18.6 0 0 1-4.42-7.009c-.362-1.03-.037-2.137.703-2.877z\"/>"
#let bi-telephone_fill-vb = "0 0 16 16"
#let bi-geo_alt_fill-body = "<path fill=\"currentColor\" d=\"M8 16s6-5.686 6-10A6 6 0 0 0 2 6c0 4.314 6 10 6 10m0-7a3 3 0 1 1 0-6a3 3 0 0 1 0 6\"/>"
#let bi-geo_alt_fill-vb = "0 0 16 16"

// pmarkb — like pmark, but for a harvested INNER SVG body (may hold several
// elements); colours it by substituting currentColor. Emits no text.
#let pmarkb(body, vb, c, h: 7pt) = box(baseline: 0.5pt, image(
  bytes("<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"" + vb
    + "\">" + body.replace("currentColor", c.to-hex()) + "</svg>"),
  format: "svg", height: h))

// One call per family: `#let mk = marks(ic-col)` then `nb(mk.li, [..])`.
#let marks(c, h: 7pt, kit: "tabler") = {
  let brand = (li: pmark(li-path, li-vb, c, h: h), gh: pmark(gh-path, gh-vb, c, h: h))
  if kit == "phosphor" {
    (mail: pmarkb(ph-envelope_simple_fill-body, ph-envelope_simple_fill-vb, c, h: h),
     web: pmarkb(ph-globe_fill-body, ph-globe_fill-vb, c, h: h),
     phone: pmarkb(ph-phone_fill-body, ph-phone_fill-vb, c, h: h),
     pin: pmarkb(ph-map_pin_fill-body, ph-map_pin_fill-vb, c, h: h),
     ..brand)
  } else if kit == "bootstrap" {
    (mail: pmarkb(bi-envelope_fill-body, bi-envelope_fill-vb, c, h: h),
     web: pmarkb(bi-globe-body, bi-globe-vb, c, h: h),
     phone: pmarkb(bi-telephone_fill-body, bi-telephone_fill-vb, c, h: h),
     pin: pmarkb(bi-geo_alt_fill-body, bi-geo_alt_fill-vb, c, h: h),
     ..brand)
  } else {
    (mail: pmark(mail-path, mail-vb, c, h: h),
     web: pmark(web-path, web-vb, c, h: h),
     phone: pmark(phone-path, phone-vb, c, h: h),
     pin: pmark(pin-path, pin-vb, c, h: h),
     ..brand)
  }
}

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
