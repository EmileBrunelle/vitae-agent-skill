"""verify.py --selftest: check_text_clip: a word straddling a filled band, a line hidden past a short band"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable

from vitae.core.base import WordBox
from vitae.verify.layout import check_text_clip
from vitae.verify.page import FURNITURE_SCALE


def text_clip() -> None:
    """check_text_clip: a word straddling a filled band, a line hidden past a short band."""
    from PIL import Image
    # check_text_clip: a word straddling a filled band's bottom edge FAILs;
    # the same word wholly inside the band, or wholly on paper, does not.
    # A line hidden past a short band (white on white) FAILs; a word flanked
    # by hairline rules (grid(1fr, auto, 1fr) + line, 1-2pt gutter) does not.
    with tempfile.TemporaryDirectory() as td:
        def _png(draw: Callable[[Image.Image], None], name: str = "t.png") -> str:
            im = Image.new("RGB", (400, 200), (255, 255, 255))
            draw(im)
            p = os.path.join(td, name); im.save(p)
            return p

        def _word(y_word: float, x0: float = 40, x1: float = 200) -> list[WordBox]:
            return [((x0 / FURNITURE_SCALE, y_word / FURNITURE_SCALE,
                      x1 / FURNITURE_SCALE, (y_word + 14) / FURNITURE_SCALE), "linkedin.com")]

        def _ink(im: Image.Image, y: int, col: tuple[int, int, int] = (255, 255, 255),
                 x0: int = 60, x1: int = 180) -> None:   # fake glyphs
            for x in range(x0, x1, 6):
                im.paste(col, (x, y + 3, x + 3, y + 11))

        def _band(im: Image.Image) -> None:
            im.paste((60, 60, 60), (0, 0, 400, 100))   # band, bottom edge y=100

        def _at(y: int) -> str:                                    # band + visible glyphs at y
            def d(im: Image.Image) -> None:
                _band(im); _ink(im, y, (255, 255, 255) if y + 14 <= 100 else (200, 30, 30))
            return _png(d)
        assert check_text_clip(_at(92), _word(92)), "word cut by the band edge must FAIL"
        assert not check_text_clip(_at(70), _word(70)), "word inside the band must pass"
        assert not check_text_clip(_at(120), _word(120)), "word on paper must pass"
        # (a) line wholly past the band: white glyphs on white paper
        def _hidden(im: Image.Image) -> None:
            _band(im); _ink(im, 120)
        assert any("indistinguishable" in m for m in check_text_clip(_png(_hidden), _word(120))), \
            "text whose colour matches the paper must FAIL"
        # (b) word flanked by rules at mid-height, 1-2pt gutter
        for thick in (1, 2):
            def _rules(im: Image.Image, thick: int = thick) -> None:
                for x in range(60, 180, 6):
                    im.paste((0, 0, 0), (x, 105, x + 3, 113))      # dark glyphs
                im.paste((0, 0, 0), (0, 108, 37, 108 + thick))     # rule left
                im.paste((0, 0, 0), (203, 108, 400, 108 + thick))  # rule right
            assert not check_text_clip(_png(_rules), _word(100, 40, 200)), \
                f"a word flanked by {thick}px rules is not cut by a fill"
