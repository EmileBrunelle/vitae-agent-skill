"""pick_design.py --selftest: the roster invariants, label substitution, font chain and pool-size spread."""
from __future__ import annotations

import hashlib
import os
import re
from typing import TypedDict

from vitae.design.emit import _chain, emit_typ
from vitae.design.fonts import _family_usable, _installed
from vitae.design.init import _apply_labels, init_folder
from vitae.design.pick import domain_register, pick
from vitae.design.report import report
from vitae.design.tables import CAREER, FAMILIES, FONTS, LABEL_VARIANTS, MIN_POOL, ORDER_ROLES, _idx


class _Flags(TypedDict, total=False):
    """The pick() flags the pool cases switch on."""
    photo: bool
    conservative: bool
    creative: bool

def selftest() -> None:
    # --init: starter headings are exactly the drawn labels; a drawn soft=None
    # leaves no soft-skills section behind (every family, every variant).
    _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    for _f, _d in FAMILIES.items():
        _fs = open(os.path.join(_root, "templates", "families", _f, "resume.typ"),
                   encoding="utf-8").read()
        for _role in ("profile", "skills", "soft"):
            _dl = _d["labels"][_role]
            if _dl is None:
                continue
            for _new in LABEL_VARIANTS[_role]:
                _o = _apply_labels(_fs, _d["labels"],
                                   dict(_d["labels"], **{_role: _new}), _f)
                _h = re.findall(r'^#section\("([^"]*)"', _o, re.M)
                if _new is None:
                    assert _dl not in _h, (_f, _role, _h)
                else:
                    assert _new in _h and (_new == _dl or _dl not in _h), \
                        (_f, _role, _new, _h)
    # _installed: plain name wins; "X <n>pt" variant resolves to the full
    # installed name, smallest n numerically; no false prefix matches.
    assert _installed("DM Sans", {"DM Sans", "DM Sans 9pt"}) == "DM Sans"
    assert _installed("DM Sans", {"DM Sans 14pt", "DM Sans 9pt"}) == "DM Sans 9pt"
    assert _installed("Noto Sans", {"Noto Sans Mono", "Noto Sans Display 12pt"}) is None
    assert _installed("Noto Sans", {"Noto Sans 12pt"}) == "Noto Sans 12pt"
    # _chain with a synthetic font set: every emitted name is installed,
    # including the tail; have=None keeps the full pool plus the tail.
    _pool = [("DM Sans", "GF (OFL)"), ("Sora", "GF (OFL)"),
             ("Red Hat Display", "GF · Linux: redhat-display-fonts")]
    _have = {"DM Sans 9pt", "Red Hat Display", "Noto Sans"}
    _names = re.findall(r'"([^"]+)"', _chain(_pool, ("DM Sans 9pt", "x"), "display", _have))
    assert _names and all(n in _have for n in _names), _names
    assert _names[0] == "DM Sans 9pt" and "Sora" not in _names, _names
    _nt = re.findall(r'"([^"]+)"', _chain(_pool, ("DM Sans", "x"), "display", None))
    assert _nt == ["DM Sans", "Sora", "Red Hat Display"], _nt
    _nt = re.findall(r'"([^"]+)"', _chain([("Sora", "GF")], ("Sora", "GF"), "display", None))
    assert _nt == ["Sora", "Noto Sans"], _nt
    # --offline: filters eligible families to those with >=1 installed face per
    # role (run 17 sandbox: 7/14 families installed, keyline-corporate's display
    # pool missing).
    _r17_have = {"Liberation Sans", "Noto Sans", "DejaVu Sans Mono", "P052",
                 "Cantarell", "PT Sans", "Adwaita Sans", "Adwaita Mono",
                 "URW Gothic", "Libertinus Serif"}
    assert not _family_usable("keyline-corporate", _r17_have)
    assert _family_usable("humanist-quiet", _r17_have)
    _po = pick("Candidate A", "operations", offline=True, have_fonts=_r17_have)
    assert all(_family_usable(_f, _r17_have) for _f in _po["eligible"]), _po["eligible"]
    assert "keyline-corporate" not in _po["eligible"]
    assert not _po["display_note"].startswith("NO pool member"), _po
    assert not _po["body_note"].startswith("NO pool member"), _po
    # --offline edge cases warn on stderr (fallback behaviour unchanged)
    import contextlib
    import io
    _err = io.StringIO()
    with contextlib.redirect_stderr(_err):
        _pe = pick("Candidate A", "operations", offline=True, have_fonts={"Nope"})
    assert "no family in the pool has all font roles installed" in _err.getvalue(), _err.getvalue()
    assert _pe["family"] == pick("Candidate A", "operations", have_fonts={"Nope"})["family"]
    assert "with --offline to draw" not in report(_pe, "us")
    assert "with --offline to draw" in report(pick("Candidate A", "operations", have_fonts={"Nope"}), "us")
    import tempfile
    for _off in (True, False):
        _pi = pick("Candidate A", "operations", offline=_off, have_fonts={"Nope"})
        _buf = io.StringIO()
        with tempfile.TemporaryDirectory() as _td, contextlib.redirect_stdout(_buf), \
                contextlib.redirect_stderr(io.StringIO()):
            init_folder(_pi, _td + "/cv")
        _o = _buf.getvalue()
        assert "install the face above before verifying" in _o, _o
        assert ("--offline --force" in _o) == (not _off), _o
    _err = io.StringIO()
    with contextlib.redirect_stderr(_err):
        _pn = pick("Candidate A", "operations", offline=True, check_fonts=False)
    assert "--offline is ignored with --no-font-check" in _err.getvalue(), _err.getvalue()
    assert _pn["family"] == pick("Candidate A", "operations", check_fonts=False)["family"]
    _err = io.StringIO()
    with contextlib.redirect_stderr(_err):
        pick("Candidate A", "operations", offline=True, have_fonts=_r17_have)
    assert _err.getvalue() == "", _err.getvalue()
    a = pick("Candidate A", "software", check_fonts=False)
    assert a == pick("Candidate A", "software", check_fonts=False), \
        "not deterministic"
    assert pick("Candidate A", "nursing", check_fonts=False)["key"] != a["key"]
    # default career is early -> a modern-first pool (all four modern families
    # in, then just enough of the widening tier to reach MIN_POOL)
    assert a["career"] == "early"
    assert all(FAMILIES[f]["register"] in ("modern", "neutral")
               for f in a["eligible"]), a["eligible"]
    assert all(f in a["eligible"] for f, d in FAMILIES.items()
               if d["register"] == "modern"), a["eligible"]
    # senior -> neutral + classic only
    s = pick("Candidate A", "software", career="senior", check_fonts=False)
    assert set(FAMILIES[f]["register"] for f in s["eligible"]) <= \
        {"neutral", "classic"}
    # every profile draws from at least MIN_POOL families (1-in-5 collision at
    # worst), flags applied on top; and the creative register is NEVER in the
    # pool without the unlock
    pools = {}
    cases: list[tuple[str, _Flags]] = [("plain", {}), ("photo", _Flags(photo=True)),
                      ("conservative", _Flags(conservative=True)),
                      ("photo+cons", _Flags(photo=True, conservative=True)),
                      ("creative", _Flags(creative=True)),
                      ("creative+cons", _Flags(creative=True,
                                             conservative=True))]
    for label, kw in cases:
        for c in CAREER:
            p = pick("X", "y", career=c, check_fonts=False, **kw)
            assert len(p["eligible"]) >= MIN_POOL, (c, kw, p["eligible"])
            pools["%s/%s" % (c, label)] = len(p["eligible"])
            if kw.get("photo"):
                assert all(FAMILIES[f]["photo_ok"] for f in p["eligible"])
            if kw.get("conservative"):
                assert all(FAMILIES[f]["conservative_ok"] for f in p["eligible"])
            crea = [f for f in p["eligible"]
                    if FAMILIES[f]["register"] == "creative"]
            if kw.get("creative") and not kw.get("conservative"):
                assert crea, (c, label, "unlock did not surface them")
            else:
                assert not crea, (c, label, crea)
    # field table: creative leans creative+modern and lifts the dial;
    # conservative caps it
    cg = pick("Candidate A", "graphic design", check_fonts=False)
    assert cg["domain"] == "creative" and cg["audacity"] == "expressive"
    assert [f for f in cg["eligible"]
            if FAMILIES[f]["register"] == "creative"], cg["eligible"]
    kl = pick("Candidate A", "corporate law", audacity="bold", check_fonts=False)
    assert kl["domain"] == "conservative" and kl["audacity"] == "sober"
    assert all(FAMILIES[f]["conservative_ok"] for f in kl["eligible"])
    assert domain_register("plumbing") is None
    # bold survives only when nothing caps it — and only because it was asked for
    assert pick("Candidate A", "software", audacity="bold",
                check_fonts=False)["audacity"] == "bold"
    assert a["accent"] in FAMILIES[a["family"]]["accents"]
    assert _idx("Candidate A+software", 3) == int(
        hashlib.sha256(b"Candidate A+software").hexdigest()[:8], 16) % 3
    # duotone: hue B is paired 1:1 with the accent (same index), and only the
    # five declared families have one
    for f, d in FAMILIES.items():
        if "accents2" in d:
            assert len(d["accents2"]) == len(d["accents"]), f
    for i in range(60):
        p = pick("N%02d" % i, "software", check_fonts=False)
        d = FAMILIES[p["family"]]
        if "accents2" in d:
            assert d["accents2"][d["accents"].index(p["accent"])] == p["accent2"]
        else:
            assert p["accent2"] is None
    # roster invariants: 14 families, fonts and families in lockstep, and the
    # three per-family keys present everywhere
    assert len(FAMILIES) == 14, len(FAMILIES)
    assert set(FONTS) == set(FAMILIES), set(FONTS) ^ set(FAMILIES)
    for f, d in FAMILIES.items():
        for k in ("page", "order", "spec"):
            assert k in d, (f, k)
        for k in ("margin", "body", "fill"):
            assert k in d["page"], (f, k)
        o = d["order"]
        assert set(o) <= set(ORDER_ROLES), (f, set(o) - set(ORDER_ROLES))
        assert len(set(o)) == len(o), (f, "duplicate section role")
        assert o[0] == "profile", (f, o)
        assert ("soft" in o) == (d["labels"]["soft"] is not None), (f, o)
    n_spec = sum(1 for d in FAMILIES.values() if d["spec"])
    assert n_spec == 4, n_spec        # a TRAIT, not a house style
    # a family's variant axis: drawn deterministically, always one of its own,
    # and None everywhere else (a variant on every family would be one more
    # thing all fourteen share).
    for i in range(40):
        q = pick("V%02d" % i, "software", creative=True, check_fonts=False)
        dv = FAMILIES[q["family"]]
        assert q["variant"] in dv["variants"] if "variants" in dv \
            else q["variant"] is None, (q["family"], q["variant"])
    # no display face is shared between two families (half of the identity)
    seen: dict[str, str] = {}
    for f, fp in FONTS.items():
        # 3 members is the documented pool minimum (see bold-display above);
        # `mono` is optional and only hard-edge declares one.
        assert set(fp) - {"register", "mono"} == {"display", "body"}, f
        for role in ("display", "body", "mono"):
            if role not in fp:
                continue
            assert 3 <= len(fp[role]) <= 5, (f, role)
            assert len(set(n for n, _ in fp[role])) == len(fp[role]), (f, role)
        for n, prov in fp["display"]:
            assert n not in seen, ("display face shared", n, f, seen.get(n))
            seen[n] = f
            assert prov, (f, n)
    # labels: every drawn variant stays inside the documented pools, and the
    # family default is always reachable
    triples: dict[tuple[str | None, ...], str] = {}
    for f, d in FAMILIES.items():
        for role, default in d["labels"].items():
            assert default is None or default in LABEL_VARIANTS[role], (f, role)
        # no two families ship the SAME default triple, over all fourteen:
        # three of them used to default to "Profile / Technical Skills / Core
        # Strengths", which is exactly the lexical fingerprint core.md
        # denounces
        t = tuple(d["labels"][r] for r in ("profile", "skills", "soft"))
        assert t not in triples, ("duplicate default labels", t, f, triples[t])
        triples[t] = f
    spread: dict[str, int] = {}
    for i in range(400):
        p = pick("Person %03d" % i, "software", career="mid", check_fonts=False)
        spread[p["family"]] = spread.get(p["family"], 0) + 1
        for role in ("profile", "skills", "soft"):
            assert p["labels"][role] in LABEL_VARIANTS[role], p["labels"]
    assert len(spread) >= MIN_POOL, spread
    n_var = sum(1 for d in FAMILIES.values() if "variants" in d)
    _p = pick("Lang Check", "software", career="mid", check_fonts=False)
    assert '#set text(font: bodyf' in emit_typ(_p, "unspecified")
    assert 'lang: "en"' in emit_typ(_p, "unspecified")
    assert 'lang: "fr"' in emit_typ(_p, "unspecified", "fr")
    assert 'lang: "fr", region: "ca"' in emit_typ(_p, "unspecified", "fr", "ca")
    assert "region:" not in emit_typ(_p, "unspecified", "fr")
    print("selftest OK — %d families, %d with a specialities line, "
          "%d with a variant axis, MIN_POOL=%d"
          % (len(FAMILIES), n_spec, n_var, MIN_POOL))
    print("  mid-career spread over 400 names: %s"
          % ", ".join("%s %d" % kv for kv in sorted(spread.items())))
    print("  eligible-pool size per profile:")
    for c in ("early", "mid", "senior"):
        print("    %-7s %s" % (c, "  ".join(
            "%s=%d" % (k.split("/")[1], v)
            for k, v in pools.items() if k.startswith(c + "/"))))
