"""Design fonts: what `typst fonts` reports, and the deterministic font draw with its availability fallback."""
from __future__ import annotations

import os
import re
import subprocess
from typing import Any, cast

from vitae.design.tables import FONTS, Font, _idx


def _fonts_available() -> set[str] | None:
    """Set of family names `typst fonts` reports (typst-py if no CLI), or None if neither."""
    try:
        out = subprocess.run(["typst", "fonts"], capture_output=True,
                             text=True, timeout=20)
    except FileNotFoundError:   # no CLI: typst-py reports the same families
        try:
            import importlib
            typst: Any = importlib.import_module("typst")
            fp = [d for d in os.environ.get("TYPST_FONT_PATHS", "").split(os.pathsep) if d]
            return set(typst.Fonts(include_system_fonts=True, **({"font_paths": fp} if fp else {})).families())
        except Exception:
            return None
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return {l.strip() for l in out.stdout.splitlines() if l.strip()}


def _installed(name: str, have: set[str]) -> str | None:
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


def _pick_font(pool: list[Font], key: str, salt: str,
               have: set[str] | None) -> tuple[Font, Font | None, str]:
    """Deterministic draw, then availability: if the drawn face is missing
    locally, fall through the pool in order and report BOTH — never a silent
    fallback (a missing font only warns in Typst and swaps itself out)."""
    drawn = pool[_idx(key, len(pool), salt)]
    if have is None:
        return drawn, None, "unverified (no `typst fonts` here — check by hand)"
    got = _installed(drawn[0], have)
    if got:
        return (got, drawn[1]), None, "available locally"
    for cand in pool:
        got = _installed(cand[0], have)
        if got:
            return (got, cand[1]), drawn, ("SUBSTITUTED: drawn %s (%s) not installed, using the "
                                 "installed face shown — install %s for the exact design"
                                 % (drawn[0], drawn[1], drawn[0]))
    return drawn, None, "NO pool member installed — install one before drafting"


def _family_usable(fam: str, have: set[str]) -> bool:
    """Every font role of `fam` has at least one member installed in `have`."""
    fp = FONTS[fam]
    return all(any(_installed(n, have) for n, _ in cast(Any, fp)[role])
               for role in ("display", "body", "mono") if role in fp)
