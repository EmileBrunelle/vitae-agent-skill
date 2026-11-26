"""_drawn_fill: the family banner is the authority for the fill target, the editable header only a witness."""
import pytest
from vitae.design.tables import FAMILIES
from vitae.verify.source import _drawn_fill

FAM = next(iter(FAMILIES))
LO, HI = (int(x) for x in FAMILIES[FAM]["page"]["fill"].split("-"))
BANNER = f"// FAMILY: {FAM}\n"


@pytest.mark.parametrize("body, target, warns", [
    (f"// vitae: pages=1 fill={LO}-{HI}\n{BANNER}", (LO, HI), 0),
    (BANNER, (LO, HI), 1),                                              # no header: WARN
    (f"// vitae: pages=1 fill=50-60\n{BANNER}", (LO, HI), 1),           # disagreeing header: the table wins, WARN
    (f"{BANNER}\n\n\n// vitae: pages=1 fill=50-60\n", (LO, HI), 1),     # header past line 3 counts as absent
    ("// vitae: pages=1 fill=91-93\n", (91, 93), 0),                    # no family known: the header, line 1 only
    ("// vitae: pages=1\n", None, 0),
    ("\n// vitae: pages=1 fill=91-93\n", None, 0),
])
def test_drawn_fill_target(tmp_path, body, target, warns):
    f = tmp_path / "cv.typ"
    f.write_text(body, encoding="utf-8")
    got, w = _drawn_fill(str(f))
    assert got == target and len(w) == warns
    assert all(str(LO) in x and str(HI) in x for x in w)
