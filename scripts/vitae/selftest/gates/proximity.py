"""verify.py --selftest: Group proximity: raster path, rail-title pairing, x-height band"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from typing import Any, cast

from vitae.core.base import DetailRow, Mark, Word
from vitae.core.env import pdf_tool, typst_can_query
from vitae.core.level import Level
from vitae.verify.groups import (
    PROX_FAIL,
    check_group_proximity,
    measure_groups,
)
from vitae.verify.page import _xheight_band
from vitae.verify.pdf import typst_compile, word_boxes


def group_proximity() -> None:
    """Group proximity: raster path, rail-title pairing, x-height band."""
    # group proximity: the gap to the next block must be >= the largest gap inside
    # the group (role->org included). Synthetic: internal gaps 3pt; next head at
    # 149 (1pt, tight -> FAIL) or 160 (12pt -> OK).
    def _words(next_top: float) -> list[list[Word]]:
        def ln(top: float, h: float, txt: str) -> list[Word]:
            return [(50.0, top, 90.0, top + h, w) for w in txt.split()]
        return [ln(100, 10, "Role One") + ln(113, 9, "Acme Corp") + ln(125, 10, "first bullet")
                + ln(138, 10, "second bullet") + ln(next_top, 10, "Role Two") + ln(next_top + 13, 9, "Beta Inc")
                + ln(next_top + 25, 10, "only bullet") + ln(next_top + 38, 10, "last bullet")]
    _flat: Callable[[Any], list[Any]] = lambda ws: [w for part in ws for w in part]
    _hd: list[Mark] = [{"kind": "entry", "text": "Role One", "org": "Acme Corp", "page": 1, "x": 50.0, "y": 105.0},
           {"kind": "entry", "text": "Role Two", "org": "Beta Inc", "page": 1, "x": 50.0, "y": 0.0}]
    for top, want_fail in ((149, True), (160, False)):
        hh = cast(list[Mark], [dict(_hd[0]), dict(_hd[1], y=top + 5.0)])
        got = check_group_proximity("", "", heads=hh, secs=[], pages=[_flat(_words(top))])
        assert (got[0][0] == "FAIL") == want_fail, (top, got)
    # raster path: the measured gap is OPTICAL (baseline -> x-height top), so the
    # same layout with different words (no ascenders / descenders at all vs
    # full of them) must give the same ratio; a squeezed layout must still FAIL.
    if typst_can_query() and pdf_tool("pdftoppm") and pdf_tool("pdftotext"):
        def _rast(last: str, squeeze: int = 0) -> tuple[float, Level]:
            with tempfile.TemporaryDirectory() as d:
                src = ('#set page(width: 240pt, height: 170pt, margin: 20pt)\n'
                       '#set text(font: "Liberation Sans", size: 10pt)\n'
                       '#set par(leading: 0.65em, spacing: 0.65em)\n'
                       '*Role One*\n\nOrg Name\n\nFirst bullet line here\n\n' + last + '\n\n'
                       f'#v({6 - squeeze}pt)\n*Role Two*\n\nOrg Two\n\nOnly bullet\n\nLast bullet\n')
                t, f = os.path.join(d, "x.typ"), os.path.join(d, "x.pdf")
                open(t, "w", encoding="utf-8").write(src)
                assert typst_compile(t, f)[0]
                wb = word_boxes(f, with_text=True)
                assert wb is not None
                pg = [(b[0], b[1], b[2], b[3], w) for b, w in wb[0]]
                hd: list[Mark] = [{"kind": "entry", "text": txt, "org": "", "page": 1, "x": w[0], "y": w[1]}
                      for txt, w in (("Role One", next(w for w in pg if w[4] == "One")),
                                     ("Role Two", next(w for w in pg if w[4] == "Two")))]
                det: list[DetailRow] = []
                got = check_group_proximity(t, f, heads=hd, secs=[], pages=[pg], detail=det)
                return [r for r in det if r["kind"] == "group"][0]["ratio"], got[-1][0]
        _ra, _la = _rast("a sure sun runs very scarce, even once")        # x-height letters only
        _rb, _lb = _rast("Kill Hill, ghj. Thick fly (gypsy) Jeff's pig")   # ascenders and descenders
        assert abs(_ra - _rb) <= 0.1 and 0.85 <= _ra < 3, (_ra, _rb)
        assert _la == _lb == "OK", (_la, _lb)
        # the squeezed layout must land under PROX_FAIL (0.7 in verify.py, the between/internal gap ratio)
        _rt, _lt = _rast("a sure sun runs very scarce, even once", squeeze=11)
        assert _lt == "FAIL" and _rt < PROX_FAIL, (_rt, _lt)
        print(f"selftest raster path: ratio {_ra:.2f} (x-height words) vs {_rb:.2f} (ascender words); squeezed {_rt:.2f} FAILs")
    else:
        print("selftest raster path SKIPPED (typst / pdftoppm / pdftotext not on PATH)")
    _nh = check_group_proximity("", "", heads=[], secs=[], pages=[[]])[0]
    assert _nh[0] == "WARN" and "not measured" in _nh[1], \
        "a CV without head markers is WARN (not measured), not FAIL"
    # rail-title pairing: skill row (single line) at the end of a section whose
    # next section title sits in a left rail ~7pt above the next body line.
    # Next block must be that in-column head, so the row has no sub-line (skipped),
    # instead of the rail title matching one line too low and faking a 26pt "sub-line".
    def _rail() -> tuple[list[Mark], list[Mark], list[list[Word]]]:
        def ln(x: float, top: float, h: float, txt: str) -> list[Word]:
            return [(x, top, x + 30.0, top + h, w) for w in txt.split()]
        pg = (ln(100, 100, 10, "Methodologies Agile") + ln(100, 130, 10, "Label evidence drawn")
              + ln(100, 143, 10, "Mentoring example") + ln(20, 140, 10, "Strengths"))
        hh: list[Mark] = [{"kind": "skill", "text": "Methodologies", "org": "", "page": 1, "x": 100.0, "y": 105.0},
              {"kind": "skill", "text": "Label", "org": "", "page": 1, "x": 100.0, "y": 135.0},
              {"kind": "skill", "text": "Mentoring", "org": "", "page": 1, "x": 100.0, "y": 148.0}]
        return hh, [{"text": "Strengths", "page": 1, "y": 129.0}], [pg]
    _hh, _ss, _pp = _rail()
    _rows, _sk = measure_groups(_hh, _ss, _pp)
    assert not _rows, _rows

    # x-height band: an em dash (a rule row, -1) inside the band must not cut it in two
    assert _xheight_band([5, 9, 300, 310, -1, -1, -1, 290, 280, 300, 40]) == (2, 9)
    assert _xheight_band([5, 9, 300, 310, 0, 0, 0, 290, 280, 300, 40]) == (7, 9)   # the old reading
