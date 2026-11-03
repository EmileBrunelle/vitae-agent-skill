# Icons — provenance and sourcing

Where the contact-line marks and the family devices come from. Drafting rules (which icon style, which colour, all-or-nothing) stay in `references/design/core.md` § Contact icons; this file is only for provenance and for adding a mark.

**Where the devices come from: harvested, not imagined.** Every device in every family recipe is traceable to a real page — a published CV, a design tradition with a name and canonical practitioners, a template gallery's expressive vocabulary — and never to "what would look creative here". This is a method, not a courtesy: an agent inventing devices converges on the same three or four obvious ones, which is the clone problem again one level up. So the loop is: **search for real examples first, name the current or the source, extract the concrete device (what is drawn, where, doing what job), check it against the invariants — extraction first — then attribute it to one to three families as a trait.** Never to all of them. A device that fails extraction goes into `ats.md` with its measured failure instead of being quietly dropped; a device that passes goes in with its proof. The same rule governs § Guided creation.

**The path data is not in this repo.** It is third-party artwork, so the skill ships the address instead: `scripts/harvest_icons.py <cv folder>` pulls every mark from the Iconify API (the same data the npm icon packages publish) into `<cv folder>/icons.typ`, at the moment a CV is built, written beside the `lib.typ` that does `#import "icons.typ": *` — never into `templates/`, whose committed `icons.typ` holds the EMPTY fallback so that import always resolves even with no network and no script run. A Typst import resolves against the importing file, so the copy of `lib.typ` in the deliverable folder finds the `icons.typ` next to it and the folder can be moved anywhere; nothing in the 28 family files changes, they still just call `marks(ic-col)`. Consequence: no vendored artwork, no tag to track, no refresh command to maintain — the marks are current by construction, and adding a kit is an entry in the script's `ICONS` table plus a branch in `marks()`.

The file is written UNCONDITIONALLY, including on a network or API failure — then with empty strings, loudly on stderr, exit status still 0. Typst has no "if this file exists", so unconditional generation is what buys graceful degradation with no conditional logic in the document: an empty body makes `pmark` return `none`, `nb` drops the mark and its nbsp, and the contact line keeps the URL it already carries in plain text (`linkedin.com/in/handle`). The CV stays valid and ATS-readable, one notch plainer. The script still refuses a stroke-based body (it would fill into a blob) and prints a NOTE for a mark flagged `hidden` upstream (LinkedIn's, withdrawn over brand guidelines). Always look at the render: upstream can redraw a path and shift its optical weight at 7pt with every mechanical check unchanged.

Provenance travels in the generated file's header. The mark is inlined as an SVG string via `image(bytes(…), format: "svg")`, so it is vector, emits no text (verified at the gate in every family) and its colour is a parameter rather than baked into a file:

```typst
#let pmark(body, vb, c, h: 7pt) = if body == "" { none } else {
  box(baseline: 0.5pt, image(
    bytes("<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"" + vb
      + "\">" + body.replace("currentColor", c.to-hex()) + "</svg>"),
    format: "svg", height: h))
}
```

**Sourcing a new icon later**: add `var: "prefix:icon-name"` to `ICONS` in `scripts/harvest_icons.py` and read `var-body` / `var-vb` from `marks()`. Prefer a FILL-based set (Tabler `*-filled`, Phosphor `*-fill`, Bootstrap `*-fill`) — the script refuses a stroke icon, which `pmark` would fill into a blob. Never paste path data into the repo, and never an icon font: private-use codepoints leak into the extraction (`references/ats.md`).
