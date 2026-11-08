# Step 4 — Manual fallbacks

Read only when `pick_design.py --init` fails, or when python3 is missing.

Fallback only if
   `--init` errors (rerun with the same `--lang`/`--region` for the manual path): `cp <skill>/templates/families/<family>/resume.typ <folder>/cv.typ`
   (then change its `#import "../../lib.typ"` line to `#import "lib.typ"`) plus `cp <skill>/templates/lib.typ <skill>/templates/icons.typ <folder>/`, then
   apply the values of `--emit-typ --lang <iso639> [--region <iso3166>]` by hand.

The family, flags and `<family>`/`<skill>` come from the `pick_design.py` report or the manual draw in [`4-draft.md`](../4-draft.md).

Without python3, use this POSIX
   fallback (`sha256sum` + modulo over the eligible families in alphabetical
   order, then the family's default accent and marker) — same family, default
   secondary parameters:
   ```sh
   key="Firstname Lastname+software"
   h=$(printf '%s' "$key" | sha256sum | cut -c1-8)
   # n = number of ELIGIBLE families: apply the flags and the career/field
   # register weighting by hand from core.md's "Family roster" list (id — register). The eligible
   # list EXCLUDES the three creative-register families unless creative is
   # unlocked (a creative --field, or --creative). Widen one register tier at a
   # time (career order), adding families ALPHABETICALLY and STOPPING as soon
   # as 5 are eligible, then sort what is left alphabetically.
   echo $(( 0x$h % n ))        # 0-based index into that alphabetical list
   ```
   The fallback does not reproduce the secondary parameters; use the family's
   documented defaults: its first accent (hue B at the same index), its first
   list marker, its own `labels`, its `page`/`order`/`spec`, and the first pool
   member of each font role that `typst fonts` actually lists.
