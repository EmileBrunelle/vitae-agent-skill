"""verify.fonts: requested families read from the Typst source, and the tiers of classify_font_fallback."""
import pytest
from vitae.verify.fonts import _fam_key, _family_requested, classify_font_fallback, requested_families

REQ = requested_families('#let bodyf = ("Noto Sans", "Liberation Sans")\n#let dispf = bodyf\n'
                         '#set text(font: bodyf, lang: "en", weight: "bold")\n#text(font: dispf)[x]\n')


def _run(face: str, text: str):
    return [(c, face) for c in text]


OK = _run("ABCDEF+NotoSans-Regular", "Hello 1")


def test_requested_families_follow_variables_and_defaults():
    assert REQ == {"notosans", "liberationsans"}
    assert requested_families("#set text(size: 10pt)\n") >= {"libertinusserif"}
    assert requested_families('#let monof = ("Fira Mono",)\n') == {"firamono"}


@pytest.mark.parametrize("face, fams, want", [
    ("ABCDEF+NotoSans-Medium", REQ, True),
    ("NotoSansMono-Regular", REQ, False),            # Noto Sans Mono is not Noto Sans
    ("BricolageGrotesque-Regular", {"bricolagegrotesque96pt"}, True),
    ("Adwaita-Mono-Bold", {"adwaitamono"}, True),
    ("TimesNewRomanPSMT", {_fam_key("Times New Roman")}, True),
    ("EBGaramond12-Regular", {_fam_key("EB Garamond")}, True),
    ("SourceSans3VF-Upright", {_fam_key("Source Sans 3")}, True),
    ("ABCDEF+Lato-SemiCondensedBold", {_fam_key("Lato")}, True),
])
def test_family_matching_is_loose_but_not_prefix_blind(face, fams, want):
    assert _family_requested(face, fams) is want


@pytest.mark.parametrize("extra, level", [
    (_run("LibertinusSerif-Regular", "Hello"), "FAIL"),                  # Latin letters in an unrequested face
    (OK * 39 + [("→", "DejaVuSans")], "INFO"),                      # one symbol
    (OK * 39 + [("é", "DejaVuSans")], "WARN"),                      # one accent, under 5 %
    (OK * 2 + [("é", "DejaVuSans")] * 3, "FAIL"),                   # accents over 5 % of Latin letters
    (OK * 2 + _run("NotoColorEmoji", "\U0001F600✓★✉☎"), "INFO"),   # symbols never FAIL
    (OK * 2 + _run("NotoSansCJKjp-Regular", "日本語のテキスト" * 20), "WARN"),          # another script: WARN
], ids=["wrong-face-letters", "one-symbol", "one-accent", "accents-over-5pct", "emoji", "cjk"])
def test_fallback_tiers(extra, level):
    res = classify_font_fallback(OK + extra, REQ)
    assert res[0][0] == level


def test_cjk_is_not_told_to_add_latin_ext():
    assert "latin-ext" not in classify_font_fallback(OK * 3 + _run("NotoSansCJKjp-Regular", "日本語" * 20), REQ)[0][1]


def test_baseline_and_named_other_script_face_are_quiet():
    assert classify_font_fallback(OK, REQ) == []
    assert classify_font_fallback(OK + _run("Sora-Regular", "Привіт їжак єнот ґанок"), REQ | {"sora"}) == []


@pytest.mark.parametrize("src, face, text, quiet", [
    ('#set text(font: "Noto Sans")\n$O(n^2)$\n', "NewCMMath-Regular", "On", True),       # math face counts only with math
    ('#set text(font: "Noto Sans")\n', "NewCMMath-Regular", "O", False),
    ('#set text(font: "New Computer Modern")\n', "NewCM10-Regular", "Hello", True),      # NewCM10 is New Computer Modern
    ("plain", "NewCM10-Regular", "Hello", True),                                         # Typst default
    ("Hello `code` World\n", "LibertinusSerif-Regular", "Hello", True),                  # raw alone keeps the defaults
])
def test_math_and_default_faces(src, face, text, quiet):
    firsts: set[str] = set()
    req = requested_families(src, firsts)
    only = classify_font_fallback(_run(face, text), req, firsts)
    assert (only == []) is quiet, only


def test_a_later_tuple_member_warns_never_fails():
    firsts: set[str] = set()
    fams = requested_families('#set text(font: ("Caladea", "Libertinus Serif"))\n/* font: "Nope" */\n', firsts)
    assert fams == {"caladea", "libertinusserif"} and firsts == {"caladea"}
    assert classify_font_fallback(_run("LibertinusSerif-Regular", "Hello"), fams, firsts)[0][0] == "WARN"
    assert classify_font_fallback(_run("Caladea-Regular", "Hello"), fams, firsts) == []
