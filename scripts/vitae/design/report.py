"""Design report: the human-readable text printed for a pick."""
from __future__ import annotations

from vitae.design.pick import Pick


def report(p: Pick, market: str) -> str:
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
        "platform marks  : email · LinkedIn · GitHub · site — in EVERY family; "
        "mail/web/phone/pin glyphs from the drawn mark set: %s (%s); "
        "LinkedIn/GitHub always Simple Icons, CC0" % p["markset"],
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
    # A GF-only face is in no distro and has to be fetched; a "GF · Linux:
    # <pkg>" face has two routes. Say so once, and only when this draw needs it.
    roles = [p["display"], p["body"]] + ([p["mono"]] if p["mono"] else [])
    notes = [p["display_note"], p["body_note"]] + (
        [p["mono_note"]] if p["mono"] else [])
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
            and p["have"] is not None and not p["offline"]:
        lines.append(
            "                  offline sandbox (cannot fetch fonts)? Re-run "
            "pick_design.py with --offline to draw from locally installed "
            "families only.")
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
        "Apply the family's recipe: read references/design/families/%s.md whole" % p["family"],
        "(plus references/design/core.md, the shared rules), then re-run",
        "scripts/verify.py — the leading/spacing above were verified",
        "on the template's own filler content, not on this candidate's, and a",
        "different font pair shifts the fill: re-run the tuning loop.",
    ]
    return "\n".join(lines)
