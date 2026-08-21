# Font provenance and installation

`scripts/pick_design.py` is the single source of truth for **which** faces each
design family may draw (its `FONTS` table). This file answers the other
question: when the script prints a face with provenance **`GF`**, where does it
come from, what is its licence, and how do you install it.

Provenance in `pick_design.py` means exactly two things:

| Provenance | Meaning |
|---|---|
| `local: <package>` | present in a standard Linux font set; install the named distro package and `typst fonts` sees it |
| `GF (...)` | Google Fonts. Not installed anywhere by default — one of the two routes below |

Every face in every pool is under the **SIL Open Font License 1.1 (OFL)**
except where the table says otherwise. OFL permits redistribution and embedding
in a PDF without attribution in the document, which is why the pools are
restricted to it: a CV is a file you hand to strangers, and a font you cannot
legally embed is a font that will be substituted on their machine.

**None of these files are vendored in this repository.** The skill ships
recipes, not binaries. That keeps the repo small and the licences unambiguous.

## The two installation routes

### Route 1 — install into the user font directory (persistent, recommended)

Once per machine. Every Typst run then sees the face, with no flags, and so
does every other application.

```sh
# Linux / BSD
mkdir -p ~/.local/share/fonts/vitae
cp /path/to/downloaded/*.ttf ~/.local/share/fonts/vitae/
fc-cache -f                      # rebuild the fontconfig cache

# macOS
cp /path/to/downloaded/*.ttf ~/Library/Fonts/

# Windows (per-user, no admin needed)
#   copy the .ttf files into %LOCALAPPDATA%\Microsoft\Windows\Fonts
```

Verify — this is the check that matters, because Typst matches on the family
name that `typst fonts` reports and nothing else:

```sh
typst fonts | grep -i "geist"
```

If the family does not appear, Typst will silently fall back to the next entry
in the family's pool. A missing font is only a *warning* in Typst, never an
error, so an unverified install shows up as a CV in the wrong typeface rather
than as a failure. `scripts/verify.py` surfaces the compile warning, but
`typst fonts` is the direct answer.

### Route 2 — `--font-path`, no installation

Useful in CI, in a container, or when you do not want to touch the user
profile. Keep the files anywhere and point Typst at the directory:

```sh
typst compile --font-path ./fonts cv.typ cv.pdf
```

The environment variable `TYPST_FONT_PATHS` does the same thing for every
invocation in a shell session (colon-separated on Unix, semicolon on Windows):

```sh
export TYPST_FONT_PATHS=$PWD/fonts
```

Caveat: `--font-path` is *additive* to the system fonts, and it is per-command.
Anything that shells out to `typst` without passing the flag — including a
plain `typst compile` you type later — will not see those faces. Route 1 is the
one that survives.

## Downloading from Google Fonts

Two equivalent ways, both giving the same OFL files:

- Web: `https://fonts.google.com/specimen/<Family+Name>` → *Get font* →
  *Download all*. The zip contains the static instances and/or a variable
  build.
- Git, for all of them at once:
  `git clone --depth 1 https://github.com/google/fonts` then take
  `ofl/<familyname>/` (lowercased, no spaces).

Variable fonts are fine and are what Google now ships for most families — a
single `Family[wght].ttf` covers every weight the recipes ask for. Note that a
variable build sometimes reports a different family name than the specimen page
suggests: `Bricolage Grotesque` installs as **`Bricolage Grotesque 96pt`**, and
that longer string is what has to appear in the `#let dispf = (...)` tuple.
Always trust `typst fonts` over the download page.

## The faces

Family names below are written **exactly as `typst fonts` reports them** — that
string is what goes in a recipe. All OFL 1.1 unless noted.

### Faces with a distro package as well as a Google Fonts entry

Prefer the distro package: it is one command and it updates with the system.

| Family | Specimen | Distro package |
|---|---|---|
| Fira Sans | `fonts.google.com/specimen/Fira+Sans` | `fonts-fira-sans` (Debian/Ubuntu), `mozilla-fira-fonts` (Fedora) |
| Fira Sans Condensed | shipped with Fira Sans | same package as Fira Sans |
| Fira Mono | `fonts.google.com/specimen/Fira+Mono` | `fonts-fira-mono`, `mozilla-fira-mono` |
| IBM Plex Sans | `fonts.google.com/specimen/IBM+Plex+Sans` | `fonts-ibm-plex` |
| IBM Plex Mono | `fonts.google.com/specimen/IBM+Plex+Mono` | `fonts-ibm-plex` |

### Google Fonts only — no distro package

These are the faces that genuinely require one of the two routes above.

| Family | Specimen (`fonts.google.com/specimen/…`) | Foundry / note |
|---|---|---|
| Alegreya | `Alegreya` | Huerta Tipográfica — carries old-style **and** tabular figures, which is why the classic families use it |
| Archivo | `Archivo` | Omnibus-Type |
| Big Shoulders Display | `Big+Shoulders+Display` | condensed poster display; variable `[wght]` |
| Bricolage Grotesque | `Bricolage+Grotesque` | Atelier Triay. Reports as **`Bricolage Grotesque 96pt`**; no italic |
| Chivo | `Chivo` | Omnibus-Type; variable, with italic |
| Crimson Pro | `Crimson+Pro` | book serif |
| DM Sans | `DM+Sans` | Colophon / Deep Mind commission |
| Familjen Grotesk | `Familjen+Grotesk` | variable, with italic |
| Geist | `Geist` | Vercel |
| Geist Mono | `Geist+Mono` | Vercel |
| Hanken Grotesk | `Hanken+Grotesk` | variable, with italic |
| Instrument Sans | `Instrument+Sans` | Instrument; variable `[wdth,wght]` |
| JetBrains Mono | `JetBrains+Mono` | **disable ligatures** in a CV — the coding ligatures mangle extraction |
| Karla | `Karla` | |
| Libre Franklin | `Libre+Franklin` | |
| Manrope | `Manrope` | |
| Newsreader | `Newsreader` | Production Type |
| Onest | `Onest` | variable `[wght]` |
| Outfit | `Outfit` | geometric display |
| Piazzolla | `Piazzolla` | |
| PT Serif | `PT+Serif` | ParaType |
| Public Sans | `Public+Sans` | USWDS (US federal design system) |
| Red Hat Mono | `Red+Hat+Mono` | Red Hat |
| Schibsted Grotesk | `Schibsted+Grotesk` | Bakken & Bæck |
| Sora | `Sora` | |
| Source Sans 3 | `Source+Sans+3` | Adobe |
| Source Serif 4 | `Source+Serif+4` | Adobe |
| Space Grotesk | `Space+Grotesk` | the sanctioned display face where Montserrat is banned |
| Spectral | `Spectral` | Production Type |
| Unbounded | `Unbounded` | heavy display |
| Work Sans | `Work+Sans` | |

Note that `Red Hat Display` and `Red Hat Text` (used by `color-band`) ship in
the same Google Fonts family group as Red Hat Mono and are packaged as
`fonts-redhat-text` / `redhat-text-fonts` on some distros.

## The three families with no local display face

Documented exemption to the pools' "at least one local member per role" rule:
**avant-poster**, **gutter-rail** and **hard-edge** have no display-pool member
in a standard Linux font set. Their registers — a wonky/heavy grotesque, a
ruled technical grotesque, a condensed poster face — have no equivalent there,
and substituting a neo-grotesque erases the family. Their *body* pools do carry
a local member. If you draw one of these three, installing its display face is
not optional; `pick_design.py` names the face and this file says where it comes
from.

## Adding a face to a pool

Vet it first — `references/design.md` § Font pools has the checklist (licence,
figure sets, weight coverage, no over-used display defaults, extraction
behaviour). Then add it to `FONTS` in `scripts/pick_design.py`, which is the
only list; adding it here as well would create a second list that drifts. This
file documents *provenance and installation*, never which family may use what.
