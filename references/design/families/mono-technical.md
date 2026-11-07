## 9. mono-technical — technical-documentation aesthetic · register: modern

The spec-sheet / changelog current: monospace devices, tabular dates, high information density. Real and current, but **concentrated in software, engineering and data roles** — on a general-business or executive CV it reads as costume. Second duotone family, and the one where the two hues are most clearly split by job.

- **Heading device**: a 6pt filled **hue-A square** followed by a 3pt hue-B bar (a two-tone spec-sheet index mark), then the title in the **monospace** face, 11.5pt bold `dark`, title case. No rules anywhere. Monospace headings *look* letterspaced but carry no `tracking` — extraction verified clean (this is the one legal way to get that look).
- **Skills block**: a spec-sheet `KEY = VALUE` row — mono uppercase key in hue A, the `=` in hue B, the values in the body sans. **Verified failure on the way**: setting each item as an inline "chip" (`box` with a fill) scatters the block in `pdftotext` — every box becomes its own text cluster and items interleave across rows. Chips are banned everywhere, not only here ([`ats.md`](../../ats.md)).
- **Accent role** (DUOTONE): hue **A** = the heading squares and the skills keys; hue **B** = the dates, the list markers and the icons.
- **Icons**: **line** style in hue **B** — the same hue that carries the data, platform marks included.
- **List marker**: a 3pt filled hue-B **square drawn as a box**, not a glyph — the only family whose marker emits no character at all.
- **Header**: name, role line, then the contacts on ONE monospace line.
- **Type**: a document-grade monospace for every device + a neutral sans body. Pool: `pick_design.py` FONTS `mono-technical`.
- **Accents** (complementary harmony). Validated A→B pairs: `#1f3a5f` navy → `#8f2d3f` crimson (8.0) · `#33475b` slate → `#8a2f2a` brick (8.3) · `#0f4c5c` petrol → `#66291a` (11.1) · `#5b2a5e` plum → `#3c633a` (6.9). The first two replaced `#664e2d` and `#66513c`: a complemented navy lands on dull bronze, which is the muddiest thing this system can produce at 8.5pt.
- **Verified**: leading `0.651em`, spacing `0.771em`, section `above` 20pt (25pt airy), 4pt after the title (5.0:1) → 1 page, fill 94%, white-run ratio 4.00 (2.4% of page height).
- Markets: software, engineering, data, hardware, startups. Not for conservative markets, not for general business. Photo: no.
