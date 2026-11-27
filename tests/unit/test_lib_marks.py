"""lib.typ `marks()`: the four generic marks are all-or-nothing; the brand marks li/gh stand on their own data."""
import json
import shutil

import pytest
import typst
from _paths import ROOT

TEMPLATES = ROOT / "templates"
PATH = "M0 0h1v1z"
GENERIC = ("mail", "web", "phone", "pin")


def _present(tmp_path, filled):
    """Names of the marks drawn when only the icons.typ variables in `filled` (e.g. 'mail') have data."""
    shutil.copy(TEMPLATES / "lib.typ", tmp_path / "lib.typ")
    icons = (TEMPLATES / "icons.typ").read_text(encoding="utf-8")
    for name in filled:
        icons = icons.replace(f'#let {name}-body = ""', f'#let {name}-body = "{PATH}"')
    (tmp_path / "icons.typ").write_text(icons, encoding="utf-8")
    typ = tmp_path / "t.typ"
    typ.write_text('#import "lib.typ": marks\n#let mk = marks(black)\n'
                   '#metadata(mk.pairs().filter(p => p.at(1) != none).map(p => p.at(0))) <out>\n',
                   encoding="utf-8")
    compiler = typst.Compiler(str(typ))
    out = json.loads(compiler.query("<out>"))
    assert len(out) == 1
    return set(out[0]["value"])


def test_marks_all_present_when_everything_has_data(tmp_path):
    assert _present(tmp_path, GENERIC + ("li", "gh")) == set(GENERIC) | {"li", "gh"}


def test_empty_brand_marks_leave_the_generic_marks_alone(tmp_path):
    assert _present(tmp_path, GENERIC) == set(GENERIC)


def test_one_missing_brand_mark_drops_only_itself(tmp_path):
    assert _present(tmp_path, GENERIC + ("gh",)) == set(GENERIC) | {"gh"}


@pytest.mark.parametrize("missing", GENERIC)
def test_one_missing_generic_mark_drops_all_generic_marks(tmp_path, missing):
    filled = tuple(g for g in GENERIC if g != missing) + ("li", "gh")
    assert _present(tmp_path, filled) == {"li", "gh"}
