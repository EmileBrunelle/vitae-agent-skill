#!/usr/bin/env python3
"""Generate a harmonised mini-palette for one CV, and validate every contrast.

A CV accent is never a lone hue: it comes with a muted variant for decorative
hairlines and an ink gray pulled toward its hue (a pure neutral gray beside a
warm accent reads as a mismatch). This script builds that set by the family's
harmony rule, then *checks* it — the same relative-luminance formula the rest
of the skill uses — and re-draws until every role clears its threshold on its
real background.

Usage:
    python3 scripts/gen_palette.py --family swiss-grid --seed "Name+field"
    python3 scripts/gen_palette.py --family color-band --audacity expressive \
        --seed "Name+field" --typst
    python3 scripts/gen_palette.py --selftest

    --audacity sober       default. Deep, contained hues only: the palette must
                           stay credible on a conservative employer's CV even
                           when the family is an expressive one. Expressiveness
                           comes from how WIDELY the family uses the colour
                           (bands, bars, oversized type), never from a louder hue.
               expressive  unlocked by a creative target field: mid saturation,
                           slightly more range.
               bold        vivid hues allowed. **Only on the explicit request of
                           the candidate or user** — never inferred by the agent
                           from anything about the person or their workplace.
                           A conservative target market caps the dial back to
                           sober (see references/regional.md); the dial is never
                           raised by a market, only lowered.

Six families are DUOTONE (color-band, bold-display, mono-technical, and the
three creative ones, hard-edge, avant-poster and gutter-rail): they get a second
hue with its own named jobs, derived by the family's harmony rule and validated
in the same draw — if hue B fails its contrast the whole palette is re-drawn, so
an invalid pair can never be emitted. The other eight stay monochrome by design;
see references/design.md § Duotone.

The curated gamuts in references/design.md stay the defaults and the worked
examples; this generator extends past them when a candidate wants a hue that
is not in the list. Invariants hold at every level of the dial: contrast
validated on the real background, the accent keeps the role its family
assigns it, extraction unaffected (colour emits no text).
"""
import argparse
import colorsys
import hashlib
import sys

# Per-audacity draw ranges: (saturation range, lightness range) in HSL %.
# The lightness ceiling is what keeps a hue "deep" rather than neon or pastel;
# the contrast validator then rejects whatever still lands too light.
DIAL = {
    "sober":      ((26, 80), (19, 34)),
    "expressive": ((40, 95), (21, 42)),
    "bold":       ((55, 100), (24, 55)),
}
# Minimum contrast on white for the accent itself, per level. 4.5 is the
# invariant; sober asks for more so it survives a bad B&W photocopy.
ACCENT_MIN = {"sober": 6.0, "expressive": 5.2, "bold": 4.5}

# Hue exclusion zone for TEXT and small elements (degrees, HSL): yellow through
# olive. A yellow has to be darkened hard to reach the contrast this skill
# requires, and a dark yellow is not "gold", it is mustard/olive — it reads as
# muddy at text sizes. The zone is a hue veto, not a contrast one: those hues
# are only acceptable as a large background flat, which no role in this palette
# is. Both hues are drawn again if hue A or hue B lands inside it.
EXCLUDE_HUE = (40, 70)

# Second veto zone, hue-B only: the red-brown band. A generated hue B is
# +180°/+62° off hue A with no say over where that lands; when it lands here
# AND gets darkened to the sober contrast floor (L≈30) it stops being a red
# and becomes a brown — R > G > B with B lowest — which is exactly where the
# curated gutter-rail rows failed (see references/design.md § 14, "brown").
# Unlike EXCLUDE_HUE this is not a redraw trigger: the fix is a hue ROTATION
# (never a lightness cut — the low lightness is *why* it reads brown, cutting
# it further only makes it worse), applied only to hue B, never hue A.
BROWN_HUE = (10, 35)
HUE_B_VETO = (EXCLUDE_HUE, BROWN_HUE)

# Minimum luminance contrast BETWEEN the two duotone hues. A duotone whose two
# inks share a lightness is one ink on a photocopier, and a résumé gets
# photocopied. 1.25 is the floor at which the two still read as two on a
# grayscale laser print (below it the band and its text merge).
DUOTONE_SEP = 1.25

# Harmony rule per family: how the muted variant relates to the accent.
# mono = same hue, lightened. analogous = a small hue rotation. complementary
# = opposite hue, heavily desaturated (decorative hairlines only, and only
# above the sober level — it must not read as a second colour).
HARMONY = {
    "swiss-grid": "mono",
    "editorial-serif": "mono",
    "color-band": "analogous",
    "humanist-quiet": "mono",
    "keyline-corporate": "analogous",
    "bold-display": "complementary",
    "margin-index": "mono",
    "quiet-luxury": "mono",
    "mono-technical": "complementary",
    "engraved-card": "mono",
    "clause-index": "mono",
    "gutter-rail": "complementary",
    "hard-edge": "complementary",
    "avant-poster": "complementary",
}

# DUOTONE families: a real second hue with a job of its own, not decoration.
# Value = how hue B is derived from hue A. Only the expressive/modern families
# get one; the sober families stay monochrome — that IS their character.
# Six families now, not three: the three creative ones are duotone by
# construction (a two-ink poster, a two-ink brutalist grid, and a chrome hue
# against the one reserved live-state accent of a themed environment).
# Each hue keeps at most 1-2 jobs (design.md § Tokens): with two hues the old
# "one accent doing six jobs" trap applies per hue, not per document.
DUOTONE = {
    "color-band":     ("far-analogous", "the band + the heading bars",
                       "the dates + the list markers"),
    "bold-display":   ("complementary", "the name",
                       "the heading underlines, markers and icons"),
    "mono-technical": ("complementary", "the heading marks + skills keys",
                       "the dates, markers and icons"),
    "hard-edge":      ("complementary",
                       "the monogram block + the specialities line",
                       "the dates, the markers and the icons (the section "
                       "slabs and skills tags are body ink, not accent)"),
    "gutter-rail":    ("complementary",
                       "the gutter rails + the crumb marks (the chrome)",
                       "the drawn marks (fold, change-bar, separator), the "
                       "dates and the platform marks (the live state)"),
    "avant-poster":   ("complementary",
                       "the bleeding bars (masthead + sections)",
                       "the skills dividers, the markers, the icons and "
                       "the dates"),
}

INK_BASE, DARK_BASE = 95, 25          # the skill's muted / body-ink grays


def _lum(rgb):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (f(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    """General formula: (L1+0.05)/(L2+0.05), L1 the lighter of the two."""
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _mix(a, b, wa):
    return tuple(round(a[i] * wa + b[i] * (1 - wa)) for i in range(3))


def _hsl(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
    return (round(r * 255), round(g * 255), round(b * 255))


def _hex(rgb):
    return "#%02x%02x%02x" % rgb


def _bits(key, salt, n):
    h = hashlib.sha256((salt + key).encode("utf-8")).hexdigest()[:8]
    return int(h, 16) % n


def _hue_sep(h1, h2):
    return abs((h2 - h1 + 180) % 360 - 180)


BROWN_MARGIN = 12  # degrees of extra clearance past the brown band's edge:
# landing 1° outside 10-35 still reads brown at the sober-floor saturation
# (26%) — measured on a rendered gutter-rail/mono-technical sample, the
# R>G>B gap shrinks with hue but is still visible right at the boundary.
# Escaping to lo-MARGIN lands in the wine/plum range (R>B>G — off the brown
# axis entirely) instead of just grazing the line.


def _escape_hue_veto(h, anchor, min_sep=55):
    """Rotate hue-B's hue h out of HUE_B_VETO, keeping >= min_sep degrees of
    separation from hue A (anchor). Starts BROWN_MARGIN degrees past whichever
    edge of the offending zone is closer, then walks further out if that
    lands in another zone or fails the separation floor; returns None if
    nothing works (the caller then re-draws the whole palette, same as
    before this fix)."""
    def vetoed(x):
        return any(lo <= x <= hi for lo, hi in HUE_B_VETO)
    if not vetoed(h):
        return h
    lo, hi = next((lo, hi) for lo, hi in HUE_B_VETO if lo <= h <= hi)
    for start in ((lo - BROWN_MARGIN) % 360, (hi + BROWN_MARGIN) % 360):
        for step in range(0, 180):
            for cand in ((start - step) % 360, (start + step) % 360):
                if not vetoed(cand) and _hue_sep(cand, anchor) >= min_sep:
                    return cand
    return None


def build(family, seed, audacity="sober"):
    """Deterministic per (family, seed, audacity). Rejects and re-draws until
    every role clears its threshold — the returned palette is always valid."""
    if family not in HARMONY:
        raise SystemExit("unknown family %r (see references/design.md)" % family)
    if audacity not in DIAL:
        raise SystemExit("audacity must be one of %s" % ", ".join(DIAL))
    (smin, smax), (lmin, lmax) = DIAL[audacity]
    harmony = HARMONY[family]
    white = (255, 255, 255)
    for attempt in range(64):                 # bounded: ranges always contain hits
        salt = "%s|%s|%d|" % (family, audacity, attempt)
        hue = _bits(seed, salt + "h", 360)
        sat = smin + _bits(seed, salt + "s", smax - smin + 1)
        lig = lmin + _bits(seed, salt + "l", lmax - lmin + 1)
        if EXCLUDE_HUE[0] <= hue <= EXCLUDE_HUE[1]:
            continue                          # muddy at text sizes, see above
        accent = _hsl(hue, sat, lig)
        if contrast(accent, white) < ACCENT_MIN[audacity]:
            continue                          # too light / too washed out
        if harmony == "mono":
            soft = _mix(accent, white, 0.40)
        elif harmony == "analogous":
            soft = _mix(_hsl((hue + 24) % 360, max(sat - 15, 10), min(lig + 14, 60)),
                        white, 0.55)
        else:                                 # complementary, heavily desaturated
            drop = 55 if audacity == "sober" else 35
            soft = _mix(_hsl((hue + 180) % 360, max(sat - drop, 8),
                             min(lig + 18, 60)), white, 0.55)
        ink = _mix((INK_BASE,) * 3, accent, 0.85)
        dark = _mix((DARK_BASE,) * 3, accent, 0.92)
        # --- duotone: hue B, drawn from the SAME dial ranges (the professional
        # guardrail applies to both hues), one notch calmer than hue A so it
        # stays subordinate — a co-equal second hue is what reads as a flyer.
        second, roles = None, None
        if family in DUOTONE:
            rule, roles = DUOTONE[family][0], DUOTONE[family][1:]
            h2 = (hue + (62 if rule == "far-analogous" else 180)) % 360
            h2 = _escape_hue_veto(h2, hue)
            if h2 is None:
                continue                      # no safe rotation: re-draw
            s2 = max(smin, min(sat - 12, smax))
            # Both hues clearing 4.5:1 on WHITE says nothing about whether they
            # separate from EACH OTHER: two different hues at the same lightness
            # have the same luminance, so they print as one identical gray.
            # Measured before this floor, replaying the old `l2 = lig + 4` rule
            # over the same 1800 keys: 510 pairs (28.3%) collapsed in
            # grayscale. contrast() is luminance-only, so contrast(A, B) IS the
            # grayscale separation — walk hue B's LIGHTNESS away from hue A
            # (darker first: it also helps hue B's own contrast on white) until
            # the pair clears DUOTONE_SEP, and reject the candidate if none does.
            second = None
            for off in (4, -9, -15, -21, 11, -27, 17):
                cand = _hsl(h2, s2, max(lmin, min(lig + off, lmax)))
                if contrast(accent, cand) >= DUOTONE_SEP:
                    second, l2 = cand, max(lmin, min(lig + off, lmax))
                    break
            if second is None:
                continue                      # hue B cannot separate: re-draw
        checks = {
            "accent on white": (contrast(accent, white), ACCENT_MIN[audacity]),
            "white on accent": (contrast(white, accent), 4.5),
            "ink on white": (contrast(ink, white), 5.0),
            "dark on white": (contrast(dark, white), 4.5),
        }
        if second is not None:
            # hue B carries text (dates, keys) on white and, in color-band,
            # sits beside a hue-A fill: validate it on white like hue A.
            checks["accent2 on white"] = (contrast(second, white),
                                          ACCENT_MIN[audacity])
            # the invariant, not just the search: the pair must stay two inks
            # once the page is photocopied in black and white
            checks["accent2 vs accent (grayscale)"] = (contrast(accent, second),
                                                       DUOTONE_SEP)
        if all(v >= t for v, t in checks.values()):
            return dict(family=family, audacity=audacity, harmony=harmony,
                        seed=seed, attempts=attempt + 1,
                        hsl=(hue, sat, lig), accent=accent, soft=soft,
                        ink=ink, dark=dark, checks=checks,
                        accent2=second, hsl2=None if second is None
                        else (h2, s2, l2), roles=roles)
    raise SystemExit("no valid palette in 64 draws — widen the dial ranges")


def typst(p):
    two = []
    if p["accent2"] is not None:
        two = ['#let accent2 = rgb("%s")  // H%d S%d%% L%d%% — duotone hue B, %s'
               % (_hex(p["accent2"]), *p["hsl2"], p["roles"][1]),
               '// hue A role — %s. Each hue keeps 1-2 jobs, never more.'
               % p["roles"][0]]
    return "\n".join([
        '#let accent = rgb("%s")   // H%d S%d%% L%d%% — %s harmony, %s'
        % (_hex(p["accent"]), *p["hsl"], p["harmony"], p["audacity"]),
        *two,
        '#let soft = rgb("%s")     // decorative hairlines only, never text'
        % _hex(p["soft"]),
        '#let ink = rgb("%s")      // metadata gray, biased to the accent hue'
        % _hex(p["ink"]),
        '#let muted = ink',
        '#let dark = rgb("%s")     // body ink, barely biased' % _hex(p["dark"]),
    ])


def report(p):
    out = ["family    : %s   (harmony: %s)" % (p["family"], p["harmony"]),
           "audacity  : %s" % p["audacity"],
           "seed      : %r   (draw %d)" % (p["seed"], p["attempts"]),
           "accent    : %s   H%d S%d%% L%d%%" % (_hex(p["accent"]), *p["hsl"]),
           *(["accent2   : %s   H%d S%d%% L%d%%   (duotone — %s; hue A: %s)"
              % (_hex(p["accent2"]), *p["hsl2"], p["roles"][1], p["roles"][0])]
             if p["accent2"] is not None else []),
           "soft      : %s   (hairlines only)" % _hex(p["soft"]),
           "ink       : %s   (metadata)" % _hex(p["ink"]),
           "dark      : %s   (body)" % _hex(p["dark"]), "contrast  :"]
    for k, (v, t) in p["checks"].items():
        out.append("  %-20s %5.2f  (min %.1f) %s"
                   % (k, v, t, "OK" if v >= t else "FAIL"))
    out.append("  hue %d is outside the muddy zone %s (yellow-olive: excluded "
               "for text roles)" % (p["hsl"][0], EXCLUDE_HUE))
    return "\n".join(out)


def selftest():
    a = build("swiss-grid", "Candidate A+software")
    assert a["accent"] == build("swiss-grid", "Candidate A+software")["accent"]
    assert build("swiss-grid", "Candidate B+software")["accent"] != a["accent"]
    seen = {}
    for level in DIAL:
        for f in HARMONY:
            for i in range(50):
                p = build(f, "Candidate %02d+x" % i, level)
                for name, (v, t) in p["checks"].items():
                    assert v >= t, (f, level, name, v, t)
                h, s, l = p["hsl"]
                assert not EXCLUDE_HUE[0] <= h <= EXCLUDE_HUE[1], (f, h)
                assert DIAL[level][0][0] <= s <= DIAL[level][0][1]
                assert DIAL[level][1][0] <= l <= DIAL[level][1][1]
                seen.setdefault(level, set()).add(_hex(p["accent"]))
                # duotone: hue B exists only where a family declares it, keeps
                # inside the same dial ranges (guardrail on BOTH hues), and is
                # far enough in hue to read as a second colour.
                if f in DUOTONE:
                    h2, s2, l2 = p["hsl2"]
                    assert not any(lo <= h2 <= hi for lo, hi in HUE_B_VETO), \
                        (f, level, h2, "hue B landed in a veto zone")
                    assert DIAL[level][0][0] <= s2 <= DIAL[level][0][1]
                    assert DIAL[level][1][0] <= l2 <= DIAL[level][1][1]
                    d = abs((h2 - h + 180) % 360 - 180)
                    assert d >= 55, (f, h, h2, d)
                    assert s2 <= s, (f, "hue B must stay subordinate")
                    assert p["checks"]["accent2 on white"][0] >= \
                        ACCENT_MIN[level]
                    assert "accent2" in typst(p)
                else:
                    assert p["accent2"] is None and "accent2" not in typst(p)
    assert len(seen["sober"]) > 100, "sober range too narrow to individualise"
    # Grayscale survival of the duotone pairs, measured over 100 draws per
    # duotone family per dial level. Replaying the old l2=lig+4 rule over these
    # same keys, 510 of the 1800 (28.3%) fell below the floor; the floor makes
    # it 0 by construction, so the assertion is that NONE of them collapses.
    worst = None
    for f in DUOTONE:
        for level in DIAL:
            for i in range(100):
                p = build(f, "Gray %03d+x" % i, level)
                sep = contrast(p["accent"], p["accent2"])
                assert sep >= DUOTONE_SEP, (f, level, i, sep)
                if worst is None or sep < worst[0]:
                    worst = (sep, f, level)
    # the guardrail: sober never produces a pale or washed-out accent
    for i in range(200):
        p = build("swiss-grid", "N%03d" % i, "sober")
        assert p["hsl"][2] <= 34 and p["checks"]["accent on white"][0] >= 6.0
    draws = 50 * len(HARMONY)
    print("selftest OK — %s"
          % ", ".join("%s: %d distinct accents/%d" % (k, len(v), draws)
                      for k, v in sorted(seen.items())))
    print("  duotone grayscale separation: %d pairs checked, all ≥ %.2f "
          "(tightest %.2f on %s/%s)"
          % (len(DUOTONE) * len(DIAL) * 100, DUOTONE_SEP, worst[0],
             worst[1], worst[2]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--family")
    ap.add_argument("--seed")
    ap.add_argument("--audacity", default="sober", choices=sorted(DIAL))
    ap.add_argument("--typst", action="store_true", help="print the #let block")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.family and a.seed:
        p = build(a.family, a.seed, a.audacity)
        print(typst(p) if a.typst else report(p))
    else:
        sys.exit(__doc__)
