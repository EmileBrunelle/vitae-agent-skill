"""pick_design: roster invariants, the draw (determinism, pools, flags) and the font helpers."""
import re

import pytest
from _paths import ROOT
from vitae.design.emit import _chain
from vitae.design.fonts import _family_usable, _installed
from vitae.design.init import _apply_labels
from vitae.design.pick import pick
from vitae.design.tables import CAREER, FAMILIES, FONTS, LABEL_VARIANTS, MIN_POOL, ORDER_ROLES


def draw(name="Candidate A", field="software", **kw):
    return pick(name, field, check_fonts=False, **kw)


# ---------- the roster ----------

def test_fonts_and_families_are_in_lockstep_with_the_required_keys():
    assert len(FAMILIES) == 14 and set(FONTS) == set(FAMILIES)
    for f, d in FAMILIES.items():
        assert {"page", "order", "spec"} <= set(d) and {"margin", "body", "fill"} <= set(d["page"]), f
        o = d["order"]
        assert set(o) <= set(ORDER_ROLES) and len(set(o)) == len(o) and o[0] == "profile", (f, o)
        if "accents2" in d:
            assert len(d["accents2"]) == len(d["accents"]), f


def test_no_display_face_is_shared_and_pools_are_well_formed():
    seen: dict[str, str] = {}
    for f, fp in FONTS.items():
        assert set(fp) - {"register", "mono"} == {"display", "body"}, f
        for role in ("display", "body", "mono"):
            pool = fp.get(role)
            assert pool is None or (3 <= len(pool) <= 5 and len({n for n, _ in pool}) == len(pool)), (f, role)
        for n, prov in fp["display"]:
            assert n not in seen and prov, ("display face shared", n, f, seen.get(n))
            seen[n] = f


def test_default_label_pairs_stay_individual():
    """The default (profile, skills) pair is a lexical fingerprint: >= 11 distinct pairs over the 14 families,
    none shared by more than three."""
    pairs: dict[tuple[str, str], list[str]] = {}
    for f, d in FAMILIES.items():
        for role, default in d["labels"].items():
            assert default in LABEL_VARIANTS[role], (f, role)
        pairs.setdefault((d["labels"]["profile"], d["labels"]["skills"]), []).append(f)
    assert len(pairs) >= 11, pairs
    assert max(map(len, pairs.values())) <= 3, pairs


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_starter_headings_are_exactly_the_drawn_labels(family):
    d = FAMILIES[family]
    src = (ROOT / "templates" / "families" / family / "resume.typ").read_text(encoding="utf-8")
    for role in ("profile", "skills"):
        for new in LABEL_VARIANTS[role]:
            out = _apply_labels(src, d["labels"], dict(d["labels"], **{role: new}), family)
            heads = re.findall(r'^#section\("([^"]*)"', out, re.MULTILINE)
            assert new in heads and (new == d["labels"][role] or d["labels"][role] not in heads), (role, new, heads)


# ---------- the draw ----------

def test_draw_is_deterministic_and_depends_on_the_field():
    a = draw()
    assert a == draw() and draw(field="nursing")["key"] != a["key"]
    assert a["accent"] in FAMILIES[a["family"]]["accents"]


@pytest.mark.parametrize("flags", [{}, {"photo": True}, {"conservative": True}, {"photo": True, "conservative": True},
                                   {"creative": True}, {"creative": True, "conservative": True}], ids=str)
@pytest.mark.parametrize("career", CAREER)
def test_pool_size_flags_and_creative_unlock(career, flags):
    elig = draw("X", "y", career=career, **flags)["eligible"]
    assert len(elig) >= MIN_POOL
    assert all(FAMILIES[f]["photo_ok"] for f in elig) or not flags.get("photo")
    assert all(FAMILIES[f]["conservative_ok"] for f in elig) or not flags.get("conservative")
    creative = any(FAMILIES[f]["register"] == "creative" for f in elig)
    assert creative == bool(flags.get("creative") and not flags.get("conservative"))


def test_career_selects_the_register_pool():
    early = draw()
    assert early["career"] == "early" and all(FAMILIES[f]["register"] in ("modern", "neutral") for f in early["eligible"])
    assert {f for f, d in FAMILIES.items() if d["register"] == "modern"} <= set(early["eligible"])
    assert {FAMILIES[f]["register"] for f in draw(career="senior")["eligible"]} <= {"neutral", "classic"}


def test_field_lifts_or_caps_the_dial():
    cg = draw(field="graphic design")
    assert cg["domain"] == "creative" and cg["audacity"] == "expressive"
    assert any(FAMILIES[f]["register"] == "creative" for f in cg["eligible"])
    kl = draw(field="corporate law", audacity="bold")
    assert kl["domain"] == "conservative" and kl["audacity"] == "sober"
    assert all(FAMILIES[f]["conservative_ok"] for f in kl["eligible"])
    assert draw(audacity="bold")["audacity"] == "bold"             # survives only when nothing caps it


def test_second_hue_and_variant_follow_the_family_declaration():
    for i in range(60):
        p = draw("N%02d" % i, creative=True)
        d = FAMILIES[p["family"]]
        want2 = d["accents2"][d["accents"].index(p["accent"])] if "accents2" in d else None
        assert p["accent2"] == want2
        assert (p["variant"] in d["variants"]) if "variants" in d else p["variant"] is None


def test_names_spread_over_the_pool_with_labels_from_the_variants():
    spread = set()
    for i in range(200):
        p = draw("Person %03d" % i, career="mid")
        spread.add(p["family"])
        assert all(p["labels"][r] in LABEL_VARIANTS[r] for r in ("profile", "skills"))
    assert len(spread) >= MIN_POOL


# ---------- fonts ----------

@pytest.mark.parametrize("name, have, want", [
    ("DM Sans", {"DM Sans", "DM Sans 9pt"}, "DM Sans"),                      # the plain name wins
    ("DM Sans", {"DM Sans 14pt", "DM Sans 9pt"}, "DM Sans 9pt"),             # smallest size numerically
    ("Noto Sans", {"Noto Sans Mono", "Noto Sans Display 12pt"}, None),       # no false prefix match
    ("Noto Sans", {"Noto Sans 12pt"}, "Noto Sans 12pt"),
])
def test_installed_resolves_the_size_variant(name, have, want):
    assert _installed(name, have) == want


def test_chain_emits_only_installed_names_and_keeps_the_tail():
    pool = [("DM Sans", "GF"), ("Sora", "GF"), ("Red Hat Display", "GF · Linux: redhat-display-fonts")]
    have = {"DM Sans 9pt", "Red Hat Display", "Noto Sans"}
    names = re.findall(r'"([^"]+)"', _chain(pool, ("DM Sans 9pt", "x"), "display", have))
    assert names[0] == "DM Sans 9pt" and "Sora" not in names and set(names) <= have
    full = lambda pl, pk: re.findall(r'"([^"]+)"', _chain(pl, pk, "display", None))
    assert full(pool, ("DM Sans", "x")) == ["DM Sans", "Sora", "Red Hat Display"]
    assert full([("Sora", "GF")], ("Sora", "GF")) == ["Sora", "Noto Sans"]


def test_offline_keeps_only_families_with_every_role_installed(capsys):
    have = {"Liberation Sans", "Noto Sans", "DejaVu Sans Mono", "P052", "Cantarell", "PT Sans", "Adwaita Sans",
            "Adwaita Mono", "URW Gothic", "Libertinus Serif"}
    assert not _family_usable("keyline-corporate", have) and _family_usable("humanist-quiet", have)
    p = pick("Candidate A", "operations", offline=True, have_fonts=have)
    assert p["eligible"] and all(_family_usable(f, have) for f in p["eligible"])
    assert capsys.readouterr().err == ""
    fallback = pick("Candidate A", "operations", offline=True, have_fonts={"Nope"})
    assert "no family in the pool has all font roles installed" in capsys.readouterr().err
    assert fallback["family"] == pick("Candidate A", "operations", have_fonts={"Nope"})["family"]
    pick("Candidate A", "operations", offline=True, check_fonts=False)
    assert "--offline is ignored with --no-font-check" in capsys.readouterr().err
