# Regression fixtures — not templates

AGENT: if you are building a CV, you do not need anything in this folder. Start from `scripts/pick_design.py --init` (see `SKILL.md`); the real templates are in `templates/families/`.

These 14 files (one per design family) are a neutral multi-entry body used to check that spacing and the `verify.py` gates hold across every family.

- `gen.py` — regenerates the fixtures from `templates/families/<f>/resume.typ`.
- `render.sh [outdir]` — compiles them all; non-zero exit on any failure. Then run `python3 scripts/verify.py --gates <fixture>.typ <fixture>.pdf` on each.
