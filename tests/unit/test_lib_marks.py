"""lib.typ `marks()`: all-or-nothing on mail/web/phone/pin; an empty li/gh falls back to the web mark."""
import json
import shutil

import pytest
import typst
from _paths import ROOT

TEMPLATES = ROOT / "templates"
GENERIC = ("mail", "web", "phone", "pin")


def _marks(tmp_path, filled):
    """{name: drawn?} and, for li/gh, whether the mark equals the web mark."""
    shutil.copy(TEMPLATES / "lib.typ", tmp_path / "lib.typ")
    icons = (TEMPLATES / "icons.typ").read_text(encoding="utf-8")
    for name in filled:
        icons = icons.replace(f'#let {name}-body = ""', f'#let {name}-body = "M0 0h{len(name)}v1z"')
    (tmp_path / "icons.typ").write_text(icons, encoding="utf-8")
    typ = tmp_path / "t.typ"
    typ.write_text('#import "lib.typ": marks\n#let mk = marks(black)\n'
                   '#metadata(mk.pairs().map(p => (p.at(0), p.at(1) != none, p.at(1) == mk.web))) <out>\n',
                   encoding="utf-8")
    out = json.loads(typst.Compiler(str(typ)).query("<out>"))
    assert len(out) == 1
    return {n: (drawn, is_web) for n, drawn, is_web in out[0]["value"]}


def test_all_present_is_unchanged(tmp_path):
    m = _marks(tmp_path, (*GENERIC, "li", "gh"))
    assert all(drawn for drawn, _ in m.values())
    assert not m["li"][1] and not m["gh"][1]  # own artwork, not the globe


def test_empty_li_falls_back_to_web(tmp_path):
    m = _marks(tmp_path, (*GENERIC, "gh"))
    assert m["li"] == (True, True)
    assert m["gh"] == (True, False)


def test_empty_gh_falls_back_to_web(tmp_path):
    m = _marks(tmp_path, (*GENERIC, "li"))
    assert m["gh"] == (True, True)
    assert m["li"] == (True, False)


def test_both_brand_marks_empty_all_draw(tmp_path):
    m = _marks(tmp_path, GENERIC)
    assert all(drawn for drawn, _ in m.values())


@pytest.mark.parametrize("missing", GENERIC)
def test_one_missing_generic_mark_gives_all_none_even_with_brand_data(tmp_path, missing):
    filled = (*(g for g in GENERIC if g != missing), "li", "gh")
    m = _marks(tmp_path, filled)
    assert not any(drawn for drawn, _ in m.values())
