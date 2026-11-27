## 1. swiss-grid — International Typographic Style · register: neutral

Müller-Brockmann / Helvetica school: flush-left, objective, structure carried by rules and size steps, never by colour on text.

- **Heading device**: 2.5pt accent rule **above** the title, full width, nothing below it. Title case, 12.5pt bold, `dark` — not accent.
- **Skills block**: small uppercase run-in label (8.5pt bold, **no tracking**), space, then the items — `LANGUAGES Python, TypeScript, …`. (A fixed-width label column was tried and rejected: at 70-82pt the labels either fuse with the values in extraction or wrap and interleave.)
- **Accent role**: the section rules only. No coloured text anywhere.
- **Icons**: the contact line is marked **all-or-nothing** (amended after a half-iconified line was found worse than either extreme: platform marks present but city/phone bare): every contact item carries a mark, city and phone included (`mk.pin` / `mk.phone`, added to `lib.typ` alongside the platform marks, same Tabler Icons provenance), all in the body ink, never in colour. No generic icon FONT and no colour on marks — that part of the original purism holds; only the "no mark on city/phone" half was the inconsistency.
- **Header**: name 24pt bold on its own row, then one grid ROW: role line left, 2-line contact block right-aligned (city · phone · email / LinkedIn · GitHub) — the contact lines start below the name's baseline, so no reader merges them with the name (column = natural width, max 55% of the measure; no photo is wired — a photo would sit at the right end of the name row).
- **Type**: one neo-grotesque for display *and* body. Pool (and provenance, and the fallback chain): `scripts/pick_design.py` FONTS `swiss-grid`.
- **Accents** (mono harmony): `#b3261e` swiss red · `#33475b` slate · `#0f4c5c` petrol.
- **Verified**: leading `0.490em`, spacing `0.550em`, list spacing `0.660em` (item gap above leading, 2026-11-26 rhythm fix), section `above` 14.5pt (19.5pt airy), 6pt after the title (2.2:1) → 1 page, fill 96%, white-run ratio 2.80 (tallest gap 1.5% of page height). Default labels: Profile / Technical Skills.
- Markets: any; safe for conservative. Photo: yes.
