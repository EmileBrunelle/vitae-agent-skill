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
