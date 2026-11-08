"""verify.py --selftest: Font fallback: requested families and the tiers of classify_font_fallback"""

from __future__ import annotations

from vitae.verify.fonts import _fam_key, _family_requested, classify_font_fallback, requested_families


def font_fallback() -> None:
    """Font fallback: requested families and the tiers of classify_font_fallback."""
    # font fallback: requested families come from font: args and variable chains, matching is loose
    _req = requested_families('#let bodyf = ("Noto Sans", "Liberation Sans")\n#let dispf = bodyf\n'
                              '#set text(font: bodyf, lang: "en", weight: "bold")\n#text(font: dispf)[x]\n')
    assert _req == {"notosans", "liberationsans"}, _req
    assert requested_families("#set text(size: 10pt)\n") >= {"libertinusserif"}
    assert requested_families('#let monof = ("Fira Mono",)\n') == {"firamono"}
    assert _family_requested("ABCDEF+NotoSans-Medium", _req)
    assert not _family_requested("NotoSansMono-Regular", _req), "NotoSansMono is not Noto Sans"
    assert _family_requested("BricolageGrotesque-Regular", {"bricolagegrotesque96pt"})
    assert _family_requested("Adwaita-Mono-Bold", {"adwaitamono"})
    # Font-fallback tiers (CHANGELOG, font-fallback gate): Latin letters or digits drawn in a face the
    # source never asks for FAIL (also past 5 % of the Latin letters); accented letters and punctuation
    # WARN; another script drawn in an unnamed face WARN; symbols and emoji INFO. Each assert below pins
    # one tier. `_okf` is the baseline text, drawn in the requested face.
    _okf = [(c, "ABCDEF+NotoSans-Regular") for c in "Hello 1"]
    assert classify_font_fallback(_okf, _req) == []
    _libertinus = [(c, "LibertinusSerif-Regular") for c in "Hello"]
    assert classify_font_fallback(_okf + _libertinus, _req)[0][0] == "FAIL"        # letters in the wrong face
    assert classify_font_fallback(_okf * 40 + [("\u2192", "DejaVuSans")], _req)[0][0] == "INFO"   # one symbol
    assert classify_font_fallback(_okf * 40 + [("\u00e9", "DejaVuSans")], _req)[0][0] == "WARN"   # one accent
    assert classify_font_fallback(_okf * 3 + [("\u00e9", "DejaVuSans")] * 3, _req)[0][0] == "FAIL"   # over 5 % of the Latin letters
    _sym = [(c, "NotoColorEmoji") for c in "\U0001F600\u2713\u2605\u2709\u260e"]
    assert [x[0] for x in classify_font_fallback(_okf * 3 + _sym, _req)] == ["INFO"]   # symbols never FAIL, whatever the share
    _cjk = [(c, "NotoSansCJKjp-Regular") for c in "日本語のテキスト" * 20]
    assert [x[0] for x in classify_font_fallback(_okf * 3 + _cjk, _req)] == ["WARN"]   # another script: WARN, never the latin-ext hint
    assert "latin-ext" not in classify_font_fallback(_okf * 3 + _cjk, _req)[0][1]
    assert classify_font_fallback(_okf + [(c, "Sora-Regular") for c in "Привет"], _req | {"sora"}) == []
    # Math faces count as requested only when the source has math, and NewCM10 is New Computer Modern
    # (CHANGELOG, font-fallback gate).
    _math = requested_families('#set text(font: "Noto Sans")\n$O(n^2)$\n')
    assert classify_font_fallback(_okf + [("O", "NewCMMath-Regular"), ("n", "NewCMMath-Regular")], _math) == []
    assert classify_font_fallback(_okf + [("O", "NewCMMath-Regular")], _req)[0][0] == "FAIL"     # no math in the source
    _ncm = requested_families('#set text(font: "New Computer Modern")\n')
    assert classify_font_fallback([(c, "NewCM10-Regular") for c in "Hello"], _ncm) == []
    assert classify_font_fallback([(c, "NewCM10-Regular") for c in "Hello"], requested_families("plain")) == []
    _m2: set[str] = set()
    _mr = requested_families('#set text(font: "Noto Sans")\n$O(n^2)$\n', _m2)
    assert classify_font_fallback([(c, "NewCMMath-Regular") for c in "On"], _mr, _m2) == []
    _n2: set[str] = set()
    _nr = requested_families('#set text(font: "New Computer Modern")\n', _n2)
    assert classify_font_fallback([(c, "NewCM10-Regular") for c in "Hello"], _nr, _n2) == []
    _r2: set[str] = set()
    _rr = requested_families("Hello `code` World\n", _r2)     # raw alone does not cancel the Typst defaults
    assert classify_font_fallback([(c, "LibertinusSerif-Regular") for c in "Hello"], _rr, _r2) == []
    # a bundled face that is a later member of the tuple: the first face was not used (WARN, never FAIL)
    _firsts: set[str] = set()
    _tup = requested_families('#set text(font: ("Caladea", "Libertinus Serif"))\n/* font: "Nope" */\n', _firsts)
    assert _tup == {"caladea", "libertinusserif"} and _firsts == {"caladea"}, (_tup, _firsts)
    assert classify_font_fallback([(c, "LibertinusSerif-Regular") for c in "Hello"], _tup, _firsts)[0][0] == "WARN"
    assert classify_font_fallback([(c, "Caladea-Regular") for c in "Hello"], _tup, _firsts) == []
    for _n, _f in (("TimesNewRomanPSMT", "Times New Roman"), ("EBGaramond12-Regular", "EB Garamond"),
                   ("SourceSans3VF-Upright", "Source Sans 3"), ("ABCDEF+Lato-SemiCondensedBold", "Lato")):
        assert _family_requested(_n, {_fam_key(_f)}), _n
