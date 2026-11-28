"""Design emit: the Typst preamble for a drawn recipe."""
from __future__ import annotations

from vitae.design.fonts import installed_face
from vitae.design.pick import Pick
from vitae.design.tables import FONTS, Font, Page


def font_chain(pool: list[Font], drawn: Font, role: str,
           have: set[str] | None = None) -> str:
    """Typst font fallback chain: the drawn face first, then the rest of the
    family's own pool, and always ENDING on a widely installed face —
    otherwise Typst silently substitutes something arbitrary."""
    names = [drawn[0]] + [n for n, _ in pool if n != drawn[0]]
    if have is not None:                # font check on: emit installed names only
        inst = [drawn[0]]               # the chosen face is always kept
        for n, _ in pool:
            got = installed_face(n, have)
            if got and got not in inst:
                inst.append(got)
        names = inst
    tail = "DejaVu Sans Mono" if role == "mono" else "Noto Sans"
    if tail not in names:
        if have is None:
            names.append(tail)
        elif (inst_tail := installed_face(tail, have)) and inst_tail not in names:
            names.append(inst_tail)
    return "(" + ", ".join(f'"{n}"' for n in names) + ")"


def _icon_colour(icons: str) -> str:
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


def vitae_header(pg: Page) -> str:
    """The FIRST line of a drawn cv.typ: verify.py reads the drawn fill target
    from it, so a lowered target on the command line cannot pass unnoticed."""
    return "// vitae: pages=1 fill={}".format(pg["fill"])


def lang_arg(lang: str, region: str | None = None) -> str:
    """The Typst `lang: "xx"[, region: "yy"]` fragment (shape-validated upstream)."""
    return f'lang: "{lang}"' + (f', region: "{region}"' if region else "")


def emit_typ(p: Pick, market: str, lang: str = "en",
             region: str | None = None, band: bool = False) -> str:
    """A ready-to-paste PREAMBLE for the drawn recipe — not a whole CV, and
    deliberately not the devices (those are the recipe: references/design/families/<family>.md)."""
    d, fp, pg = p.recipe, FONTS[p.family], p.recipe["page"]
    lo, hi = pg["fill"].split("-")
    try:                                  # the duotone hue jobs live next door
        from vitae.palette import DUOTONE
        duotone: dict[str, tuple[str, str, str]] = DUOTONE
    except ImportError:
        duotone = {}
    o = [vitae_header(pg),
         f"// {p.family} — {p.career} / {market}, drawn for key {p.key!r}",
         "// PREAMBLE ONLY. The hand-off is TWO files: this .typ and lib.typ "
         "beside it.",
         "// Copy templates/icons.typ here too (the empty fallback lib.typ "
         "imports), then",
         "// fetch the real contact marks into THIS folder (the path data is "
         "third-party",
         "// artwork the skill does not ship): python3 scripts/harvest_icons.py .",
         "// It always writes ./icons.typ — on a network failure with empty "
         "marks, and the CV",
         "// then compiles with no icons and its contact URLs in plain text.",
         '#import "lib.typ": *',
         "",
         "// ---------- Palette (scripts/gen_palette.py validates every "
         "contrast) ----------"]
    jobs = duotone.get(p.family)
    o.append('#let accent = rgb("{}"){}'.format(
        p.accent, f"        // hue A — {jobs[1]}" if jobs else ""))
    if p.accent2:
        o.append('#let accent2 = rgb("{}"){}'.format(
            p.accent2, f"       // hue B — {jobs[2]}" if jobs else
            "       // hue B, paired with hue A by index"))
        o.append("// Each hue keeps 1-2 jobs, never more (core.md § Tokens).")
    o += ["#let pal = derive(accent)",
          "#let soft = pal.soft        // decorative hairlines only, never text",
          "#let ink = pal.ink          // metadata gray, biased to the accent hue",
          "#let muted = ink",
          "#let dark = pal.dark        // body ink",
          "",
          f"// ---------- Type: {p.font_register} ----------",
          "#let bodyf = {}".format(font_chain(fp["body"], p.body, "body", p.have)),
          "#let dispf = {}".format(font_chain(fp["display"], p.display, "display", p.have))]
    mono_pool = fp.get("mono")
    if p.mono and mono_pool is not None:
        o.append("#let monof = {}   // ALL metadata sits in this face".format(font_chain(mono_pool, p.mono, "mono", p.have)))
    col = _icon_colour(d["icons"])
    o += ["",
          "// ---------- Contact icons + platform marks ----------",
          "// family icon style: {}".format(d["icons"]),
          f"#let ic-col = {col}"]
    if "no generic icon" in d["icons"]:
        o.append("// no `ic`: this family carries NO generic pin/phone icon — "
                 "see its `icons` line just above for why.")
    else:
        o.append("#let ic = icons-%s(ic-col)"
                 % ("solid" if d["icons"].startswith("solid") else "line")
                 + ("   // bg: the band colour where they sit reversed out"
                    if col == "white" else ""))
    o += ["#let mk = marks(ic-col, kit: \"{}\")   // drawn mark set: {}".format(*p.markset)]
    if "no generic icon" not in d["icons"]:
        o.append("#let ic = gate-icons(ic, mk)   // drawn icons follow marks' "
                 "all-or-nothing")
    o += ["",
          "// ---------- Gabarit (fill target {}% is derived from the bottom "
          "margin) ----------".format(pg["fill"]),
          '#set page(paper: "us-letter", margin: ({}))'.format(pg["margin"]),
          '#set text(font: bodyf, size: {}, {}, fill: dark, '
          "hyphenate: false)".format(pg["body"], lang_arg(lang, region)),
          *(['#set page(background: accent-band(accent))   // opt-in --band: '
             "text-free strip in the left margin"] if band else []),
          "// Primary fill-tuning knobs ↓ (±0.01-0.03em steps)",
          "#set par(justify: false, leading: {}, spacing: {})".format(d["leading"], d["spacing"]),
          "// section blocks: above {}".format(d["above"]),
          "",
          "// ---------- The rest of the recipe (NOT emitted, on purpose) "
          "----------",
          "// section labels : profile={!r}  skills={!r}".format(p.labels["profile"], p.labels["skills"]),
          "//                  Education / Languages / the experience sections "
          "keep their",
          "//                  conventional stems (regional.md, ats.md).",
          *([f"// family variant : {p.variant}"] if p.variant else []),
          "// section order  : {}".format(" → ".join(d["order"])),
          "//                  the family DEFAULT — a target market's own "
          "convention overrides it.",
          "// specialities   : %s" % ("YES — the skills the facts support, "
                                      "in the header, small caps, separator-joined, no"
                                      if d["spec"] else "no — this family "
                                      "carries no specialities line."),
          ]
    if d["spec"]:
        o.append("//                  letterspacing. SKILL.md rule 2 applies "
                 "to EVERY item on it.")
    o += ["// Heading device, skills-block shape, accent roles and header "
          "composition are NOT",
          "// emitted: see references/design/families/<family>.md. They ARE "
          "the recipe, and",
          "// emitting them is what would turn fourteen families back into one "
          "template.",
          "// header order   : {}".format(d["header"]),
          "",
          f"// Verify after EVERY edit:  scripts/verify.py cv.typ 1 {lo} {hi}"]
    return "\n".join(o)
