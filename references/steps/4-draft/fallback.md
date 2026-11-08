# Step 4 — Manual copy when `--init` fails

Read only when `pick_design.py --init` fails.

`--init` errors (rerun with the same `--lang`/`--region` for the manual path): `cp <skill>/templates/families/<family>/resume.typ <folder>/cv.typ`
   (then change its `#import "../../lib.typ"` line to `#import "lib.typ"`) plus `cp <skill>/templates/lib.typ <skill>/templates/icons.typ <folder>/`, then
   apply the values of `--emit-typ --lang <iso639> [--region <iso3166>]` by hand.
