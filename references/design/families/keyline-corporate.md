## 5. keyline-corporate — contemporary corporate report · register: modern

*(Formerly `smallcaps-sober`, whose serif small caps read dated.)* The sober family for professional services, rebuilt in a current register: an accent keyline plus a soft section rule as the devices, an accent-labelled skills block, and a clean grotesque throughout.

- **Heading device**: an accent **keyline down the left of the title** — `box(inset: (left: 11pt), stroke: (left: 4pt + accent))[…]`, which hugs the title's own height exactly, PLUS a `soft` horizontal rule across each section boundary (`line(length: 100%, stroke: 0.6pt + soft)`). The rule is what separates sections; the keyline marks the title and is invisible to a horizontal boundary scan. Title case 13pt bold `dark`.
- **Skills block**: the **label itself carries the accent** (bold accent label, then the items in `dark`) — no colon, no separator glyph, no rule. Nobody else colours the skills label.
- **Accent role**: the heading keylines, the skills labels, and the dates. Headings, roles and organizations stay `dark`.
- **Icons**: **line** style, accent, in the contact column; platform marks in the accent too.
- **Header**: name 24pt bold on its own row, then one grid ROW: role line left, 2-line contact block right-aligned (column = natural width, max 55% of the measure; no photo is wired — a photo would sit at the right end of the name row), closed by a `soft` hairline. The contact lines start below the name, never beside it.
- **Type**: a clean grotesque; weight and size do the contrast, no second typeface needed. Pool: `pick_design.py` FONTS `keyline-corporate`.
- **Accents** (analogous harmony): `#33475b` slate · `#1f3a5f` navy · `#0f4c5c` petrol · `#5b2a5e` plum (bronze `#6e4a1f` dropped — muddy-hue veto).
- **Verified**: leading `0.544em`, spacing `0.624em`, list spacing `0.698em`, section `above` 16.5pt (20.5pt airy), 5pt after the title (4.6:1) → 1 page, fill 96%, white-run ratio 4.17 (resume.typ) / 9.33 (resume-pair-b.typ: the median intra-section run is only 3px, so the boundary rule carries it and the ratio reads high).
- Markets: law, finance, consulting, public sector, DACH. Safe for conservative. Photo: yes.
