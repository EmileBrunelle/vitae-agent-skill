# Typst primer — the 20 lines this skill actually uses

For agents whose model knows little Typst. The full language reference lives
only online (typst.app/docs); `man typst` and `--help` cover the CLI, not the
language. Every mistake below was observed in a real cold run of this skill.

## Three contexts — the root of every error

- **Markup** (the document body): `*bold*`, `- ` bullets, `= heading`, plain prose.
- **Code**, entered with `#`: `#let x = 1`, `#set text(size: 10pt)`, `#box[...]`,
  any function call.
- **Content `[...]` vs string `"..."`**: content allows markup inside; a string
  renders markup *literally*. Helper calls take either:
  `#skill("Languages", "C\#, Python")` (plain string) or
  `#skill("Languages", [C\#, *Python*])` (content — bold works).

## Escaping in prose (markup mode)

Escape `\#  \$  \[  \]  \~  \@` in generated text. Unescaped: `#` starts code
(`C#` → *error: expected expression*), `~` silently becomes a non-breaking
space (used on purpose in `#cat~:` for French), `@` starts a reference,
`$` starts math.

## Mistakes agents actually make (each observed in a cold run)

- `C#` unescaped → *expected expression*. Write `C\#`.
- Adding extra brackets inside a bullet — `- [*text*]` → *unclosed delimiter*.
  A bullet body is ALREADY markup: write `- *text*` directly.
- Giving up on `#box` for fragile tokens when unsure of the syntax. Don't:
  `#box[*C\#/.NET*]` in markup/content context is all it takes, and keeping
  fragile tokens unbroken is a design rule (design.md).
- Guessing instead of testing: `typst eval '<snippet>'` (or compiling a
  3-line scratch file) verifies any doubtful construct in milliseconds.

## Everything the template uses — nothing else is needed

`#let name = value` · `#set text/par/page/list(...)` (global defaults) ·
`block(breakable: false)[...]` (the no-section-split guarantee) ·
`grid(columns: (a, b), x, y)` (one row only — see ats.md) · `#pagebreak()` ·
`#upper()` · `#h(5pt)` / `#v(2pt)` (spacing) · `line(length: 100%, stroke: ...)` ·
`#link("url")[shown text]` · `rgb("#7d2231")` / `luma(90)` (colors).

## More traps, each actually hit

- **`block(breakable: false)` shrinks to its content width.**
  `align(center, …)` inside it therefore centres on the BLOCK, not on the page
  measure — section titles drifted by up to 150px between sections, each one
  centred on its own section's widest line. Fix:
  `block(width: 100%, breakable: false, …)`. Only matters for a centred
  family, which is why it went unseen while every family was flush-left.
  **It bites the HEADER block too, and there it is worse**: `engraved-card`'s
  centred lockup had no `width: 100%`, so it centred on the contact line — its
  own widest line — and sat 42pt left of the centred section titles. A reader
  saw it immediately as "the rule under the name is not centred while the
  title is". Any block you centre needs the width, not just the ones you
  remembered.
- **`/` at the start of a markup item is term-list syntax.** `sep: [ / ]`
  fails with `error: expected colon`. Escape it: `[ \/ ]`.
- **`context measure(content)`** is how you size a drawn shape to a piece of
  text. Prefer `box(fill: …)` when the shape is simply a field *behind* the
  text: it shrinks to its content and needs no `measure()` at all (that is
  what `hard-edge`'s knockout slab uses). `measure()` is for a shape that must
  be drawn separately and still fit the title. Same trap as
  above from the other side: `rect(width: 100%)` / `line(length: 100%)`
  inside a box resolves to the AVAILABLE width and silently produces a
  full-width bar.
- **A `counter` read with `display()` shows the value BEFORE a `step()`
  queued in the same context**, so a counter stepped once per row and
  displayed in the same expression is 0-based; initialise it to 1 (or step
  after displaying) to get 1-based numbering. Measured on a sub-clause index
  that came out `2.0, 2.1, …`.
- **`#let f(l, v) = …` shadowing a builtin**: a parameter named `v` shadows
  the `v()` spacing function inside the body, giving
  `error: expected function, found content`. Rename the parameter.
- **Importing a shared module**: `#import "lib.typ": *`, path resolved
  relative to the project root. The hand-off is then TWO files, because
  Typst has no bundler.
