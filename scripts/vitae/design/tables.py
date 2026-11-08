"""Design tables: the family roster, font pools, label variants and the lookup tables that steer the draw. Data only."""
from __future__ import annotations

import hashlib
from typing import Literal, NotRequired, TypedDict

Audacity = Literal["sober", "expressive", "bold"]
Font = tuple[str, str]               # (family name, provenance)

class Labels(TypedDict):
    profile: str
    skills: str
    soft: str | None


class Page(TypedDict):
    margin: str
    body: str
    fill: str


class Family(TypedDict):
    register: str
    current: str
    icons: str
    accents: list[str]
    accents2: NotRequired[list[str]]
    markers: list[str]
    labels: Labels
    header: str
    photo_ok: bool
    conservative_ok: bool
    page: Page
    order: tuple[str, ...]
    spec: bool
    leading: str
    spacing: str
    above: str
    variants: NotRequired[list[str]]


class FontPool(TypedDict):
    register: str
    display: list[Font]
    body: list[Font]
    mono: NotRequired[list[Font]]


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
STD_PAGE = Page(margin="x: 1.5cm, top: 1.2cm, bottom: 1.2cm", body="10.5pt",
                fill="94-96")
CHRONO = ("profile", "experience", "other", "education", "skills", "soft",
          "languages")
SKILLS_FIRST = ("profile", "skills", "experience", "other", "education",
                "soft", "languages")
FAMILIES: dict[str, Family] = {
    "avant-poster": Family(
        register="creative",
        current="constructivist poster, two-ink discipline (El Lissitzky lineage)",
        icons="solid: filled + angular, hue B",
        accents=["#b3261e", "#8c3b00", "#72191f"],
        accents2=["#1f3a5f", "#0e6862", "#2f4858"],
        markers=["● (vector circle, hue B)", "•"],
        labels=Labels(profile="Summary", skills="Technical Stack",
                    soft="Working Style"),
        header="full-bleed masthead bar, oversized name, specialities "
               "line, contacts on one line (NO diagonal)",
        photo_ok=True, conservative_ok=False,
        page=Page(margin="x: 1.8cm, top: 1.3cm, bottom: 1.6cm",
                  body="10.5pt", fill="92-94"),
        order=CHRONO,          # narrative-led: education before skills
        spec=True,
        leading="0.548em", spacing="0.638em",
        above="15pt / 20pt airy, 6pt after"),
    "bold-display": Family(
        register="modern",
        current="geometric display / heavy weight contrast (Avant-Garde lineage)",
        icons="solid: filled + angular, hue B",
        accents=["#8c3b00", "#0e6862", "#3b3486", "#b3261e"],
        accents2=["#105a90", "#72191f", "#7d3312", "#1a6265"],
        markers=["▪", "•"],
        labels=Labels(profile="Profile", skills="Technical Stack",
                    soft="Core Strengths"),
        header="oversized hue-A name, role line, contacts on two wide-gap lines",
        photo_ok=False, conservative_ok=False,
        page=STD_PAGE, order=CHRONO, spec=True,
        leading="0.536em", spacing="0.616em", above="14pt / 19pt airy, 6pt after"),
    "clause-index": Family(
        register="neutral",
        current="numbered-clause technical-standard document "
                "(ISO 2145 / DIN 1421 divisions)",
        icons="line: thin stroke + rounded, metadata gray (the accent is "
              "reserved for the numbers)",
        accents=["#33475b", "#1f3a5f", "#0f4c5c"],
        markers=["–", "▪"],
        labels=Labels(profile="Summary", skills="Skills & Tools",
                    soft="Strengths"),
        header="two zones: identity + DIN-676 reference row + specialities "
               "line left, contact column right",
        photo_ok=True, conservative_ok=True,
        page=STD_PAGE,
        order=SKILLS_FIRST,    # skills-forward hybrid
        spec=True,
        leading="0.849em", spacing="0.929em",
        above="22pt / 27pt airy, 5pt after"),
    "color-band": Family(
        register="modern",
        current="colored masthead band, name reversed out (editorial/brand)",
        icons="solid: filled + angular, white inside the band",
        accents=["#1f3a5f", "#1e5631", "#3b3486", "#0f4c5c"],
        accents2=["#502d66", "#2b4b5d", "#733b6c", "#2c1a66"],
        markers=["•", "▪"],
        labels=Labels(profile="Profile", skills="Skills & Tools",
                    soft="Core Strengths"),
        header="full-width hue-A band: name + role + contacts reversed out",
        photo_ok=True, conservative_ok=False,
        page=STD_PAGE, order=CHRONO, spec=False,
        leading="0.583em", spacing="0.643em", above="7pt / 12pt airy, 5pt after"),
    "gutter-rail": Family(
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
        # rather than as a colour. Measured on 300dpi crops — references/design/families/gutter-rail.md.
        accents2=["#6a2f4d", "#983e6a", "#2e6b24", "#1b6a63"],
        markers=["▎ (vector change-bar, hue B)", "▎"],
        labels=Labels(profile="Profile", skills="Skills", soft="Working Style"),
        header="a STATUSLINE STRIP of painted segments across the top "
               "(contacts), then the name and the role line under it",
        # the one variant axis: the harvested square-vs-pill binary of the
        # tradition, applied to every painted surface at once (one corner-style
        # token, the way an institutional desktop does it).
        variants=["square segments (flat dialect, radius 0pt)",
                  "pill segments (rounded dialect, radius 2.5pt)"],
        photo_ok=False, conservative_ok=False,
        page=Page(margin="x: 1.5cm, top: 1.5cm, bottom: 1.5cm",
                  body="10.5pt", fill="93-95"),
        order=SKILLS_FIRST,    # skills-forward hybrid
        spec=False,
        leading="0.761em", spacing="0.851em",
        above="16pt / 21pt airy, 4.5pt after"),
    "editorial-serif": Family(
        register="classic",
        current="contemporary editorial: serif display over a sans body",
        icons="line: thin stroke + rounded, accent",
        accents=["#1f3a5f", "#5b2a5e", "#72191f"],
        markers=["–", "·"],
        labels=Labels(profile="Summary", skills="Technical Skills",
                    soft="Core Strengths"),
        header="one grid row: serif name + accent role line left, contacts right",
        photo_ok=True, conservative_ok=True,
        page=STD_PAGE, order=CHRONO, spec=False,
        leading="0.550em", spacing="0.630em", above="15pt / 20pt airy, 3pt after"),
    "engraved-card": Family(
        register="classic",
        current="engraved stationery / social-card typography "
                "(centred axis, one quiet serif)",
        icons="no generic icon (engraving carried none); platform marks in ink",
        accents=["#5c1f3a", "#2f4858", "#3d3550"],
        markers=["–", "·"],
        labels=Labels(profile="Summary", skills="Skills", soft=None),
        header="fully CENTRED: name, a short accent rule under it, role line, "
               "contacts on one centred line",
        photo_ok=False, conservative_ok=True,
        page=Page(margin="x: 2.0cm, top: 1.6cm, bottom: 1.6cm",
                  body="10.5pt", fill="92-94"),
        # credential-led: education raised, and NO soft section at all
        order=("profile", "education", "experience", "other", "skills",
               "languages"),
        spec=False,
        leading="0.556em", spacing="0.656em",
        above="15pt / 20pt airy, 5pt after"),
    "hard-edge": Family(
        register="creative",
        current="neo-brutalist PRINT dialect: knockout black slabs + monospace metadata (no border, no shadow, no tint fields)",
        icons="solid: filled + angular, hue B",
        accents=["#b3261e", "#1e5631", "#3b3486"],
        accents2=["#0f4c5c", "#5c1f3a", "#8c3b00"],
        markers=["▫ (vector outlined square, hue B)", "▫"],
        labels=Labels(profile="Profile", skills="Technical Stack",
                    soft="Strengths"),
        header="monogram block + name, then the specialities line, then one "
               "mono contact line",
        photo_ok=False, conservative_ok=False,
        page=Page(margin="x: 1.6cm, top: 1.3cm, bottom: 1.3cm",
                  body="10.5pt", fill="94-96"),
        order=SKILLS_FIRST,    # skills-forward hybrid
        spec=True,
        leading="0.786em", spacing="0.876em",
        above="20pt / 25pt airy, 6pt after"),
    "humanist-quiet": Family(
        register="neutral",
        current="Vignelli-style restraint: no rules, whitespace as the device",
        icons="no generic icon (its device is absence); platform marks in the accent",
        accents=["#0e6862", "#33475b", "#8c3b00"],
        markers=["–", "•"],
        labels=Labels(profile="Profile", skills="Skills", soft="Core Strengths"),
        header="name + role left, contacts on two left-aligned lines below",
        photo_ok=False, conservative_ok=True,
        page=STD_PAGE, order=CHRONO, spec=False,
        leading="0.545em", spacing="0.645em", above="26pt / 31pt airy, 4pt after"),
    "keyline-corporate": Family(
        register="modern",
        current="contemporary corporate report: accent keylines, accent labels",
        icons="line: thin stroke + rounded, accent",
        accents=["#33475b", "#1f3a5f", "#0f4c5c", "#5b2a5e"],
        markers=["–", "·"],
        labels=Labels(profile="Professional Summary", skills="Technical Skills",
                    soft="Core Strengths"),
        header="one grid row: name + role left, contacts right, soft hairline under",
        photo_ok=True, conservative_ok=True,
        page=STD_PAGE, order=CHRONO, spec=False,
        leading="0.540em", spacing="0.620em", above="23pt / 28pt airy, 5pt after"),
    "margin-index": Family(
        register="classic",
        current="classic marginalia / book typography (titles hang in the margin)",
        icons="no generic icon (marginalia bolts none on); platform marks in ink",
        accents=["#4a2f10", "#1f3a5f", "#5b2a5e"],
        markers=["—", "·"],
        labels=Labels(profile="Summary", skills="Expertise", soft="Strengths"),
        header="name + italic role in the content column, contacts on one line "
               "below (photo slot = the margin column)",
        photo_ok=True, conservative_ok=True,
        # margin-index keeps its own body size: the marginalia grid was tuned
        # at 11pt, not 10.5pt.
        page=Page(margin="x: 1.5cm, top: 1.2cm, bottom: 1.2cm", body="11pt",
                  fill="94-96"),
        order=CHRONO, spec=False,
        leading="0.800em", spacing="1.000em", above="30pt / 35pt airy, body 11pt"),
    "mono-technical": Family(
        register="modern",
        current="technical-documentation / spec-sheet aesthetic (mono headings, "
                "tabular dates)",
        icons="line: thin stroke + rounded, hue B",
        accents=["#1f3a5f", "#33475b", "#0f4c5c", "#5b2a5e"],
        accents2=["#8f2d3f", "#8a2f2a", "#66291a", "#3c633a"],
        markers=["▪ (vector square, hue B)", "▪"],
        labels=Labels(profile="Profile", skills="Technical Stack",
                    soft="Working Style"),
        header="name, role, then one mono contact line",
        photo_ok=False, conservative_ok=False,
        # NOT STD_PAGE: the spec-sheet look needs a roomier measure than the
        # standard gabarit, and the template's own verified values are these.
        page=Page(margin="x: 1.6cm, top: 1.25cm, bottom: 1.2cm", body="10.5pt",
                  fill="94-96"),
        order=CHRONO, spec=False,
        leading="0.651em", spacing="0.771em",
        above="20pt / 25pt airy, 4pt after"),
    "quiet-luxury": Family(
        register="neutral",
        current="warm restrained minimalism (2020s “quiet luxury”)",
        icons="line: thin stroke + rounded, metadata gray (never the accent)",
        accents=["#5c4632", "#33475b", "#0e6862"],
        markers=["·", "–"],
        labels=Labels(profile="Professional Summary", skills="Skills & Tools",
                    soft="Working Style"),
        header="CONTACTS FIRST (letterhead line), then the name, then the role "
               "(photo slot = right cell)",
        photo_ok=True, conservative_ok=True,
        # NOT STD_PAGE: the restraint of this family IS the extra white, and
        # the template's own verified values are these.
        page=Page(margin="x: 1.6cm, top: 1.3cm, bottom: 1.2cm", body="10.5pt",
                  fill="94-96"),
        order=CHRONO, spec=False,
        leading="0.580em", spacing="0.680em",
        above="20pt / 25pt airy, 4pt after"),
    "swiss-grid": Family(
        register="neutral",
        current="International Typographic Style (Müller-Brockmann / Helvetica)",
        icons="no generic icon (typographic purism); platform marks in the body ink",
        accents=["#b3261e", "#33475b", "#0f4c5c"],
        markers=["▪", "–"],
        labels=Labels(profile="Profile", skills="Technical Skills",
                    soft="Strengths"),
        header="one grid row: name 24pt + role left, 5-line contact column right",
        photo_ok=True, conservative_ok=True,
        page=STD_PAGE, order=CHRONO, spec=False,
        leading="0.555em", spacing="0.615em", above="13pt / 18pt airy, 6pt after"),
}

# ---------------------------------------------------------------- font pools
# ONE source of truth for typography; references/design/core.md describes the
# REGISTER each pool serves and never repeats the lists (a second list drifts).
# Entry = (family name exactly as `typst fonts` reports it, provenance).
# Hard rule: no display face is shared between two families — the display face
# is half of a family's identity. Body faces may overlap.
# A family may declare an OPTIONAL third role, `mono`, when its recipe sets all
# metadata in a monospace (hard-edge and gutter-rail).
# "local:" = present in a standard Linux font set here (verified with
# `typst fonts`); "GF (...)" = Google Fonts only, OFL, download; "GF · Linux:
# <pkg>" = on Google Fonts AND packaged on some Linux distros (either route).
# Documented EXEMPTION to the "at least one local member per role" rule: the
# three CREATIVE families (avant-poster, gutter-rail, hard-edge) have NO
# display-pool member in a standard Linux font set — their registers (a
# wonky/heavy grotesque, a ruled technical grotesque, a
# condensed poster face) have no equivalent there, and substituting a
# neo-grotesque would erase the family. The exemption is creative-register
# only, their BODY pools do carry a local member, and the hand-off names the
# package to install. Every other family keeps the rule.
# Extending a pool: run core.md's vetting checklist first, then add here.
FONTS: dict[str, FontPool] = {
    "swiss-grid": FontPool(
        register="neo-grotesque, one family for display and body",
        display=[("Nimbus Sans", "local: urw-base35-fonts / fonts-urw-base35"),
                 ("Liberation Sans", "local: liberation-fonts"),
                 ("Archivo", "GF (OFL)"),
                 ("Work Sans", "GF (OFL)")],
        body=[("Nimbus Sans", "local: urw-base35-fonts / fonts-urw-base35"),
              ("Liberation Sans", "local: liberation-fonts"),
              ("Source Sans 3", "GF (OFL, Adobe)"),
              ("Public Sans", "GF (OFL, USWDS)")]),
    "editorial-serif": FontPool(
        register="serif display over a humanist sans body",
        display=[("Caladea", "GF · Linux: fonts-crosextra-caladea (OFL)"),
                 ("Noto Serif", "GF · Linux: google-noto-serif-fonts / fonts-noto"),
                 ("Newsreader", "GF (OFL, Production Type)"),
                 ("Spectral", "GF (OFL, Production Type)")],
        body=[("Open Sans", "GF · Linux: open-sans-fonts / fonts-open-sans"),
              ("Source Sans 3", "GF (OFL, Adobe)"),
              ("IBM Plex Sans", "GF (OFL, IBM) / fonts-ibm-plex"),
              ("Karla", "GF (OFL)")]),
    "color-band": FontPool(
        register="contemporary brand sans, display + text cuts of one system",
        display=[("Red Hat Display", "GF · Linux: redhat-display-fonts (OFL)"),
                 ("DM Sans", "GF (OFL)"),
                 ("Sora", "GF (OFL)")],
        body=[("Red Hat Text", "GF · Linux: redhat-text-fonts (OFL)"),
              ("Noto Sans", "GF · Linux: google-noto-sans-fonts / fonts-noto"),
              ("Public Sans", "GF (OFL, USWDS)")]),
    "humanist-quiet": FontPool(
        register="one humanist sans, display and body, nothing else",
        display=[("Cantarell", "GF · Linux: abattis-cantarell-fonts (OFL)"),
                 ("Karla", "GF (OFL)"),
                 ("Source Sans 3", "GF (OFL, Adobe)")],
        body=[("Cantarell", "GF · Linux: abattis-cantarell-fonts (OFL)"),
              ("Noto Sans", "GF · Linux: google-noto-sans-fonts / fonts-noto"),
              ("Karla", "GF (OFL)")]),
    "keyline-corporate": FontPool(
        register="clean grotesque, weight and size carry the hierarchy",
        display=[("Vazirmatn", "GF · Linux: vazirmatn-fonts (OFL)"),
                 ("IBM Plex Sans", "GF (OFL, IBM) / fonts-ibm-plex"),
                 ("Libre Franklin", "GF (OFL)")],
        body=[("Noto Sans", "GF · Linux: google-noto-sans-fonts / fonts-noto"),
              ("Liberation Sans", "local: liberation-fonts"),
              ("Source Sans 3", "GF (OFL, Adobe)")]),
    "margin-index": FontPool(
        register="text serif with real italics and old-style figures, "
                 "one family throughout",
        display=[("STIX Two Text", "GF · Linux: stix-fonts (OFL)"),
                 ("Libertinus Serif", "GF · Linux: libertinus-fonts (OFL)"),
                 ("Source Serif 4", "GF (OFL, Adobe)"),
                 ("Piazzolla", "GF (OFL)")],
        body=[("STIX Two Text", "GF · Linux: stix-fonts (OFL)"),
              ("Libertinus Serif", "GF · Linux: libertinus-fonts (OFL)"),
              ("PT Serif", "GF (OFL, ParaType)"),
              ("Source Serif 4", "GF (OFL, Adobe)")]),
    "mono-technical": FontPool(
        register="document-grade monospace for the devices + a neutral sans body",
        display=[("Source Code Pro", "GF · Linux: adobe-source-code-pro-fonts (OFL)"),
                 ("Adwaita Mono", "local: adwaita-mono-fonts (OFL)"),
                 ("IBM Plex Mono", "GF (OFL, IBM) / fonts-ibm-plex"),
                 ("JetBrains Mono", "GF (OFL) — disable ligatures")],
        body=[("Noto Sans", "GF · Linux: google-noto-sans-fonts / fonts-noto"),
              ("IBM Plex Sans", "GF (OFL, IBM) / fonts-ibm-plex"),
              ("Public Sans", "GF (OFL, USWDS)")]),
    "quiet-luxury": FontPool(
        register="one warm humanist sans, generous but unshowy",
        display=[("Adwaita Sans", "local: adwaita-sans-fonts (OFL)"),
                 ("Manrope", "GF (OFL)"),
                 ("Outfit", "GF (OFL)")],
        body=[("Adwaita Sans", "local: adwaita-sans-fonts (OFL)"),
              ("Noto Sans", "GF · Linux: google-noto-sans-fonts / fonts-noto"),
              ("Manrope", "GF (OFL)")]),
    "bold-display": FontPool(
        register="geometric display for the name + a neutral sans body",
        # Montserrat was removed here on purpose: core.md § Font pools bans
        # the over-used defaults (Inter, Roboto, Montserrat, Lato, Open Sans)
        # as DISPLAY faces, and leaving it in the pool meant drawing a banned
        # face on ~6% of the draws. Three members left = the documented minimum.
        display=[("URW Gothic", "local: urw-base35-fonts / fonts-urw-base35"),
                 ("Space Grotesk", "GF (OFL)"),
                 ("Unbounded", "GF (OFL)")],
        body=[("Adwaita Sans", "local: adwaita-sans-fonts (OFL)"),
              ("Noto Sans", "GF · Linux: google-noto-sans-fonts / fonts-noto"),
              ("Work Sans", "GF (OFL)")]),
    "engraved-card": FontPool(
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
    "clause-index": FontPool(
        register="institutional grotesque with tabular figures",
        display=[("PT Sans", "GF · Linux: pt-sans-fonts / fonts-paratype "
                             "(OFL/ParaType FFL)"),
                 ("Schibsted Grotesk", "GF (OFL, Bakken & Bæck)"),
                 ("Fira Sans", "GF (OFL) / fonts-fira-sans")],
        body=[("PT Sans", "GF · Linux: pt-sans-fonts / fonts-paratype"),
              ("Public Sans", "GF (OFL, USWDS)"),
              ("Noto Sans", "GF · Linux: google-noto-sans-fonts / fonts-noto")]),
    "hard-edge": FontPool(
        register="heavy grotesque display + a neutral sans body + a document "
                 "mono for ALL metadata",
        display=[("Familjen Grotesk", "GF (OFL)"),
                 ("Hanken Grotesk", "GF (OFL)"),
                 ("Bricolage Grotesque", "GF (OFL, Atelier Triay) — the "
                  "variable build reports as \"Bricolage Grotesque 96pt\"; "
                  "no italic")],
        mono=[("Fira Mono", "GF (OFL) / fonts-fira-mono"),
              ("DejaVu Sans Mono", "local: dejavu-sans-mono-fonts / fonts-dejavu"),
              ("Noto Sans Mono", "GF · Linux: google-noto-sans-mono-fonts / fonts-noto")],
        body=[("Public Sans", "GF (OFL, USWDS)"),
              ("Noto Sans", "GF · Linux: google-noto-sans-fonts / fonts-noto"),
              ("IBM Plex Sans", "GF (OFL, IBM) / fonts-ibm-plex")]),
    "gutter-rail": FontPool(
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
              ("Noto Sans Mono", "GF · Linux: google-noto-sans-mono-fonts / fonts-noto")],
        body=[("Public Sans", "GF (OFL, USWDS)"),
              ("Noto Sans", "GF · Linux: google-noto-sans-fonts / fonts-noto"),
              ("IBM Plex Sans", "GF (OFL, IBM) / fonts-ibm-plex")]),
    "avant-poster": FontPool(
        register="condensed grotesque display + a humanist sans body",
        display=[("Chivo", "GF (OFL, Omnibus-Type)"),
                 ("Big Shoulders Display", "GF (OFL)"),
                 ("Fira Sans Condensed", "GF (OFL) / fonts-fira-sans")],
        body=[("Fira Sans", "GF (OFL) / fonts-fira-sans"),
              ("Noto Sans", "GF · Linux: google-noto-sans-fonts / fonts-noto"),
              ("Public Sans", "GF (OFL, USWDS)")]),
}

# Section-label pools. The lexical skeleton varies per candidate too, INSIDE
# the regional conventions (references/regional.md § Section names per
# language, references/ats.md): a conventional stem, optionally qualified —
# never an exotic name. "Education", "Languages" and the experience sections
# are NOT variable: their stems are what ATS section classifiers key on.
# soft=None means the family drops the soft-skills section entirely.
LABEL_VARIANTS: dict[str, list[str | None]] = dict(
    profile=["Profile", "Summary", "Professional Summary"],
    skills=["Technical Skills", "Skills & Tools", "Skills", "Expertise",
            "Technical Stack"],
    soft=["Core Strengths", "Strengths", "Working Style", None],
)

# Career stage → preferred registers, then the widening tier if the preferred
# pool is too small to individualise (< 2 families).
CAREER: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "early":  (("modern",), ("neutral",)),
    "mid":    (("modern", "neutral"), ("classic",)),
    "senior": (("neutral", "classic"), ("modern",)),
}

# Field → how the pool and the colour dial lean. DATA, not logic: extend it.
# Matched in the case-folded --field (see _field_has: short keys must begin a word, so "art" no longer hits
# "département" nor "ml" "html"; longer keys and stems stay substrings); first hit wins.
DOMAIN_REGISTER: dict[str, str] = {
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


# gutter-rail is the one family whose device is domain-specific, not just
# register-specific: the ruled gutter is a code gutter. Requiring one of these
# in the field is the second half of its lock (see draw()).
GUTTER_RAIL_DOMAIN = (
    "software", "developer", "engineer", "data", "devops", "backend",
    "frontend", "sre", "security", "ml", "informatique", "logiciel",
)


# platform-mark glyph set (mail/web/phone/pin): drawn per candidate so the
# small glyphs stop being a shared fingerprint. LinkedIn/GitHub stay Simple
# Icons in every set — a brand logo is a functional identifier, not a style.
# Sets are fetched into the CV folder's icons.typ; add more in harvest_icons.py
# (Iconify API — the same data the npm icon packages publish).
MARK_SETS: list[tuple[str, str]] = [
    ("tabler", "Tabler Icons filled, MIT"),
    ("phosphor", "Phosphor fill, MIT — harvested via Iconify/npm"),
    ("bootstrap", "Bootstrap Icons fill, MIT — harvested via Iconify/npm"),
]


def _idx(key: str, n: int, salt: str = "") -> int:
    """First 8 hex digits of sha256(salt+key), modulo n — POSIX-reproducible."""
    h = hashlib.sha256((salt + key).encode("utf-8")).hexdigest()[:8]
    return int(h, 16) % n


MIN_POOL = 5        # a profile that draws from fewer than 5 families collides
                    # too often; 14 families make a 5-family floor reachable
                    # for every profile combination (asserted in selftest()).
