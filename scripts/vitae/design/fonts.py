"""Design fonts: what `typst fonts` reports, and the deterministic font draw with its availability fallback."""
from __future__ import annotations

import re

from vitae.core.env import typst_fonts
from vitae.design.tables import FONTS, Font, table_index


def fonts_available() -> set[str] | None:
    """Set of family names Typst reports (see `env.typst_fonts`), or None if it cannot list them."""
    have = typst_fonts()
    return None if have is None else set(have)


def installed_face(name: str, have: set[str]) -> str | None:
    """The name Typst reports for pool family `name`, or None. A variable font
    with an optical-size axis installs as "X <digits>pt" (references/fonts.md),
    so "X" matches that variant and the FULL installed name is what to emit."""
    if name in have:
        return name
    best = None
    for h in have:
        m = re.fullmatch(r"(.+?) (\d+)pt", h)
        if m and m.group(1) == name and (best is None or int(m.group(2)) < best[0]):
            best = (int(m.group(2)), h)
    return best[1] if best else None


def pick_font(pool: list[Font], key: str, salt: str,
               have: set[str] | None) -> tuple[Font, Font | None, str]:
    """Deterministic draw, then availability: if the drawn face is missing
    locally, fall through the pool in order and report BOTH — never a silent
    fallback (a missing font only warns in Typst and swaps itself out)."""
    drawn = pool[table_index(key, len(pool), salt)]
    if have is None:
        return drawn, None, "unverified (no `typst fonts` here — check by hand)"
    got = installed_face(drawn[0], have)
    if got:
        return (got, drawn[1]), None, "available locally"
    for cand in pool:
        got = installed_face(cand[0], have)
        if got:
            return (got, cand[1]), drawn, ("SUBSTITUTED: drawn {} ({}) not installed, using the "
                                 "installed face shown — install {} for the exact design".format(drawn[0], drawn[1], drawn[0]))
    return drawn, None, "NO pool member installed — install one before drafting"


def family_usable(fam: str, have: set[str]) -> bool:
    """Every font role of `fam` has at least one member installed in `have`."""
    fp = FONTS[fam]
    pools = [fp["display"], fp["body"], *([fp["mono"]] if "mono" in fp else [])]
    return all(any(installed_face(n, have) for n, _ in pool) for pool in pools)
