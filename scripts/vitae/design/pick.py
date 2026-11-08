"""Design picker: the deterministic draw of a family, accent, marker, labels and fonts for one candidate."""
from __future__ import annotations

import re
import sys
from collections.abc import Mapping
from typing import TypedDict, cast

from vitae.design.fonts import _family_usable, _fonts_available, _pick_font
from vitae.design.tables import (
    CAREER,
    DOMAIN_REGISTER,
    FAMILIES,
    FONTS,
    GUTTER_RAIL_DOMAIN,
    LABEL_VARIANTS,
    MARK_SETS,
    MIN_POOL,
    Audacity,
    Family,
    Font,
    _idx,
)


class Pick(TypedDict):
    key: str
    family: str
    have: set[str] | None
    offline: bool
    eligible: list[str]
    recipe: Family
    mono: Font | None
    mono_note: str | None
    variant: str | None
    career: str
    domain: str
    audacity: Audacity
    accent: str
    accent2: str | None
    marker: str
    markset: tuple[str, str]
    labels: dict[str, str | None]
    font_register: str
    display: Font
    display_wanted: Font | None
    display_note: str
    body: Font
    body_wanted: Font | None
    body_note: str


def _field_has(field: str | None, key: str) -> bool:
    """`key` is in the case-folded field. A SHORT key (up to 4 letters: art, ui, ux, ml, tax, law, data, sre) must
    begin a word, so it cannot sit inside another one ("département", "html", "syntax"); a longer key stays a plain
    substring, stems and compounds included ("financ" in "finance", "security" in "cybersecurity")."""
    f = (field or "").casefold()
    return re.search(r"(?<!\w)" + re.escape(key), f) is not None if len(key) <= 4 else key in f


def domain_register(field: str | None) -> str | None:
    for k, v in DOMAIN_REGISTER.items():
        if _field_has(field, k):
            return v
    return None                                    # unknown field: full pool


def pick(name: str, field: str | None, career: str = "early",
         photo: bool = False, conservative: bool = False,
         audacity: Audacity = "sober", check_fonts: bool = True,
         creative: bool = False, offline: bool = False,
         have_fonts: set[str] | None = None) -> Pick:
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
    if not any(_field_has(field, t) for t in GUTTER_RAIL_DOMAIN):
        hard = [f for f in hard if f != "gutter-rail"]
    have = have_fonts if have_fonts is not None else (
        _fonts_available() if check_fonts else None)
    # In an offline sandbox (--offline), restrict `hard` to families whose font
    # roles all have at least one locally installed face (when at least one
    # eligible family is usable), so the draw never lands on a family whose
    # display or mono pool has 0 installed members (run 17: 7/14 families were
    # installed, yet keyline-corporate was drawn with no display face).
    if offline and have is None:
        print("warning: --offline is ignored with --no-font-check (no installed-font "
              "list to filter by); drawing from the full pool", file=sys.stderr)
    elif offline and have is not None:
        usable = [f for f in hard if _family_usable(f, have)]
        if usable:
            hard = usable
        else:
            print("warning: --offline: no family in the pool has all font roles "
                  "installed; falling back to the full pool", file=sys.stderr)
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
    lab: dict[str, str | None] = {}
    for role, default in cast("Mapping[str, str | None]", d["labels"]).items():
        # the family's own default is in the pool, so it can be drawn back.
        # A family whose default is None DROPS that section as a trait (its
        # `order` has no slot for it): no variant is drawn back in.
        if default is None:
            lab[role] = None
            continue
        opts = [default] + [v for v in LABEL_VARIANTS[role] if v != default]
        lab[role] = opts[_idx(key, len(opts), "label|%s|" % role)]
    return dict(key=key, family=fam, have=have, offline=offline, eligible=eligible, recipe=d,
                mono=mono, mono_note=mono_note, variant=variant,
                career=career, domain=dom or "none, full pool", audacity=audacity,
                accent=d["accents"][ai],
                accent2=d.get("accents2", [None] * len(d["accents"]))[ai],
                marker=d["markers"][_idx(key, len(d["markers"]), "marker|")],
                markset=MARK_SETS[_idx(key, len(MARK_SETS), "markset|")],
                labels=lab, font_register=fp["register"],
                display=disp, display_wanted=disp_want, display_note=disp_note,
                body=body, body_wanted=body_want, body_note=body_note)
