"""verify.py --selftest: The leading and body-size WARNs"""

from __future__ import annotations

import os
import tempfile

from vitae.selftest.gates.fixtures import VERIFY_FILE
from vitae.verify.cv import (
    _body_size_warn,
    _leading_warn,
)


def document_warns() -> None:
    """The leading and body-size WARNs."""
    with tempfile.TemporaryDirectory() as _lw_d:
        _lw_f = os.path.join(_lw_d, "cv.typ")
        open(_lw_f, "w", encoding="utf-8").write("#set par(leading: 1.2em)\n")
        assert _leading_warn(_lw_f).startswith("WARN"), _leading_warn(_lw_f)
        open(_lw_f, "w", encoding="utf-8").write("#set par(spacing: 8pt, leading: 0.7em)\n")
        assert _leading_warn(_lw_f) == ""
    # Body-size WARN: fires strictly above 11pt; every shipped template is silent.
    with tempfile.TemporaryDirectory() as _bs_d:
        _bs_f = os.path.join(_bs_d, "cv.typ")
        for _bz, _bwant in ((10.5, False), (11, False), (12, True)):
            open(_bs_f, "w", encoding="utf-8").write("#set text(font: \"x\", size: %gpt, lang: \"en\")\n" % _bz)
            assert bool(_body_size_warn(_bs_f)) == _bwant, (_bz, _body_size_warn(_bs_f))
        assert "padded with type size" in _body_size_warn(_bs_f) and "12pt" in _body_size_warn(_bs_f)
        open(_bs_f, "w", encoding="utf-8").write("#let h(b) = [\n#set text(size: 14pt)\n b]\n#set text(size: 10.5pt)\n")
        assert _body_size_warn(_bs_f) == ""
        open(_bs_f, "w", encoding="utf-8").write("#set par(leading: 0.6em)\n")
        assert _body_size_warn(_bs_f) == ""
    _bsz_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(VERIFY_FILE))), "templates")
    # Not a synthetic case: every shipped template (lib.typ and icons.typ are libraries, not CVs) must
    # stay silent, the premise of BODY_SIZE_WARN ("shipped templates: 10.5pt, margin-index and letter 11pt").
    for _bsr, _bsd, _bsfs in os.walk(_bsz_root):
        for _bsn in _bsfs:
            if _bsn.endswith(".typ") and _bsn not in ("lib.typ", "icons.typ"):
                assert _body_size_warn(os.path.join(_bsr, _bsn)) == "", os.path.join(_bsr, _bsn)


def leading_warn() -> None:
    """Leading WARN: fires strictly above 1.00em, silent at the shipped maximum."""
    # Leading WARN: fires strictly above 1.00em, silent at the shipped maximum.
    with tempfile.TemporaryDirectory() as _lw:
        _lwf = os.path.join(_lw, "cv.typ")
        for _lv, _lwant in ((0.96, False), (1.00, False), (1.09, True), (1.10, True)):
            open(_lwf, "w", encoding="utf-8").write(
                '#set par(leading: %.2fem, spacing: 1.2em)\n' % _lv)
            _lm = _leading_warn(_lwf)
            assert bool(_lm) == _lwant, (_lv, _lm)
        assert "DOUBLE-SPACED" in _lm and "1.100em" in _lm, _lm
        # Tuples are (leading, list spacing, expect WARN) around LEADING_RATIO_WARN (1.95, strictly above fires):
        # 1.0/0.5 is the real run (ratio 2.00) that read double-spaced; 0.85/0.45 computes to 1.89, the value
        # verify.py records as the highest shipped template.
        # Relative check: leading / explicit list spacing, strictly above 1.95.
        for _rl, _rs, _rwant in ((0.942, 0.45, True), (0.90, 0.45, True), (1.0, 0.5, True), (0.85, 0.45, False), (0.839, 0.45, False),
                                 (0.942, 0.55, False), (0.9, 0.5, False)):
            open(_lwf, "w", encoding="utf-8").write(
                '#set par(leading: %.3fem, spacing: 1.0em)\n#set list(\n  indent: 10pt,\n'
                '  spacing: %.2fem)\n' % (_rl, _rs))
            _lm = _leading_warn(_lwf)
            assert bool(_lm) == _rwant, (_rl, _rs, _lm)
        open(_lwf, "w", encoding="utf-8").write('#set par(leading: 0.942em)\n#set list(spacing: 0.45em)\n')
        _lm = _leading_warn(_lwf)
        assert _lm.startswith("WARN") and "DOUBLE-SPACED" in _lm and "ratio 2.09" in _lm, _lm
        open(_lwf, "w", encoding="utf-8").write('#set par(leading: 0.942em)\n#set list(indent: 10pt)\n')
        assert _leading_warn(_lwf) == ""      # no explicit list spacing: unknown, silent
        open(_lwf, "w", encoding="utf-8").write(
            '#set par(leading: 0.9em)\n#set list(spacing: 0.4em)\n#set list(spacing: auto)\n')
        assert _leading_warn(_lwf) == ""      # a later non-numeric spacing resets it: silent
        open(_lwf, "w", encoding="utf-8").write(
            '#set par(leading: 0.9em)\n#set list(marker: box(spacing: 0.1em)[•])\n')
        assert _leading_warn(_lwf) == ""      # nested spacing: is not the list's own
        open(_lwf, "w", encoding="utf-8").write('#set par(leading: 1.1em)\n#set list(spacing: 0.3em)\n')
        _lm = _leading_warn(_lwf)
        assert _lm.startswith("WARN") and "ratio" not in _lm and "1.100em" in _lm, _lm   # absolute wins
