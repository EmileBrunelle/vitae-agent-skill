## 6. bold-display — geometric display, heavy contrast · register: modern

Avant-Garde-lineage display type: oversized geometric caps, big weight jumps, colour spent on the name.

- **Heading device**: 13pt UPPERCASE `dark` display title over a **2.5pt accent underline as wide as the title itself** — `box(inset: (bottom: 3pt), stroke: (bottom: 2.5pt + accent))[…]`. A `line(length: 100%)` inside a box resolves to the *available* width and silently reproduces the banned full-width rule (verified) — use the box stroke.
- **Skills block**: bold title-case label, a 12pt gap, then the items — no colon, no dash, no punctuation; weight and space do the separating.
- **Accent role** (DUOTONE, see core.md § Duotone): hue **A** is spent on the name (29pt) and nothing else; hue **B** carries the heading underlines, the list markers and the icons. Everything else `dark`/`ink`.
- **Icons**: **solid** style, hue **B**, on the contact lines — platform marks in hue B too.
- **Header**: oversized accent name left, role line below, contacts on two left-aligned lines with wide `#h(9pt)` gaps instead of separators.
- **Type**: a geometric display face for the name over a neutral sans body. With URW Gothic, `weight: "bold"` maps to URW Gothic Demi — verified rendering, not a fallback. Pool: `pick_design.py` FONTS `bold-display`.
- **Accents** (complementary harmony). Validated A→B pairs (hue B = the opposite hue, one notch calmer, contrast in brackets), never mixed across rows: `#8c3b00` rust → `#105a90` steel (7.3) · `#0e6862` teal → `#72191f` oxblood (11.2) · `#3b3486` indigo → `#7d3312` sienna (8.9 — olive `#4e512a` was dropped, its hue 65° sits inside the muddy band) · `#b3261e` red → `#1a6265` petrol (7.1).
- **Verified**: leading `0.536em`, spacing `0.616em`, section `above` 14pt (19pt airy), 6pt after the title (2.3:1) → 1 page, fill 94%, white-run ratio 3.60 (1.8% of page height). Its heavy underline carries the boundary, which is why it clears the floor on so little white. Default labels: Profile / Technical Stack / Core Strengths.
- Markets: tech, product, design-adjacent, startups. Not for conservative markets. Photo: no.
