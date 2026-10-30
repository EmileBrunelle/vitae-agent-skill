# Step 4 — Traps that constrain drafting

Not enforced by a gate: avoid these while writing `cv.typ`.

- Multi-row data grids, and single lines of `•`-separated items that wrap,
  both scatter fragments in extraction → linear paragraphs / bulleted lists
  (`references/ats.md`).
- Letterspacing (`tracking`) on headings extracts as "S O F T WA R E" → none
  on ATS-read text; single-row alignment grids are safe, data grids are not.
- Typst markup (`#box`, `*bold*`) inside a helper's *string* argument renders
  literally → pass content in `[brackets]` when markup is needed.
- `#`, `$`, `[`, `]`, `~`, `@` in generated prose are Typst syntax → escape.
- Straight + curly apostrophes mixed (strings passed to helpers bypass smart
  quotes) → normalize to typographic ones everywhere.
- A fixed-width `#box` label column in the skills block fuses label with
  values in extraction when the label fills it, and wraps + interleaves when
  it doesn't (verified both ways) → use one of the family shapes. Any **box**
  around skills content breaks the same way — one `box(fill:…)` per item (the
  chip look) *and* a single `box(stroke:…)` around the label alone both tore
  the rows apart on a dense page. But a **painted** chip is safe: `highlight()`
  puts the tint behind the same text run, no new box, and the row extracts
  byte-identically to a plain linear row — keep the separators outside the tint
  (`references/ats.md`, the `chip()` function of lib.typ — call it, don't open the file). The failure does NOT
  reproduce on a short synthetic page: test extraction on the real one.
- A **single-ROW** alignment grid is safe only while each cell is ONE line: a
  cell stacking a label over its value made every label extract before every
  value. And a full-width row *under* a two-zone header gets its right end
  pulled into the other zone — poppler clusters by column before it reads by
  line (verified both, `references/ats.md`).
- Contact info, dates or an availability line placed in a page `header:` /
  `footer:` field: many parsers skip those regions outright. Keep everything
  load-bearing in the flow. Same verdict for a monogram rendered as an image,
  a QR code, and any skill/language meter drawn as a bar or a dot rating.
