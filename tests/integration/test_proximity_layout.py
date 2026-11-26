"""Group proximity end to end: the gap to the next block is measured OPTICALLY (baseline to x-height top) on the raster of
a compiled PDF, on both toolchains (typst CLI + poppler, then typst-py + pypdfium2)."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from vitae.core import env
from vitae.core.base import DetailRow, Mark
from vitae.core.level import Level
from vitae.verify.groups import PROX_FAIL, check_group_proximity
from vitae.verify.page import _xheight_band
from vitae.verify.pdf import typst_compile, word_boxes

X_HEIGHT_ONLY = "a sure sun runs very scarce, even once"
ASCENDERS_DESCENDERS = "Kill Hill, ghj. Thick fly (gypsy) Jeff's pig"

Ratio = Callable[[str, int], tuple[float, Level]]


@pytest.fixture
def ratio(toolchain: str, tmp_path: Path) -> Ratio:
    """ratio(last_line, squeeze): group ratio and level of "Role One" against "Role Two" (6pt - squeeze apart)."""
    if "Liberation Sans" not in (env.typst_fonts() or []):
        pytest.skip("Liberation Sans not visible to Typst: the ratios below are measured with it")
    def measure(last: str, squeeze: int = 0) -> tuple[float, Level]:
        src, pdf = tmp_path / "x.typ", tmp_path / "x.pdf"
        src.write_text('#set page(width: 240pt, height: 170pt, margin: 20pt)\n#set text(font: "Liberation Sans", size: 10pt)\n'
                       '#set par(leading: 0.65em, spacing: 0.65em)\n*Role One*\n\nOrg Name\n\nFirst bullet line here\n\n' + last
                       + f'\n\n#v({6 - squeeze}pt)\n*Role Two*\n\nOrg Two\n\nOnly bullet\n\nLast bullet\n', encoding="utf-8")
        assert typst_compile(str(src), str(pdf))[0]
        wb = word_boxes(str(pdf), with_text=True)
        assert wb is not None
        page = [(b[0], b[1], b[2], b[3], w) for b, w in wb[0]]
        heads: list[Mark] = [{"kind": "entry", "text": f"Role {n}", "org": "", "page": 1,
                              "x": (w := next(p for p in page if p[4] == n))[0], "y": w[1]} for n in ("One", "Two")]
        detail: list[DetailRow] = []
        out = check_group_proximity(str(src), str(pdf), heads=heads, secs=[], pages=[page], detail=detail)
        return [r for r in detail if r["kind"] == "group"][0]["ratio"], out[-1][0]
    return measure


def test_ratio_does_not_depend_on_the_glyphs_of_the_last_line(ratio: Ratio) -> None:
    flat, lv_flat = ratio(X_HEIGHT_ONLY, 0)
    tall, lv_tall = ratio(ASCENDERS_DESCENDERS, 0)
    # optical ratio ~1.7; the box gap of the same layout (no raster) would read 2.5 or more
    assert abs(flat - tall) <= 0.1 and 0.85 <= flat < 3, (flat, tall)
    assert lv_flat == lv_tall == Level.OK


def test_a_squeezed_layout_fails_below_the_threshold(ratio: Ratio) -> None:
    squeezed, level = ratio(X_HEIGHT_ONLY, 11)
    assert level == Level.FAIL and squeezed < PROX_FAIL, (squeezed, level)


@pytest.mark.parametrize("profile, band", [
    ([5, 9, 300, 310, -1, -1, -1, 290, 280, 300, 40], (2, 9)),     # a rule row (-1) inside the band does not cut it in two
    ([5, 9, 300, 310, 0, 0, 0, 290, 280, 300, 40], (7, 9)),        # a blank stretch does: the lower dense run is the band
])
def test_xheight_band_across_a_rule_row(profile: list[int], band: tuple[int, int]) -> None:
    assert _xheight_band(profile) == band
