#!/usr/bin/env python3
"""Pick the design family and its secondary parameters for one candidate.

Deterministic: the same candidate always gets the same look, so the 1-page,
2-page and translated versions of one CV never drift apart. Nothing random,
nothing to remember between sessions.

Usage:
    python3 scripts/pick_design.py --name "Firstname Lastname" \
        --field software --market north-america \
        [--career early|mid|senior] [--photo] [--conservative] \
        [--audacity sober|expressive|bold] [--creative] [--emit-typ]
    python3 scripts/pick_design.py --list        # families, registers, gamuts
    python3 scripts/pick_design.py --selftest    # assert determinism + pools

    --career        early (DEFAULT) → the pool leans MODERN. mid → modern +
                    neutral. senior → neutral + classic. Derive it from the
                    fact sheet: years of experience, whether this is a first
                    job, the seniority of the titles. NEVER from age or any
                    demographic datum — the skill does not ask for age and
                    does not infer from it.
    --field         also weights the pool through DOMAIN_REGISTER below:
                    creative fields lean expressive, conservative fields lean
                    sober. An unknown field leaves the pool full.
    --photo         the market/employer expects a photo in the header (keeps
                    only families whose header has a right-hand slot).
    --conservative  regulated / traditional target market — drops the loud
                    families and caps the audacity dial at sober.
    --audacity      colour dial, see scripts/gen_palette.py. Default sober.
                    Raise it ONLY on the explicit request of the candidate or
                    user, never by inference. A conservative target market caps
                    it back down; a market never raises it.
    --creative      unlock the `creative` register (avant-poster, gutter-rail,
                    hard-edge).
                    Those families are NEVER in the default pool: they need
                    either a --field whose DOMAIN_REGISTER is creative, or this
                    flag, i.e. an explicit request from the candidate or user —
                    never an inference. --conservative drops them regardless.
                    gutter-rail carries a SECOND lock: its ruled gutter is a
                    code gutter, so it also needs a TECHNICAL --field
                    (GUTTER_RAIL_DOMAIN below). The creative unlock alone never
                    draws it for a non-technical trade.
    --emit-typ      print a ready-to-paste Typst PREAMBLE for the drawn recipe
                    (tokens, fonts, page/text/par) — never the devices: the
                    heading device, skills block, accent roles and header
                    composition stay in references/design.md, because they ARE
                    the recipe and the whole anti-clone system.

Fourteen families, and every profile draws from at least MIN_POOL = 5 of them
(so two candidates of the same profile collide at worst 1 time in 5).
Secondary parameters, drawn from the same hash: accent (plus its paired duotone
hue B where the family has one), list marker, section-label variant, the
family's own VARIANT where it declares one, and the font pair from the family's
own typographic pool. FONTS below is the single
source of truth for typography — design.md describes the registers and the
vetting checklist and does NOT repeat the lists (a second list drifts).

The recipes themselves (heading device, skills block, accent role, icons,
verified leading/spacing) live in references/design.md § Design families. This
script only decides WHICH one; design.md says how to build it.

Only name+field enter the hash: the same person keeps their look when the CV
is retargeted, unless a flag changes which families are eligible.

POSIX fallback (no python3) — same result for the family choice:
    key="Firstname Lastname+software"
    h=$(printf '%s' "$key" | sha256sum | cut -c1-8)
    # n = number of ELIGIBLE families: apply the flags and the career/field
    # register weighting by hand from design.md's register column. The eligible
    # list EXCLUDES the three creative-register families unless creative is
    # unlocked (a creative --field, or --creative). Widen one register tier at a
    # time (career order), adding families ALPHABETICALLY and STOPPING as soon
    # as 5 are eligible, then sort what is left alphabetically.
    echo $(( 0x$h % n ))        # 0-based index into that alphabetical list
Same key, same sha256, same modulo, so the family matches this script exactly
— as long as the eligible list matches. The modulo changes when the roster or
the pool sizes change, and it did change when the roster went from 9 to 13 to 14
and MIN_POOL from 4 to 5; that is accepted (a family reshuffle is not a
regression). The secondary parameters do NOT reproduce: take the family's
documented defaults — its FIRST accent (with the hue B at the same index), its
first list marker, its own `labels`, its `page`/`order`/`spec`, and the first
pool member of each font role that `typst fonts` actually lists.
"""
import argparse
import hashlib
import subprocess
import sys

# register: modern | neutral | classic | creative — how current the look reads.
#   `creative` is NEVER in the default pool: see the pool rules in pick().
# icons: the family's contact-icon style (none is itself a design statement).
# labels: the family's DEFAULT section names (the lexical skeleton is a
#   fingerprint too: fourteen families that all say "Profile / Technical Skills
#   / Core Strengths" still read as one tool). Variants in LABEL_VARIANTS.
# header: the order of the header block — another per-family marker.
# accents2: duotone families only — hue B, paired 1:1 with `accents` (same
#   index: the pair was validated together, never mix indexes).
# page: the family's GABARIT — margins, body size and the measured fill target
#   for scripts/verify.py. The target is DERIVED from the bottom margin
#   ((100 − bottom-margin%) − 0..2%), which is why a roomier family aims lower:
#   a 1.2cm bottom leaves 94-96, a 1.6cm bottom leaves 92-94.
# order: the family's DEFAULT section order, from the 7 legal role names only
#   (see ORDER_ROLES). A target market's own convention (references/regional.md
#   § Section order) ALWAYS overrides it.
# spec: does the header carry a SPECIALITIES LINE (the 5-7 mastered skills,
#   small caps, separator-joined, no letterspacing)? A family TRAIT, true on
# variants: a family's OWN variant axis, where its current documents one (only
#   gutter-rail: the square-vs-pill segment binary). Drawn from the same hash.
# spec: … true on
#   exactly FOUR of the fourteen — never universal: the same device on all
#   fourteen would be a new fingerprint for the tool, which is the opposite of
#   what the roster exists for. Where it is true, SKILL.md rule 2 applies to
#   every item on the line.
ORDER_ROLES = ("profile", "skills", "experience", "other", "education", "soft",
               "languages")
STD_PAGE = dict(margin="x: 1.5cm, top: 1.2cm, bottom: 1.2cm", body="10.5pt",
                fill="94-96")
CHRONO = ("profile", "experience", "other", "education", "skills", "soft",
          "languages")
SKILLS_FIRST = ("profile", "skills", "experience", "other", "education",
                "soft", "languages")
FAMILIES = {
    "avant-poster": dict(
        register="creative",
        current="constructivist poster, two-ink discipline (El Lissitzky lineage)",
        icons="solid: filled + angular, hue B",
        accents=["#b3261e", "#8c3b00", "#72191f"],
        accents2=["#1f3a5f", "#0e6862", "#2f4858"],
        markers=["● (vector circle, hue B)", "•"],
        labels=dict(profile="Summary", skills="Technical Stack",
                    soft="Working Style"),
        header="full-bleed masthead bar, oversized name, specialities "
               "line, contacts on one line (NO diagonal)",
        photo_ok=True, conservative_ok=False,
        page=dict(margin="x: 1.8cm, top: 1.3cm, bottom: 1.6cm",
                  body="10.5pt", fill="92-94"),
        order=CHRONO,          # narrative-led: education before skills
        spec=True,
        leading="0.548em", spacing="0.638em",
        above="15pt / 20pt airy, 6pt after"),
    "bold-display": dict(
        register="modern",
        current="geometric display / heavy weight contrast (Avant-Garde lineage)",
        icons="solid: filled + angular, hue B",
        accents=["#8c3b00", "#0e6862", "#3b3486", "#b3261e"],
        accents2=["#105a90", "#72191f", "#7d3312", "#1a6265"],
        markers=["▪", "•"],
        labels=dict(profile="Profile", skills="Technical Stack",
                    soft="Core Strengths"),
        header="oversized hue-A name, role line, contacts on two wide-gap lines",
        photo_ok=False, conservative_ok=False,
        page=STD_PAGE, order=CHRONO, spec=True,
        leading="0.536em", spacing="0.616em", above="14pt / 19pt airy, 6pt after"),
    "clause-index": dict(
        register="neutral",
        current="numbered-clause technical-standard document "
                "(ISO 2145 / DIN 1421 divisions)",
        icons="line: thin stroke + rounded, metadata gray (the accent is "
              "reserved for the numbers)",
        accents=["#33475b", "#1f3a5f", "#0f4c5c"],
        markers=["–", "▪"],
        labels=dict(profile="Summary", skills="Skills & Tools",
                    soft="Strengths"),
        header="two zones: identity + DIN-676 reference row + specialities "
               "line left, contact column right",
        photo_ok=True, conservative_ok=True,
        page=STD_PAGE,
        order=SKILLS_FIRST,    # skills-forward hybrid
        spec=True,
        leading="0.849em", spacing="0.929em",
        above="22pt / 27pt airy, 5pt after"),
    "color-band": dict(
        register="modern",
        current="colored masthead band, name reversed out (editorial/brand)",
        icons="solid: filled + angular, white inside the band",
        accents=["#1f3a5f", "#1e5631", "#3b3486", "#0f4c5c"],
        accents2=["#502d66", "#2b4b5d", "#733b6c", "#2c1a66"],
        markers=["•", "▪"],
        labels=dict(profile="Profile", skills="Skills & Tools",
                    soft="Core Strengths"),
        header="full-width hue-A band: name + role + contacts reversed out",
        photo_ok=True, conservative_ok=False,
        page=STD_PAGE, order=CHRONO, spec=False,
        leading="0.583em", spacing="0.643em", above="7pt / 12pt airy, 5pt after"),
    "gutter-rail": dict(
        register="creative",
        current="the themed developer environment read in print: editor chrome "
                "(a margin gutter, fold marks, a statusline of segments) + the "
                "tiling-desktop conventions (bar modules, uniform gaps, ONE "
                "reserved accent for the live state), from the LIGHT half of "
                "that tradition",
        icons="no generic icon (measured: a 0.9pt stroked pin/handset collapses "
              "at statusline size); every mark is a platform mark, hue B",
        accents=["#286983", "#174f78", "#4d2287", "#7e3c07"],
        # hue B is deliberately OUT of the red-brown band (10-35°): at the
        # lightness the 6:1 guardrail forces, a hue in that band is not a red,
        # it is a brown, and hue B here carries the page's SMALLEST ink (8.5pt
        # dates, the 1.5pt change-bar) where a brown reads as faded black
        # rather than as a colour. Measured on 300dpi crops — design.md § 14.
        accents2=["#6a2f4d", "#983e6a", "#2e6b24", "#1b6a63"],
        markers=["▎ (vector change-bar, hue B)", "▎"],
        labels=dict(profile="Profile", skills="Skills", soft="Working Style"),
        header="a STATUSLINE STRIP of painted segments across the top "
               "(contacts), then the name and the role line under it",
        # the one variant axis: the harvested square-vs-pill binary of the
        # tradition, applied to every painted surface at once (one corner-style
        # token, the way an institutional desktop does it).
        variants=["square segments (flat dialect, radius 0pt)",
                  "pill segments (rounded dialect, radius 2.5pt)"],
        photo_ok=False, conservative_ok=False,
        page=dict(margin="x: 1.5cm, top: 1.5cm, bottom: 1.5cm",
                  body="10.5pt", fill="93-95"),
        order=SKILLS_FIRST,    # skills-forward hybrid
        spec=False,
        leading="0.761em", spacing="0.851em",
        above="16pt / 21pt airy, 4.5pt after"),
    "editorial-serif": dict(
        register="classic",
        current="contemporary editorial: serif display over a sans body",
        icons="line: thin stroke + rounded, accent",
        accents=["#1f3a5f", "#5b2a5e", "#72191f"],
        markers=["–", "·"],
        labels=dict(profile="Summary", skills="Technical Skills",
                    soft="Core Strengths"),
        header="one grid row: serif name + accent role line left, contacts right",
        photo_ok=True, conservative_ok=True,
        page=STD_PAGE, order=CHRONO, spec=False,
        leading="0.550em", spacing="0.630em", above="15pt / 20pt airy, 3pt after"),
    "engraved-card": dict(
        register="classic",
        current="engraved stationery / social-card typography "
                "(centred axis, one quiet serif)",
        icons="no generic icon (engraving carried none); platform marks in ink",
        accents=["#5c1f3a", "#2f4858", "#3d3550"],
        markers=["–", "·"],
        labels=dict(profile="Summary", skills="Skills", soft=None),
        header="fully CENTRED: name, a short accent rule under it, role line, "
               "contacts on one centred line",
        photo_ok=False, conservative_ok=True,
        page=dict(margin="x: 2.0cm, top: 1.6cm, bottom: 1.6cm",
                  body="10.5pt", fill="92-94"),
        # credential-led: education raised, and NO soft section at all
        order=("profile", "education", "experience", "other", "skills",
               "languages"),
        spec=False,
        leading="0.556em", spacing="0.656em",
        above="15pt / 20pt airy, 5pt after"),
    "hard-edge": dict(
        register="creative",
        current="neo-brutalist PRINT dialect: knockout black slabs + monospace metadata (no border, no shadow, no tint fields)",
        icons="solid: filled + angular, hue B",
        accents=["#b3261e", "#1e5631", "#3b3486"],
        accents2=["#0f4c5c", "#5c1f3a", "#8c3b00"],
        markers=["▫ (vector outlined square, hue B)", "▫"],
        labels=dict(profile="Profile", skills="Technical Stack",
                    soft="Strengths"),
        header="monogram block + name, then the specialities line, then one "
               "mono contact line",
        photo_ok=False, conservative_ok=False,
        page=dict(margin="x: 1.6cm, top: 1.3cm, bottom: 1.3cm",
                  body="10.5pt", fill="94-96"),
        order=SKILLS_FIRST,    # skills-forward hybrid
        spec=True,
        leading="0.786em", spacing="0.876em",
        above="20pt / 25pt airy, 6pt after"),
    "humanist-quiet": dict(
        register="neutral",
        current="Vignelli-style restraint: no rules, whitespace as the device",
        icons="no generic icon (its device is absence); platform marks in the accent",
        accents=["#0e6862", "#33475b", "#8c3b00"],
        markers=["–", "•"],
        labels=dict(profile="Profile", skills="Skills", soft="Core Strengths"),
        header="name + role left, contacts on two left-aligned lines below",
        photo_ok=False, conservative_ok=True,
        page=STD_PAGE, order=CHRONO, spec=False,
        leading="0.545em", spacing="0.645em", above="26pt / 31pt airy, 4pt after"),
    "keyline-corporate": dict(
        register="modern",
        current="contemporary corporate report: accent keylines, accent labels",
        icons="line: thin stroke + rounded, accent",
        accents=["#33475b", "#1f3a5f", "#0f4c5c", "#5b2a5e"],
        markers=["–", "·"],
        labels=dict(profile="Professional Summary", skills="Technical Skills",
                    soft="Core Strengths"),
        header="one grid row: name + role left, contacts right, soft hairline under",
        photo_ok=True, conservative_ok=True,
        page=STD_PAGE, order=CHRONO, spec=False,
        leading="0.540em", spacing="0.620em", above="23pt / 28pt airy, 5pt after"),
    "margin-index": dict(
        register="classic",
        current="classic marginalia / book typography (titles hang in the margin)",
        icons="no generic icon (marginalia bolts none on); platform marks in ink",
        accents=["#4a2f10", "#1f3a5f", "#5b2a5e"],
        markers=["—", "·"],
        labels=dict(profile="Summary", skills="Expertise", soft="Strengths"),
        header="name + italic role in the content column, contacts on one line "
               "below (photo slot = the margin column)",
        photo_ok=True, conservative_ok=True,
        # margin-index keeps its own body size: the marginalia grid was tuned
        # at 11pt, not 10.5pt.
        page=dict(margin="x: 1.5cm, top: 1.2cm, bottom: 1.2cm", body="11pt",
                  fill="94-96"),
        order=CHRONO, spec=False,
        leading="0.800em", spacing="1.000em", above="30pt / 35pt airy, body 11pt"),
    "mono-technical": dict(
        register="modern",
        current="technical-documentation / spec-sheet aesthetic (mono headings, "
                "tabular dates)",
        icons="line: thin stroke + rounded, hue B",
        accents=["#1f3a5f", "#33475b", "#0f4c5c", "#5b2a5e"],
        accents2=["#8f2d3f", "#8a2f2a", "#66291a", "#3c633a"],
        markers=["▪ (vector square, hue B)", "▪"],
        labels=dict(profile="Profile", skills="Technical Stack",
                    soft="Working Style"),
        header="name, role, then one mono contact line",
        photo_ok=False, conservative_ok=False,
        # NOT STD_PAGE: the spec-sheet look needs a roomier measure than the
        # standard gabarit, and the template's own verified values are these.
        page=dict(margin="x: 1.6cm, top: 1.25cm, bottom: 1.2cm", body="10.5pt",
                  fill="94-96"),
        order=CHRONO, spec=False,
        leading="0.651em", spacing="0.771em",
        above="20pt / 25pt airy, 4pt after"),
    "quiet-luxury": dict(
        register="neutral",
        current="warm restrained minimalism (2020s “quiet luxury”)",
        icons="line: thin stroke + rounded, metadata gray (never the accent)",
        accents=["#5c4632", "#33475b", "#0e6862"],
        markers=["·", "–"],
        labels=dict(profile="Professional Summary", skills="Skills & Tools",
                    soft="Working Style"),
        header="CONTACTS FIRST (letterhead line), then the name, then the role "
               "(photo slot = right cell)",
        photo_ok=True, conservative_ok=True,
        # NOT STD_PAGE: the restraint of this family IS the extra white, and
        # the template's own verified values are these.
        page=dict(margin="x: 1.6cm, top: 1.3cm, bottom: 1.2cm", body="10.5pt",
                  fill="94-96"),
        order=CHRONO, spec=False,
        leading="0.580em", spacing="0.680em",
        above="20pt / 25pt airy, 4pt after"),
    "swiss-grid": dict(
        register="neutral",
        current="International Typographic Style (Müller-Brockmann / Helvetica)",
        icons="no generic icon (typographic purism); platform marks in the body ink",
        accents=["#b3261e", "#33475b", "#0f4c5c"],
        markers=["▪", "–"],
        labels=dict(profile="Profile", skills="Technical Skills",
                    soft="Strengths"),
        header="one grid row: name 24pt + role left, 5-line contact column right",
        photo_ok=True, conservative_ok=True,
        page=STD_PAGE, order=CHRONO, spec=False,
        leading="0.555em", spacing="0.615em", above="13pt / 18pt airy, 6pt after"),
}

# ---------------------------------------------------------------- font pools
# ONE source of truth for typography; references/design.md describes the
# REGISTER each pool serves and never repeats the lists (a second list drifts).
# Entry = (family name exactly as `typst fonts` reports it, provenance).
# Hard rule: no display face is shared between two families — the display face
# is half of a family's identity. Body faces may overlap.
# A family may declare an OPTIONAL third role, `mono`, when its recipe sets all
# metadata in a monospace (hard-edge and gutter-rail).
# "local:" = present in a standard Linux font set here (verified with
# `typst fonts`); "GF:" = Google Fonts, OFL, download or distro package.
# Documented EXEMPTION to the "at least one local member per role" rule: the
# three CREATIVE families (avant-poster, gutter-rail, hard-edge) have NO
# display-pool member in a standard Linux font set — their registers (a
# wonky/heavy grotesque, a ruled technical grotesque, a
# condensed poster face) have no equivalent there, and substituting a
# neo-grotesque would erase the family. The exemption is creative-register
# only, their BODY pools do carry a local member, and the hand-off names the
# package to install. Every other family keeps the rule.
# Extending a pool: run design.md's vetting checklist first, then add here.
FONTS = {
    "swiss-grid": dict(
        register="neo-grotesque, one family for display and body",
        display=[("Nimbus Sans", "local: urw-base35-fonts / fonts-urw-base35"),
                 ("Liberation Sans", "local: liberation-fonts"),
                 ("Archivo", "GF (OFL)"),
                 ("Work Sans", "GF (OFL)")],
        body=[("Nimbus Sans", "local: urw-base35-fonts / fonts-urw-base35"),
              ("Liberation Sans", "local: liberation-fonts"),
              ("Source Sans 3", "GF (OFL, Adobe)"),
              ("Public Sans", "GF (OFL, USWDS)")]),
    "editorial-serif": dict(
        register="serif display over a humanist sans body",
        display=[("Caladea", "local: fonts-crosextra-caladea (OFL)"),
                 ("Noto Serif", "local: google-noto-serif-fonts / fonts-noto"),
                 ("Newsreader", "GF (OFL, Production Type)"),
                 ("Spectral", "GF (OFL, Production Type)")],
        body=[("Open Sans", "local: open-sans-fonts / fonts-open-sans"),
              ("Source Sans 3", "GF (OFL, Adobe)"),
              ("IBM Plex Sans", "GF (OFL, IBM) / fonts-ibm-plex"),
              ("Karla", "GF (OFL)")]),
    "color-band": dict(
        register="contemporary brand sans, display + text cuts of one system",
        display=[("Red Hat Display", "local: redhat-display-fonts (OFL)"),
                 ("DM Sans", "GF (OFL)"),
                 ("Sora", "GF (OFL)")],
        body=[("Red Hat Text", "local: redhat-text-fonts (OFL)"),
              ("Noto Sans", "local: google-noto-sans-fonts / fonts-noto"),
              ("Public Sans", "GF (OFL, USWDS)")]),
    "humanist-quiet": dict(
        register="one humanist sans, display and body, nothing else",
        display=[("Cantarell", "local: abattis-cantarell-fonts (OFL)"),
                 ("Karla", "GF (OFL)"),
                 ("Source Sans 3", "GF (OFL, Adobe)")],
        body=[("Cantarell", "local: abattis-cantarell-fonts (OFL)"),
              ("Noto Sans", "local: google-noto-sans-fonts / fonts-noto"),
              ("Karla", "GF (OFL)")]),
    "keyline-corporate": dict(
        register="clean grotesque, weight and size carry the hierarchy",
        display=[("Vazirmatn", "local: vazirmatn-fonts (OFL)"),
                 ("IBM Plex Sans", "GF (OFL, IBM) / fonts-ibm-plex"),
                 ("Libre Franklin", "GF (OFL)")],
        body=[("Noto Sans", "local: google-noto-sans-fonts / fonts-noto"),
              ("Liberation Sans", "local: liberation-fonts"),
              ("Source Sans 3", "GF (OFL, Adobe)")]),
    "margin-index": dict(
        register="text serif with real italics and old-style figures, "
                 "one family throughout",
        display=[("STIX Two Text", "local: stix-fonts (OFL)"),
                 ("Libertinus Serif", "local: libertinus-fonts (OFL)"),
                 ("Source Serif 4", "GF (OFL, Adobe)"),
                 ("Piazzolla", "GF (OFL)")],
        body=[("STIX Two Text", "local: stix-fonts (OFL)"),
              ("Libertinus Serif", "local: libertinus-fonts (OFL)"),
              ("PT Serif", "GF (OFL, ParaType)"),
              ("Source Serif 4", "GF (OFL, Adobe)")]),
    "mono-technical": dict(
        register="document-grade monospace for the devices + a neutral sans body",
        display=[("Source Code Pro", "local: adobe-source-code-pro-fonts (OFL)"),
                 ("Adwaita Mono", "local: adwaita-mono-fonts (OFL)"),
                 ("IBM Plex Mono", "GF (OFL, IBM) / fonts-ibm-plex"),
                 ("JetBrains Mono", "GF (OFL) — disable ligatures")],
        body=[("Noto Sans", "local: google-noto-sans-fonts / fonts-noto"),
              ("IBM Plex Sans", "GF (OFL, IBM) / fonts-ibm-plex"),
              ("Public Sans", "GF (OFL, USWDS)")]),
    "quiet-luxury": dict(
        register="one warm humanist sans, generous but unshowy",
        display=[("Adwaita Sans", "local: adwaita-sans-fonts (OFL)"),
                 ("Manrope", "GF (OFL)"),
                 ("Outfit", "GF (OFL)")],
        body=[("Adwaita Sans", "local: adwaita-sans-fonts (OFL)"),
              ("Noto Sans", "local: google-noto-sans-fonts / fonts-noto"),
              ("Manrope", "GF (OFL)")]),
    "bold-display": dict(
        register="geometric display for the name + a neutral sans body",
        # Montserrat was removed here on purpose: design.md § Font pools bans
        # the over-used defaults (Inter, Roboto, Montserrat, Lato, Open Sans)
        # as DISPLAY faces, and leaving it in the pool meant drawing a banned
        # face on ~6% of the draws. Three members left = the documented minimum.
        display=[("URW Gothic", "local: urw-base35-fonts / fonts-urw-base35"),
                 ("Space Grotesk", "GF (OFL)"),
                 ("Unbounded", "GF (OFL)")],
        body=[("Adwaita Sans", "local: adwaita-sans-fonts (OFL)"),
              ("Noto Sans", "local: google-noto-sans-fonts / fonts-noto"),
              ("Work Sans", "GF (OFL)")]),
    "engraved-card": dict(
        register="one quiet serif for display and body, "
                 "engraved-letterform lineage",
        display=[("P052", "local: urw-base35-fonts / fonts-urw-base35 "
                          "(URW Palladio, Palatino-lineage)"),
                 ("C059", "local: urw-base35-fonts / fonts-urw-base35 "
                          "(URW Century Schoolbook)"),
                 ("URW Bookman", "local: urw-base35-fonts / fonts-urw-base35"),
                 ("Alegreya", "GF (OFL, Huerta Tipográfica) — old-style AND "
                              "tabular figures")],
        body=[("P052", "local: urw-base35-fonts / fonts-urw-base35"),
              ("C059", "local: urw-base35-fonts / fonts-urw-base35"),
              ("Crimson Pro", "GF (OFL)"),
              ("Alegreya", "GF (OFL, Huerta Tipográfica)")]),
    "clause-index": dict(
        register="institutional grotesque with tabular figures",
        display=[("PT Sans", "local pkg: pt-sans-fonts / fonts-paratype "
                             "(OFL/ParaType FFL)"),
                 ("Schibsted Grotesk", "GF (OFL, Bakken & Bæck)"),
                 ("Fira Sans", "GF (OFL) / fonts-fira-sans")],
        body=[("PT Sans", "local pkg: pt-sans-fonts / fonts-paratype"),
              ("Public Sans", "GF (OFL, USWDS)"),
              ("Noto Sans", "local: google-noto-sans-fonts / fonts-noto")]),
    "hard-edge": dict(
        register="heavy grotesque display + a neutral sans body + a document "
                 "mono for ALL metadata",
        display=[("Familjen Grotesk", "GF (OFL)"),
                 ("Hanken Grotesk", "GF (OFL)"),
                 ("Bricolage Grotesque", "GF (OFL, Atelier Triay) — the "
                  "variable build reports as \"Bricolage Grotesque 96pt\"; "
                  "no italic")],
        mono=[("Fira Mono", "GF (OFL) / fonts-fira-mono"),
              ("DejaVu Sans Mono", "local: dejavu-sans-mono-fonts / fonts-dejavu"),
              ("Noto Sans Mono", "local: google-noto-sans-mono-fonts / fonts-noto")],
        body=[("Public Sans", "GF (OFL, USWDS)"),
              ("Noto Sans", "local: google-noto-sans-fonts / fonts-noto"),
              ("IBM Plex Sans", "GF (OFL, IBM) / fonts-ibm-plex")]),
    "gutter-rail": dict(
        register="UI grotesque for the chrome + a document mono for the BUFFER "
                 "(all metadata) + a neutral sans body",
        display=[("Geist", "GF (OFL, Vercel)"),
                 ("Instrument Sans", "GF (OFL, Instrument)"),
                 ("Onest", "GF (OFL)")],
        # MEASURED constraint on this pool, and it is specific to a family whose
        # ENTIRE metadata register is monospaced: a DISPLAY mono is disqualified.
        # Martian Mono was drawn first and passed the gate (1 page, fill 95%,
        # ratio 3.75) while breaking line integrity twice — the statusline strip
        # wrapped onto a second line and the education descriptor wrapped after
        # "foreign" — because at 8.5pt its advance width is ~25% over a document
        # mono's. No amount of `--tune` fixes a width problem. Red Hat Mono, Geist
        # Mono and Noto Sans Mono all hold both lines (verified by bbox).
        mono=[("Geist Mono", "GF (OFL, Vercel)"),
              ("Red Hat Mono", "GF (OFL, Red Hat)"),
              ("Noto Sans Mono", "local: google-noto-sans-mono-fonts / fonts-noto")],
        body=[("Public Sans", "GF (OFL, USWDS)"),
              ("Noto Sans", "local: google-noto-sans-fonts / fonts-noto"),
              ("IBM Plex Sans", "GF (OFL, IBM) / fonts-ibm-plex")]),
    "avant-poster": dict(
        register="condensed grotesque display + a humanist sans body",
        display=[("Chivo", "GF (OFL, Omnibus-Type)"),
                 ("Big Shoulders Display", "GF (OFL)"),
                 ("Fira Sans Condensed", "GF (OFL) / fonts-fira-sans")],
        body=[("Fira Sans", "GF (OFL) / fonts-fira-sans"),
              ("Noto Sans", "local: google-noto-sans-fonts / fonts-noto"),
              ("Public Sans", "GF (OFL, USWDS)")]),
}

# Section-label pools. The lexical skeleton varies per candidate too, INSIDE
# the regional conventions (references/regional.md § Section names per
# language, references/ats.md): a conventional stem, optionally qualified —
# never an exotic name. "Education", "Languages" and the experience sections
# are NOT variable: their stems are what ATS section classifiers key on.
# soft=None means the family drops the soft-skills section entirely.
LABEL_VARIANTS = dict(
    profile=["Profile", "Summary", "Professional Summary"],
    skills=["Technical Skills", "Skills & Tools", "Skills", "Expertise",
            "Technical Stack"],
    soft=["Core Strengths", "Strengths", "Working Style", None],
)

# Career stage → preferred registers, then the widening tier if the preferred
# pool is too small to individualise (< 2 families).
CAREER = {
    "early":  (("modern",), ("neutral",)),
    "mid":    (("modern", "neutral"), ("classic",)),
    "senior": (("neutral", "classic"), ("modern",)),
}

# Field → how the pool and the colour dial lean. DATA, not logic: extend it.
# Matched as a substring of the lowercased --field; first hit wins.
DOMAIN_REGISTER = {
    # creative: the CV is itself a portfolio piece — expressive families first
    "design": "creative", "graphic": "creative", "ux": "creative",
    "ui": "creative", "art": "creative", "illustration": "creative",
    "photo": "creative", "fashion": "creative", "marketing": "creative",
    "advertis": "creative", "brand": "creative", "motion": "creative",
    "architect": "creative", "creative": "creative", "copywrit": "creative",
    # conservative: sober families, dial capped at sober
    "law": "conservative", "legal": "conservative", "notar": "conservative",
    "financ": "conservative", "account": "conservative", "audit": "conservative",
    "tax": "conservative", "bank": "conservative", "insur": "conservative",
    "govern": "conservative", "public administration": "conservative",
    "compliance": "conservative", "actuar": "conservative",
}


def domain_register(field):
    f = (field or "").lower()
    for k, v in DOMAIN_REGISTER.items():
        if k in f:
            return v
    return None                                    # unknown field: full pool


# gutter-rail is the one family whose device is domain-specific, not just
# register-specific: the ruled gutter is a code gutter. Requiring one of these
# in the field is the second half of its lock (see draw()).
GUTTER_RAIL_DOMAIN = (
    "software", "developer", "engineer", "data", "devops", "backend",
    "frontend", "sre", "security", "ml", "informatique", "logiciel",
)


def _idx(key, n, salt=""):
    """First 8 hex digits of sha256(salt+key), modulo n — POSIX-reproducible."""
    h = hashlib.sha256((salt + key).encode("utf-8")).hexdigest()[:8]
    return int(h, 16) % n


MIN_POOL = 5        # a profile that draws from fewer than 5 families collides
                    # too often; 14 families make a 5-family floor reachable
                    # for every profile combination (asserted in selftest()).


def _fonts_available():
    """Set of family names `typst fonts` reports, or None if typst is absent."""
    try:
        out = subprocess.run(["typst", "fonts"], capture_output=True,
                             text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return {l.strip() for l in out.stdout.splitlines() if l.strip()}


def _pick_font(pool, key, salt, have):
    """Deterministic draw, then availability: if the drawn face is missing
    locally, fall through the pool in order and report BOTH — never a silent
    fallback (a missing font only warns in Typst and swaps itself out)."""
    drawn = pool[_idx(key, len(pool), salt)]
    if have is None:
        return drawn, None, "unverified (no `typst fonts` here — check by hand)"
    if drawn[0] in have:
        return drawn, None, "available locally"
    for cand in pool:
        if cand[0] in have:
            return cand, drawn, ("DRAWN FACE MISSING: install %s (%s), or use "
                                 "this available pool member meanwhile"
                                 % (drawn[0], drawn[1]))
    return drawn, None, "NO pool member installed — install one before drafting"


def pick(name, field, career="early", photo=False, conservative=False,
         audacity="sober", check_fonts=True, creative=False):
    key = "%s+%s" % (name, field)
    dom = domain_register(field)
    conservative = conservative or dom == "conservative"
    if conservative and audacity != "sober":
        audacity = "sober"                         # a market only caps the dial
    elif dom == "creative" and audacity == "sober":
        audacity = "expressive"

    hard = [f for f, d in FAMILIES.items()
            if (d["photo_ok"] or not photo)
            and (d["conservative_ok"] or not conservative)]
    # The `creative` register is NEVER in the default pool: those families are
    # eligible only when the FIELD resolves to creative or --creative was
    # passed (an explicit request from the candidate or user). Filtered out of
    # `hard` HERE, before the widening loop, so widening can never pull one in
    # for a non-creative profile. --conservative drops them anyway via
    # conservative_ok=False, which is why creative+conservative is not an
    # empty pool but simply the conservative one.
    unlocked = creative or dom == "creative"
    if not unlocked:
        hard = [f for f in hard if FAMILIES[f]["register"] != "creative"]
    # gutter-rail carries a SECOND lock on top of the creative one: its vertical
    # rail with the ruled gutter reads as a code gutter / line-number column, so
    # it needs a technical FIELD as well as the creative unlock. Measured before
    # this lock: a fashion designer passing --creative drew it, and the device
    # was simply wrong for the trade. The creative unlock is necessary, not
    # sufficient.
    if not any(t in (field or "").lower() for t in GUTTER_RAIL_DOMAIN):
        hard = [f for f in hard if f != "gutter-rail"]
    if not hard:
        raise SystemExit("no family satisfies those flags — pick one by hand")

    # Register weighting: a creative field (or --creative) leans on the
    # creative then modern families whatever the career stage; otherwise the
    # career stage decides.
    prefer, widen = CAREER[career]
    if unlocked:
        prefer, widen = ("creative", "modern"), ("neutral", "classic")
    # Widening is ADDITIVE and stops the moment MIN_POOL is reached: replacing
    # the pool with `hard` wholesale made an EXTRA constraint GROW the pool
    # (measured before the fix: conservative drew from 4 families,
    # conservative+photo from 5). Tier order = the career's register
    # preference, then alphabetical inside a tier, so the result stays
    # reproducible by hand (see the POSIX fallback above).
    pool = [f for f in sorted(hard) if FAMILIES[f]["register"] in prefer]
    # the final catch-all tier does NOT name `creative` either — a creative
    # family only ever enters through `prefer` above.
    for tier in (widen, ("modern", "neutral", "classic")):
        for f in sorted(hard):
            if len(pool) >= MIN_POOL:
                break
            if f not in pool and FAMILIES[f]["register"] in tier:
                pool.append(f)
    eligible = sorted(pool)

    fam = eligible[_idx(key, len(eligible))]
    d = FAMILIES[fam]
    ai = _idx(key, len(d["accents"]), "accent|")
    have = _fonts_available() if check_fonts else None
    fp = FONTS[fam]
    disp, disp_want, disp_note = _pick_font(fp["display"], key, "display|", have)
    body, body_want, body_note = _pick_font(fp["body"], key, "body|", have)
    mono = mono_note = None
    if "mono" in fp:                    # optional third role
        mono, _, mono_note = _pick_font(fp["mono"], key, "mono|", have)
    # a family MAY declare its own variant axis (only gutter-rail does: the
    # square-vs-pill segment binary its current documents). Drawn from the same
    # hash, so it stays deterministic per candidate like everything else.
    variant = None
    if "variants" in d:
        variant = d["variants"][_idx(key, len(d["variants"]), "variant|")]
    lab = {}
    for role, default in d["labels"].items():
        # the family's own default is in the pool, so it can be drawn back.
        # A family whose default is None DROPS that section as a trait (its
        # `order` has no slot for it): no variant is drawn back in.
        if default is None:
            lab[role] = None
            continue
        opts = [default] + [v for v in LABEL_VARIANTS[role] if v != default]
        lab[role] = opts[_idx(key, len(opts), "label|%s|" % role)]
    return dict(key=key, family=fam, eligible=eligible, recipe=d,
                mono=mono, mono_note=mono_note, variant=variant,
                career=career, domain=dom or "unknown", audacity=audacity,
                accent=d["accents"][ai],
                accent2=d.get("accents2", [None] * len(d["accents"]))[ai],
                marker=d["markers"][_idx(key, len(d["markers"]), "marker|")],
                labels=lab, font_register=fp["register"],
                display=disp, display_wanted=disp_want, display_note=disp_note,
                body=body, body_wanted=body_want, body_note=body_note)


def report(p, market):
    d = p["recipe"]
    lines = [
        "design family   : %s   [register: %s]" % (p["family"], d["register"]),
        "  current       : %s" % d["current"],
        "accent          : %s   (from that family's gamut %s)"
        % (p["accent"], " ".join(d["accents"])),
    ]
    if p["accent2"]:
        lines.append("accent2 (duotone): %s   hue B, validated as a PAIR with "
                     "the accent above — never mix indexes" % p["accent2"])
    # right after the colour block, duotone or not: an insert(4) landed before
    # the hue B line on monochrome families and after it on duotone ones.
    if p["audacity"] != "sober":
        lines.append("  palette       : python3 scripts/gen_palette.py "
                     "--family %s --seed %r --audacity %s --typst"
                     % (p["family"], p["key"], p["audacity"]))
    lines += [
        "audacity        : %s" % p["audacity"],
        "list marker     : %s" % p["marker"],
        *(["family variant  : %s   (this family's own variant axis — apply it "
           "as drawn)" % p["variant"]] if p["variant"] else []),
        "contact icons   : %s" % d["icons"],
        "platform marks  : email · LinkedIn · GitHub · site — in EVERY family "
        "(Font Awesome Free path data, Icons CC BY 4.0, inlined as SVG)",
        "section labels  : profile=%r  skills=%r  soft=%r"
        % (p["labels"]["profile"], p["labels"]["skills"], p["labels"]["soft"]),
        "                  (Education / Languages / the experience sections keep"
        " their conventional stems — regional.md)",
        "type register    : %s" % p["font_register"],
        "display font    : %s   [%s]  — %s"
        % (p["display"][0], p["display"][1], p["display_note"]),
        "body font       : %s   [%s]  — %s"
        % (p["body"][0], p["body"][1], p["body_note"]),
    ]
    if p["mono"]:
        lines.append("mono font       : %s   [%s]  — %s   (ALL metadata)"
                     % (p["mono"][0], p["mono"][1], p["mono_note"]))
    # Any face marked GF has to be fetched before drafting — it is in no distro.
    # Say where from, once, and only when this draw actually needs it.
    roles = [p["display"], p["body"]] + ([p["mono"]] if p["mono"] else [])
    if any("GF" in (r[1] or "") for r in roles):
        lines.append(
            "                  faces marked [GF] are Google Fonts (OFL) and "
            "ship in no distro package:")
        lines.append(
            "                  install them, then confirm with `typst fonts` "
            "— references/fonts.md has the URL,")
        lines.append(
            "                  the licence and both installation routes "
            "(~/.local/share/fonts + fc-cache, or --font-path).")
    pg = d["page"]
    lines += [
        "par leading     : %s      spacing: %s" % (d["leading"], d["spacing"]),
        "section spacing : %s" % d["above"],
        "gabarit         : margin (%s), body %s" % (pg["margin"], pg["body"]),
        "fill target     : %s%%   → scripts/verify.py cv.typ 1 %s %s"
        % (pg["fill"], *pg["fill"].split("-")),
        "section order   : %s" % " → ".join(d["order"]),
        "                  (the family DEFAULT — a target market's own "
        "convention overrides it: regional.md)",
        "header order    : %s" % d["header"],
        "career / market : %s / %s (field register: %s)"
        % (p["career"], market, p["domain"]),
        "eligible were   : %s" % ", ".join(p["eligible"]),
        "hash key        : %r" % p["key"],
    ]
    if d["spec"]:
        lines += [
            "specialities    : this family CARRIES a specialities line in the "
            "header (5-7 mastered",
            "                  skills, small caps, separator-joined, no "
            "letterspacing). SKILL.md rule 2",
            "                  applies to EVERY item on it.",
        ]
    lines += [
        "",
        "Apply the family's recipe from references/design.md § Design families,",
        "then re-run scripts/verify.py — the leading/spacing above were verified",
        "on the template's own filler content, not on this candidate's, and a",
        "different font pair shifts the fill: re-run the tuning loop.",
    ]
    return "\n".join(lines)


def _chain(pool, drawn, role):
    """Typst font fallback chain: the drawn face first, then the rest of the
    family's own pool, and always ENDING on a face a standard Linux font set
    has — otherwise Typst silently substitutes something arbitrary."""
    names = [drawn[0]] + [n for n, _ in pool if n != drawn[0]]
    if not any("local" in prov for n, prov in pool if n in names):
        names.append("DejaVu Sans Mono" if role == "mono" else "Noto Sans")
    return "(" + ", ".join('"%s"' % n for n in names) + ")"


def _icon_colour(icons):
    """The family's icon colour, read off its own `icons` string."""
    for needle, tok in (("hue B", "accent2"),
                        ("white inside the band", "white"),
                        ("metadata gray", "muted"),
                        ("body ink", "dark"),
                        ("accent", "accent"),
                        ("in ink", "ink")):
        if needle in icons:
            return tok
    return "ink"


def emit_typ(p, market):
    """A ready-to-paste PREAMBLE for the drawn recipe — not a whole CV, and
    deliberately not the devices (those are the recipe: design.md)."""
    d, fp, pg = p["recipe"], FONTS[p["family"]], p["recipe"]["page"]
    lo, hi = pg["fill"].split("-")
    try:                                  # the duotone hue jobs live next door
        from gen_palette import DUOTONE
    except ImportError:
        DUOTONE = {}
    o = ["// %s — %s / %s, drawn for key %r"
         % (p["family"], p["career"], market, p["key"]),
         "// PREAMBLE ONLY. The hand-off is TWO files: this .typ and lib.typ "
         "beside it.",
         '#import "lib.typ": *',
         "",
         "// ---------- Palette (scripts/gen_palette.py validates every "
         "contrast) ----------"]
    jobs = DUOTONE.get(p["family"])
    o.append('#let accent = rgb("%s")%s' % (
        p["accent"], "        // hue A — %s" % jobs[1] if jobs else ""))
    if p["accent2"]:
        o.append('#let accent2 = rgb("%s")%s' % (
            p["accent2"], "       // hue B — %s" % jobs[2] if jobs else
            "       // hue B, paired with hue A by index"))
        o.append("// Each hue keeps 1-2 jobs, never more (design.md § Tokens).")
    o += ["#let pal = derive(accent)",
          "#let soft = pal.soft        // decorative hairlines only, never text",
          "#let ink = pal.ink          // metadata gray, biased to the accent hue",
          "#let muted = ink",
          "#let dark = pal.dark        // body ink",
          "",
          "// ---------- Type: %s ----------" % p["font_register"],
          "#let bodyf = %s" % _chain(fp["body"], p["body"], "body"),
          "#let dispf = %s" % _chain(fp["display"], p["display"], "display")]
    if p["mono"]:
        o.append("#let monof = %s   // ALL metadata sits in this face"
                 % _chain(fp["mono"], p["mono"], "mono"))
    col = _icon_colour(d["icons"])
    o += ["",
          "// ---------- Contact icons + platform marks ----------",
          "// family icon style: %s" % d["icons"],
          "#let ic-col = %s" % col]
    if "no generic icon" in d["icons"]:
        o.append("// no `ic`: this family carries NO generic pin/phone icon — "
                 "see its `icons` line just above for why.")
    else:
        o.append("#let ic = icons-%s(ic-col)"
                 % ("solid" if d["icons"].startswith("solid") else "line")
                 + ("   // bg: the band colour where they sit reversed out"
                    if col == "white" else ""))
    o += ["#let mk = marks(ic-col)     // platform marks: EVERY family carries these",
          "",
          "// ---------- Gabarit (fill target %s%% is derived from the bottom "
          "margin) ----------" % pg["fill"],
          '#set page(paper: "us-letter", margin: (%s))' % pg["margin"],
          '#set text(font: bodyf, size: %s, lang: "en", fill: dark, '
          "hyphenate: false)" % pg["body"],
          "// Primary fill-tuning knobs ↓ (±0.01-0.03em steps)",
          "#set par(justify: false, leading: %s, spacing: %s)"
          % (d["leading"], d["spacing"]),
          "// section blocks: above %s" % d["above"],
          "",
          "// ---------- The rest of the recipe (NOT emitted, on purpose) "
          "----------",
          "// section labels : profile=%r  skills=%r  soft=%r"
          % (p["labels"]["profile"], p["labels"]["skills"], p["labels"]["soft"]),
          "//                  Education / Languages / the experience sections "
          "keep their",
          "//                  conventional stems (regional.md, ats.md).",
          *(["// family variant : %s" % p["variant"]] if p["variant"] else []),
          "// section order  : %s" % " → ".join(d["order"]),
          "//                  the family DEFAULT — a target market's own "
          "convention overrides it.",
          *(["//                  soft=None for this draw: drop `soft` from "
             "that order."] if p["labels"]["soft"] is None
            and "soft" in d["order"] else []),
          "// specialities   : %s" % ("YES — 5-7 mastered skills in the header, "
                                      "small caps, separator-joined, no"
                                      if d["spec"] else "no — this family "
                                      "carries no specialities line."),
          ]
    if d["spec"]:
        o.append("//                  letterspacing. SKILL.md rule 2 applies "
                 "to EVERY item on it.")
    o += ["// Heading device, skills-block shape, accent roles and header "
          "composition are NOT",
          "// emitted: see references/design.md § Design families. They ARE "
          "the recipe, and",
          "// emitting them is what would turn fourteen families back into one "
          "template.",
          "// header order   : %s" % d["header"],
          "",
          "// Verify after EVERY edit:  scripts/verify.py cv.typ 1 %s %s"
          % (lo, hi)]
    return "\n".join(o)


def selftest():
    a = pick("Candidate A", "software", check_fonts=False)
    assert a == pick("Candidate A", "software", check_fonts=False), \
        "not deterministic"
    assert pick("Candidate A", "nursing", check_fonts=False)["key"] != a["key"]
    # default career is early -> a modern-first pool (all four modern families
    # in, then just enough of the widening tier to reach MIN_POOL)
    assert a["career"] == "early"
    assert all(FAMILIES[f]["register"] in ("modern", "neutral")
               for f in a["eligible"]), a["eligible"]
    assert all(f in a["eligible"] for f, d in FAMILIES.items()
               if d["register"] == "modern"), a["eligible"]
    # senior -> neutral + classic only
    s = pick("Candidate A", "software", career="senior", check_fonts=False)
    assert set(FAMILIES[f]["register"] for f in s["eligible"]) <= \
        {"neutral", "classic"}
    # every profile draws from at least MIN_POOL families (1-in-5 collision at
    # worst), flags applied on top; and the creative register is NEVER in the
    # pool without the unlock
    pools = {}
    for label, kw in [("plain", {}), ("photo", dict(photo=True)),
                      ("conservative", dict(conservative=True)),
                      ("photo+cons", dict(photo=True, conservative=True)),
                      ("creative", dict(creative=True)),
                      ("creative+cons", dict(creative=True,
                                             conservative=True))]:
        for c in CAREER:
            p = pick("X", "y", career=c, check_fonts=False, **kw)
            assert len(p["eligible"]) >= MIN_POOL, (c, kw, p["eligible"])
            pools["%s/%s" % (c, label)] = len(p["eligible"])
            if kw.get("photo"):
                assert all(FAMILIES[f]["photo_ok"] for f in p["eligible"])
            if kw.get("conservative"):
                assert all(FAMILIES[f]["conservative_ok"] for f in p["eligible"])
            crea = [f for f in p["eligible"]
                    if FAMILIES[f]["register"] == "creative"]
            if kw.get("creative") and not kw.get("conservative"):
                assert crea, (c, label, "unlock did not surface them")
            else:
                assert not crea, (c, label, crea)
    # field table: creative leans creative+modern and lifts the dial;
    # conservative caps it
    c = pick("Candidate A", "graphic design", check_fonts=False)
    assert c["domain"] == "creative" and c["audacity"] == "expressive"
    assert [f for f in c["eligible"]
            if FAMILIES[f]["register"] == "creative"], c["eligible"]
    k = pick("Candidate A", "corporate law", audacity="bold", check_fonts=False)
    assert k["domain"] == "conservative" and k["audacity"] == "sober"
    assert all(FAMILIES[f]["conservative_ok"] for f in k["eligible"])
    assert domain_register("plumbing") is None
    # bold survives only when nothing caps it — and only because it was asked for
    assert pick("Candidate A", "software", audacity="bold",
                check_fonts=False)["audacity"] == "bold"
    assert a["accent"] in FAMILIES[a["family"]]["accents"]
    assert _idx("Candidate A+software", 3) == int(
        hashlib.sha256(b"Candidate A+software").hexdigest()[:8], 16) % 3
    # duotone: hue B is paired 1:1 with the accent (same index), and only the
    # five declared families have one
    for f, d in FAMILIES.items():
        if "accents2" in d:
            assert len(d["accents2"]) == len(d["accents"]), f
    for i in range(60):
        p = pick("N%02d" % i, "software", check_fonts=False)
        d = FAMILIES[p["family"]]
        if "accents2" in d:
            assert d["accents2"][d["accents"].index(p["accent"])] == p["accent2"]
        else:
            assert p["accent2"] is None
    # roster invariants: 14 families, fonts and families in lockstep, and the
    # three per-family keys present everywhere
    assert len(FAMILIES) == 14, len(FAMILIES)
    assert set(FONTS) == set(FAMILIES), set(FONTS) ^ set(FAMILIES)
    for f, d in FAMILIES.items():
        for k in ("page", "order", "spec"):
            assert k in d, (f, k)
        for k in ("margin", "body", "fill"):
            assert k in d["page"], (f, k)
        o = d["order"]
        assert set(o) <= set(ORDER_ROLES), (f, set(o) - set(ORDER_ROLES))
        assert len(set(o)) == len(o), (f, "duplicate section role")
        assert o[0] == "profile", (f, o)
        assert ("soft" in o) == (d["labels"]["soft"] is not None), (f, o)
    n_spec = sum(1 for d in FAMILIES.values() if d["spec"])
    assert n_spec == 4, n_spec        # a TRAIT, not a house style
    # a family's variant axis: drawn deterministically, always one of its own,
    # and None everywhere else (a variant on every family would be one more
    # thing all fourteen share).
    for i in range(40):
        q = pick("V%02d" % i, "software", creative=True, check_fonts=False)
        dv = FAMILIES[q["family"]]
        assert q["variant"] in dv["variants"] if "variants" in dv \
            else q["variant"] is None, (q["family"], q["variant"])
    # no display face is shared between two families (half of the identity)
    seen = {}
    for f, fp in FONTS.items():
        # 3 members is the documented pool minimum (see bold-display above);
        # `mono` is optional and only hard-edge declares one.
        assert set(fp) - {"register", "mono"} == {"display", "body"}, f
        for role in ("display", "body", "mono"):
            if role not in fp:
                continue
            assert 3 <= len(fp[role]) <= 5, (f, role)
            assert len(set(n for n, _ in fp[role])) == len(fp[role]), (f, role)
        for n, prov in fp["display"]:
            assert n not in seen, ("display face shared", n, f, seen.get(n))
            seen[n] = f
            assert prov, (f, n)
    # labels: every drawn variant stays inside the documented pools, and the
    # family default is always reachable
    triples = {}
    for f, d in FAMILIES.items():
        for role, default in d["labels"].items():
            assert default is None or default in LABEL_VARIANTS[role], (f, role)
        # no two families ship the SAME default triple, over all fourteen:
        # three of them used to default to "Profile / Technical Skills / Core
        # Strengths", which is exactly the lexical fingerprint design.md
        # denounces
        t = tuple(d["labels"][r] for r in ("profile", "skills", "soft"))
        assert t not in triples, ("duplicate default labels", t, f, triples[t])
        triples[t] = f
    spread = {}
    for i in range(400):
        p = pick("Person %03d" % i, "software", career="mid", check_fonts=False)
        spread[p["family"]] = spread.get(p["family"], 0) + 1
        for role in ("profile", "skills", "soft"):
            assert p["labels"][role] in LABEL_VARIANTS[role], p["labels"]
    assert len(spread) >= MIN_POOL, spread
    n_var = sum(1 for d in FAMILIES.values() if "variants" in d)
    print("selftest OK — %d families, %d with a specialities line, "
          "%d with a variant axis, MIN_POOL=%d"
          % (len(FAMILIES), n_spec, n_var, MIN_POOL))
    print("  mid-career spread over 400 names: %s"
          % ", ".join("%s %d" % kv for kv in sorted(spread.items())))
    print("  eligible-pool size per profile:")
    for c in ("early", "mid", "senior"):
        print("    %-7s %s" % (c, "  ".join(
            "%s=%d" % (k.split("/")[1], v)
            for k, v in pools.items() if k.startswith(c + "/"))))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.split("\n")[0])
    ap.add_argument("--name")
    ap.add_argument("--field")
    ap.add_argument("--market", default="unspecified")
    ap.add_argument("--career", default="early", choices=sorted(CAREER))
    ap.add_argument("--audacity", default="sober",
                    choices=["sober", "expressive", "bold"])
    ap.add_argument("--photo", action="store_true")
    ap.add_argument("--conservative", action="store_true")
    ap.add_argument("--creative", action="store_true",
                    help="unlock the creative-register families (explicit "
                         "request only — never inferred)")
    ap.add_argument("--emit-typ", action="store_true",
                    help="print a paste-ready Typst preamble for the recipe")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--no-font-check", action="store_true",
                    help="skip the local `typst fonts` availability check")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.list:
        for f in sorted(FAMILIES):
            d = FAMILIES[f]
            print("%-18s %-8s photo=%-5s cons=%-5s duotone=%-5s spec=%-5s "
                  "icons=%s"
                  % (f, d["register"], d["photo_ok"], d["conservative_ok"],
                     "accents2" in d, d["spec"], d["icons"]))
            print("%18s   gabarit margin (%s), body %s, fill %s%%"
                  % ("", d["page"]["margin"], d["page"]["body"],
                     d["page"]["fill"]))
            print("%18s   order   %s" % ("", " → ".join(d["order"])))
            print("%18s   accents %s" % ("", " ".join(d["accents"])))
            if "accents2" in d:
                print("%18s   hue B   %s  (paired by index)"
                      % ("", " ".join(d["accents2"])))
            print("%18s   labels  %s" % ("", d["labels"]))
            print("%18s   type    %s" % ("", FONTS[f]["register"]))
            for role in ("display", "mono", "body"):
                if role in FONTS[f]:
                    print("%18s   %-8s%s" % ("", role, ", ".join(
                        "%s [%s]" % nv for nv in FONTS[f][role])))
    elif a.name and a.field:
        p = pick(a.name, a.field, a.career, a.photo, a.conservative,
                 a.audacity, not a.no_font_check, a.creative)
        print(emit_typ(p, a.market) if a.emit_typ else report(p, a.market))
    else:
        sys.exit(__doc__)
