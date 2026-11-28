"""Design report: the human-readable text printed for a pick."""
from __future__ import annotations

from vitae.design.pick import Pick


def report(p: Pick, market: str) -> str:
    d = p.recipe
    lines = [
        "design family   : {}   [register: {}]".format(p.family, d["register"]),
        "  current       : {}".format(d["current"]),
        "accent          : {}   (from that family's gamut {})".format(p.accent, " ".join(d["accents"])),
    ]
    if p.accent2:
        lines.append(f"accent2 (duotone): {p.accent2}   hue B, validated as a PAIR with "
                     "the accent above — never mix indexes")
    # right after the colour block, duotone or not: an insert(4) landed before
    # the hue B line on monochrome families and after it on duotone ones.
    if p.audacity != "sober":
        lines.append("  palette       : python3 scripts/gen_palette.py "
                     f"--family {p.family} --seed {p.key!r} --audacity {p.audacity} --typst")
    lines += [
        f"audacity        : {p.audacity}",
        f"list marker     : {p.marker}",
        *([f"family variant  : {p.variant}   (this family's own variant axis — apply it "
           "as drawn)"] if p.variant else []),
        "contact icons   : {}".format(d["icons"]),
        "platform marks  : email · LinkedIn · GitHub · site — in EVERY family; "
        "mail/web/phone/pin glyphs from the drawn mark set: {} ({}); "
        "LinkedIn/GitHub always Simple Icons, CC0".format(*p.markset),
        "section labels  : profile={!r}  skills={!r}".format(p.labels["profile"], p.labels["skills"]),
        "                  (Education / Languages / the experience sections keep"
        " their conventional stems — regional.md)",
        f"type register    : {p.font_register}",
        f"display font    : {p.display[0]}   [{p.display[1]}]  — {p.display_note}",
        f"body font       : {p.body[0]}   [{p.body[1]}]  — {p.body_note}",
    ]
    if p.mono:
        lines.append(f"mono font       : {p.mono[0]}   [{p.mono[1]}]  — {p.mono_note}   (ALL metadata)")
    # A GF-only face is in no distro and has to be fetched; a "GF · Linux:
    # <pkg>" face has two routes. Say so once, and only when this draw needs it.
    roles = [p.display, p.body] + ([p.mono] if p.mono else [])
    notes = [p.display_note, p.body_note] + (
        [p.mono_note] if p.mono else [])
    need = [r[1] or "" for r, nt in zip(roles, notes)
            if "GF" in (r[1] or "") and not (
                "Linux:" in r[1] and (nt or "").startswith("available"))]
    if any("Linux:" not in x for x in need):
        lines.append(
            "                  faces marked [GF] are Google Fonts (OFL) and "
            "ship in no distro package:")
    elif need:
        lines.append(
            "                  faces marked [GF · Linux: pkg] are Google Fonts "
            "(OFL) AND packaged on some distros:")
    if need:
        lines.append(
            "                  install them (Google Fonts download%s), then "
            "confirm with `typst fonts` — references/fonts.md has the URL,"
            % (", or the named Linux package"
               if any("Linux:" in x for x in need) else ""))
        lines.append(
            "                  the licence and both installation routes "
            "(~/.local/share/fonts + fc-cache, or --font-path).")
    if any((nt or "").startswith("NO pool member") for nt in notes) \
            and p.have is not None and not p.offline:
        lines.append(
            "                  offline sandbox (cannot fetch fonts)? Re-run "
            "pick_design.py with --offline to draw from locally installed "
            "families only.")
    pg = d["page"]
    lines += [
        "par leading     : {}      spacing: {}".format(d["leading"], d["spacing"]),
        "section spacing : {}".format(d["above"]),
        "gabarit         : margin ({}), body {}".format(pg["margin"], pg["body"]),
        "fill target     : {}%   → scripts/verify.py cv.typ 1 {} {}".format(pg["fill"], *pg["fill"].split("-")),
        "section order   : {}".format(" → ".join(d["order"])),
        "                  (the family DEFAULT — a target market's own "
        "convention overrides it: regional.md)",
        "header order    : {}".format(d["header"]),
        f"career / market : {p.career} / {market} (field register: {p.domain})",
        "eligible were   : {}".format(", ".join(p.eligible)),
        f"hash key        : {p.key!r}",
    ]
    if d["spec"]:
        lines += [
            "specialities    : this family CARRIES a specialities line in the "
            "header (the skills the facts support,",
            "                  small caps, separator-joined, no "
            "letterspacing). SKILL.md rule 2",
            "                  applies to EVERY item on it.",
        ]
    lines += [
        "",
        f"Apply the family's recipe: read references/design/families/{p.family}.md whole",
        "(plus references/design/core.md, the shared rules), then re-run",
        "scripts/verify.py — the leading/spacing above were verified",
        "on the template's own filler content, not on this candidate's, and a",
        "different font pair shifts the fill: re-run the tuning loop.",
    ]
    return "\n".join(lines)
