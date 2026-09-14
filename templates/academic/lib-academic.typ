// vitae-academic — shared MECHANICS for the academic-CV genre.
// Import with `#import "lib-academic.typ": *`.
//
// This is a SIBLING of templates/lib.typ, not a modification of it: lib.typ
// is imported by all 14 industry families (some by symlink) and is
// off-limits (see its own header, "Ne pas le modifier"). The academic genre
// needs different mechanics anyway — the entry shape is YEAR-FIRST here
// (industry's `entry` in lib.typ is role-first, date flush right), there are
// no icons/photos/palette (design is an explicit anti-goal for this genre),
// and the running head goes through real page `header:`/`footer:` (the
// ats.md ban on header/footer content does not apply: there is no ATS
// parsing an academic dossier). So this file does not import lib.typ at all
// — nothing in it is reusable without re-introducing a shape this genre
// deliberately drops.
//
// Two invariants every entry in this file exists to guarantee, because the
// gate (built separately, reading the companion TOML) checks them by exact
// string match on `pdftotext -layout` output, never by rendering geometry:
//   B. antechronology — the year token is the first thing on the entry's
//      line, so the extracted line order IS the year order.
//   D. no entry straddles a page break — every entry is one
//      `block(breakable: false)`, so a break can only fall BETWEEN entries.

// ------------------------------------------------------------ section shell
// asection — heading + hairline, glued to the FIRST entry in one unbreakable
// block so a heading can never sit alone at the bottom of a page (check C:
// a title is always followed by at least one entry's worth of lines on the
// same page). Remaining entries flow normally after, each already
// unbreakable on its own via `aentry`/`apub`. `entries` is an array of
// already-built entry content (never raw data) — call site decides order.
#let asection(title, entries, above: 14pt) = {
  if entries.len() == 0 { return }
  block(breakable: false, above: above, below: 2pt)[
    #text(size: 12pt, weight: "bold")[#upper(title)]
    #v(2pt)
    #line(length: 100%, stroke: 0.6pt + luma(150))
    #v(4pt)
    #entries.at(0)
  ]
  for e in entries.slice(1) { e }
}

// ------------------------------------------------------------------ entries
// aentry — the ONE academic entry mechanic. Emission order is fixed and is
// the whole point of this function: YEAR (left column) then BODY (right),
// same grid row, so the year is always the first token `pdftotext -layout`
// emits for that line (check B and D depend on this). `year` takes any
// content, not just a number: an undated-prefix item passes a status string
// ("submitted", "forthcoming") instead of a year — the TOML's declared
// undated-prefix length is what tells the gate to skip those lines rather
// than fail check B on them.
//
// `block(breakable: false)` is non-negotiable per the design note (check D):
// never lift it to fix an orphan — a short page tail is free here, there is
// no fill target in this genre (§3.4 of the design note).
#let aentry(year, body, above: 3pt, below: 3pt, year-w: 2.2cm,
            year-st: it => text(weight: "bold", it)) = block(
  breakable: false, above: above, below: below)[
  #grid(columns: (year-w, 1fr), column-gutter: 10pt,
    align: (left + top, left + top),
    year-st(year), body)
]

// apub — a publication entry: same year-first mechanic as `aentry`, with a
// bracketed running number folded into the BODY (never before the year —
// that would put a non-year token first and break check D). Pass numbers in
// descending order as you emit the list (most recent = highest number, the
// usual math/CS convention) for a contiguous, monotone sequence: check A's
// bonus verifies that `[n]` run is unbroken, which catches a swallowed or
// duplicated entry that a plain count would miss.
#let apub(n, year, body, ..args) = aentry(year,
  [#text(weight: "bold")[[#n]] #h(4pt) #body], ..args)

// ---------------------------------------------------------------- headings
// aheader — the 5-line general-information block (note §1.1: "la norme, pas
// une économie"). Plain text, no icons (harvest_icons.py does not apply to
// this genre), no photo. Exactly 5 lines, in this order: name; title +
// affiliation; address; email + website + ORCID; CV version date. Any of
// the optional fields (website, orcid) that is `none` is simply dropped from
// its line, never left as an empty separator.
#let aheader(name, title, affiliation, address, email, cv-date,
             website: none, orcid: none) = block(below: 12pt)[
  #text(size: 15pt, weight: "bold")[#name] \
  #title#if affiliation != none [, #affiliation] \
  #address \
  #email#if website != none [ · #website]#if orcid != none [ · ORCID: #orcid] \
  #text(size: 8.5pt, style: "italic")[CV updated #cv-date]
]

// ------------------------------------------------------------ running head
// Real page header/footer — deliberately, and unlike the industry genre.
// references/ats.md bans load-bearing header/footer content because many
// ATS parsers skip those regions; that ban is about ATS ingestion, and an
// academic dossier is never run through one (it is printed, stapled,
// photocopied, passed around a committee). `poppler`/pdftotext DOES extract
// header/footer regions, which is exactly what check E reads.
#let arunning-header(surname) = context {
  align(right, text(size: 8.5pt)[#surname])
}
#let arunning-footer() = context {
  let n = counter(page).get().first()
  let total = counter(page).final().first()
  align(center, text(size: 8.5pt)[#n / #total])
}
