# Step 4 — Draft from the family's worked file

4. **Draft from the family's worked file — never from scratch. One command:** `python3 <skill>/scripts/pick_design.py --name "<candidate>" --field <field> --market <market> --career early|mid|senior [--photo] [--conservative] [--creative] --init <cv folder>` — it prints the design report (family, fonts, palette, leading, fill target), then writes `<cv folder>/lib.typ` and `icons.typ` (byte copies), and `<cv folder>/cv.typ` = the drawn family's worked file with the drawn palette, fonts, leading and mark kit already substituted. `pick_design.py --init` refuses to overwrite an existing `cv.typ` (`--force` to replace) and prints the next commands (`harvest_icons.py <folder>`, `verify.py --tune <folder>/cv.typ 1
   <lo> <hi>`, then `verify.py <folder>/cv.typ 1 <lo> <hi>`) — run them verbatim, but
   on the untouched filler starter a fill FAIL/overflow is expected (drawn fonts): first
   replace the filler with the candidate's facts, then read
   `references/steps/4-tune.md`, then `--tune`, then verify. **Scripts are
   run, never read — their printed output is the instruction.** Fallback only if
   `--init` errors: `cp <skill>/templates/families/<family>/resume.typ <folder>/cv.typ`
   plus `cp <skill>/templates/lib.typ <skill>/templates/icons.typ <folder>/`, then
   apply the values of `--emit-typ` by hand. **Never retype, rewrite or summarize
   `lib.typ`** (a rewrite from memory lost `derive()` and the build never compiled
   again); customization goes in `cv.typ`. `verify.py` FAILs a lib that is not a
   copy. `section()`, `job()`, `skill()` and the other devices are defined in the
   family file, NOT in `lib.typ` — a résumé written from `lib.typ` alone dies with
   `unknown variable: section`. (`templates/resume.typ` is only the generic
   starter, for when no family is drawn.) **Fill `cv.typ` one section at a time:
   one edit, then compile — never write the whole file in one go, and never plan
   the whole CV in your head first. The starter already shows every call form with
   all arguments (`job(role, org, dates, note)` — `note` is required — then `- ` bullets;
   `skill(cat, items)`, `section(title)[...]`): copy those, don't read `lib.typ`.**
   Read `references/typst-primer.md`
   (1 minute) before writing any Typst. Typst has no bundler, so the folder
   holds three files: `cv.typ` (the family file), `lib.typ` (the verified
   shared mechanics) and `icons.typ` (the EMPTY fallback `lib.typ` imports;
   copying it keeps the folder compiling with no network). `--init` prints the `harvest_icons.py <that folder>` command: run it once: the contact/platform mark path data is third-party
   artwork this skill does not ship, so it is fetched at build time into
   `<that folder>/icons.typ`, overwriting the empty copy — never into
   `templates/`. The script always writes the file and always exits 0 — if the
   API is unreachable it says so on stderr and writes empty marks, and the CV
   then compiles with no icons and its contact URLs in plain text. `verify.py`
   copies the empty fallback in if the folder has none, so the gate never
   fails for a missing `icons.typ`, load the field pack if one exists, keep the design system's
   invariants (`references/design.md` — read its shared sections plus ONLY the recipe of the family `pick_design.py` drew, via offset/limit; its "Design families — jump to your family" index gives the lines; never the whole file). All fourteen family files
   (`templates/families/<family>/resume.typ`) are gate-passing, with
   `resume-pair-b.typ` beside each showing the same recipe on its second font
   pair.
   `templates/families/swiss-grid/resume-2page.typ` is the worked **2-page**
   example (deliberate break, `runhead`, both pages measured). For the look, do **not** choose freely
   — an agent choosing freely reconverges on the template's own combination and
   every candidate ends up with the same CV. The draw is the `--init` command above (without `--init` it only prints the report; `--emit-typ` prints the preamble values alone — it deliberately does **not** emit the devices, because those are the recipe). **`--market` is documentation only**
   — it is echoed in the report and changes nothing: a conservative market
   must be passed as `--conservative` (the `--field` table also flips it on by
   itself for law, finance, accounting, insurance, government…).
   Build it by following that family's recipe in
   `references/design.md` § Design families (heading device, skills-block
   shape, accent role, contact icons, platform marks, header composition,
   verified leading/spacing/`above`). **Fourteen families in four registers**,
   and the pool is widened until at least **five** are eligible for any
   profile. The `creative` register (`hard-edge`, `avant-poster`, `gutter-rail`)
   is **never in the default pool**: it is unlocked by a creative target field or
   by `--creative` (an explicit request from the candidate or user, never
   inferred), and a conservative market caps it straight back out.
   `gutter-rail` carries a second lock on top: its current only reads to a
   software audience, so it needs a technical field **plus** the explicit ask. A creative family is
   held to the *same* gate as every other — "beautiful **and** parseable" is
   the whole bar, and it does not soften.
   The script also draws the
   **secondary parameters**, all of which are part of the anti-clone system —
   apply them, don't re-choose: the **font pair** from that family's pool
   (`FONTS` in the script is the single source of truth; it checks local
   availability and prints the provenance of anything missing — never let a
   font warning stand; two families also draw a third face, a metadata
   monospace), the **section labels** (the lexical skeleton is a fingerprint
   too), the list marker, on a **duotone** family the second hue with its own
   named jobs, and three things that change the page before a word is read:
   the family's **gabarit** (its own margins, body size and *derived* fill
   target — do not assume 94-96%), its **default section order** (a target
   market's convention always overrides it), and whether it carries a
   **specialities line** (four families do; on those, every item on that line
   is content and rule 2 applies to it in the most prominent position on the
   page). Where a family declares its own **variant** axis (one does), apply the
   drawn variant too.
   Every dated entry must use lib `entry()`: a hand-built grid is not measured by the date-adjacency gate. Check that verify.py's `INFO  date adjacency: N lib entries measured, …` line counts every dated entry in the CV.
   Fresh fonts beyond the pool: only on the user's explicit request, or when
   nothing in the pool is available — then follow design.md § Font pools
   (vetting checklist, no over-used display defaults, add the winner back into
   `FONTS` once it passed the gate). The draw is deterministic per candidate,
   so the 1-page, 2-page and translated versions share one look. The user may
   override with an explicit family or their own combination — an explicit
   choice always wins; silence does not. Without python3, use this POSIX
   fallback (`sha256sum` + modulo over the eligible families in alphabetical
   order, then the family's default accent and marker) — same family, default
   secondary parameters:
   ```sh
   key="Firstname Lastname+software"
   h=$(printf '%s' "$key" | sha256sum | cut -c1-8)
   # n = number of ELIGIBLE families: apply the flags and the career/field
   # register weighting by hand from design.md's register column. The eligible
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
   **Derive `--career` from the fact sheet** — years of experience, whether
   this is a first job, the seniority of the titles — and the market from
   step 2's regional file and the employer type. **Never from age, birth year,
   graduation year used as an age proxy, or any other demographic datum**: the
   skill does not ask for age and does not infer from it (anti-discrimination
   conventions). The default is `early`, which leans modern.
   **Colour audacity dial** (`--audacity`, and `scripts/gen_palette.py`):
   default `sober`. It is raised only on the explicit request of the candidate
   or user — never inferred by the agent from anything about the person or
   their workplace — and a conservative target market caps it back down
   (`references/regional.md`); a market never raises it.
   Shipping the template's own combination (bordeaux `#7d2231`, accent tick +
   full-width hairline under an UPPERCASE accent title, `Category: items`,
   Carlito body + Montserrat headings) is a defect — Montserrat is also one of
   the over-used faces design.md bans as a *display* face, which is one more
   reason the template's look is a starting point and never a deliverable. The bar the result must clear is
   design.md's **non-recognition** test: a recruiter who has seen two CVs from
   this skill must not recognise the third, and no page may pass for a consumer
   tool's default template.
   Before writing any job title onto the page, check each title in the fact
   sheet against the protected titles in `references/regional.md` and the
   target market's file — the wording on the source CV does not by itself
   authorize reusing a reserved title.
   After ANY compile error, re-read `references/typst-primer.md` (pointer in
   step 4) before retrying: it covers every construct the
   template uses and the exact errors agents actually hit; don't guess
   syntax, test with `typst eval`. If the primer doesn't cover the error,
   don't try random variants — consult up-to-date documentation by whatever
   means are available (web search for the official Typst docs, a docs MCP
   if one is configured) and fold the lesson back into the primer.
   Structure notes: the "target-field experience / other professional
   experience" split exists only to keep an off-track role from leading the
   page — when every job is on target, use a single experience section.
   For French output, change the `skill()` helper to `#cat~:` (non-breaking
   space before the colon). Employer descriptor line under each role;
   evidence-based soft-skill lines instead of bare adjective lists.
   Long careers (15+ years): condense old roles into one "Early career"
   block — one line per role (title, org, years), no bullets, linear entry
   variant — and detail only the recent decade; if honest content still
   overflows 2 pages and the market tolerates it (academic, DACH +
   attachments), a third page beats cramming. Career changers with under ~1
   year in the target field: lead with an evidence-anchored skills/projects
   section before the chronological timeline instead of letting an off-track
   role lead the page.
