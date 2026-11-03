## 3. color-band — reversed-out masthead · register: modern

Brand/editorial current: a solid colour field carries the identity, the body below is plain black-on-white.

- **Heading device**: heading reversed out **white on a solid accent bar** (full text-width block, `inset: (x: 6pt, y: 2.5pt)`), UPPERCASE 11.5pt bold. No rules anywhere in the document.
- **Skills block**: two-line rows — small uppercase bold label on its own line, items on the line below (verified: extraction keeps label and values adjacent).
- **Accent role** (DUOTONE, see core.md § Duotone): hue **A** does backgrounds only — the header band and the heading bars; hue **B** does the dates and the list markers. No other coloured text anywhere.
- **Icons**: **solid** style in **white**, inside the band — platform marks in white too.
- **Header**: full-width band, `#place(top + left, dx: -1.5cm, dy: -1.2cm, rect(width: 100% + 3cm, height: 3.0cm, fill: accent))` — `place` takes no flow space, so the band lands on page 1 only (a page `background` would repeat it on page 2). Name 24pt bold white, role line and contacts white inside the band; photo slot = right of the band.
- **Type**: a contemporary brand sans with display and text cuts of one system. Pool: `pick_design.py` FONTS `color-band`.
- **Accents** (analogous harmony; hue A must also clear 4.5:1 against **white** text, not just on white). Validated A→B pairs, far-analogous (+62°), never mixed across rows: `#1f3a5f` navy → `#502d66` (11.0) · `#1e5631` forest → `#2b4b5d` (9.3) · `#3b3486` indigo → `#733b6c` (8.2) · `#0f4c5c` petrol → `#2c1a66` (14.5).
- **Verified**: leading `0.583em`, spacing `0.643em`, section `above` 7pt (12pt airy), 5pt after the title (1.4:1 — the *filled-device* exemption: the reversed bar is the boundary) → 1 page, fill 94%, white-run ratio 2.31 (1.5% of page height, re-measured 2026-09-13; 2.33 under the pre-42049f6 sampling), among the lowest of the roster and still the boundary that reads best — it carries 8 devices. Knife-edge on the template's content: +1pt of `above` spills to 2 pages. Budget a re-tune.
- Markets: tech, startups, creative-adjacent, marketing. Not for conservative markets. Photo: yes.
