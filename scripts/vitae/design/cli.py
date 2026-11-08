#!/usr/bin/env python3
# AGENT: do not read this file — run it. Its printed output is the instruction.
# Usage: python3 scripts/pick_design.py --name "<candidate>" --field <field> --market <market> --init <cv folder>
# (Reading it wastes context: a small model read a sibling script 3 times and never wrote the CV.)
"""Pick the design family and its secondary parameters for one candidate.

Deterministic: the same candidate always gets the same look, so the 1-page,
2-page and translated versions of one CV never drift apart. Nothing random,
nothing to remember between sessions.

Usage:
    python3 scripts/pick_design.py --name "Firstname Lastname" \
        --field software --market north-america \
        [--career early|mid|senior] [--photo] [--conservative] \
        [--audacity sober|expressive|bold] [--creative] [--offline] [--band] \
        [--emit-typ] [--init <cv folder> [--force]]
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
    --band          OPT-IN, never by default or by inference: a solid text-free
                    accent strip (8mm) down the left page edge, in the page
                    background (it never enters the text flow). Eligible: the
                    sober families with free margins; color-band, margin-index
                    and the creative families ignore it with a notice. It never
                    changes the draw.
    --offline       sandbox with no network to fetch missing fonts: filter the
                    eligible pool to families that already have at least one
                    locally installed face in every font role (display, body,
                    and mono where declared).
    --init FOLDER   the ONE-COMMAND start: prints the report, then writes
                    FOLDER/lib.typ + icons.typ (byte copies) and FOLDER/cv.typ
                    (the drawn family's worked file with the drawn palette,
                    fonts, leading, mark kit substituted). Refuses to overwrite
                    an existing cv.typ unless --force. Its printed next steps
                    are the instruction: scripts are run, never read.
    --emit-typ      print a ready-to-paste Typst PREAMBLE for the drawn recipe
                    (tokens, fonts, page/text/par) — never the devices: the
                    heading device, skills block, accent roles and header
                    composition stay in references/design/families/<name>.md, because they ARE
                    the recipe and the whole anti-clone system.

Fourteen families, and every profile draws from at least MIN_POOL = 5 of them
(so two candidates of the same profile collide at worst 1 time in 5).
Secondary parameters, drawn from the same hash: accent (plus its paired duotone
hue B where the family has one), list marker, section-label variant, the
family's own VARIANT where it declares one, and the font pair from the family's
own typographic pool. FONTS below is the single
source of truth for typography — core.md describes the registers and the
vetting checklist and does NOT repeat the lists (a second list drifts).

The recipes themselves (heading device, skills block, accent role, icons,
verified leading/spacing) live in references/design/families/<name>.md. This
script only decides WHICH one; that file says how to build it.

Only name+field enter the hash: the same person keeps their look when the CV
is retargeted, unless a flag changes which families are eligible.

The draw is deterministic: same name+field, same family, until the roster or
the pool sizes change (a family reshuffle then is accepted, not a regression).
"""
from __future__ import annotations

import argparse
import re
import sys
from typing import cast

from vitae.design.emit import emit_typ
from vitae.design.init import init_folder
from vitae.design.pick import pick
from vitae.design.report import report
from vitae.design.tables import CAREER, FAMILIES, FONTS, Audacity, band_ok
from vitae.selftest.design import selftest


def main() -> None:
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
    ap.add_argument("--band", action="store_true",
                    help="opt-in: a text-free accent band (8mm, the family's "
                         "accent) down the left page edge, drawn in the page "
                         "background. Ignored with a notice for families that "
                         "have their own band/rail/margin furniture or are "
                         "creative. Never part of the draw")
    ap.add_argument("--emit-typ", action="store_true",
                    help="print a paste-ready Typst preamble for the recipe")
    ap.add_argument("--init", metavar="FOLDER",
                    help="write a compiling starting point into FOLDER: "
                         "lib.typ + icons.typ (byte copies) and cv.typ = the "
                         "drawn family's worked file with the drawn recipe's "
                         "palette/fonts/leading substituted")
    ap.add_argument("--force", action="store_true",
                    help="with --init: overwrite an existing cv.typ")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--offline", action="store_true",
                    help="restrict the eligible pool to families whose font "
                         "roles all have at least one locally installed face")
    ap.add_argument("--no-font-check", action="store_true",
                    help="skip the local `typst fonts` availability check")
    ap.add_argument("--lang", default="en", metavar="CODE",
                    help="language of the CV, ISO 639 code (fr, en, de, fil...) — "
                         "emitted as Typst `lang:` (default en)")
    ap.add_argument("--region", metavar="CC",
                    help="optional ISO 3166-1 alpha-2 region (CA, CH...) — "
                         "emitted as Typst `region:` only when given")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if not re.fullmatch(r"[a-z]{2,3}", a.lang):
        ap.error("--lang must be a lowercase ISO 639 language code (2-3 letters) like fr, en, de "
                 "(got %r)" % a.lang)
    if a.region is not None:
        if not re.fullmatch(r"[A-Za-z]{2}", a.region):
            ap.error("--region must be two letters like CA (got %r)" % a.region)
        a.region = a.region.lower()
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
                 cast(Audacity, a.audacity), not a.no_font_check, a.creative,
                 a.offline)
        band = a.band
        if band and not band_ok(p["family"]):
            band = False
            sys.stderr.write("note: --band ignored: %s has its own band/rail/"
                             "margin furniture or is creative-register\n"
                             % p["family"])
        if a.init:
            print(report(p, a.market))
            print()
            init_folder(p, a.init, a.force, a.lang, a.region, band)
        else:
            print(emit_typ(p, a.market, a.lang, a.region, band) if a.emit_typ
                  else report(p, a.market))
    else:
        sys.exit(__doc__)
